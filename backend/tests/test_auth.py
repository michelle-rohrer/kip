from collections.abc import Generator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_role
from app.models import User, UserRole
from app.routers.auth import router as auth_router
from app.services.auth import hash_password, reset_auth_state


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/api/coach-only")
    def coach_only(_: User = Depends(require_role(UserRole.COACH))) -> dict[str, str]:
        return {"status": "ok"}

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    reset_auth_state()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_auth_state()


def test_register_and_me(client: TestClient) -> None:
    register_res = client.post(
        "/api/auth/register",
        json={
            "username": "player_one",
            "email": "player@example.com",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Player One",
        },
    )
    assert register_res.status_code == 201
    assert register_res.json()["email"] == "player@example.com"

    login_res = client.post(
        "/api/auth/login",
        json={"username": "player_one", "password": "SuperSecret123"},
    )
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Player One"


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    res = client.post(
        "/api/auth/login",
        json={"username": "missing_user", "password": "wrong-password"},
    )
    assert res.status_code == 401


def test_refresh_rotates_and_logout_invalidates_refresh_token(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={
            "username": "coach_one",
            "email": "coach@example.com",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Coach One",
        },
    )
    login_res = client.post(
        "/api/auth/login",
        json={"username": "coach_one", "password": "SuperSecret123"},
    )
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    rotated_refresh = refresh_res.json()["refresh_token"]
    assert rotated_refresh != refresh_token

    reuse_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_res.status_code == 401

    logout_res = client.post("/api/auth/logout", json={"refresh_token": rotated_refresh})
    assert logout_res.status_code == 200

    post_logout_refresh_res = client.post(
        "/api/auth/refresh", json={"refresh_token": rotated_refresh}
    )
    assert post_logout_refresh_res.status_code == 401


def test_invalid_access_token_rejected(client: TestClient) -> None:
    me_res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert me_res.status_code == 401


def test_require_role_forbidden_for_non_coach(client: TestClient, db_session: Session) -> None:
    user = User(
        username="player_two",
        email="player2@example.com",
        password_hash=hash_password("SuperSecret123"),
        role=UserRole.PLAYER,
        name="Player Two",
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post(
        "/api/auth/login",
        json={"username": "player_two", "password": "SuperSecret123"},
    )
    token = login_res.json()["access_token"]

    role_res = client.get("/api/coach-only", headers={"Authorization": f"Bearer {token}"})
    assert role_res.status_code == 403


def test_register_rejects_coach_role(client: TestClient) -> None:
    res = client.post(
        "/api/auth/register",
        json={
            "username": "blocked_coach",
            "password": "SuperSecret123",
            "role": "coach",
            "name": "Blocked Coach",
        },
    )
    assert res.status_code == 403


def _register_and_login(client: TestClient, username: str) -> str:
    created = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Delete Me",
        },
    )
    assert created.status_code == 201, created.text
    tokens = client.post(
        "/api/auth/login",
        json={"username": username, "password": "SuperSecret123"},
    )
    assert tokens.status_code == 200, tokens.text
    return tokens.json()["access_token"]


def test_delete_account_removes_the_player_and_her_data(
    client: TestClient, db_session: Session
) -> None:
    from datetime import date

    from app.models import CycleEntry, RefreshSession, WellnessEntry

    token = _register_and_login(client, "player_delete")
    headers = {"Authorization": f"Bearer {token}"}
    player_id = client.get("/api/auth/me", headers=headers).json()["id"]

    db_session.add_all(
        [
            WellnessEntry(player_id=player_id, date=date(2026, 11, 1), sleep_hours=7.0),
            CycleEntry(player_id=player_id, date=date(2026, 11, 1), cycle_day=3),
        ]
    )
    db_session.commit()

    deleted = client.request(
        "DELETE",
        "/api/auth/me",
        headers=headers,
        json={"password": "SuperSecret123"},
    )
    assert deleted.status_code == 204, deleted.text

    assert db_session.get(User, player_id) is None
    assert db_session.query(WellnessEntry).filter(WellnessEntry.player_id == player_id).count() == 0
    assert db_session.query(CycleEntry).filter(CycleEntry.player_id == player_id).count() == 0
    # Refresh sessions have no ORM relationship, so they are the one thing a
    # cascade would not have taken care of.
    assert db_session.query(RefreshSession).filter(RefreshSession.user_id == player_id).count() == 0

    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_delete_account_requires_the_right_password(
    client: TestClient, db_session: Session
) -> None:
    token = _register_and_login(client, "player_keep")
    headers = {"Authorization": f"Bearer {token}"}
    player_id = client.get("/api/auth/me", headers=headers).json()["id"]

    refused = client.request(
        "DELETE",
        "/api/auth/me",
        headers=headers,
        json={"password": "WrongPassword123"},
    )
    # 403 rather than 401 so the app keeps the session and shows the reason.
    assert refused.status_code == 403
    assert db_session.get(User, player_id) is not None


def test_delete_account_needs_authentication(client: TestClient) -> None:
    res = client.request("DELETE", "/api/auth/me", json={"password": "SuperSecret123"})
    assert res.status_code == 401


def test_coach_account_cannot_be_deleted_through_the_app(
    client: TestClient, db_session: Session
) -> None:
    coach = User(
        username="coach_delete",
        email="coach_delete@example.com",
        password_hash=hash_password("SuperSecret123"),
        role=UserRole.COACH,
        name="Coach",
    )
    db_session.add(coach)
    db_session.commit()

    token = client.post(
        "/api/auth/login",
        json={"username": "coach_delete", "password": "SuperSecret123"},
    ).json()["access_token"]

    res = client.request(
        "DELETE",
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "SuperSecret123"},
    )
    assert res.status_code == 403
    assert db_session.get(User, coach.id) is not None
