from collections.abc import Generator
from pathlib import Path

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


# ------------------------------------------------------------ password change


def _register_and_login_full(client: TestClient, username: str) -> dict[str, str]:
    """Register a player and return her whole token pair, not just the access token."""
    created = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Password Player",
        },
    )
    assert created.status_code == 201, created.text
    tokens = client.post(
        "/api/auth/login",
        json={"username": username, "password": "SuperSecret123"},
    )
    assert tokens.status_code == 200, tokens.text
    return tokens.json()


def test_change_password_lets_the_player_sign_in_with_the_new_one(client: TestClient) -> None:
    tokens = _register_and_login_full(client, "pw_change")

    changed = client.post(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"current_password": "SuperSecret123", "new_password": "BrandNewPass456"},
    )
    assert changed.status_code == 200, changed.text

    old = client.post(
        "/api/auth/login",
        json={"username": "pw_change", "password": "SuperSecret123"},
    )
    assert old.status_code == 401

    new = client.post(
        "/api/auth/login",
        json={"username": "pw_change", "password": "BrandNewPass456"},
    )
    assert new.status_code == 200, new.text


def test_change_password_keeps_this_device_signed_in_and_drops_the_others(
    client: TestClient,
) -> None:
    """The point of the new token pair in the response.

    Changing a password revokes every refresh session. Without fresh tokens the
    device that made the change would be the first one logged out - the exact
    opposite of what she asked for.
    """
    first = _register_and_login_full(client, "pw_sessions")
    second = client.post(
        "/api/auth/login",
        json={"username": "pw_sessions", "password": "SuperSecret123"},
    ).json()

    changed = client.post(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {first['access_token']}"},
        json={"current_password": "SuperSecret123", "new_password": "BrandNewPass456"},
    )
    assert changed.status_code == 200, changed.text
    issued = changed.json()

    # The other phone cannot renew its session any more ...
    stale = client.post("/api/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert stale.status_code == 401

    # ... and neither can the refresh token this device started with.
    replaced = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replaced.status_code == 401

    # But the pair handed back by the change still works.
    alive = client.post("/api/auth/refresh", json={"refresh_token": issued["refresh_token"]})
    assert alive.status_code == 200, alive.text
    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {issued['access_token']}"},
    )
    assert me.status_code == 200


def test_change_password_rejects_a_wrong_current_password(client: TestClient) -> None:
    tokens = _register_and_login_full(client, "pw_wrong")

    refused = client.post(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"current_password": "NotMyPassword", "new_password": "BrandNewPass456"},
    )
    # 403 rather than 401 so the app keeps the session and shows the reason.
    assert refused.status_code == 403

    still_works = client.post(
        "/api/auth/login",
        json={"username": "pw_wrong", "password": "SuperSecret123"},
    )
    assert still_works.status_code == 200


def test_change_password_rejects_reusing_the_current_password(client: TestClient) -> None:
    tokens = _register_and_login_full(client, "pw_same")

    refused = client.post(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"current_password": "SuperSecret123", "new_password": "SuperSecret123"},
    )
    assert refused.status_code == 400


def test_change_password_enforces_the_minimum_length(client: TestClient) -> None:
    tokens = _register_and_login_full(client, "pw_short")

    refused = client.post(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"current_password": "SuperSecret123", "new_password": "short"},
    )
    assert refused.status_code == 422


def test_change_password_needs_authentication(client: TestClient) -> None:
    res = client.post(
        "/api/auth/password",
        json={"current_password": "SuperSecret123", "new_password": "BrandNewPass456"},
    )
    assert res.status_code == 401


def test_coach_can_change_her_own_password(client: TestClient, db_session: Session) -> None:
    """Coaches are created from environment variables and never see that password
    again - without this they would be stuck with whatever the server was given."""
    coach = User(
        username="coach_pw",
        email="coach_pw@example.com",
        password_hash=hash_password("SuperSecret123"),
        role=UserRole.COACH,
        name="Coach",
    )
    db_session.add(coach)
    db_session.commit()

    token = client.post(
        "/api/auth/login",
        json={"username": "coach_pw", "password": "SuperSecret123"},
    ).json()["access_token"]

    changed = client.post(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "SuperSecret123", "new_password": "BrandNewPass456"},
    )
    assert changed.status_code == 200, changed.text

    signed_in = client.post(
        "/api/auth/login",
        json={"username": "coach_pw", "password": "BrandNewPass456"},
    )
    assert signed_in.status_code == 200


# ------------------------------------------------- what registration accepts


def test_registration_accepts_a_one_character_username(client: TestClient) -> None:
    """Short usernames are fine - this is a 14-person team, not a public sign-up.

    A player typed "lu" and got back the raw regex. The minimum is 1 now.
    """
    created = client.post(
        "/api/auth/register",
        json={
            "username": "l",
            "email": "l@example.com",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Luana Petris",
        },
    )
    assert created.status_code == 201, created.text

    signed_in = client.post("/api/auth/login", json={"username": "l", "password": "SuperSecret123"})
    assert signed_in.status_code == 200


def test_registration_treats_an_empty_email_as_not_given(client: TestClient) -> None:
    """The schema calls email optional, so "" must not be a pattern error.

    The form sends "" for an untouched field; the API used to answer with the
    email regex, naming a box the player had deliberately left alone.
    """
    created = client.post(
        "/api/auth/register",
        json={
            "username": "no.email",
            "email": "",
            "password": "SuperSecret123",
            "role": "player",
            "name": "No Email",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["email"] is None


def test_registration_still_rejects_a_username_with_a_space(client: TestClient) -> None:
    """Relaxing the length must not quietly relax the character set too."""
    refused = client.post(
        "/api/auth/register",
        json={
            "username": "Luana Petris",
            "email": "luana@example.com",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Luana Petris",
        },
    )
    assert refused.status_code == 422
    # The app turns loc into a readable sentence, so it has to stay present.
    assert refused.json()["detail"][0]["loc"][-1] == "username"


def test_registration_rejects_an_email_without_a_domain_dot(client: TestClient) -> None:
    """Browsers pass "luana@gmx" for type=email; the API must still name the field."""
    refused = client.post(
        "/api/auth/register",
        json={
            "username": "luana.gmx",
            "email": "luana@gmx",
            "password": "SuperSecret123",
            "role": "player",
            "name": "Luana Petris",
        },
    )
    assert refused.status_code == 422
    assert refused.json()["detail"][0]["loc"][-1] == "email"


# --------------------------------------- keeping the two pattern copies in step


def test_username_pattern_survives_browser_compilation() -> None:
    """The frontend puts this same string into an input's ``pattern`` attribute.

    A browser compiles that as ``^(?:<pattern>)$`` with the ``v`` flag, where a
    bare ``-`` at the end of a character class is a syntax error - and a pattern
    that fails to compile is dropped in silence. The field then accepts
    everything while looking guarded, which is how "Test Person" reached the API
    and came back as a raw regex in a player's face.

    So the dash has to stay escaped. This test fails loudly if anyone tidies it
    away, because the browser never will.
    """
    from app.schemas.auth import EMAIL_PATTERN, USERNAME_PATTERN

    assert r"\-" in USERNAME_PATTERN, "the dash must stay escaped for the browser"
    assert "._-]" not in USERNAME_PATTERN

    # Both copies have to be the same string, or the form and the API disagree
    # about what a valid entry is - and only the API gets to say no.
    frontend = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "utils.ts").read_text(
        encoding="utf-8"
    )
    for name, pattern in (("USERNAME_PATTERN", USERNAME_PATTERN), ("EMAIL_PATTERN", EMAIL_PATTERN)):
        # TypeScript doubles every backslash inside its string literal.
        expected = f'export const {name} = "{pattern.replace(chr(92), chr(92) * 2)}";'
        assert expected in frontend, f"{name} differs between backend and frontend"
