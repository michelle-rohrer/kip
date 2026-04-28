from datetime import date

import numpy as np
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
