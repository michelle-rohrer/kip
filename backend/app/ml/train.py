from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    recall_score,
    roc_auc_score,
)
from sqlalchemy.orm import Session

from app.ml.features import build_player_feature_frame
from app.ml.labeling import add_overload_label
from app.models import User, UserRole

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "risk_model.joblib"
TRAINING_STATUS_PATH = MODEL_DIR / "training_status.json"
SYNTHETIC_EMAIL_SUFFIX = "@kip.local"
SYNTHETIC_EMAIL_PREFIX = "synthetic."


@dataclass(frozen=True)
class ModelBundle:
    model: RandomForestClassifier
    feature_columns: list[str]
    version: str


def _is_synthetic_user(email: str) -> bool:
    lowered = email.lower()
    return lowered.startswith(SYNTHETIC_EMAIL_PREFIX) and lowered.endswith(SYNTHETIC_EMAIL_SUFFIX)


def _build_dataset(db: Session) -> pd.DataFrame:
    players = db.query(User).filter(User.role == UserRole.PLAYER).all()
    frames: list[pd.DataFrame] = []
    for p in players:
        f = build_player_feature_frame(db, player_id=p.id)
        if f.empty:
            continue
        f = add_overload_label(f)
        f["player_id"] = p.id
        f["is_synthetic"] = int(_is_synthetic_user(p.email))
        frames.append(f)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _feature_columns(df: pd.DataFrame) -> list[str]:
    ignore = {"date", "phase", "overload_risk_3d", "player_id", "is_synthetic"}
    return [c for c in df.columns if c not in ignore]


def _select_training_frame(
    df: pd.DataFrame,
    *,
    min_real_rows: int,
    allow_synthetic_bootstrap: bool,
) -> tuple[pd.DataFrame, str]:
    real_df = df[df["is_synthetic"] == 0]
    if len(real_df) >= min_real_rows and real_df["overload_risk_3d"].nunique() >= 2:
        return real_df.copy(), "real_only"

    if allow_synthetic_bootstrap and df["overload_risk_3d"].nunique() >= 2:
        return df.copy(), "bootstrap_mixed"

    raise ValueError(
        "Not enough real data with class balance yet. "
        "Collect more data or allow synthetic bootstrap training."
    )


def _write_training_status(payload: dict[str, Any]) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    TRAINING_STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def record_training_failure(*, error: str, context: dict[str, Any] | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "status": "failed",
        "updated_at": now,
        "last_failure_at": now,
        "error": error,
    }
    if context:
        payload["context"] = context
    _write_training_status(payload)


def load_training_status() -> dict[str, Any] | None:
    if not TRAINING_STATUS_PATH.exists():
        return None
    return json.loads(TRAINING_STATUS_PATH.read_text(encoding="utf-8"))


def train_random_forest(
    db: Session,
    *,
    min_real_rows: int = 500,
    allow_synthetic_bootstrap: bool = True,
) -> dict[str, float | str | int]:
    df = _build_dataset(db)
    if df.empty:
        raise ValueError("Not enough labeled data to train model")

    real_rows = int((df["is_synthetic"] == 0).sum())
    synthetic_rows = int((df["is_synthetic"] == 1).sum())

    df_selected, training_data_mode = _select_training_frame(
        df,
        min_real_rows=min_real_rows,
        allow_synthetic_bootstrap=allow_synthetic_bootstrap,
    )
    df_selected = df_selected.sort_values(["player_id", "date"]).reset_index(drop=True)

    df = df_selected
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

    result = {
        "model_version": version,
        "training_data_mode": training_data_mode,
        "real_rows": real_rows,
        "synthetic_rows": synthetic_rows,
        "rows": int(len(df)),
        "min_real_rows": int(min_real_rows),
        **metrics,
    }
    _write_training_status(
        {
            "status": "ok",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_success_at": datetime.now(timezone.utc).isoformat(),
            "metrics": result,
        }
    )
    return result
