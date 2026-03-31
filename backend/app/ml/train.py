from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, recall_score, roc_auc_score
from sqlalchemy.orm import Session

from app.ml.features import build_player_feature_frame
from app.ml.labeling import add_overload_label
from app.models import User, UserRole

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "risk_model.joblib"


@dataclass(frozen=True)
class ModelBundle:
    model: RandomForestClassifier
    feature_columns: list[str]
    version: str


def _build_dataset(db: Session) -> pd.DataFrame:
    players = db.query(User).filter(User.role == UserRole.PLAYER).all()
    frames: list[pd.DataFrame] = []
    for p in players:
        f = build_player_feature_frame(db, player_id=p.id)
        if f.empty:
            continue
        f = add_overload_label(f)
        f["player_id"] = p.id
        frames.append(f)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _feature_columns(df: pd.DataFrame) -> list[str]:
    ignore = {"date", "phase", "overload_risk_3d", "player_id"}
    return [c for c in df.columns if c not in ignore]


def train_random_forest(db: Session) -> dict[str, float | str | int]:
    df = _build_dataset(db)
    if df.empty or df["overload_risk_3d"].nunique() < 2:
        raise ValueError("Not enough labeled data to train model")

    df = df.sort_values(["player_id", "date"]).reset_index(drop=True)
    feature_cols = _feature_columns(df)
    X = df[feature_cols].astype(float)
    y = df["overload_risk_3d"].astype(int)

    split_idx = max(int(len(df) * 0.8), 1)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    if len(X_test) == 0 or y_test.nunique() < 2:
        X_train, X_test = X.iloc[:-1], X.iloc[-1:]
        y_train, y_test = y.iloc[:-1], y.iloc[-1:]
        if y_train.nunique() < 2:
            raise ValueError("Not enough class balance to train model")

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
    )
    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    metrics = {
        "pr_auc": float(average_precision_score(y_test, y_prob)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)) if y_test.nunique() > 1 else 0.0,
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "brier_score": float(brier_score_loss(y_test, y_prob)),
    }

    version = datetime.now(timezone.utc).strftime("rf-%Y%m%d%H%M%S")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    dump(ModelBundle(model=model, feature_columns=feature_cols, version=version), MODEL_PATH)

    return {
        "model_version": version,
        "rows": int(len(df)),
        **metrics,
    }
