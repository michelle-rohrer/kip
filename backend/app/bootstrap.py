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

import json
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


def _create_or_update_coach(
    session: Session,
    *,
    username: str,
    password: str,
    name: str,
    email: str | None,
    team_name: str,
    reset_password: bool,
) -> str:
    """Create one coach, or report why it was skipped. Idempotent."""
    if not username or not password:
        return f"coach '{username or '?'}': skipped (username or password missing)"
    if len(password) < 8:
        return f"coach '{username}': skipped (password must have at least 8 characters)"

    if team_name:
        team = session.execute(select(Team).where(Team.name == team_name)).scalar_one_or_none()
    else:
        team = session.execute(select(Team).order_by(Team.id.asc())).scalars().first()
    if team is None:
        return f"coach '{username}': skipped (team '{team_name or 'any'}' not found)"

    coach = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if coach is not None:
        if reset_password:
            coach.password_hash = hash_password(password)
            session.commit()
            return f"coach '{username}': password reset"
        return f"coach '{username}': already exists"

    session.add(
        User(
            username=username,
            email=email or None,
            password_hash=hash_password(password),
            role=UserRole.COACH,
            team_id=team.id,
            name=name or username,
        )
    )
    session.commit()
    return f"coach '{username}': created for team '{team.name}'"


def ensure_additional_coaches(session: Session) -> list[str]:
    """Coaches from ``BOOTSTRAP_COACHES``, a JSON list.

    The single BOOTSTRAP_COACH_* variables only ever described one person, and
    a team usually has more than one. JSON rather than a delimited string
    because a password may contain any character a separator could claim.

        [{"username": "denise", "password": "...", "name": "Denise Muster"}]

    Each entry may carry "email" and "team"; without a team the entry joins
    the same team as the main coach.
    """
    raw = os.getenv("BOOTSTRAP_COACHES", "").strip()
    if not raw:
        return []
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"coaches: skipped (BOOTSTRAP_COACHES is not valid JSON: {exc})"]
    if not isinstance(entries, list):
        return ["coaches: skipped (BOOTSTRAP_COACHES must be a JSON list)"]

    default_team = os.getenv("BOOTSTRAP_COACH_TEAM", "").strip()
    reset = os.getenv("BOOTSTRAP_COACH_RESET_PASSWORD", "false").lower() == "true"
    results: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            results.append("coach: skipped (entry is not an object)")
            continue
        results.append(
            _create_or_update_coach(
                session,
                username=str(entry.get("username", "")).strip(),
                password=str(entry.get("password", "")).strip(),
                name=str(entry.get("name", "")).strip(),
                email=(str(entry["email"]).strip() if entry.get("email") else None),
                team_name=str(entry.get("team", default_team)).strip(),
                reset_password=reset,
            )
        )
    return results


def ensure_coach(session: Session) -> str:
    username = os.getenv("BOOTSTRAP_COACH_USERNAME", "").strip()
    password = os.getenv("BOOTSTRAP_COACH_PASSWORD", "").strip()
    if not username or not password:
        return "coach: skipped (BOOTSTRAP_COACH_USERNAME/PASSWORD not set)"
    if len(password) < 8:
        return "coach: skipped (BOOTSTRAP_COACH_PASSWORD must have at least 8 characters)"

    team_name = os.getenv("BOOTSTRAP_COACH_TEAM", "").strip()
    return _create_or_update_coach(
        session,
        username=username,
        password=password,
        name=os.getenv("BOOTSTRAP_COACH_NAME", username),
        email=os.getenv("BOOTSTRAP_COACH_EMAIL"),
        team_name=team_name,
        reset_password=os.getenv("BOOTSTRAP_COACH_RESET_PASSWORD", "false").lower() == "true",
    )


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
        for line in ensure_additional_coaches(session):
            print(line)
        print(apply_test_accounts(session))


if __name__ == "__main__":
    bootstrap()
