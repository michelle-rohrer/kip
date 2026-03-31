from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from joblib import load
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.ml.features import build_player_feature_frame
from app.ml.train import MODEL_PATH, ModelBundle
from app.models import RiskLevel, RiskPrediction


@dataclass(frozen=True)
class PredictionResult:
    score: float
    level: RiskLevel
    model_version: str
    features_used: dict


def map_risk_level(score: float) -> RiskLevel:
    if score < 0.35:
        return RiskLevel.GREEN
    if score < 0.65:
        return RiskLevel.YELLOW
    return RiskLevel.RED


def _load_model_bundle() -> ModelBundle | None:
    if not Path(MODEL_PATH).exists():
        return None
    return load(MODEL_PATH)


def _heuristic_score(features: dict) -> float:
    acwr = float(features.get("acwr", 1.0))
    soreness = float(features.get("muscle_soreness", 5.0))
    stress = float(features.get("stress_level", 5.0))
    energy = float(features.get("mental_energy", 6.0))
    score = 0.22 + (max(acwr - 1.0, 0) * 0.38) + ((soreness - 5.0) * 0.04) + ((stress - energy) * 0.03)
    return float(np.clip(score, 0.02, 0.98))


def predict_current_risk(db: Session, *, player_id: int) -> PredictionResult:
    features_df = build_player_feature_frame(db, player_id=player_id)
    if features_df.empty:
        features = {
            "acwr": 1.0,
            "muscle_soreness": 5.0,
            "stress_level": 5.0,
            "mental_energy": 6.0,
        }
        score = _heuristic_score(features)
        return PredictionResult(
            score=score,
            level=map_risk_level(score),
            model_version="heuristic-v1",
            features_used=features,
        )

    latest = features_df.sort_values("date").iloc[-1]
    bundle = _load_model_bundle()
    if bundle is None:
        features = latest.to_dict()
        score = _heuristic_score(features)
        return PredictionResult(
            score=score,
            level=map_risk_level(score),
            model_version="heuristic-v1",
            features_used={
                "acwr": float(features.get("acwr", 1.0)),
                "muscle_soreness": float(features.get("muscle_soreness", 5.0)),
                "stress_level": float(features.get("stress_level", 5.0)),
                "mental_energy": float(features.get("mental_energy", 6.0)),
            },
        )

    x = latest.reindex(bundle.feature_columns, fill_value=0).astype(float).to_numpy().reshape(1, -1)
    score = float(bundle.model.predict_proba(x)[0, 1])
    features_used = {k: float(latest.get(k, 0.0)) for k in bundle.feature_columns}
    return PredictionResult(
        score=score,
        level=map_risk_level(score),
        model_version=bundle.version,
        features_used=features_used,
    )


def upsert_daily_prediction(db: Session, *, player_id: int, result: PredictionResult, on_date: date | None = None) -> RiskPrediction:
    target_date = on_date or date.today()
    row = (
        db.query(RiskPrediction)
        .filter(and_(RiskPrediction.player_id == player_id, RiskPrediction.date == target_date))
        .one_or_none()
    )
    if row is None:
        row = RiskPrediction(
            player_id=player_id,
            date=target_date,
            risk_score=result.score,
            risk_level=result.level,
            model_version=result.model_version,
            features_used=result.features_used,
        )
        db.add(row)
    else:
        row.risk_score = result.score
        row.risk_level = result.level
        row.model_version = result.model_version
        row.features_used = result.features_used
    db.commit()
    db.refresh(row)
    return row
