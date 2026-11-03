"""Tests for the wearable integrations (Whoop, Oura, Apple Health)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PrivacyConsent, Team, User, UserRole, WearableDaily, WearableProvider
from app.routers import auth_router, integrations_router, training_router, wellness_router
from app.services.auth import hash_password, reset_auth_state
from app.services.crypto import decrypt_secret, encrypt_secret, hash_ingest_token
from app.services.wearables import apple_health, oura, whoop
from app.services.wearables import service as wearables
from app.services.wearables.base import (
    DailyMetrics,
    TokenBundle,
    WearableAuthError,
    WearableError,
)


@pytest.fixture()
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(wellness_router)
    app.include_router(training_router)
    app.include_router(integrations_router)

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    reset_auth_state()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    reset_auth_state()


@pytest.fixture()
def player(db_session: Session, api_client: TestClient) -> dict[str, Any]:
    team = Team(name="Team Wearable")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    created = api_client.post(
        "/api/auth/register",
        json={
            "username": "player_wear",
            "email": "wear@example.com",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Wear Player",
            "team_id": team.id,
        },
    )
    assert created.status_code == 201, created.text

    token = api_client.post(
        "/api/auth/login",
        json={"username": "player_wear", "password": "SuperSecret123"},
    ).json()["access_token"]

    return {
        "team_id": team.id,
        "id": created.json()["id"],
        "headers": {"Authorization": f"Bearer {token}"},
    }


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> Any:
        return self._payload


# ------------------------------------------------------------------- crypto


def test_token_encryption_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEARABLE_ENCRYPTION_KEY", "a-test-key-that-is-long-enough-123456")
    encrypted = encrypt_secret("super-secret-oauth-token")
    assert encrypted != "super-secret-oauth-token"
    assert decrypt_secret(encrypted) == "super-secret-oauth-token"


def test_decrypt_with_rotated_key_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEARABLE_ENCRYPTION_KEY", "first-key-first-key-first-key-123456")
    encrypted = encrypt_secret("token")
    monkeypatch.setenv("WEARABLE_ENCRYPTION_KEY", "second-key-second-key-second-key-7890")
    assert decrypt_secret(encrypted) is None


# ------------------------------------------------------------------- status


def test_status_lists_every_provider_as_disconnected(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    res = api_client.get("/api/integrations/", headers=player["headers"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert {row["provider"] for row in body} == {"whoop", "oura", "apple_health"}
    assert all(row["connected"] is False for row in body)


def test_whoop_authorize_without_credentials_is_rejected(
    api_client: TestClient, player: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("WHOOP_CLIENT_ID", raising=False)
    monkeypatch.delenv("WHOOP_CLIENT_SECRET", raising=False)
    res = api_client.post("/api/integrations/whoop/authorize", headers=player["headers"])
    assert res.status_code == 400


def test_whoop_authorize_url_contains_client_and_state(
    api_client: TestClient, player: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "client-123")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "secret-456")
    monkeypatch.setenv("API_BASE_URL", "https://api.example.com")

    res = api_client.post("/api/integrations/whoop/authorize", headers=player["headers"])
    assert res.status_code == 200, res.text
    url = res.json()["authorize_url"]
    assert "client_id=client-123" in url
    assert "state=" in url
    assert "api.example.com%2Fapi%2Fintegrations%2Fcallback%2Fwhoop" in url


def test_unknown_provider_is_a_404(api_client: TestClient, player: dict[str, Any]) -> None:
    res = api_client.post("/api/integrations/fitbit/sync", headers=player["headers"])
    assert res.status_code == 404


# ------------------------------------------------------------- apple health


def test_apple_health_ingest_stores_days(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    issued = api_client.post("/api/integrations/apple-health/token", headers=player["headers"])
    assert issued.status_code == 200, issued.text
    token = issued.json()["ingest_token"]

    today = date.today()
    pushed = api_client.post(
        "/api/integrations/apple-health/ingest",
        headers={"X-Ingest-Token": token},
        json={
            "date": today.isoformat(),
            "sleep_hours": 7.5,
            "hrv_ms": 62,
            "resting_hr": 48,
            "steps": 8200,
        },
    )
    assert pushed.status_code == 200, pushed.text
    assert pushed.json()["days_written"] == 1

    row = (
        db_session.query(WearableDaily)
        .filter(WearableDaily.player_id == player["id"], WearableDaily.date == today)
        .one()
    )
    assert row.provider is WearableProvider.APPLE_HEALTH
    assert row.sleep_hours == pytest.approx(7.5)
    assert row.hrv_ms == pytest.approx(62.0)
    assert row.steps == 8200

    listed = api_client.get("/api/integrations/daily", headers=player["headers"])
    assert listed.status_code == 200
    assert listed.json()[0]["provider"] == "apple_health"


def test_apple_health_ingest_rejects_unknown_token(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    api_client.post("/api/integrations/apple-health/token", headers=player["headers"])
    res = api_client.post(
        "/api/integrations/apple-health/ingest",
        headers={"X-Ingest-Token": "not-a-real-token"},
        json={"date": date.today().isoformat(), "sleep_hours": 7},
    )
    assert res.status_code == 401


def test_apple_health_ingest_requires_a_token(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    res = api_client.post(
        "/api/integrations/apple-health/ingest",
        json={"date": date.today().isoformat(), "sleep_hours": 7},
    )
    assert res.status_code == 401


def test_rotating_the_ingest_token_invalidates_the_old_one(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    first = api_client.post(
        "/api/integrations/apple-health/token", headers=player["headers"]
    ).json()["ingest_token"]
    api_client.post("/api/integrations/apple-health/token", headers=player["headers"])

    res = api_client.post(
        "/api/integrations/apple-health/ingest",
        headers={"X-Ingest-Token": first},
        json={"date": date.today().isoformat(), "sleep_hours": 7},
    )
    assert res.status_code == 401


def test_apple_health_ingest_rejects_an_empty_payload(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    token = api_client.post(
        "/api/integrations/apple-health/token", headers=player["headers"]
    ).json()["ingest_token"]
    res = api_client.post(
        "/api/integrations/apple-health/ingest",
        headers={"X-Ingest-Token": token},
        json={"nothing": "useful"},
    )
    assert res.status_code == 422


def test_health_auto_export_payload_is_parsed() -> None:
    days = apple_health.parse_payload(
        {
            "data": {
                "metrics": [
                    {
                        "name": "heart_rate_variability",
                        "units": "ms",
                        "data": [{"date": "2026-11-02 00:00:00 +0100", "qty": 54.25}],
                    },
                    {
                        "name": "resting_heart_rate",
                        "units": "count/min",
                        "data": [{"date": "2026-11-02 00:00:00 +0100", "qty": 47}],
                    },
                    {
                        "name": "sleep_analysis",
                        "units": "hr",
                        "data": [
                            {
                                "date": "2026-11-02 00:00:00 +0100",
                                "asleep": 7.4,
                                "inBed": 8.1,
                            }
                        ],
                    },
                    {
                        "name": "active_energy",
                        "units": "kJ",
                        "data": [{"date": "2026-11-02 00:00:00 +0100", "qty": 2092.0}],
                    },
                ]
            }
        }
    )
    assert len(days) == 1
    day = days[0]
    assert day.day == date(2026, 11, 2)
    assert day.hrv_ms == pytest.approx(54.25)
    assert day.resting_hr == pytest.approx(47.0)
    assert day.sleep_hours == pytest.approx(7.4)
    # 2092 kJ is 500 kcal - the app stores kcal.
    assert day.active_calories == pytest.approx(500.0, abs=0.5)


def test_sleep_stages_are_summed_when_asleep_is_missing() -> None:
    days = apple_health.parse_payload(
        {
            "data": {
                "metrics": [
                    {
                        "name": "sleep_analysis",
                        "data": [
                            {
                                "date": "2026-11-02",
                                "core": 4.0,
                                "deep": 1.5,
                                "rem": 1.25,
                                "awake": 0.4,
                            }
                        ],
                    }
                ]
            }
        }
    )
    assert days[0].sleep_hours == pytest.approx(6.75)


def test_workout_minutes_come_from_start_and_end() -> None:
    days = apple_health.parse_payload(
        {
            "data": {
                "workouts": [
                    {
                        "name": "Volleyball",
                        "start": "2026-11-02 19:00:00 +0100",
                        "end": "2026-11-02 20:30:00 +0100",
                    }
                ]
            }
        }
    )
    assert days[0].workout_minutes == pytest.approx(90.0)


def test_workout_duration_falls_back_to_seconds() -> None:
    days = apple_health.parse_payload(
        {"data": {"workouts": [{"date": "2026-11-02", "duration": 5400}]}}
    )
    assert days[0].workout_minutes == pytest.approx(90.0)


def test_payload_without_usable_values_raises() -> None:
    with pytest.raises(WearableError):
        apple_health.parse_payload({"date": "2026-11-02"})


def test_list_of_simple_entries_is_accepted() -> None:
    days = apple_health.parse_payload(
        [
            {"date": "2026-11-01", "sleep_hours": 7.0},
            {"date": "2026-11-02", "sleep_hours": 8.0, "steps": 9000},
        ]
    )
    assert [item.day for item in days] == [date(2026, 11, 1), date(2026, 11, 2)]
    assert days[1].steps == 9000


# --------------------------------------------------------------------- oura


def test_oura_personal_token_connects_and_syncs(
    api_client: TestClient,
    player: dict[str, Any],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/personal_info"):
            return FakeResponse({"id": "oura-user-1"})
        if url.endswith("/sleep"):
            return FakeResponse(
                {
                    "data": [
                        {
                            "day": yesterday,
                            "type": "long_sleep",
                            "total_sleep_duration": 27000,
                            "average_hrv": 58,
                            "lowest_heart_rate": 46,
                            "average_breath": 14.2,
                        }
                    ]
                }
            )
        if url.endswith("/daily_sleep"):
            return FakeResponse({"data": [{"day": yesterday, "score": 84}]})
        if url.endswith("/daily_readiness"):
            return FakeResponse({"data": [{"day": yesterday, "score": 71}]})
        if url.endswith("/daily_activity"):
            return FakeResponse(
                {"data": [{"day": yesterday, "steps": 11000, "active_calories": 620}]}
            )
        return FakeResponse({"data": []})

    monkeypatch.setattr(oura.httpx, "get", fake_get)

    res = api_client.post(
        "/api/integrations/oura/personal-token",
        headers=player["headers"],
        json={"token": "personal-access-token-value"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["connected"] is True

    row = (
        db_session.query(WearableDaily)
        .filter(
            WearableDaily.player_id == player["id"],
            WearableDaily.provider == WearableProvider.OURA,
        )
        .one()
    )
    assert row.sleep_hours == pytest.approx(7.5)
    assert row.sleep_score == 84
    assert row.readiness_score == 71
    assert row.hrv_ms == pytest.approx(58.0)
    assert row.steps == 11000


def test_oura_rejects_an_invalid_personal_token(
    api_client: TestClient, player: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        oura.httpx, "get", lambda url, **kwargs: FakeResponse({"detail": "nope"}, 401)
    )
    res = api_client.post(
        "/api/integrations/oura/personal-token",
        headers=player["headers"],
        json={"token": "wrong-token-value"},
    )
    # 409, not 401: a bad Oura token must not look like an expired VolleySync
    # session, or the app signs the player out over a copy-paste slip.
    assert res.status_code == 409


def test_oura_access_token_is_not_stored_in_plain_text(
    api_client: TestClient,
    player: dict[str, Any],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oura.httpx,
        "get",
        lambda url, **kwargs: (
            FakeResponse({"id": "oura-user-2"})
            if url.endswith("/personal_info")
            else FakeResponse({"data": []})
        ),
    )
    api_client.post(
        "/api/integrations/oura/personal-token",
        headers=player["headers"],
        json={"token": "very-secret-oura-token"},
    )
    connection = wearables.get_connection(
        db_session, player_id=player["id"], provider=WearableProvider.OURA
    )
    assert connection is not None
    assert connection.access_token is not None
    assert "very-secret-oura-token" not in connection.access_token
    assert decrypt_secret(connection.access_token) == "very-secret-oura-token"


def test_oura_naps_do_not_replace_the_main_night() -> None:
    days = oura._sleep_detail_days(
        [
            {"day": "2026-11-02", "type": "long_sleep", "total_sleep_duration": 28800},
            {"day": "2026-11-02", "type": "late_nap", "total_sleep_duration": 2700},
        ]
    )
    assert len(days) == 1
    assert days[0].sleep_hours == pytest.approx(8.0)


# -------------------------------------------------------------------- whoop


def test_whoop_sleep_is_counted_on_the_wake_up_day() -> None:
    days = whoop._sleep_days(
        [
            {
                "end": "2026-11-03T06:30:00.000Z",
                "timezone_offset": "+01:00",
                "nap": False,
                "score": {
                    "stage_summary": {
                        "total_in_bed_time_milli": 29_400_000,
                        "total_awake_time_milli": 1_800_000,
                    },
                    "sleep_performance_percentage": 88,
                    "respiratory_rate": 14.8,
                },
            }
        ]
    )
    assert len(days) == 1
    assert days[0].day == date(2026, 11, 3)
    # 29.4M ms in bed minus 1.8M ms awake is 7.666 h of sleep.
    assert days[0].sleep_hours == pytest.approx(7.67, abs=0.01)
    assert days[0].sleep_score == 88


def test_whoop_naps_are_ignored() -> None:
    assert whoop._sleep_days([{"end": "2026-11-03T13:00:00.000Z", "nap": True, "score": {}}]) == []


def test_whoop_recovery_maps_hrv_and_resting_heart_rate() -> None:
    days = whoop._recovery_days(
        [
            {
                "created_at": "2026-11-03T06:45:00.000Z",
                "score": {
                    "recovery_score": 64,
                    "hrv_rmssd_milli": 51.2,
                    "resting_heart_rate": 49,
                },
            }
        ]
    )
    assert days[0].readiness_score == 64
    assert days[0].hrv_ms == pytest.approx(51.2)
    assert days[0].resting_hr == pytest.approx(49.0)


def test_whoop_strain_converts_kilojoules_to_kcal() -> None:
    days = whoop._cycle_days(
        [
            {
                "start": "2026-11-03T04:00:00.000Z",
                "timezone_offset": "+01:00",
                "score": {"strain": 14.3, "kilojoule": 8368.0},
            }
        ]
    )
    assert days[0].strain == pytest.approx(14.3)
    assert days[0].active_calories == pytest.approx(2000.0, abs=1.0)


# ------------------------------------------------------------ sync + access


def test_sync_requires_a_connection(api_client: TestClient, player: dict[str, Any]) -> None:
    res = api_client.post("/api/integrations/whoop/sync", headers=player["headers"])
    assert res.status_code == 404


def test_disconnect_removes_the_connection_but_keeps_the_data(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    token = api_client.post(
        "/api/integrations/apple-health/token", headers=player["headers"]
    ).json()["ingest_token"]
    api_client.post(
        "/api/integrations/apple-health/ingest",
        headers={"X-Ingest-Token": token},
        json={"date": date.today().isoformat(), "sleep_hours": 7.2},
    )

    removed = api_client.delete("/api/integrations/apple-health", headers=player["headers"])
    assert removed.status_code == 204
    assert (
        wearables.get_connection(
            db_session, player_id=player["id"], provider=WearableProvider.APPLE_HEALTH
        )
        is None
    )
    assert (
        db_session.query(WearableDaily).filter(WearableDaily.player_id == player["id"]).count() == 1
    )


def test_coach_needs_consent_for_device_data(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    coach = User(
        username="coach_wear",
        email="coach_wear@example.com",
        password_hash=hash_password("SuperSecret123"),
        role=UserRole.COACH,
        name="Coach Wear",
        team_id=player["team_id"],
    )
    db_session.add(coach)
    db_session.commit()
    db_session.refresh(coach)

    coach_token = api_client.post(
        "/api/auth/login", json={"username": "coach_wear", "password": "SuperSecret123"}
    ).json()["access_token"]
    coach_headers = {"Authorization": f"Bearer {coach_token}"}

    blocked = api_client.get(f"/api/integrations/daily/{player['id']}", headers=coach_headers)
    assert blocked.status_code == 403

    db_session.add(
        PrivacyConsent(
            player_id=player["id"],
            coach_id=coach.id,
            share_wellness_data=True,
            share_cycle_data=False,
        )
    )
    db_session.commit()

    allowed = api_client.get(f"/api/integrations/daily/{player['id']}", headers=coach_headers)
    assert allowed.status_code == 200


def test_sync_all_requires_the_cron_secret(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CRON_SECRET", raising=False)
    assert api_client.post("/api/integrations/sync-all").status_code == 503

    monkeypatch.setenv("CRON_SECRET", "nightly-secret")
    assert (
        api_client.post(
            "/api/integrations/sync-all", headers={"X-Cron-Secret": "wrong"}
        ).status_code
        == 401
    )
    ok = api_client.post("/api/integrations/sync-all", headers={"X-Cron-Secret": "nightly-secret"})
    assert ok.status_code == 200
    assert ok.json()["connections"] == 0


def test_oauth_callback_stores_tokens_and_returns_to_the_app(
    api_client: TestClient,
    player: dict[str, Any],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "client-123")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "secret-456")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://app.example.com")

    monkeypatch.setattr(
        whoop,
        "exchange_code",
        lambda **kwargs: TokenBundle(
            access_token="whoop-access",
            refresh_token="whoop-refresh",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scope=whoop.scopes(),
            external_user_id="whoop-user-9",
        ),
    )
    monkeypatch.setattr(
        whoop,
        "fetch_daily",
        lambda **kwargs: [
            DailyMetrics(day=date.today(), readiness_score=66, hrv_ms=47.5, resting_hr=52.0)
        ],
    )

    state = wearables.build_state_token(player_id=player["id"], provider=WearableProvider.WHOOP)
    res = api_client.get(
        "/api/integrations/callback/whoop",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert res.status_code == 303, res.text
    assert res.headers["location"].startswith("https://app.example.com/?")
    assert "status=connected" in res.headers["location"]

    connection = wearables.get_connection(
        db_session, player_id=player["id"], provider=WearableProvider.WHOOP
    )
    assert connection is not None
    assert connection.external_user_id == "whoop-user-9"
    assert decrypt_secret(connection.access_token) == "whoop-access"
    assert decrypt_secret(connection.refresh_token) == "whoop-refresh"
    assert connection.last_sync_status == "ok"

    row = (
        db_session.query(WearableDaily)
        .filter(WearableDaily.provider == WearableProvider.WHOOP)
        .one()
    )
    assert row.readiness_score == 66


def test_oauth_callback_with_a_stale_state_does_not_connect(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    res = api_client.get(
        "/api/integrations/callback/whoop",
        params={"code": "auth-code", "state": "not-a-real-state"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "status=error" in res.headers["location"]
    assert (
        wearables.get_connection(
            db_session, player_id=player["id"], provider=WearableProvider.WHOOP
        )
        is None
    )


def test_oauth_callback_reports_a_rejected_code_as_an_error(
    api_client: TestClient,
    player: dict[str, Any],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed exchange connected nothing - it must not claim otherwise."""
    monkeypatch.setattr(
        whoop,
        "exchange_code",
        lambda **kwargs: (_ for _ in ()).throw(WearableAuthError("redirect_uri mismatch")),
    )
    state = wearables.build_state_token(player_id=player["id"], provider=WearableProvider.WHOOP)
    res = api_client.get(
        "/api/integrations/callback/whoop",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "status=error" in res.headers["location"]
    assert "connected" not in res.headers["location"]
    assert (
        wearables.get_connection(
            db_session, player_id=player["id"], provider=WearableProvider.WHOOP
        )
        is None
    )


def test_oauth_callback_keeps_tokens_when_only_the_first_sync_fails(
    api_client: TestClient,
    player: dict[str, Any],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        whoop,
        "exchange_code",
        lambda **kwargs: TokenBundle(
            access_token="whoop-access",
            refresh_token="whoop-refresh",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
    )
    monkeypatch.setattr(
        whoop,
        "fetch_daily",
        lambda **kwargs: (_ for _ in ()).throw(WearableError("Whoop rate limit reached")),
    )
    state = wearables.build_state_token(player_id=player["id"], provider=WearableProvider.WHOOP)
    res = api_client.get(
        "/api/integrations/callback/whoop",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "status=connected_with_warning" in res.headers["location"]

    connection = wearables.get_connection(
        db_session, player_id=player["id"], provider=WearableProvider.WHOOP
    )
    assert connection is not None
    assert decrypt_secret(connection.access_token) == "whoop-access"


def test_oauth_callback_reports_a_declined_consent(api_client: TestClient) -> None:
    res = api_client.get(
        "/api/integrations/callback/whoop",
        params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "status=denied" in res.headers["location"]


def test_state_token_is_bound_to_one_provider(player: dict[str, Any]) -> None:
    state = wearables.build_state_token(player_id=player["id"], provider=WearableProvider.WHOOP)
    assert wearables.read_state_token(state, provider=WearableProvider.WHOOP) == player["id"]
    with pytest.raises(HTTPException):
        wearables.read_state_token(state, provider=WearableProvider.OURA)


def test_an_expired_access_token_is_refreshed_before_syncing(
    api_client: TestClient,
    player: dict[str, Any],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHOOP_CLIENT_ID", "client-123")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "secret-456")

    connection = wearables.store_tokens(
        db_session,
        player_id=player["id"],
        provider=WearableProvider.WHOOP,
        bundle=TokenBundle(
            access_token="stale-access",
            refresh_token="good-refresh",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        ),
    )

    refreshed: list[str] = []

    def fake_refresh(refresh_token: str) -> TokenBundle:
        refreshed.append(refresh_token)
        return TokenBundle(
            access_token="fresh-access",
            refresh_token="rotated-refresh",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    used_tokens: list[str] = []

    def fake_fetch(*, access_token: str, start: date, end: date) -> list[DailyMetrics]:
        used_tokens.append(access_token)
        return [DailyMetrics(day=end, readiness_score=70)]

    monkeypatch.setattr(whoop, "refresh_access_token", fake_refresh)
    monkeypatch.setattr(whoop, "fetch_daily", fake_fetch)

    summary = wearables.sync_connection(db_session, connection, days=7)

    assert refreshed == ["good-refresh"]
    assert used_tokens == ["fresh-access"]
    assert summary.days_written == 1
    db_session.refresh(connection)
    assert decrypt_secret(connection.access_token) == "fresh-access"
    assert decrypt_secret(connection.refresh_token) == "rotated-refresh"


def test_a_failed_sync_is_recorded_on_the_connection(
    api_client: TestClient,
    player: dict[str, Any],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = wearables.store_tokens(
        db_session,
        player_id=player["id"],
        provider=WearableProvider.OURA,
        bundle=TokenBundle(access_token="pat", scope="personal-access-token"),
    )
    monkeypatch.setattr(
        oura,
        "fetch_daily",
        lambda **kwargs: (_ for _ in ()).throw(WearableError("Oura rate limit reached")),
    )

    res = api_client.post("/api/integrations/oura/sync", headers=player["headers"])
    assert res.status_code == 502
    assert "rate limit" in res.json()["detail"]

    db_session.refresh(connection)
    assert connection.last_sync_status == "failed"
    assert "rate limit" in (connection.last_error or "")

    listed = api_client.get("/api/integrations/", headers=player["headers"]).json()
    oura_row = next(row for row in listed if row["provider"] == "oura")
    assert oura_row["last_sync_status"] == "failed"


def test_revoked_access_asks_the_player_to_reconnect(
    api_client: TestClient,
    player: dict[str, Any],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wearables.store_tokens(
        db_session,
        player_id=player["id"],
        provider=WearableProvider.OURA,
        bundle=TokenBundle(access_token="pat", scope="personal-access-token"),
    )
    monkeypatch.setattr(
        oura,
        "fetch_daily",
        lambda **kwargs: (_ for _ in ()).throw(WearableAuthError("please reconnect")),
    )
    res = api_client.post("/api/integrations/oura/sync", headers=player["headers"])
    assert res.status_code == 409


def test_sync_never_erases_a_value_with_a_later_blank(
    player: dict[str, Any], db_session: Session
) -> None:
    today = date.today()
    wearables.store_days(
        db_session,
        player_id=player["id"],
        provider=WearableProvider.OURA,
        days=[DailyMetrics(day=today, sleep_hours=7.5, hrv_ms=55.0)],
    )
    # A later pull that only knows the readiness score must keep the rest.
    wearables.store_days(
        db_session,
        player_id=player["id"],
        provider=WearableProvider.OURA,
        days=[DailyMetrics(day=today, readiness_score=80)],
    )
    row = db_session.query(WearableDaily).filter(WearableDaily.player_id == player["id"]).one()
    assert row.sleep_hours == pytest.approx(7.5)
    assert row.hrv_ms == pytest.approx(55.0)
    assert row.readiness_score == 80


def test_ingest_token_hash_is_stable() -> None:
    assert hash_ingest_token("abc") == hash_ingest_token("abc")
    assert hash_ingest_token("abc") != hash_ingest_token("abd")


# ----------------------------------------------------- wellness suggestions


def test_wellness_suggestion_from_device_data(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    today = date.today()
    token = api_client.post(
        "/api/integrations/apple-health/token", headers=player["headers"]
    ).json()["ingest_token"]
    api_client.post(
        "/api/integrations/apple-health/ingest",
        headers={"X-Ingest-Token": token},
        json={
            "date": today.isoformat(),
            "sleep_hours": 6.4,
            "sleep_score": 73,
            "hrv_ms": 44,
        },
    )

    res = api_client.get(
        "/api/integrations/suggestion",
        headers=player["headers"],
        params={"date": today.isoformat()},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["wellness"]["sleep_hours"] == pytest.approx(6.4)
    # 73/100 becomes 7 on the app's 1-10 scale.
    assert body["wellness"]["sleep_quality"] == 7
    assert body["sources"] == ["apple_health"]


def test_wellness_suggestion_without_data_is_404(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    res = api_client.get("/api/integrations/suggestion", headers=player["headers"])
    assert res.status_code == 404


# ------------------------------------------------- regressions found on the way


def test_training_entry_keeps_the_participation_status(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    """The form collected this, but the schema had dropped the column."""
    res = api_client.post(
        "/api/training/",
        headers=player["headers"],
        json={
            "date": date.today().isoformat(),
            "duration_min": 90,
            "intensity": 7,
            "session_rpe": 6,
            "session_type": "team",
            "participation_status": "modified",
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["participation_status"] == "modified"

    listed = api_client.get("/api/training/", headers=player["headers"]).json()
    assert listed[0]["participation_status"] == "modified"
    assert "jump_count" not in listed[0]


def test_training_rejects_an_unknown_participation_status(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    res = api_client.post(
        "/api/training/",
        headers=player["headers"],
        json={"date": date.today().isoformat(), "participation_status": "whatever"},
    )
    assert res.status_code == 422


def test_wellness_put_overwrites_the_same_day(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    """POST answers 409 on a second entry, so a typo used to be permanent."""
    today = date.today().isoformat()
    first = api_client.put(
        "/api/wellness/",
        headers=player["headers"],
        json={"date": today, "sleep_hours": 6.0, "sleep_quality": 5},
    )
    assert first.status_code == 200, first.text

    second = api_client.put(
        "/api/wellness/",
        headers=player["headers"],
        json={"date": today, "sleep_hours": 8.0, "sleep_quality": 9},
    )
    assert second.status_code == 200, second.text
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["sleep_hours"] == pytest.approx(8.0)

    entries = api_client.get("/api/wellness/", headers=player["headers"]).json()
    assert len(entries) == 1


def test_test_accounts_stay_out_of_the_team_overview(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    """A test account must use the app fully but never skew the squad."""
    from app.bootstrap import apply_test_accounts
    from app.routers import predictions_router

    api_client.app.include_router(predictions_router)

    coach = User(
        username="coach_overview",
        email="coach_overview@example.com",
        password_hash=hash_password("SuperSecret123"),
        role=UserRole.COACH,
        name="Coach",
        team_id=player["team_id"],
    )
    db_session.add(coach)
    db_session.commit()
    coach_headers = {
        "Authorization": "Bearer "
        + api_client.post(
            "/api/auth/login",
            json={"username": "coach_overview", "password": "SuperSecret123"},
        ).json()["access_token"]
    }

    before = api_client.get("/api/predictions/team", headers=coach_headers)
    assert before.status_code == 200, before.text
    assert player["id"] in [row["player_id"] for row in before.json()]

    db_session.get(User, player["id"]).is_test_account = True
    db_session.commit()

    after = api_client.get("/api/predictions/team", headers=coach_headers)
    assert after.status_code == 200
    assert player["id"] not in [row["player_id"] for row in after.json()]

    # ...and the player herself still works exactly as before.
    assert api_client.get("/api/auth/me", headers=player["headers"]).status_code == 200
    assert api_client.get("/api/auth/me", headers=player["headers"]).json()["is_test_account"]

    # The flag is driven by the environment, so it survives a fresh database.
    import os

    os.environ["BOOTSTRAP_TEST_PLAYERS"] = ""
    apply_test_accounts(db_session)
    assert db_session.get(User, player["id"]).is_test_account is False
    os.environ["BOOTSTRAP_TEST_PLAYERS"] = "player_wear"
    apply_test_accounts(db_session)
    assert db_session.get(User, player["id"]).is_test_account is True
    del os.environ["BOOTSTRAP_TEST_PLAYERS"]


def test_test_accounts_are_excluded_from_training_data(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    from datetime import date as _date

    from app.ml.train import _build_dataset
    from app.models import WellnessEntry

    for offset in range(8):
        db_session.add(
            WellnessEntry(
                player_id=player["id"],
                date=_date(2026, 10, 1 + offset),
                sleep_hours=7.0,
                sleep_quality=6,
                muscle_soreness=5,
                mental_energy=6,
                stress_level=5,
                motivation=6,
            )
        )
    db_session.commit()

    assert not _build_dataset(db_session).empty

    db_session.get(User, player["id"]).is_test_account = True
    db_session.commit()
    assert _build_dataset(db_session).empty


# --------------------------------------------- training and cycle suggestions


def _push(api_client: TestClient, player: dict[str, Any], payload: Any) -> Any:
    token = api_client.post(
        "/api/integrations/apple-health/token", headers=player["headers"]
    ).json()["ingest_token"]
    return api_client.post(
        "/api/integrations/apple-health/ingest",
        headers={"X-Ingest-Token": token},
        json=payload,
    )


def test_a_workout_becomes_a_training_suggestion(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    today = date.today()
    assert (
        _push(
            api_client,
            player,
            {
                "data": {
                    "workouts": [
                        {
                            "name": "Volleyball",
                            "start": f"{today} 19:00:00 +0100",
                            "end": f"{today} 20:30:00 +0100",
                        }
                    ]
                }
            },
        ).status_code
        == 200
    )

    res = api_client.get(
        "/api/integrations/suggestion",
        headers=player["headers"],
        params={"date": today.isoformat()},
    )
    assert res.status_code == 200, res.text
    training = res.json()["training"]
    assert training["duration_min"] == 90
    assert training["sport"] == "Volleyball"
    assert training["session_type"] == "team"
    # Nothing measured the effort, so the app must not invent an intensity.
    assert training["intensity"] is None


def test_an_unknown_sport_does_not_pretend_to_be_a_volleyball_session(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    today = date.today()
    _push(
        api_client,
        player,
        {"date": today.isoformat(), "workout_minutes": 75, "workout_sport": "Cycling"},
    )
    training = api_client.get(
        "/api/integrations/suggestion",
        headers=player["headers"],
        params={"date": today.isoformat()},
    ).json()["training"]
    assert training["sport"] == "Cycling"
    assert training["session_type"] is None


def test_a_short_walk_is_not_a_training_suggestion(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    today = date.today()
    _push(api_client, player, {"date": today.isoformat(), "workout_minutes": 6, "steps": 900})
    res = api_client.get(
        "/api/integrations/suggestion",
        headers=player["headers"],
        params={"date": today.isoformat()},
    )
    # Steps and six minutes are not worth a single prefilled field, so the
    # whole suggestion is absent rather than an empty shell.
    assert res.status_code == 404


def test_cycle_data_is_ignored_until_the_player_allows_it(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    today = date.today()
    _push(api_client, player, {"date": today.isoformat(), "menstrual_flow": "medium"})

    row = (
        db_session.query(WearableDaily)
        .filter(WearableDaily.player_id == player["id"], WearableDaily.date == today)
        .one_or_none()
    )
    assert row is None or row.menstrual_flow is None

    status_rows = api_client.get("/api/integrations/", headers=player["headers"]).json()
    assert next(r for r in status_rows if r["provider"] == "apple_health")["sync_cycle"] is False


def test_cycle_suggestion_once_the_player_allows_it(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    today = date.today()
    api_client.post("/api/integrations/apple-health/token", headers=player["headers"])
    enabled = api_client.put(
        "/api/integrations/apple-health/cycle-sync",
        headers=player["headers"],
        json={"enabled": True},
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["sync_cycle"] is True

    start = today - timedelta(days=11)
    _push(
        api_client,
        player,
        [
            {"date": (start + timedelta(days=i)).isoformat(), "menstrual_flow": "medium"}
            for i in range(4)
        ],
    )

    res = api_client.get(
        "/api/integrations/suggestion",
        headers=player["headers"],
        params={"date": today.isoformat()},
    )
    assert res.status_code == 200, res.text
    cycle = res.json()["cycle"]
    assert cycle["cycle_day"] == 12
    assert cycle["phase"] == "follicular"
    assert cycle["cycle_length"] == 28


def test_switching_cycle_sync_off_deletes_what_was_taken(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    today = date.today()
    api_client.post("/api/integrations/apple-health/token", headers=player["headers"])
    assert (
        api_client.put(
            "/api/integrations/apple-health/cycle-sync",
            headers=player["headers"],
            json={"enabled": True},
        ).status_code
        == 200
    )
    _push(api_client, player, {"date": today.isoformat(), "menstrual_flow": "heavy"})
    assert (
        db_session.query(WearableDaily).filter(WearableDaily.menstrual_flow.is_not(None)).count()
        == 1
    )

    off = api_client.put(
        "/api/integrations/apple-health/cycle-sync",
        headers=player["headers"],
        json={"enabled": False},
    )
    assert off.status_code == 200
    assert off.json()["sync_cycle"] is False
    db_session.expire_all()
    assert (
        db_session.query(WearableDaily).filter(WearableDaily.menstrual_flow.is_not(None)).count()
        == 0
    )


def test_cycle_sync_needs_a_connected_provider(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    res = api_client.put(
        "/api/integrations/oura/cycle-sync",
        headers=player["headers"],
        json={"enabled": True},
    )
    assert res.status_code == 404


def test_strain_becomes_an_intensity(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    from app.services.wearables.service import intensity_from_strain

    assert intensity_from_strain(None) is None
    assert intensity_from_strain(0.0) == 1
    assert intensity_from_strain(10.5) == 5
    assert intensity_from_strain(21.0) == 10


def test_whoop_does_not_ask_for_scopes_it_never_uses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whoop refuses the whole authorisation when one scope is not enabled.

    Asking for "read:profile" - which no call here needs - cost a working
    connection with nothing but `invalid_scope` to show for it.
    """
    monkeypatch.delenv("WHOOP_SCOPES", raising=False)
    granted = whoop.scopes().split()
    assert "read:profile" not in granted
    assert set(granted) == {
        "read:recovery",
        "read:cycles",
        "read:sleep",
        "read:workout",
        "offline",
    }


def test_whoop_scopes_can_be_overridden_without_a_deploy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHOOP_SCOPES", "read:sleep offline")
    assert whoop.scopes() == "read:sleep offline"
    monkeypatch.setenv("WHOOP_SCOPES", "   ")
    assert "read:recovery" in whoop.scopes()


def test_a_refused_authorisation_explains_itself(
    api_client: TestClient, player: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bare code says "invalid_scope"; the hint says which scope."""
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://app.example.com")
    res = api_client.get(
        "/api/integrations/callback/whoop",
        params={
            "error": "invalid_scope",
            "error_description": "The requested scope is invalid",
            "error_hint": 'The OAuth 2.0 Client is not allowed to request scope "read:profile"',
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    location = res.headers["location"]
    assert "status=denied" in location
    assert "invalid_scope" in location
    assert "read%3Aprofile" in location or "read:profile" in location


def test_oura_needs_a_registered_application(monkeypatch: pytest.MonkeyPatch) -> None:
    """Oura stopped issuing personal tokens, so OAuth is the only way in.

    This used to report Oura as always available, which sent every new player
    to a page where she can no longer get a token.
    """
    monkeypatch.delenv("OURA_CLIENT_ID", raising=False)
    monkeypatch.delenv("OURA_CLIENT_SECRET", raising=False)
    assert oura.is_configured() is False

    monkeypatch.setenv("OURA_CLIENT_ID", "id")
    monkeypatch.setenv("OURA_CLIENT_SECRET", "secret")
    assert oura.is_configured() is True


def test_oura_does_not_ask_for_scopes_it_never_uses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Oura presents "personal" to the player as height, weight and biological
    sex. Nothing on the OAuth path reads it, so it must not be requested."""
    monkeypatch.delenv("OURA_SCOPES", raising=False)
    granted = oura.scopes().split()
    assert "session" not in granted
    assert "personal" not in granted
    assert set(granted) == {"daily", "heartrate", "workout"}


def test_oura_scopes_can_be_overridden_without_a_deploy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OURA_SCOPES", "daily workout")
    assert oura.scopes() == "daily workout"


def test_a_collection_oura_refuses_is_reported_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing scope used to mean data vanished silently, forever."""

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/workout"):
            return FakeResponse({"detail": "not found"}, 404)
        return FakeResponse({"data": []})

    monkeypatch.setattr(oura.httpx, "get", fake_get)
    skipped: list[str] = []
    oura.fetch_daily(
        access_token="token",
        start=date(2026, 11, 1),
        end=date(2026, 11, 3),
        skipped=skipped,
    )
    assert skipped == ["workout"]


def test_a_refused_cycle_collection_does_not_kill_the_whole_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact failure a player hit after switching cycle sync on.

    Oura refused only daily_cycle_phases, and the sync reported "access was
    revoked - please reconnect" while discarding sleep, readiness and
    activity that had arrived without trouble. Reconnecting could not have
    helped, because the token was never the problem.
    """
    calls: list[str] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append(url.rsplit("/", 1)[-1])
        if url.endswith("/daily_cycle_phases"):
            return FakeResponse({"detail": "forbidden"}, 403)
        if url.endswith("/daily_sleep"):
            return FakeResponse({"data": [{"day": "2026-11-02", "score": 80}]})
        return FakeResponse({"data": []})

    monkeypatch.setattr(oura.httpx, "get", fake_get)
    skipped: list[str] = []
    days = oura.fetch_daily(
        access_token="token",
        start=date(2026, 11, 1),
        end=date(2026, 11, 3),
        with_cycle=True,
        skipped=skipped,
    )
    assert "daily_cycle_phases" in calls
    assert skipped == ["daily_cycle_phases"]
    # ...and the data that did arrive is kept.
    assert [d.day for d in days] == [date(2026, 11, 2)]
    assert days[0].sleep_score == 80


def test_a_dead_token_still_asks_for_a_reconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 401 on a collection every account has is the real thing."""
    monkeypatch.setattr(
        oura.httpx, "get", lambda url, **kwargs: FakeResponse({"detail": "unauthorized"}, 401)
    )
    with pytest.raises(WearableAuthError):
        oura.fetch_daily(access_token="dead", start=date(2026, 11, 1), end=date(2026, 11, 3))


def test_whoop_distinguishes_a_missing_scope_from_a_dead_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        whoop.httpx, "get", lambda url, **kwargs: FakeResponse({"detail": "forbidden"}, 403)
    )
    with pytest.raises(WearableError) as caught:
        whoop.fetch_daily(access_token="token", start=date(2026, 11, 1), end=date(2026, 11, 3))
    assert not isinstance(caught.value, WearableAuthError)
    assert "scopes" in str(caught.value)

    monkeypatch.setattr(
        whoop.httpx, "get", lambda url, **kwargs: FakeResponse({"detail": "nope"}, 401)
    )
    with pytest.raises(WearableAuthError):
        whoop.fetch_daily(access_token="dead", start=date(2026, 11, 1), end=date(2026, 11, 3))
