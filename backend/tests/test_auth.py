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
