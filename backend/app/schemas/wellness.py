from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class WellnessEntryCreate(BaseModel):
    date: date
    sleep_hours: float = Field(gt=0, le=24)
    sleep_quality: int = Field(ge=1, le=10)
    muscle_soreness: int = Field(ge=1, le=10)
    mental_energy: int = Field(ge=1, le=10)
    stress_level: int = Field(ge=1, le=10)
    motivation: int = Field(ge=1, le=10)
    rpe_previous_day: int | None = Field(default=None, ge=1, le=10)
    free_text: str | None = None


class WellnessEntryResponse(BaseModel):
    id: int
    player_id: int
    date: date
    sleep_hours: float
    sleep_quality: int
    muscle_soreness: int
    mental_energy: int
    stress_level: int
    motivation: int
    rpe_previous_day: int | None
    free_text: str | None

    model_config = ConfigDict(from_attributes=True)
