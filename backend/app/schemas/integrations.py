import enum
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntegrationStatus(BaseModel):
    provider: str
    connected: bool
    configured: bool
    supports_oauth: bool
    # Cycle data is only taken from a device once the player says so, per provider.
    sync_cycle: bool = False
    # False once the provider has refused cycle data for this account - the app
    # then stops offering the switch instead of letting it lead nowhere.
    cycle_available: bool = True
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    last_error: str | None = None
    last_data_date: date | None = None


class AuthorizeUrlResponse(BaseModel):
    provider: str
    authorize_url: str


class OuraPersonalTokenRequest(BaseModel):
    # Oura personal access tokens are opaque; only the length is validated.
    token: str = Field(min_length=10, max_length=512)


class IngestTokenResponse(BaseModel):
    provider: str = "apple_health"
    ingest_token: str
    ingest_url: str


class SyncRequest(BaseModel):
    days: int = Field(default=14, ge=1, le=60)


class SyncResponse(BaseModel):
    provider: str
    days_written: int
    first_day: date | None = None
    last_day: date | None = None
    synced_at: datetime


class WearableDailyResponse(BaseModel):
    id: int
    player_id: int
    date: date
    provider: str
    sleep_hours: float | None = None
    sleep_score: int | None = None
    readiness_score: int | None = None
    hrv_ms: float | None = None
    resting_hr: float | None = None
    respiratory_rate: float | None = None
    strain: float | None = None
    steps: int | None = None
    active_calories: float | None = None
    workout_minutes: float | None = None
    workout_sport: str | None = None
    menstrual_flow: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("provider", mode="before")
    @classmethod
    def _plain_provider(cls, value: Any) -> Any:
        """Serialise the enum as its slug so clients see ``"oura"``."""
        return value.value if isinstance(value, enum.Enum) else value


class SyncCycleRequest(BaseModel):
    """Turn cycle sync on or off for one provider."""

    enabled: bool


class WellnessSuggestion(BaseModel):
    sleep_hours: float | None = None
    sleep_quality: int | None = None
    readiness_score: int | None = None
    hrv_ms: float | None = None
    resting_hr: float | None = None
    strain: float | None = None


class TrainingSuggestion(BaseModel):
    duration_min: int | None = None
    # Only present when the device measured strain.
    intensity: int | None = None
    # Only present when the sport is one the app recognises.
    session_type: str | None = None
    sport: str | None = None


class CycleSuggestion(BaseModel):
    cycle_day: int | None = None
    phase: str | None = None
    cycle_length: int | None = None
    flow: str | None = None


class SuggestionResponse(BaseModel):
    """Everything the forms can prefill for one day, in one call."""

    date: date
    sources: list[str] = []
    wellness: WellnessSuggestion | None = None
    training: TrainingSuggestion | None = None
    cycle: CycleSuggestion | None = None
