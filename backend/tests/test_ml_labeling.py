from __future__ import annotations

import pandas as pd
import pytest

from app.ml.labeling import add_overload_label
from app.ml.train import _select_training_frame


def test_add_overload_label_uses_injury_ground_truth() -> None:
    df = pd.DataFrame(
        {
            "acwr": [1.0, 1.0, 1.0, 1.0],
            "muscle_soreness": [3, 3, 3, 3],
            "stress_level": [3, 3, 3, 3],
            "mental_energy": [7, 7, 7, 7],
            "injury_time_loss_days": [0, 0, 2, 0],
            "injury_medical_attention": [0, 0, 0, 0],
            "injury_pain_intensity": [2, 2, 8, 2],
        }
    )
    out = add_overload_label(df)
    # horizon=3 means rows before an injury flag become positive
    assert out["overload_risk_3d"].tolist() == [1, 1, 0, 0]


def test_select_training_frame_requires_min_positive_rows() -> None:
    df = pd.DataFrame(
        {
            "is_synthetic": [0, 0, 0, 0, 0, 0],
            "overload_risk_3d": [0, 0, 0, 0, 1, 0],
        }
    )
    with pytest.raises(ValueError):
        _select_training_frame(
            df,
            min_real_rows=5,
            min_positive_rows=2,
            allow_synthetic_bootstrap=False,
        )
