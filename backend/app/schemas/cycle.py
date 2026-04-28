from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models import CyclePhase


class CycleEntryCreate(BaseModel):
    date: date
    cycle_day: int | None = Field(default=None, ge=1, le=60)
    phase: CyclePhase | None = None
    cycle_length: int | None = Field(default=None, ge=20, le=45)
    pms_score: int | None = Field(default=None, ge=0, le=10)
    cramps: bool = False
    migraine: bool = False
    fatigue: bool = False
    contraception_type: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class CycleEntryResponse(BaseModel):
    id: int
    player_id: int
    date: date
    cycle_day: int | None
    phase: CyclePhase | None
    cycle_length: int | None
    pms_score: int | None
    cramps: bool
    migraine: bool
    fatigue: bool
    contraception_type: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
