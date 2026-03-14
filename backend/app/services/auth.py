import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

_revoked_refresh_jtis: set[str] = set()
_active_refresh_jtis_by_user: dict[int, set[str]] = {}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(*, user: User, token_type: str, expires_delta: timedelta) -> str:
    now = _now_utc()
    jti = uuid4().hex
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    if token_type == "refresh":
        _active_refresh_jtis_by_user.setdefault(user.id, set()).add(jti)
    return token


def create_access_token(user: User) -> str:
    return _create_token(
        user=user,
        token_type="access",
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user: User) -> str:
    return _create_token(
        user=user,
        token_type="refresh",
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


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
    existing_user = db.execute(select(User).where(User.email == user_in.email)).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        team_id=user_in.team_id,
        name=user_in.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    return create_access_token(user), create_refresh_token(user)


def refresh_tokens(db: Session, refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = int(payload["sub"])
    jti = payload.get("jti")

    if jti is None or jti in _revoked_refresh_jtis or jti not in _active_refresh_jtis_by_user.get(user_id, set()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Rotate refresh tokens to reduce replay risk.
    _revoked_refresh_jtis.add(jti)
    _active_refresh_jtis_by_user[user_id].discard(jti)
    return issue_tokens(user)


def logout_refresh_token(refresh_token: str) -> None:
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = int(payload["sub"])
    jti = payload.get("jti")
    if jti is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    _revoked_refresh_jtis.add(jti)
    _active_refresh_jtis_by_user.get(user_id, set()).discard(jti)


def reset_auth_state() -> None:
    _revoked_refresh_jtis.clear()
    _active_refresh_jtis_by_user.clear()
