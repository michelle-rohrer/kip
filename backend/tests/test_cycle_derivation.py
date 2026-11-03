"""Entering only the period, and getting the rest worked out."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CycleEntry, Team, WearableConnection, WearableDaily, WearableProvider
from app.routers import auth_router, cycle_router
from app.services.auth import reset_auth_state


@pytest.fixture()
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(cycle_router)

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
    team = Team(name="Team Cycle")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    created = api_client.post(
        "/api/auth/register",
        json={
            "username": "player_cycle",
            "email": "cycle@example.com",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Cycle Player",
            "team_id": team.id,
        },
    )
    assert created.status_code == 201, created.text
    token = api_client.post(
        "/api/auth/login",
        json={"username": "player_cycle", "password": "SuperSecret123"},
    ).json()["access_token"]
    return {"id": created.json()["id"], "headers": {"Authorization": f"Bearer {token}"}}


def _mark_period(api_client: TestClient, player: dict[str, Any], day: date, flow: str = "medium"):
    return api_client.put(
        "/api/cycle/",
        headers=player["headers"],
        json={"date": day.isoformat(), "menstrual_flow": flow},
    )


def test_marking_the_period_fills_in_the_rest(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    """The whole point: she ticks "period today" and nothing else."""
    start = date(2026, 10, 1)
    for offset in range(4):
        assert _mark_period(api_client, player, start + timedelta(days=offset)).status_code == 200

    first = api_client.get("/api/cycle/", headers=player["headers"]).json()[-1]
    assert first["cycle_day"] == 1
    assert first["phase"] == "menstruation"

    # A day with no period at all, twelve days in.
    later = api_client.put(
        "/api/cycle/",
        headers=player["headers"],
        json={"date": date(2026, 10, 12).isoformat(), "menstrual_flow": "none"},
    )
    assert later.status_code == 200, later.text
    assert later.json()["cycle_day"] == 12
    assert later.json()["phase"] == "follicular"
    assert later.json()["cycle_length"] == 28


def test_her_own_numbers_are_never_overwritten(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    """A derivation is a guess; what she typed is a statement."""
    for offset in range(3):
        _mark_period(api_client, player, date(2026, 10, 1) + timedelta(days=offset))

    res = api_client.put(
        "/api/cycle/",
        headers=player["headers"],
        json={
            "date": date(2026, 10, 12).isoformat(),
            "menstrual_flow": "none",
            "cycle_day": 40,
            "phase": "luteal",
            "cycle_length": 35,
        },
    )
    assert res.status_code == 200
    assert res.json()["cycle_day"] == 40
    assert res.json()["phase"] == "luteal"
    assert res.json()["cycle_length"] == 35


def test_the_length_follows_her_own_rhythm(api_client: TestClient, player: dict[str, Any]) -> None:
    for start in (date(2026, 8, 1), date(2026, 8, 27), date(2026, 9, 22)):
        for offset in range(4):
            _mark_period(api_client, player, start + timedelta(days=offset))

    res = api_client.put(
        "/api/cycle/",
        headers=player["headers"],
        json={"date": date(2026, 9, 30).isoformat(), "menstrual_flow": "none"},
    )
    # 26 days between her starts, not the textbook 28.
    assert res.json()["cycle_length"] == 26


def test_nothing_is_invented_without_a_period_on_record(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    res = api_client.put(
        "/api/cycle/",
        headers=player["headers"],
        json={"date": date(2026, 10, 12).isoformat(), "pms_score": 3},
    )
    assert res.status_code == 200
    assert res.json()["cycle_day"] is None
    assert res.json()["phase"] is None


def test_the_form_can_preview_what_it_would_save(
    api_client: TestClient, player: dict[str, Any]
) -> None:
    empty = api_client.get(
        "/api/cycle/estimate",
        headers=player["headers"],
        params={"date": date(2026, 10, 12).isoformat()},
    )
    assert empty.status_code == 200
    assert empty.json()["available"] is False

    for offset in range(4):
        _mark_period(api_client, player, date(2026, 10, 1) + timedelta(days=offset))

    preview = api_client.get(
        "/api/cycle/estimate",
        headers=player["headers"],
        params={"date": date(2026, 10, 12).isoformat()},
    ).json()
    assert preview["available"] is True
    assert preview["cycle_day"] == 12
    assert preview["phase"] == "follicular"
    assert preview["period_start"] == "2026-10-01"


def test_device_period_days_count_too(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    """A player who syncs her period from a device need not retype it."""
    db_session.add(
        WearableConnection(
            player_id=player["id"],
            provider=WearableProvider.APPLE_HEALTH,
            ingest_token_hash="x",
            sync_cycle=True,
        )
    )
    for offset in range(4):
        db_session.add(
            WearableDaily(
                player_id=player["id"],
                date=date(2026, 10, 1) + timedelta(days=offset),
                provider=WearableProvider.APPLE_HEALTH,
                menstrual_flow="medium",
            )
        )
    db_session.commit()

    res = api_client.put(
        "/api/cycle/",
        headers=player["headers"],
        json={"date": date(2026, 10, 12).isoformat(), "pms_score": 2},
    )
    assert res.json()["cycle_day"] == 12
    assert res.json()["phase"] == "follicular"


def test_her_correction_beats_the_device(
    api_client: TestClient, player: dict[str, Any], db_session: Session
) -> None:
    """She knows better than the ring - the device said nothing that day."""
    db_session.add(
        WearableDaily(
            player_id=player["id"],
            date=date(2026, 10, 5),
            provider=WearableProvider.APPLE_HEALTH,
            menstrual_flow="none",
        )
    )
    db_session.commit()
    _mark_period(api_client, player, date(2026, 10, 5), "heavy")

    stored = db_session.query(CycleEntry).filter(CycleEntry.date == date(2026, 10, 5)).one()
    assert stored.menstrual_flow == "heavy"

    preview = api_client.get(
        "/api/cycle/estimate",
        headers=player["headers"],
        params={"date": date(2026, 10, 5).isoformat()},
    ).json()
    assert preview["cycle_day"] == 1


def test_an_unknown_flow_value_is_refused(api_client: TestClient, player: dict[str, Any]) -> None:
    res = api_client.put(
        "/api/cycle/",
        headers=player["headers"],
        json={"date": date(2026, 10, 5).isoformat(), "menstrual_flow": "sehr stark"},
    )
    assert res.status_code == 422
