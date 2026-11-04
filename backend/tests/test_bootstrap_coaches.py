"""Creating the team's coaches from configuration."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from app.bootstrap import ensure_additional_coaches, ensure_coach, ensure_teams
from app.models import Team, User, UserRole
from app.services.auth import verify_password


@pytest.fixture()
def team(db_session: Session) -> Team:
    ensure_teams(db_session, ["BTV Aarau F1"])
    return db_session.query(Team).one()


def _coach(db_session: Session, username: str) -> User | None:
    return db_session.query(User).filter(User.username == username).one_or_none()


def test_several_coaches_are_created(
    db_session: Session, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BOOTSTRAP_COACH_TEAM", "BTV Aarau F1")
    monkeypatch.setenv(
        "BOOTSTRAP_COACHES",
        json.dumps(
            [
                {"username": "denise", "password": "SuperSecret123", "name": "Denise"},
                {"username": "timo", "password": "SuperSecret456", "name": "Timo"},
            ]
        ),
    )
    lines = ensure_additional_coaches(db_session)
    assert all("created" in line for line in lines), lines

    for username, name in (("denise", "Denise"), ("timo", "Timo")):
        coach = _coach(db_session, username)
        assert coach is not None
        assert coach.role is UserRole.COACH
        assert coach.team_id == team.id
        assert coach.name == name
        assert coach.password_hash != "SuperSecret123"


def test_running_it_again_changes_nothing(
    db_session: Session, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bootstrap runs on every start - it must not reset anybody's password."""
    monkeypatch.setenv("BOOTSTRAP_COACH_TEAM", "BTV Aarau F1")
    monkeypatch.setenv(
        "BOOTSTRAP_COACHES",
        json.dumps([{"username": "denise", "password": "SuperSecret123", "name": "Denise"}]),
    )
    ensure_additional_coaches(db_session)
    _coach(db_session, "denise").password_hash = "changed-by-her-own-reset"
    db_session.commit()

    lines = ensure_additional_coaches(db_session)
    assert "already exists" in lines[0]
    assert _coach(db_session, "denise").password_hash == "changed-by-her-own-reset"


def test_a_password_can_be_reset_on_purpose(
    db_session: Session, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BOOTSTRAP_COACH_TEAM", "BTV Aarau F1")
    monkeypatch.setenv(
        "BOOTSTRAP_COACHES",
        json.dumps([{"username": "denise", "password": "SuperSecret123", "name": "Denise"}]),
    )
    ensure_additional_coaches(db_session)

    monkeypatch.setenv(
        "BOOTSTRAP_COACHES",
        json.dumps([{"username": "denise", "password": "BrandNewPass99", "name": "Denise"}]),
    )
    monkeypatch.setenv("BOOTSTRAP_COACH_RESET_PASSWORD", "true")
    lines = ensure_additional_coaches(db_session)
    assert "password reset" in lines[0]
    assert verify_password("BrandNewPass99", _coach(db_session, "denise").password_hash)


def test_a_short_password_is_refused(
    db_session: Session, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BOOTSTRAP_COACHES", json.dumps([{"username": "timo", "password": "kurz"}]))
    lines = ensure_additional_coaches(db_session)
    assert "at least 8 characters" in lines[0]
    assert _coach(db_session, "timo") is None


def test_broken_configuration_does_not_crash_the_start(
    db_session: Session, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bootstrap runs before the server does - a typo must not keep it down."""
    monkeypatch.setenv("BOOTSTRAP_COACHES", "{nicht json")
    lines = ensure_additional_coaches(db_session)
    assert "not valid JSON" in lines[0]

    monkeypatch.setenv("BOOTSTRAP_COACHES", '{"username": "denise"}')
    assert "must be a JSON list" in ensure_additional_coaches(db_session)[0]


def test_nothing_configured_means_nothing_happens(
    db_session: Session, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("BOOTSTRAP_COACHES", raising=False)
    assert ensure_additional_coaches(db_session) == []
    assert db_session.query(User).count() == 0


def test_the_main_coach_still_works(
    db_session: Session, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The single-coach variables kept their behaviour through the refactor."""
    monkeypatch.setenv("BOOTSTRAP_COACH_USERNAME", "michelle")
    monkeypatch.setenv("BOOTSTRAP_COACH_PASSWORD", "SuperSecret123")
    monkeypatch.setenv("BOOTSTRAP_COACH_NAME", "Michelle Rohrer")
    monkeypatch.setenv("BOOTSTRAP_COACH_TEAM", "BTV Aarau F1")
    assert "created" in ensure_coach(db_session)
    coach = _coach(db_session, "michelle")
    assert coach.name == "Michelle Rohrer"
    assert coach.team_id == team.id
