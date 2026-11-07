from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
USERNAME_PATTERN = r"^[A-Za-z0-9._-]{3,64}$"
PLAYER_POSITIONS = {
    "setter",
    "outside_hitter",
    "opposite",
    "middle_blocker",
    "libero",
}


class UserCreate(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    email: str | None = Field(default=None, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    team_id: int | None = None
    player_position: str | None = None
    name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str = Field(pattern=USERNAME_PATTERN)
    email: str | None = Field(default=None, pattern=EMAIL_PATTERN)
    role: UserRole
    team_id: int | None
    training_uid: str | None = None
    player_position: str | None = None
    name: str
    is_test_account: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccountDeleteRequest(BaseModel):
    """Deleting an account is irreversible, so it asks for the password again."""

    password: str = Field(min_length=1, max_length=128)


class PasswordChangeRequest(BaseModel):
    """Change the signed-in user's password.

    The current password is part of the body on purpose: an access token lying
    around on an unlocked phone should not be enough to lock the owner out of
    her own account.
    """

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    detail: str
