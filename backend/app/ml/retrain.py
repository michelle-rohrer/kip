"""Retrain risk model with gradual shift from synthetic to real data.

Usage (from backend/):
    python -m app.ml.retrain
"""

from __future__ import annotations

import argparse
import json
import sys

from app.db import SessionLocal
from app.ml.train import record_training_failure, train_random_forest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train the risk model with real-data gate and optional synthetic bootstrap."
    )
    parser.add_argument(
        "--min-real-rows",
        type=int,
        default=500,
        help="Minimum number of real labeled rows required before switching to real-only training.",
    )
    parser.add_argument(
        "--no-synthetic-bootstrap",
        action="store_true",
        help="Disable fallback to mixed synthetic+real training before enough real rows exist.",
    )
    parser.add_argument(
        "--min-positive-rows",
        type=int,
        default=20,
        help="Minimum number of positive (overload/injury) labeled rows required for training.",
    )
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        metrics = train_random_forest(
            db,
            min_real_rows=max(args.min_real_rows, 50),
            min_positive_rows=max(args.min_positive_rows, 5),
            allow_synthetic_bootstrap=not args.no_synthetic_bootstrap,
        )
    except Exception as exc:  # noqa: BLE001 - CLI output for operators
        db.rollback()
        record_training_failure(
            error=str(exc),
            context={
                "runner": "manual_cli",
                "min_real_rows": max(args.min_real_rows, 50),
                "min_positive_rows": max(args.min_positive_rows, 5),
                "allow_synthetic_bootstrap": not args.no_synthetic_bootstrap,
            },
        )
        print(f"Training failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Training finished.")
    print(json.dumps(metrics, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
