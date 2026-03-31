from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.models import CycleEntry, TrainingEntry, WellnessEntry


@dataclass(frozen=True)
class FeatureConfig:
    acute_window_days: int = 7
    chronic_window_days: int = 28


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    out = a / b.replace(0, pd.NA)
    return out.fillna(1.0)


def build_player_feature_frame(
    db: Session,
    *,
    player_id: int,
    config: FeatureConfig | None = None,
) -> pd.DataFrame:
    cfg = config or FeatureConfig()

    training_rows = (
        db.query(TrainingEntry)
        .filter(TrainingEntry.player_id == player_id)
        .order_by(TrainingEntry.date.asc(), TrainingEntry.id.asc())
        .all()
    )
    wellness_rows = (
        db.query(WellnessEntry)
        .filter(WellnessEntry.player_id == player_id)
        .order_by(WellnessEntry.date.asc())
        .all()
    )
    cycle_rows = (
        db.query(CycleEntry)
        .filter(CycleEntry.player_id == player_id)
        .order_by(CycleEntry.date.asc())
        .all()
    )

    df_train = pd.DataFrame(
        [
            {
                "date": r.date,
                "duration_min": r.duration_min,
                "intensity": r.intensity,
                "daily_load": float(r.duration_min) * float(r.intensity) / 90.0,
            }
            for r in training_rows
        ]
    )
    df_wellness = pd.DataFrame(
        [
            {
                "date": r.date,
                "sleep_hours": r.sleep_hours,
                "sleep_quality": r.sleep_quality,
                "muscle_soreness": r.muscle_soreness,
                "mental_energy": r.mental_energy,
                "stress_level": r.stress_level,
                "motivation": r.motivation,
                "rpe_previous_day": r.rpe_previous_day if r.rpe_previous_day is not None else 0,
            }
            for r in wellness_rows
        ]
    )
    df_cycle = pd.DataFrame(
        [
            {
                "date": r.date,
                "phase": r.phase.value,
                "pms_score": r.pms_score if r.pms_score is not None else 0,
                "cramps": int(r.cramps),
                "migraine": int(r.migraine),
                "fatigue_flag": int(r.fatigue),
            }
            for r in cycle_rows
        ]
    )

    if df_wellness.empty and df_train.empty and df_cycle.empty:
        return pd.DataFrame()

    base_dates = pd.DataFrame({"date": sorted(set(df_wellness.get("date", [])) | set(df_train.get("date", [])) | set(df_cycle.get("date", [])))})
    df = base_dates.copy()
    if not df_train.empty:
        df = df.merge(df_train, on="date", how="left")
    if not df_wellness.empty:
        df = df.merge(df_wellness, on="date", how="left")
    if not df_cycle.empty:
        df = df.merge(df_cycle, on="date", how="left")

    # Default values keep feature generation stable even with sparse historic data.
    defaults = {
        "duration_min": 0,
        "intensity": 0,
        "daily_load": 0.0,
        "sleep_hours": 7.0,
        "sleep_quality": 6,
        "muscle_soreness": 5,
        "mental_energy": 6,
        "stress_level": 5,
        "motivation": 6,
        "rpe_previous_day": 0,
        "phase": "follicular",
        "pms_score": 0,
        "cramps": 0,
        "migraine": 0,
        "fatigue_flag": 0,
    }
    for col, value in defaults.items():
        if col not in df.columns:
            df[col] = value
        else:
            df[col] = df[col].fillna(value)

    df = df.sort_values("date").reset_index(drop=True)

    acute = df["daily_load"].rolling(window=cfg.acute_window_days, min_periods=1).mean()
    chronic = df["daily_load"].rolling(window=cfg.chronic_window_days, min_periods=1).mean()
    df["acwr"] = _safe_div(acute, chronic)

    for col in ["sleep_quality", "muscle_soreness", "mental_energy", "stress_level", "motivation", "daily_load"]:
        df[f"{col}_ma3"] = df[col].rolling(window=3, min_periods=1).mean()
        df[f"{col}_ma7"] = df[col].rolling(window=7, min_periods=1).mean()
        df[f"{col}_delta"] = df[col] - df[col].shift(1).fillna(df[col])

    df["phase_intensity_interaction"] = df["intensity"] * (df["phase"] == "luteal").astype(int)
    df["sleep_energy_interaction"] = df["sleep_hours"] * df["mental_energy"]
    df["symptom_score"] = df["pms_score"] + (df["cramps"] * 2) + (df["migraine"] * 2) + df["fatigue_flag"]

    phase_dummies = pd.get_dummies(df["phase"], prefix="phase")
    df = pd.concat([df, phase_dummies], axis=1)

    return df
