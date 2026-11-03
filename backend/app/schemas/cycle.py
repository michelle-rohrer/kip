from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import CyclePhase
from app.services.wearables.base import FLOW_LEVELS


class CycleEntryCreate(BaseModel):
    date: date
    cycle_day: int | None = Field(default=None, ge=1, le=60)
    phase: CyclePhase | None = None
    cycle_length: int | None = Field(default=None, ge=20, le=45)
    # What the player actually knows. Cycle day, phase and length above are
    # derived from a run of these when she leaves them empty.
    menstrual_flow: str | None = Field(default=None, max_length=16)
    pms_score: int | None = Field(default=None, ge=0, le=10)

    @field_validator("menstrual_flow")
    @classmethod
    def _known_flow(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if value not in FLOW_LEVELS:
            raise ValueError(f"menstrual_flow must be one of: {', '.join(FLOW_LEVELS)}")
        return value

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
    menstrual_flow: str | None = None
    pms_score: int | None
    cramps: bool
    migraine: bool
    fatigue: bool
    contraception_type: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class CycleEstimateResponse(BaseModel):
    """What the app would fill in, shown before anything is saved."""

    date: date
    available: bool
    cycle_day: int | None = None
    phase: str | None = None
    cycle_length: int | None = None
    period_start: date | None = None
    flow: str | None = None
