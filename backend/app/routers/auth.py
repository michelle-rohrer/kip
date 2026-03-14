from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import MessageResponse, RefreshTokenRequest, TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.auth import authenticate_user, issue_tokens, logout_refresh_token, refresh_tokens, register_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    return register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, email=payload.email, password=payload.password)
    access_token, refresh_token = issue_tokens(user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    access_token, new_refresh_token = refresh_tokens(db, payload.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: RefreshTokenRequest) -> MessageResponse:
    logout_refresh_token(payload.refresh_token)
    return MessageResponse(detail="Logged out")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
