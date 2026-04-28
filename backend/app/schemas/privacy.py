from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PrivacyConsentUpsert(BaseModel):
    coach_id: int
    share_cycle_data: bool = False
    share_wellness_data: bool = False


class PrivacyConsentResponse(BaseModel):
    id: int
    player_id: int
    coach_id: int
    coach_name: str | None = None
    share_cycle_data: bool
    share_wellness_data: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
