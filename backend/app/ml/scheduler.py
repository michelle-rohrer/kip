"""Periodic retraining scheduler for the risk model.

Usage (from backend/):
    python -m app.ml.scheduler
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

from app.db import SessionLocal
from app.ml.train import record_training_failure, train_random_forest


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _run_training(
    *, min_real_rows: int, min_positive_rows: int, allow_synthetic_bootstrap: bool
) -> None:
    db = SessionLocal()
    try:
        metrics = train_random_forest(
            db,
            min_real_rows=min_real_rows,
            min_positive_rows=min_positive_rows,
            allow_synthetic_bootstrap=allow_synthetic_bootstrap,
        )
        print(f"[retrainer] success: {metrics}")
    except Exception as exc:  # noqa: BLE001 - long-running ops logging
        db.rollback()
        record_training_failure(
            error=str(exc),
            context={
                "runner": "scheduler",
                "min_real_rows": min_real_rows,
                "min_positive_rows": min_positive_rows,
                "allow_synthetic_bootstrap": allow_synthetic_bootstrap,
            },
        )
        print(f"[retrainer] failed: {exc}")
    finally:
        db.close()


def main() -> int:
    interval_seconds = max(_env_int("ML_RETRAIN_INTERVAL_SECONDS", 7 * 24 * 60 * 60), 60)
    min_real_rows = max(_env_int("ML_MIN_REAL_ROWS", 500), 50)
    min_positive_rows = max(_env_int("ML_MIN_POSITIVE_ROWS", 20), 5)
    allow_synthetic_bootstrap = _env_bool("ML_ALLOW_SYNTHETIC_BOOTSTRAP", True)
    run_immediately = _env_bool("ML_RETRAIN_ON_STARTUP", True)

    print(
        "[retrainer] started with "
        f"interval_seconds={interval_seconds}, "
        f"min_real_rows={min_real_rows}, "
        f"min_positive_rows={min_positive_rows}, "
        f"allow_synthetic_bootstrap={allow_synthetic_bootstrap}, "
        f"run_immediately={run_immediately}"
    )

    if run_immediately:
        _run_training(
            min_real_rows=min_real_rows,
            min_positive_rows=min_positive_rows,
            allow_synthetic_bootstrap=allow_synthetic_bootstrap,
        )

    while True:
        next_run_at = datetime.now(UTC).timestamp() + interval_seconds
        print(
            "[retrainer] sleeping until next run at "
            f"{datetime.fromtimestamp(next_run_at, tz=UTC).isoformat()}"
        )
        time.sleep(interval_seconds)
        _run_training(
            min_real_rows=min_real_rows,
            min_positive_rows=min_positive_rows,
            allow_synthetic_bootstrap=allow_synthetic_bootstrap,
        )


if __name__ == "__main__":
    raise SystemExit(main())
