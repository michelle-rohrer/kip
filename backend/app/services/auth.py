import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshSession, Team, User, UserRole
from app.schemas import UserCreate
from app.schemas.auth import PLAYER_POSITIONS

JWT_DEFAULT_SECRET = "dev-secret-change-me"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", JWT_DEFAULT_SECRET)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_jwt_secret_secure(secret: str) -> bool:
    if secret in {JWT_DEFAULT_SECRET, "change-me-in-production", "changeme", "secret"}:
        return False
    return len(secret.strip()) >= 32


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(
    *, user: User, token_type: str, expires_delta: timedelta
) -> tuple[str, str, datetime]:
    now = _now_utc()
    jti = uuid4().hex
    expires_at = now + expires_delta
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, jti, expires_at


def create_access_token(user: User) -> str:
    token, _, _ = _create_token(
        user=user,
        token_type="access",
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return token


def create_refresh_token(db: Session, user: User) -> str:
    token, jti, expires_at = _create_token(
        user=user,
        token_type="refresh",
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(RefreshSession(jti=jti, user_id=user.id, expires_at=expires_at))
    db.commit()
    return token


def decode_token(token: str, *, expected_type: str | None = None) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise credentials_exception
    if payload.get("sub") is None:
        raise credentials_exception

    return payload


def register_user(db: Session, user_in: UserCreate) -> User:
    existing_user = db.execute(
        select(User).where(User.username == user_in.username)
    ).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
        )
    if user_in.email:
        existing_email = db.execute(
            select(User).where(User.email == user_in.email)
        ).scalar_one_or_none()
        if existing_email is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )

    team_id = user_in.team_id
    if user_in.role == UserRole.PLAYER and team_id is None:
        # Only fill this in when the choice is unambiguous. Picking a team at
        # random used to drop players into a squad their coach cannot see, and
        # nothing in the app would ever point at the cause.
        teams = db.execute(select(Team)).scalars().all()
        if len(teams) == 1:
            team_id = teams[0].id

    training_uid: str | None = None
    if user_in.role == UserRole.PLAYER:
        training_uid = uuid4().hex
        if user_in.player_position and user_in.player_position not in PLAYER_POSITIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid player position",
            )

    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        team_id=team_id,
        training_uid=training_uid,
        player_position=user_in.player_position,
        name=user_in.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, username: str, password: str) -> User:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    return user


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    return create_access_token(user), create_refresh_token(db, user)


def _load_active_session(db: Session, refresh_token: str) -> tuple[RefreshSession, User]:
    payload = decode_token(refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )
    if jti is None:
        raise invalid

    session = db.execute(
        select(RefreshSession).where(RefreshSession.jti == jti)
    ).scalar_one_or_none()
    if session is None or session.revoked_at is not None:
        raise invalid

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _now_utc():
        raise invalid

    user = db.get(User, session.user_id)
    if user is None:
        raise invalid
    return session, user


def _purge_expired_sessions(db: Session) -> None:
    db.query(RefreshSession).filter(RefreshSession.expires_at < _now_utc()).delete(
        synchronize_session=False
    )


def refresh_tokens(db: Session, refresh_token: str) -> tuple[str, str]:
    session, user = _load_active_session(db, refresh_token)

    # Rotate refresh tokens to reduce replay risk.
    session.revoked_at = _now_utc()
    _purge_expired_sessions(db)
    db.commit()
    return issue_tokens(db, user)


def logout_refresh_token(db: Session, refresh_token: str) -> None:
    session, _ = _load_active_session(db, refresh_token)
    session.revoked_at = _now_utc()
    db.commit()


def change_password(db: Session, user: User, *, current_password: str, new_password: str) -> None:
    """Set a new password and sign every session out, including this one.

    Changing a password is how somebody reacts to a phone left in a changing
    room, so every refresh session is revoked - a token that is still valid
    afterwards would make the change pointless. The caller issues a fresh pair
    for the device that made the change, so only the others are logged out.

    The current password is re-checked for the same reason: otherwise a
    borrowed access token could lock the owner out of her own account.
    """
    if not verify_password(current_password, user.password_hash):
        # 403, not 401: the session is valid, the confirmation is wrong. The
        # app reads 401 as "you have been signed out" and would bounce her to
        # the login screen instead of saying what actually went wrong.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Current password is not correct"
        )
    if verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current one",
        )

    user.password_hash = hash_password(new_password)
    db.query(RefreshSession).filter(
        RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None)
    ).update({RefreshSession.revoked_at: _now_utc()}, synchronize_session=False)
    db.commit()


def delete_account(db: Session, user: User, *, password: str) -> None:
    """Erase a player and everything she ever entered.

    Health and cycle data are special-category personal data, so "delete my
    account" has to mean exactly that - not a flag that hides the rows. The
    ORM relationships cascade to cycle, wellness, training, injury, risk,
    consent and wearable records; refresh sessions have no relationship on
    ``User`` and are removed explicitly, or the foreign key would block the
    delete.

    The password is re-checked because this is irreversible and a stolen
    access token should not be enough to wipe a season of data.
    """
    if user.role != UserRole.PLAYER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Coach accounts cannot be deleted through the app - "
                "they are managed through the server configuration."
            ),
        )
    if not verify_password(password, user.password_hash):
        # Deliberately not 401: the session is fine, the confirmation is wrong.
        # The app treats 401 as "you have been signed out" and would throw the
        # player back to the login screen instead of showing the real reason.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password is not correct")

    db.query(RefreshSession).filter(RefreshSession.user_id == user.id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()


def reset_auth_state() -> None:
    # Keep auth-related in-memory state deterministic across tests.
    from app.services.rate_limit import reset_auth_rate_limit_state

    reset_auth_rate_limit_state()
