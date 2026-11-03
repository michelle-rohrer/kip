"""Prepare a fresh production database: ``python -m app.bootstrap``.

Idempotent on purpose - it runs on every start of the deployed backend and only
creates what is missing:

* the teams players can pick during registration
  (``BOOTSTRAP_TEAMS``, comma separated)
* one coach account, because coach registration is disabled in the public API
  (``BOOTSTRAP_COACH_USERNAME`` / ``BOOTSTRAP_COACH_PASSWORD``)

No synthetic data is touched here - that is what ``app.data_generation.seed``
is for, and it must never run against production.
"""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Team, User, UserRole
from app.services.auth import hash_password

# One team by default. A coach only ever sees her own team, so a second entry
# here quietly splits the squad into a visible and an invisible half.
DEFAULT_TEAMS = "BTV Aarau F1"


def _split_env_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def ensure_teams(session: Session, names: list[str]) -> list[Team]:
    created: list[Team] = []
    for name in names:
        existing = session.execute(select(Team).where(Team.name == name)).scalar_one_or_none()
        if existing is None:
            team = Team(name=name)
            session.add(team)
            created.append(team)
    if created:
        session.commit()
    return created


def ensure_coach(session: Session) -> str:
    username = os.getenv("BOOTSTRAP_COACH_USERNAME", "").strip()
    password = os.getenv("BOOTSTRAP_COACH_PASSWORD", "").strip()
    if not username or not password:
        return "coach: skipped (BOOTSTRAP_COACH_USERNAME/PASSWORD not set)"
    if len(password) < 8:
        return "coach: skipped (BOOTSTRAP_COACH_PASSWORD must have at least 8 characters)"

    team_name = os.getenv("BOOTSTRAP_COACH_TEAM", "").strip()
    if team_name:
        team = session.execute(select(Team).where(Team.name == team_name)).scalar_one_or_none()
    else:
        team = session.execute(select(Team).order_by(Team.id.asc())).scalars().first()
    if team is None:
        return f"coach: skipped (team '{team_name or 'any'}' not found)"

    coach = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if coach is not None:
        if os.getenv("BOOTSTRAP_COACH_RESET_PASSWORD", "false").lower() == "true":
            coach.password_hash = hash_password(password)
            session.commit()
            return f"coach: password reset for '{username}'"
        return f"coach: '{username}' already exists"

    session.add(
        User(
            username=username,
            email=os.getenv("BOOTSTRAP_COACH_EMAIL") or None,
            password_hash=hash_password(password),
            role=UserRole.COACH,
            team_id=team.id,
            name=os.getenv("BOOTSTRAP_COACH_NAME", username),
        )
    )
    session.commit()
    return f"coach: created '{username}' for team '{team.name}'"


def apply_test_accounts(session: Session) -> str:
    """Flag the usernames in ``BOOTSTRAP_TEST_PLAYERS`` as test accounts.

    The list is authoritative: anybody on it is flagged, anybody flagged who
    is no longer on it is unflagged. That way the setting lives in one place
    and survives a rebuilt database, instead of being a one-off edit in the
    table that nobody can find again later.
    """
    wanted = {name.lower() for name in _split_env_list(os.getenv("BOOTSTRAP_TEST_PLAYERS", ""))}
    changed: list[str] = []

    for user in session.execute(select(User)).scalars().all():
        should_flag = user.username.lower() in wanted
        if user.is_test_account != should_flag:
            user.is_test_account = should_flag
            changed.append(f"{'+' if should_flag else '-'}{user.username}")

    if changed:
        session.commit()
        return "test accounts: " + ", ".join(changed)
    return f"test accounts: nothing to do ({len(wanted)} configured)"


def bootstrap() -> None:
    team_names = _split_env_list(os.getenv("BOOTSTRAP_TEAMS", DEFAULT_TEAMS))
    with SessionLocal() as session:
        created_teams = ensure_teams(session, team_names)
        print(
            "teams: "
            + (
                ", ".join(f"created '{team.name}'" for team in created_teams)
                if created_teams
                else "nothing to do"
            )
        )
        print(ensure_coach(session))
        print(apply_test_accounts(session))


if __name__ == "__main__":
    bootstrap()
