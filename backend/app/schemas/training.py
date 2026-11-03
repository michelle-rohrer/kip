from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

PARTICIPATION_STATUSES = {"full", "modified", "individual", "rest"}


class TrainingEntryCreate(BaseModel):
    date: date
    duration_min: int | None = Field(default=None, ge=1, le=600)
    intensity: int | None = Field(default=None, ge=1, le=10)
    session_rpe: int | None = Field(default=None, ge=0, le=10)
    session_type: str | None = Field(default=None, max_length=32)
    jump_count: int | None = Field(default=None, ge=0, le=2000)
    participation_status: str | None = Field(default=None, max_length=32)
    strength_values: dict[str, Any] | None = None

    @field_validator("participation_status")
    @classmethod
    def _known_status(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if value not in PARTICIPATION_STATUSES:
            allowed = ", ".join(sorted(PARTICIPATION_STATUSES))
            raise ValueError(f"participation_status must be one of: {allowed}")
        return value


class TrainingEntryResponse(BaseModel):
    id: int
    player_id: int
    date: date
    duration_min: int | None
    intensity: int | None
    session_rpe: int | None
    session_type: str | None
    jump_count: int | None = None
    participation_status: str | None = None
    strength_values: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)
