from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class WellnessEntryCreate(BaseModel):
    date: date
    sleep_hours: float | None = Field(default=None, gt=0, le=24)
    sleep_quality: int | None = Field(default=None, ge=1, le=10)
    muscle_soreness: int | None = Field(default=None, ge=1, le=10)
    mental_energy: int | None = Field(default=None, ge=1, le=10)
    stress_level: int | None = Field(default=None, ge=1, le=10)
    motivation: int | None = Field(default=None, ge=1, le=10)
    rpe_previous_day: int | None = Field(default=None, ge=1, le=10)
    free_text: str | None = None


class WellnessEntryResponse(BaseModel):
    id: int
    player_id: int
    date: date
    sleep_hours: float | None
    sleep_quality: int | None
    muscle_soreness: int | None
    mental_energy: int | None
    stress_level: int | None
    motivation: int | None
    rpe_previous_day: int | None
    free_text: str | None

    model_config = ConfigDict(from_attributes=True)
