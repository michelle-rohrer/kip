from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.models import CycleEntry, InjuryEntry, TrainingEntry, WellnessEntry


@dataclass(frozen=True)
class FeatureConfig:
    acute_window_days: int = 7
    chronic_window_days: int = 28


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    out = a / b.replace(0, pd.NA)
    return out.fillna(1.0)


def _season_phase(dates: pd.Series) -> pd.Series:
    """1 = Spielsaison (Okt–Apr), 0 = Sommerpause (Mai–Sep)."""
    return dates.apply(lambda d: 0 if 5 <= d.month <= 9 else 1).astype(int)


def build_player_feature_frame(
    db: Session,
    *,
    player_id: int,
    player_position: str | None = None,
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
    injury_rows = (
        db.query(InjuryEntry)
        .filter(InjuryEntry.player_id == player_id)
        .order_by(InjuryEntry.date.asc(), InjuryEntry.id.asc())
        .all()
    )

    df_train = pd.DataFrame(
        [
            {
                "date": r.date,
                "duration_min": r.duration_min,
                "intensity": r.intensity,
                "session_rpe": r.session_rpe,
                "session_type": r.session_type if r.session_type is not None else "team",
                "daily_load": (
                    float(r.duration_min) * float(r.intensity) / 90.0
                    if r.duration_min is not None and r.intensity is not None
                    else None
                ),
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
                "rpe_previous_day": r.rpe_previous_day,
            }
            for r in wellness_rows
        ]
    )
    df_cycle = pd.DataFrame(
        [
            {
                "date": r.date,
                "phase": r.phase.value if r.phase is not None else None,
                "pms_score": r.pms_score,
                "cramps": int(r.cramps),
                "migraine": int(r.migraine),
                "fatigue_flag": int(r.fatigue),
            }
            for r in cycle_rows
        ]
    )
    df_injury = pd.DataFrame(
        [
            {
                "date": r.date,
                "injury_pain_intensity": r.pain_intensity,
                "injury_medical_attention": int(r.medical_attention),
                "injury_time_loss_days": r.time_loss_days if r.time_loss_days is not None else 0,
            }
            for r in injury_rows
        ]
    )

    if df_wellness.empty and df_train.empty and df_cycle.empty and df_injury.empty:
        return pd.DataFrame()

    base_dates = pd.DataFrame(
        {
            "date": sorted(
                set(df_wellness.get("date", []))
                | set(df_train.get("date", []))
                | set(df_cycle.get("date", []))
                | set(df_injury.get("date", []))
            )
        }
    )
    df = base_dates.copy()
    if not df_train.empty:
        df = df.merge(df_train, on="date", how="left")
    if not df_wellness.empty:
        df = df.merge(df_wellness, on="date", how="left")
    if not df_cycle.empty:
        df = df.merge(df_cycle, on="date", how="left")
    if not df_injury.empty:
        df = df.merge(df_injury, on="date", how="left")

    defaults = {
        "duration_min": 0,
        "intensity": 0,
        "session_rpe": 0,
        "session_type": "team",
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
        "injury_pain_intensity": 0,
        "injury_medical_attention": 0,
        "injury_time_loss_days": 0,
    }
    for col, value in defaults.items():
        if col not in df.columns:
            df[col] = value
        else:
            df[col] = df[col].fillna(value)

    df = df.sort_values("date").reset_index(drop=True)

    # Season phase: 1 = Spielsaison (Okt–Apr), 0 = Sommerpause (Mai–Sep)
    df["season_phase"] = _season_phase(pd.to_datetime(df["date"]))

    acute = df["daily_load"].rolling(window=cfg.acute_window_days, min_periods=1).mean()
    chronic = df["daily_load"].rolling(window=cfg.chronic_window_days, min_periods=1).mean()
    df["acwr"] = _safe_div(acute, chronic)

    rolling_cols = [
        "sleep_quality",
        "muscle_soreness",
        "mental_energy",
        "stress_level",
        "motivation",
        "daily_load",
    ]
    for col in rolling_cols:
        df[f"{col}_ma3"] = df[col].rolling(window=3, min_periods=1).mean()
        df[f"{col}_ma7"] = df[col].rolling(window=7, min_periods=1).mean()
        df[f"{col}_delta"] = df[col] - df[col].shift(1).fillna(df[col])

    # Within-player z-score: normalizes each metric relative to the player's own baseline.
    # Uses expanding window so only past data is used (no leakage).
    wellness_cols = ["sleep_quality", "muscle_soreness", "mental_energy", "stress_level", "motivation"]
    for col in wellness_cols:
        exp_mean = df[col].expanding(min_periods=5).mean()
        exp_std = df[col].expanding(min_periods=5).std().replace(0, 1.0)
        df[f"{col}_zscore"] = ((df[col] - exp_mean) / exp_std).fillna(0.0)

    df["phase_intensity_interaction"] = df["intensity"] * (df["phase"] == "luteal").astype(int)
    df["session_rpe_x_intensity"] = df["session_rpe"] * df["intensity"]
    df["sleep_energy_interaction"] = df["sleep_hours"] * df["mental_energy"]
    df["symptom_score"] = (
        df["pms_score"] + (df["cramps"] * 2) + (df["migraine"] * 2) + df["fatigue_flag"]
    )

    # Player position as categorical feature
    pos = player_position if player_position else "unknown"
    df["player_position_raw"] = pos
    position_dummies = pd.get_dummies(df["player_position_raw"], prefix="position")
    df = pd.concat([df, position_dummies], axis=1)
    df.drop(columns=["player_position_raw"], inplace=True)

    phase_dummies = pd.get_dummies(df["phase"], prefix="phase")
    session_type_dummies = pd.get_dummies(df["session_type"], prefix="session_type")
    df = pd.concat([df, phase_dummies, session_type_dummies], axis=1)

    return df
