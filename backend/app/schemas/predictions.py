from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models import RiskLevel


class RiskPredictionResponse(BaseModel):
    id: int
    player_id: int
    player_name: str | None = None
    date: date
    risk_score: float
    risk_level: RiskLevel
    model_version: str
    features_used: dict
    player_position: str | None = None
    latest_training_date: date | None = None
    latest_session_rpe: int | None = None
    latest_session_type: str | None = None
    latest_participation_status: str | None = None
    latest_injury_date: date | None = None
    latest_pain_intensity: int | None = None
    latest_medical_attention: bool | None = None
    latest_time_loss_days: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ModelTrainingStatusResponse(BaseModel):
    status: str
    updated_at: str
    last_success_at: str | None = None
    last_failure_at: str | None = None
    error: str | None = None
    metrics: dict | None = None
    context: dict | None = None
