from __future__ import annotations

import pandas as pd


def add_overload_label(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        out = df.copy()
        out["overload_risk_3d"] = pd.Series(dtype=int)
        return out

    out = df.copy()
    heuristic_overload_today = (
        (out["acwr"] >= 1.35)
        | (out["muscle_soreness"] >= 8)
        | ((out["stress_level"] >= 8) & (out["mental_energy"] <= 4))
    )
    injury_overload_today = (
        (out.get("injury_time_loss_days", 0) > 0)
        | (out.get("injury_medical_attention", 0) > 0)
        | (out.get("injury_pain_intensity", 0) >= 7)
    )
    overload_today = heuristic_overload_today | injury_overload_today

    horizon = 3
    future_flag = pd.Series(False, index=out.index)
    for i in range(1, horizon + 1):
        future_flag = future_flag | overload_today.shift(-i).fillna(False)

    out["overload_risk_3d"] = future_flag.astype(int)
    return out
