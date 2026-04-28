"""Load synthetic data into the database: ``python -m app.data_generation.seed`` (from ``backend/``)."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import date

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_generation.generate import (
    SyntheticDatasetConfig,
    build_privacy_consents,
    build_synthetic_dataset,
)
from app.db import SessionLocal
from app.models import Team, User


def _delete_synthetic_users(session: Session, team_name: str) -> None:
    """Remove users created by a previous seed run (ORM cascades delete related rows)."""
    q = select(User).where(User.email.like("synthetic.%@kip.local"))
    for user in session.scalars(q).all():
        session.delete(user)
    session.flush()

    team = session.scalars(select(Team).where(Team.name == team_name)).first()
    if team is not None:
        session.delete(team)
    session.flush()


def seed_database(
    *,
    session: Session,
    config: SyntheticDatasetConfig | None = None,
    end_date: date | None = None,
    replace: bool = True,
) -> None:
    cfg = config or SyntheticDatasetConfig()
    if replace:
        _delete_synthetic_users(session, cfg.team_name)

    rng = np.random.default_rng(cfg.random_seed)
    team, coaches, players, cycle_rows, wellness_rows, training_rows, injury_rows = (
        build_synthetic_dataset(
            rng=rng,
            end_date=end_date,
            config=cfg,
        )
    )

    session.add(team)
    session.flush()

    for coach in coaches:
        coach.team_id = team.id
    for p in players:
        p.team_id = team.id

    session.add_all(coaches)
    session.add_all(players)
    session.flush()

    session.add_all(build_privacy_consents(coaches=coaches, players=players, rng=rng))
    session.add_all(cycle_rows)
    session.add_all(wellness_rows)
    session.add_all(training_rows)
    session.add_all(injury_rows)
    session.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the database with synthetic KIP data.")
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Do not delete existing synthetic@kip.local users first (may fail on duplicate emails).",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Override random seed (default: config 42)."
    )
    parser.add_argument(
        "--players", type=int, default=None, help="Number of synthetic players (15–20)."
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Last day of history (YYYY-MM-DD). Default: today.",
    )
    args = parser.parse_args(argv)

    cfg = SyntheticDatasetConfig()
    if args.seed is not None:
        cfg = replace(cfg, random_seed=args.seed)
    if args.players is not None:
        cfg = replace(cfg, num_players=int(np.clip(args.players, 15, 20)))
    end: date | None = None
    if args.end_date:
        end = date.fromisoformat(args.end_date)

    db = SessionLocal()
    try:
        seed_database(session=db, config=cfg, end_date=end, replace=not args.no_replace)
    except Exception as exc:  # noqa: BLE001 — CLI: print and exit
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Synthetic data seeded successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
