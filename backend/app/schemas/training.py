from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TrainingEntryCreate(BaseModel):
    date: date
    duration_min: int = Field(ge=1, le=600)
    intensity: int = Field(ge=1, le=10)
    jump_count: int | None = Field(default=None, ge=0)
    sprint_times: dict[str, Any] | None = None
    strength_values: dict[str, Any] | None = None
    match_stats: dict[str, Any] | None = None


class TrainingEntryResponse(BaseModel):
    id: int
    player_id: int
    date: date
    duration_min: int
    intensity: int
    jump_count: int | None
    sprint_times: dict[str, Any] | None
    strength_values: dict[str, Any] | None
    match_stats: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)
