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
