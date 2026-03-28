from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class InjuryEntryCreate(BaseModel):
    date: date
    body_location: str = Field(min_length=1, max_length=255)
    pain_intensity: int = Field(ge=1, le=10)
    is_chronic: bool = False
    description: str | None = None


class InjuryEntryResponse(BaseModel):
    id: int
    player_id: int
    date: date
    body_location: str
    pain_intensity: int
    is_chronic: bool
    description: str | None

    model_config = ConfigDict(from_attributes=True)
