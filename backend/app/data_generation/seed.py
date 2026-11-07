"""Load synthetic data into the database: ``python -m app.data_generation.seed`` (from ``backend/``).

Never point this at the production database. It starts by deleting every user
and every team, so one mistyped ``DATABASE_URL`` costs a season of real
wellness, cycle, training and injury entries. ``_refuse_in_production`` is the
seatbelt; the only way past it is to say out loud what it does.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from datetime import date

import numpy as np
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.data_generation.generate import (
    SyntheticDatasetConfig,
    build_privacy_consents,
    build_synthetic_dataset,
)
from app.db import SessionLocal
from app.models import (
    CycleEntry,
    InjuryEntry,
    PrivacyConsent,
    RiskPrediction,
    Team,
    TrainingEntry,
    User,
    WellnessEntry,
)

OVERRIDE_FLAG = "--yes-delete-every-account"


def _refuse_in_production(*, override: bool) -> str | None:
    """Return a refusal message when this must not run here, else ``None``.

    Two independent signals, because either one alone can be wrong: a local
    ``.env`` copied from the server says ``production`` without any real data
    behind it, and a hand-exported production ``DATABASE_URL`` says nothing at
    all about ``APP_ENV``.
    """
    if override:
        return None

    reasons: list[str] = []
    if os.getenv("APP_ENV", "development").strip().lower() == "production":
        reasons.append("APP_ENV is 'production'")

    database_url = os.getenv("DATABASE_URL", "")
    remote_hosts = ("neon.tech", "render.com", "amazonaws.com", "supabase.co")
    if any(host in database_url for host in remote_hosts):
        reasons.append("DATABASE_URL points at a hosted database")

    if not reasons:
        return None
    return (
        "Refusing to seed: "
        + " and ".join(reasons)
        + ".\nThis deletes EVERY user and team in that database first.\n"
        + f"If you really mean it, run it again with {OVERRIDE_FLAG}."
    )


def _reset_all_application_data(session: Session) -> None:
    """Remove all app data and accounts before recreating seed data."""
    session.execute(delete(PrivacyConsent))
    session.execute(delete(RiskPrediction))
    session.execute(delete(CycleEntry))
    session.execute(delete(WellnessEntry))
    session.execute(delete(TrainingEntry))
    session.execute(delete(InjuryEntry))
    session.execute(delete(User))
    session.execute(delete(Team))
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
        _reset_all_application_data(session)

    rng = np.random.default_rng(cfg.random_seed)
    teams, coaches, players, cycle_rows, wellness_rows, training_rows, injury_rows = (
        build_synthetic_dataset(
            rng=rng,
            end_date=end_date,
            config=cfg,
        )
    )

    session.add_all(teams)
    session.flush()

    # Both coaches belong to BTV Aarau F1; second team exists without a coach (e.g. NNV).
    btv_team_id = teams[0].id
    for coach in coaches:
        coach.team_id = btv_team_id
    for p in players:
        p.team_id = int(rng.choice([team.id for team in teams]))

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
    parser.add_argument(
        OVERRIDE_FLAG,
        action="store_true",
        help="Seed even though this looks like production. Deletes every account first.",
    )
    args = parser.parse_args(argv)

    refusal = _refuse_in_production(override=args.yes_delete_every_account)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2

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

    # The passwords are drawn fresh on every run and exist nowhere else, so
    # this is the only moment they can be read. Printed rather than stored:
    # a demo login belongs in a terminal, not in a file somebody commits.
    print("Synthetic data seeded successfully.")
    print("Demo logins (new on every seed run):")
    for username, password in zip(cfg.coach_usernames, cfg.coach_passwords):
        print(f"  coach  {username}: {password}")
    print(f"  players player.01 ... player.{cfg.num_players:02d}: {cfg.player_password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
