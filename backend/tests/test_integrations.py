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
            scope=whoop.SCOPES,
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
    assert body["sleep_hours"] == pytest.approx(6.4)
    # 73/100 becomes 7 on the app's 1-10 scale.
    assert body["sleep_quality"] == 7
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
