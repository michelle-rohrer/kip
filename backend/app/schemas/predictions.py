from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models import RiskLevel


class RiskPredictionResponse(BaseModel):
    id: int
    player_id: int
    date: date
    risk_score: float
    risk_level: RiskLevel
    model_version: str
    features_used: dict

    model_config = ConfigDict(from_attributes=True)


class ModelTrainingStatusResponse(BaseModel):
    status: str
    updated_at: str
    last_success_at: str | None = None
    last_failure_at: str | None = None
    error: str | None = None
    metrics: dict | None = None
    context: dict | None = None
