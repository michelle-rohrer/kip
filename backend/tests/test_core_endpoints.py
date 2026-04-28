from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Team, User, UserRole
from app.routers import (
    auth_router,
    cycle_router,
    injury_router,
    predictions_router,
    privacy_router,
    training_router,
    wellness_router,
)
from app.services.auth import hash_password, reset_auth_state


@pytest.fixture()
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(wellness_router)
    app.include_router(cycle_router)
    app.include_router(training_router)
    app.include_router(injury_router)
    app.include_router(privacy_router)
    app.include_router(predictions_router)

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    reset_auth_state()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_auth_state()


def _register(
    client: TestClient, username: str, email: str | None, role: str, name: str, team_id: int | None
) -> dict:
    res = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "SuperSecret123",
            "role": role,
            "name": name,
            "team_id": team_id,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def _login(client: TestClient, username: str) -> str:
    res = client.post(
        "/api/auth/login",
        json={"username": username, "password": "SuperSecret123"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def _create_coach(db_session: Session, *, username: str, name: str, team_id: int) -> User:
    coach = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=hash_password("SuperSecret123"),
        role=UserRole.COACH,
        name=name,
        team_id=team_id,
    )
    db_session.add(coach)
    db_session.commit()
    db_session.refresh(coach)
    return coach


@pytest.fixture()
def team_and_users(db_session: Session, api_client: TestClient) -> dict:
    team = Team(name="Team Alpha")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    coach = _create_coach(db_session, username="coach_alpha", name="Coach", team_id=team.id)
    player = _register(api_client, "player_alpha", "player@example.com", "player", "Player", team.id)

    coach_token = _login(api_client, "coach_alpha")
    player_token = _login(api_client, "player_alpha")

    return {
        "team_id": team.id,
        "coach_id": coach.id,
        "player_id": player["id"],
        "coach_token": coach_token,
        "player_token": player_token,
    }


def test_wellness_happy_path_and_coach_access_with_consent(
    api_client: TestClient, team_and_users: dict
) -> None:
    p = team_and_users
    headers = {"Authorization": f"Bearer {p['player_token']}"}

    create = api_client.post(
        "/api/wellness/",
        headers=headers,
        json={
            "date": "2026-03-01",
            "sleep_hours": 7.5,
            "sleep_quality": 7,
            "muscle_soreness": 4,
            "mental_energy": 6,
            "stress_level": 5,
            "motivation": 8,
            "rpe_previous_day": 6,
            "free_text": "ok",
        },
    )
    assert create.status_code == 201
    assert create.json()["player_id"] == p["player_id"]

    listed = api_client.get("/api/wellness/", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    coach_headers = {"Authorization": f"Bearer {p['coach_token']}"}
    denied = api_client.get(f"/api/wellness/{p['player_id']}", headers=coach_headers)
    assert denied.status_code == 403

    consent = api_client.put(
        "/api/privacy/consent",
        headers=headers,
        json={
            "coach_id": p["coach_id"],
            "share_cycle_data": False,
            "share_wellness_data": True,
        },
    )
    assert consent.status_code == 200

    allowed = api_client.get(f"/api/wellness/{p['player_id']}", headers=coach_headers)
    assert allowed.status_code == 200
    assert len(allowed.json()) == 1


def test_wellness_duplicate_date_conflict(api_client: TestClient, team_and_users: dict) -> None:
    p = team_and_users
    headers = {"Authorization": f"Bearer {p['player_token']}"}
    body = {
        "date": "2026-03-02",
        "sleep_hours": 8.0,
        "sleep_quality": 6,
        "muscle_soreness": 5,
        "mental_energy": 7,
        "stress_level": 4,
        "motivation": 7,
    }
    assert api_client.post("/api/wellness/", headers=headers, json=body).status_code == 201
    dup = api_client.post("/api/wellness/", headers=headers, json=body)
    assert dup.status_code == 409


def test_wellness_validation_out_of_range(api_client: TestClient, team_and_users: dict) -> None:
    p = team_and_users
    headers = {"Authorization": f"Bearer {p['player_token']}"}
    res = api_client.post(
        "/api/wellness/",
        headers=headers,
        json={
            "date": "2026-03-03",
            "sleep_hours": 30,
            "sleep_quality": 7,
            "muscle_soreness": 4,
            "mental_energy": 6,
            "stress_level": 5,
            "motivation": 8,
        },
    )
    assert res.status_code == 422


def test_wellness_coach_list_forbidden_without_player_role(
    api_client: TestClient, team_and_users: dict
) -> None:
    p = team_and_users
    coach_headers = {"Authorization": f"Bearer {p['coach_token']}"}
    res = api_client.get("/api/wellness/", headers=coach_headers)
    assert res.status_code == 403


def test_cycle_coach_requires_share_cycle(api_client: TestClient, team_and_users: dict) -> None:
    p = team_and_users
    player_headers = {"Authorization": f"Bearer {p['player_token']}"}
    coach_headers = {"Authorization": f"Bearer {p['coach_token']}"}

    create = api_client.post(
        "/api/cycle/",
        headers=player_headers,
        json={
            "date": "2026-03-10",
            "cycle_day": 5,
            "phase": "menstruation",
            "cycle_length": 28,
            "pms_score": 2,
            "cramps": True,
            "migraine": False,
            "fatigue": True,
        },
    )
    assert create.status_code == 201

    assert api_client.get(f"/api/cycle/{p['player_id']}", headers=coach_headers).status_code == 403

    api_client.put(
        "/api/privacy/consent",
        headers=player_headers,
        json={"coach_id": p["coach_id"], "share_cycle_data": True, "share_wellness_data": False},
    )

    got = api_client.get(f"/api/cycle/{p['player_id']}", headers=coach_headers)
    assert got.status_code == 200
    assert got.json()[0]["phase"] == "menstruation"


def test_training_coach_same_team(api_client: TestClient, team_and_users: dict) -> None:
    p = team_and_users
    player_headers = {"Authorization": f"Bearer {p['player_token']}"}
    coach_headers = {"Authorization": f"Bearer {p['coach_token']}"}

    assert (
        api_client.post(
            "/api/training/",
            headers=player_headers,
            json={"date": "2026-03-12", "duration_min": 90, "intensity": 7, "jump_count": 120},
        ).status_code
        == 201
    )

    team = api_client.get(f"/api/training/{p['player_id']}", headers=coach_headers)
    assert team.status_code == 200
    assert len(team.json()) == 1


def test_training_coach_different_team_forbidden(
    api_client: TestClient, db_session: Session
) -> None:
    team_a = Team(name="Team A")
    team_b = Team(name="Team B")
    db_session.add_all([team_a, team_b])
    db_session.commit()
    db_session.refresh(team_a)
    db_session.refresh(team_b)

    _create_coach(db_session, username="coach_a", name="Coach A", team_id=team_a.id)
    player_b = _register(api_client, "player_b", "player_b@example.com", "player", "Player B", team_b.id)

    player_token = _login(api_client, "player_b")
    coach_token = _login(api_client, "coach_a")

    assert (
        api_client.post(
            "/api/training/",
            headers={"Authorization": f"Bearer {player_token}"},
            json={"date": "2026-04-01", "duration_min": 60, "intensity": 6},
        ).status_code
        == 201
    )

    res = api_client.get(
        f"/api/training/{player_b['id']}",
        headers={"Authorization": f"Bearer {coach_token}"},
    )
    assert res.status_code == 403


def test_injury_player_only(api_client: TestClient, team_and_users: dict) -> None:
    p = team_and_users
    player_headers = {"Authorization": f"Bearer {p['player_token']}"}
    res = api_client.post(
        "/api/injury/",
        headers=player_headers,
        json={
            "date": "2026-03-15",
            "body_location": "knee",
            "pain_intensity": 4,
            "is_chronic": False,
            "description": "mild",
        },
    )
    assert res.status_code == 201

    coach_headers = {"Authorization": f"Bearer {p['coach_token']}"}
    assert api_client.get("/api/injury/", headers=coach_headers).status_code == 403

    listed = api_client.get("/api/injury/", headers=player_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_privacy_get_and_invalid_coach(api_client: TestClient, team_and_users: dict) -> None:
    p = team_and_users
    player_headers = {"Authorization": f"Bearer {p['player_token']}"}

    empty = api_client.get("/api/privacy/consent", headers=player_headers)
    assert empty.status_code == 200
    payload = empty.json()
    assert len(payload) == 1
    assert payload[0]["coach_id"] == p["coach_id"]
    assert payload[0]["share_cycle_data"] is False
    assert payload[0]["share_wellness_data"] is False

    bad = api_client.put(
        "/api/privacy/consent",
        headers=player_headers,
        json={"coach_id": 99999, "share_cycle_data": True, "share_wellness_data": True},
    )
    assert bad.status_code == 400


def test_privacy_upsert_updates(api_client: TestClient, team_and_users: dict) -> None:
    p = team_and_users
    player_headers = {"Authorization": f"Bearer {p['player_token']}"}

    first = api_client.put(
        "/api/privacy/consent",
        headers=player_headers,
        json={"coach_id": p["coach_id"], "share_cycle_data": True, "share_wellness_data": False},
    )
    assert first.status_code == 200
    cid = first.json()["id"]

    second = api_client.put(
        "/api/privacy/consent",
        headers=player_headers,
        json={"coach_id": p["coach_id"], "share_cycle_data": False, "share_wellness_data": True},
    )
    assert second.status_code == 200
    assert second.json()["id"] == cid
    assert second.json()["share_cycle_data"] is False
    assert second.json()["share_wellness_data"] is True


def test_predictions_player_can_read_own_prediction(
    api_client: TestClient, team_and_users: dict
) -> None:
    p = team_and_users
    player_headers = {"Authorization": f"Bearer {p['player_token']}"}
    create_wellness = api_client.post(
        "/api/wellness/",
        headers=player_headers,
        json={
            "date": "2026-04-10",
            "sleep_hours": 6.5,
            "sleep_quality": 5,
            "muscle_soreness": 7,
            "mental_energy": 4,
            "stress_level": 7,
            "motivation": 6,
            "rpe_previous_day": 7,
        },
    )
    assert create_wellness.status_code == 201

    create_training = api_client.post(
        "/api/training/",
        headers=player_headers,
        json={"date": "2026-04-10", "duration_min": 100, "intensity": 8},
    )
    assert create_training.status_code == 201

    pred = api_client.get(f"/api/predictions/{p['player_id']}", headers=player_headers)
    assert pred.status_code == 200
    payload = pred.json()
    assert payload["player_id"] == p["player_id"]
    assert 0.0 <= payload["risk_score"] <= 1.0
    assert payload["risk_level"] in {"green", "yellow", "red"}


def test_predictions_player_cannot_read_other_player(
    api_client: TestClient, db_session: Session
) -> None:
    team = Team(name="Team Pred")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    p1 = _register(api_client, "pred_p1", "pred.p1@example.com", "player", "Pred P1", team.id)
    p2 = _register(api_client, "pred_p2", "pred.p2@example.com", "player", "Pred P2", team.id)
    token1 = _login(api_client, "pred_p1")

    res = api_client.get(
        f"/api/predictions/{p2['id']}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res.status_code == 403
    assert p1["id"] != p2["id"]


def test_predictions_team_for_coach(api_client: TestClient, team_and_users: dict) -> None:
    p = team_and_users
    player_headers = {"Authorization": f"Bearer {p['player_token']}"}
    coach_headers = {"Authorization": f"Bearer {p['coach_token']}"}

    assert (
        api_client.post(
            "/api/training/",
            headers=player_headers,
            json={"date": "2026-05-01", "duration_min": 75, "intensity": 6},
        ).status_code
        == 201
    )
    assert (
        api_client.post(
            "/api/wellness/",
            headers=player_headers,
            json={
                "date": "2026-05-01",
                "sleep_hours": 7.2,
                "sleep_quality": 6,
                "muscle_soreness": 5,
                "mental_energy": 6,
                "stress_level": 4,
                "motivation": 7,
            },
        ).status_code
        == 201
    )

    res = api_client.get("/api/predictions/team", headers=coach_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1
