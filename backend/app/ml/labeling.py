from __future__ import annotations

import pandas as pd


def add_overload_label(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        out = df.copy()
        out["overload_risk_3d"] = pd.Series(dtype=int)
        return out

    out = df.copy()
    overload_today = (
        (out["acwr"] >= 1.35)
        | (out["muscle_soreness"] >= 8)
        | ((out["stress_level"] >= 8) & (out["mental_energy"] <= 4))
    )

    horizon = 3
    future_flag = pd.Series(False, index=out.index)
    for i in range(1, horizon + 1):
        future_flag = future_flag | overload_today.shift(-i).fillna(False)

    out["overload_risk_3d"] = future_flag.astype(int)
    return out
