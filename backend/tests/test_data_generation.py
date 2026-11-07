from datetime import date

import numpy as np
import pytest
from sqlalchemy import func, select

from app.data_generation.generate import SyntheticDatasetConfig, build_synthetic_dataset
from app.data_generation.seed import seed_database
from app.models import CycleEntry, InjuryEntry, PrivacyConsent, Team, User, WellnessEntry


def test_build_synthetic_dataset_produces_expected_entities():
    rng = np.random.default_rng(0)
    cfg = SyntheticDatasetConfig(num_players=15, days_min=14, days_max=14, random_seed=0)
    teams, coaches, players, cycles, wellness, training, injuries = build_synthetic_dataset(
        rng=rng, config=cfg, end_date=date(2026, 1, 31)
    )

    assert len(teams) == 2
    assert {team.name for team in teams} == set(cfg.team_names)
    assert len(coaches) == 2
    assert {coach.username for coach in coaches} == set(cfg.coach_usernames)
    assert len(players) == 15
    assert len(cycles) == 15 * 14
    assert len(wellness) == 15 * 14
    assert len(training) > 0
    for c in cycles:
        assert 1 <= c.cycle_day <= c.cycle_length
        assert 26 <= c.cycle_length <= 32


def test_seed_database_persists_and_replace_clears_previous(db_session):
    cfg = SyntheticDatasetConfig(num_players=15, days_min=10, days_max=10, random_seed=1)
    seed_database(session=db_session, config=cfg, replace=True, end_date=date(2026, 2, 1))

    n_users = db_session.scalar(select(func.count()).select_from(User))
    assert n_users == 17

    n_team = db_session.scalar(select(func.count()).select_from(Team))
    assert n_team == 2

    assert db_session.scalar(select(func.count()).select_from(CycleEntry)) == 150
    assert db_session.scalar(select(func.count()).select_from(WellnessEntry)) == 150
    assert db_session.scalar(select(func.count()).select_from(PrivacyConsent)) == 30

    seed_database(session=db_session, config=cfg, replace=True, end_date=date(2026, 2, 1))
    assert db_session.scalar(select(func.count()).select_from(User)) == 17
    assert db_session.scalar(select(func.count()).select_from(InjuryEntry)) >= 0


# ------------------------------------------------- guarding the seed command


def test_seed_refuses_when_app_env_is_production(monkeypatch):
    """The seed deletes every user and team before it writes anything.

    Against the production database that is a season of real wellness, cycle,
    training and injury entries, so it has to say no by default.
    """
    from app.data_generation.seed import _refuse_in_production

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://local/calm")

    refusal = _refuse_in_production(override=False)
    assert refusal is not None
    assert "APP_ENV" in refusal


def test_seed_refuses_when_the_database_is_hosted(monkeypatch):
    """A production connection string exported by hand carries no APP_ENV."""
    from app.data_generation.seed import _refuse_in_production

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@ep-x.eu-central-1.aws.neon.tech/db")

    refusal = _refuse_in_production(override=False)
    assert refusal is not None
    assert "hosted database" in refusal


def test_seed_allows_a_local_development_database(monkeypatch):
    from app.data_generation.seed import _refuse_in_production

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://calm:calm@db:5432/calm")

    assert _refuse_in_production(override=False) is None


def test_seed_override_gets_through(monkeypatch):
    from app.data_generation.seed import _refuse_in_production

    monkeypatch.setenv("APP_ENV", "production")
    assert _refuse_in_production(override=True) is None


def test_seed_cli_exits_without_touching_a_production_database(monkeypatch):
    """End to end: the CLI returns non-zero and never opens a session."""
    from app.data_generation import seed as seed_module

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(
        seed_module,
        "SessionLocal",
        lambda: pytest.fail("the seed opened a database session in production"),
    )

    assert seed_module.main([]) == 2


def test_synthetic_passwords_are_not_hardcoded():
    """No synthetic credential may be readable from the repository.

    The seed used to ship the real coaches' first names together with fixed
    passwords, so anyone with the repo could sign in as a coach anywhere those
    accounts existed.
    """
    first = SyntheticDatasetConfig()
    second = SyntheticDatasetConfig()

    assert first.coach_passwords != second.coach_passwords
    assert first.player_password != second.player_password
    assert all(len(password) >= 12 for password in first.coach_passwords)


def test_synthetic_accounts_cannot_be_mistaken_for_real_ones():
    """Seed names stay unmistakably synthetic.

    'Timo' and 'Denise' are the real coaches. While the seed used those names,
    a seeded account could quietly stand in for a real one - and bootstrap
    would skip creating the real coach because the username already existed.
    """
    cfg = SyntheticDatasetConfig()
    real_names = {"timo", "denise"}

    assert not real_names & {name.lower() for name in cfg.coach_usernames}
    assert not real_names & {name.lower() for name in cfg.coach_names}
    # And no seed team may collide with the real squad: a second team breaks
    # registration, because players then pick a squad their coach cannot see.
    assert "btv aarau f1" not in {name.lower() for name in cfg.team_names}
