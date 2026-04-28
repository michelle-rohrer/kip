from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class InjuryEntryCreate(BaseModel):
    date: date
    body_location: str = Field(min_length=1, max_length=255)
    pain_intensity: int | None = Field(default=None, ge=1, le=10)
    is_chronic: bool = False
    medical_attention: bool = False
    time_loss_days: int | None = Field(default=None, ge=0, le=365)
    description: str | None = None


class InjuryEntryResponse(BaseModel):
    id: int
    player_id: int
    date: date
    body_location: str
    pain_intensity: int | None
    is_chronic: bool
    medical_attention: bool
    time_loss_days: int | None
    description: str | None

    model_config = ConfigDict(from_attributes=True)
