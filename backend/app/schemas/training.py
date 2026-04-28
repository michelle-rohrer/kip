from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TrainingEntryCreate(BaseModel):
    date: date
    duration_min: int | None = Field(default=None, ge=1, le=600)
    intensity: int | None = Field(default=None, ge=1, le=10)
    session_rpe: int | None = Field(default=None, ge=0, le=10)
    session_type: str | None = Field(default=None, max_length=32)
    strength_values: dict[str, Any] | None = None


class TrainingEntryResponse(BaseModel):
    id: int
    player_id: int
    date: date
    duration_min: int | None
    intensity: int | None
    session_rpe: int | None
    session_type: str | None
    strength_values: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)
