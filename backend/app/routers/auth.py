from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import User, UserRole
from app.schemas import (
    AccountDeleteRequest,
    MessageResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth import (
    authenticate_user,
    change_password,
    delete_account,
    issue_tokens,
    logout_refresh_token,
    refresh_tokens,
    register_user,
)
from app.services.rate_limit import check_auth_rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> User:
    ip = request.client.host if request.client else "unknown"
    check_auth_rate_limit(action="register", key=f"{ip}:{payload.username}")
    if payload.role == UserRole.COACH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coach registration is disabled",
        )
    return register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    ip = request.client.host if request.client else "unknown"
    check_auth_rate_limit(action="login", key=f"{ip}:{payload.username}")
    user = authenticate_user(db, username=payload.username, password=payload.password)
    access_token, refresh_token = issue_tokens(db, user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    access_token, new_refresh_token = refresh_tokens(db, payload.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> MessageResponse:
    logout_refresh_token(db, payload.refresh_token)
    return MessageResponse(detail="Logged out")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/password", response_model=TokenResponse)
def change_own_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TokenResponse:
    """Change the signed-in user's password.

    Returns a fresh token pair: the change revokes every refresh session, so
    without new tokens the device that just changed the password would be the
    first one thrown out.

    Rate limited like a login - the body carries the current password, so
    repeated calls would otherwise be a way to test guesses.
    """
    ip = request.client.host if request.client else "unknown"
    check_auth_rate_limit(action="change-password", key=f"{ip}:{current_user.username}")
    change_password(
        db,
        current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    access_token, refresh_token = issue_tokens(db, current_user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    payload: AccountDeleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete the signed-in player's account and all of her data.

    Rate limited like a login: the body carries a password, so repeated calls
    would otherwise be a way to test guesses.
    """
    ip = request.client.host if request.client else "unknown"
    check_auth_rate_limit(action="delete-account", key=f"{ip}:{current_user.username}")
    delete_account(db, current_user, password=payload.password)
