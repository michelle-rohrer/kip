"""Generate correlated synthetic cycle, wellness, training, and injury data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import uuid4

import numpy as np

from app.models import (
    CycleEntry,
    CyclePhase,
    InjuryEntry,
    PrivacyConsent,
    Team,
    TrainingEntry,
    User,
    UserRole,
    WellnessEntry,
)
from app.services.auth import hash_password

BODY_LOCATIONS = (
    "Knie",
    "Sprunggelenk",
    "Schulter",
    "Unterer Rücken",
    "Oberschenkel",
    "Fuß",
    "Hüfte",
    "Handgelenk",
)


def _clip_int(x: float, lo: int, hi: int) -> int:
    return int(np.clip(round(x), lo, hi))


def _sample_cycle_length(rng: np.random.Generator) -> int:
    raw = rng.normal(29.0, 2.0)
    return int(np.clip(round(raw), 26, 32))


def _phase_for_day(cycle_day: int, cycle_length: int) -> CyclePhase:
    if cycle_day <= 5:
        return CyclePhase.MENSTRUATION
    if cycle_day <= 12:
        return CyclePhase.FOLLICULAR
    if cycle_day <= 15:
        return CyclePhase.OVULATION
    if cycle_day <= cycle_length:
        return CyclePhase.LUTEAL
    return CyclePhase.LUTEAL


def _cycle_day_for_date(anchor: date, cycle_length: int, d: date) -> int:
    delta = (d - anchor).days % cycle_length
    return delta + 1


@dataclass(frozen=True)
class SyntheticDatasetConfig:
    """Configuration for synthetic data generation."""

    num_players: int = 18
    days_min: int = 90
    days_max: int = 180
    team_names: tuple[str, str] = ("BTV Aarau F1", "Eaglets NNV")
    coach_usernames: tuple[str, str] = ("Timo", "Denise")
    coach_names: tuple[str, str] = ("Timo", "Denise")
    coach_passwords: tuple[str, str] = ("Killerlippi610", "cazzo!")
    player_password: str = "synthetic-seed-password"
    random_seed: int | None = 42


def build_privacy_consents(
    *,
    coaches: Sequence[User],
    players: Sequence[User],
    rng: np.random.Generator,
) -> list[PrivacyConsent]:
    """Create one consent row per player and synthetic coach."""
    _ = rng
    rows: list[PrivacyConsent] = []
    for coach in coaches:
        for player in players:
            rows.append(
                PrivacyConsent(
                    player=player,
                    coach=coach,
                    share_cycle_data=False,
                    share_wellness_data=False,
                )
            )
    return rows


def build_synthetic_dataset(
    *,
    rng: np.random.Generator,
    end_date: date | None = None,
    config: SyntheticDatasetConfig | None = None,
) -> tuple[
    list[Team],
    list[User],
    list[User],
    list[CycleEntry],
    list[WellnessEntry],
    list[TrainingEntry],
    list[InjuryEntry],
]:
    """Build in-memory model instances (not persisted)."""
    cfg = config or SyntheticDatasetConfig()
    if end_date is None:
        end_date = date.today()

    n_players = int(np.clip(cfg.num_players, 15, 20))
    teams = [Team(name=cfg.team_names[0]), Team(name=cfg.team_names[1])]
    coaches = [
        User(
            username=cfg.coach_usernames[0],
            email=None,
            password_hash=hash_password(cfg.coach_passwords[0]),
            role=UserRole.COACH,
            team_id=None,
            name=cfg.coach_names[0],
        ),
        User(
            username=cfg.coach_usernames[1],
            email=None,
            password_hash=hash_password(cfg.coach_passwords[1]),
            role=UserRole.COACH,
            team_id=None,
            name=cfg.coach_names[1],
        ),
    ]

    players: list[User] = []
    for i in range(n_players):
        players.append(
            User(
                username=f"player.{i + 1:02d}",
                email=f"synthetic.player.{i + 1:02d}@kip.local",
                password_hash=hash_password(cfg.player_password),
                role=UserRole.PLAYER,
                team_id=None,
                training_uid=uuid4().hex,
                name=f"Synthetic Player {i + 1:02d}",
            )
        )

    cycle_rows: list[CycleEntry] = []
    wellness_rows: list[WellnessEntry] = []
    training_rows: list[TrainingEntry] = []
    injury_rows: list[InjuryEntry] = []

    for p_idx, player in enumerate(players):
        player_rng = np.random.default_rng(
            (int(rng.integers(0, 2**31)) ^ (p_idx * 100_003)) & 0x7FFFFFFF
        )
        n_days = int(player_rng.integers(cfg.days_min, cfg.days_max + 1))
        start_date = end_date - timedelta(days=n_days - 1)

        cycle_length = _sample_cycle_length(player_rng)
        anchor_offset = int(player_rng.integers(0, cycle_length))
        cycle_anchor = start_date - timedelta(days=anchor_offset)

        contraception = None
        if player_rng.random() < 0.25:
            contraception = player_rng.choice(["Pille", "IUP", "Implantat"])

        daily_load: list[float] = []
        daily_intensity: list[int] = []
        daily_duration: list[int] = []

        for day_i in range(n_days):
            d = start_date + timedelta(days=day_i)
            dow = d.weekday()

            if dow == 6:
                daily_load.append(0.0)
                daily_intensity.append(0)
                daily_duration.append(0)
                continue

            week_idx = (d - start_date).days // 7
            is_load_week = (week_idx // 3) % 2 == 0
            base_int = player_rng.integers(5, 9) if is_load_week else player_rng.integers(3, 6)
            noise = int(player_rng.integers(-1, 2))
            intensity = int(np.clip(base_int + noise, 1, 10))
            duration = int(player_rng.integers(55, 125))
            if not is_load_week:
                duration = int(player_rng.integers(40, 85))

            load = float(intensity) * (duration / 90.0)
            daily_load.append(load)
            daily_intensity.append(intensity)
            daily_duration.append(duration)

            training_rows.append(
                TrainingEntry(
                    player=player,
                    date=d,
                    duration_min=duration,
                    intensity=intensity,
                    session_rpe=None,
                    session_type=None,
                    strength_values=None,
                )
            )

        for day_i in range(n_days):
            d = start_date + timedelta(days=day_i)
            cd = _cycle_day_for_date(cycle_anchor, cycle_length, d)
            phase = _phase_for_day(cd, cycle_length)

            pms_base = 0.0
            if phase == CyclePhase.LUTEAL:
                late = max(0, cd - 18)
                pms_base = 2.0 + late * 0.35
            pms_score = None
            if phase in (CyclePhase.LUTEAL, CyclePhase.MENSTRUATION) and player_rng.random() < 0.85:
                pms_score = _clip_int(pms_base + player_rng.normal(0, 1.2), 0, 10)

            cramps = phase == CyclePhase.MENSTRUATION and player_rng.random() < 0.42
            migraine = (phase == CyclePhase.LUTEAL and player_rng.random() < 0.12) or (
                phase == CyclePhase.MENSTRUATION and player_rng.random() < 0.08
            )
            fatigue = (
                phase in (CyclePhase.MENSTRUATION, CyclePhase.LUTEAL) and player_rng.random() < 0.28
            ) or (phase == CyclePhase.OVULATION and player_rng.random() < 0.1)

            cycle_rows.append(
                CycleEntry(
                    player=player,
                    date=d,
                    cycle_day=cd,
                    phase=phase,
                    cycle_length=cycle_length,
                    pms_score=pms_score,
                    cramps=cramps,
                    migraine=migraine,
                    fatigue=fatigue,
                    contraception_type=contraception,
                    notes=None,
                )
            )

            prev_i = day_i - 1
            prev_load = daily_load[prev_i] if prev_i >= 0 else 0.0
            prev_intensity = daily_intensity[prev_i] if prev_i >= 0 else 0

            sleep_quality = _clip_int(player_rng.normal(6.5, 1.4), 1, 10)
            if phase == CyclePhase.LUTEAL:
                sleep_quality = _clip_int(sleep_quality - player_rng.uniform(0.3, 1.2), 1, 10)
            if fatigue:
                sleep_quality = _clip_int(sleep_quality - player_rng.uniform(0.5, 1.5), 1, 10)

            sleep_hours = float(
                np.clip(player_rng.normal(7.2 + (sleep_quality - 6) * 0.15, 0.85), 4.5, 10.5)
            )

            mental_energy = _clip_int(
                0.55 * sleep_quality + 2.8 + player_rng.normal(0, 1.15), 1, 10
            )

            muscle_soreness = _clip_int(
                2.5
                + 0.55 * prev_load
                + (1.2 if phase in (CyclePhase.MENSTRUATION, CyclePhase.LUTEAL) else 0)
                + player_rng.normal(0, 1.0),
                1,
                10,
            )

            stress_level = _clip_int(player_rng.normal(5.0, 1.5), 1, 10)
            if pms_score is not None and pms_score >= 6:
                stress_level = _clip_int(stress_level + player_rng.uniform(0.5, 2.0), 1, 10)

            motivation = _clip_int(
                6.5 - 0.35 * muscle_soreness + 0.2 * mental_energy + player_rng.normal(0, 1.2),
                1,
                10,
            )

            rpe_prev = None
            if prev_i >= 0 and prev_intensity > 0:
                rpe_prev = _clip_int(
                    prev_intensity * 0.65 + (prev_load / 3.0) * 2 + player_rng.normal(0, 0.9),
                    1,
                    10,
                )

            wellness_rows.append(
                WellnessEntry(
                    player=player,
                    date=d,
                    sleep_hours=sleep_hours,
                    sleep_quality=sleep_quality,
                    muscle_soreness=muscle_soreness,
                    mental_energy=mental_energy,
                    stress_level=stress_level,
                    motivation=motivation,
                    rpe_previous_day=rpe_prev,
                    free_text=None,
                )
            )

            lo = max(0, day_i - 6)
            hi7 = day_i + 1
            acute = float(sum(daily_load[lo:hi7]))
            lo28 = max(0, day_i - 27)
            chronic_window = daily_load[lo28 : day_i + 1]
            chronic = float(sum(chronic_window) / 4.0) if chronic_window else 0.0
            acwr = acute / chronic if chronic > 1e-6 else 1.0

            injury_base = 0.002
            if acwr > 1.35:
                injury_base += 0.012 * min(acwr - 1.35, 1.5)
            if phase in (CyclePhase.MENSTRUATION, CyclePhase.LUTEAL):
                injury_base += 0.004
            if muscle_soreness >= 8:
                injury_base += 0.006

            if player_rng.random() < injury_base:
                loc = str(player_rng.choice(BODY_LOCATIONS))
                pain = _clip_int(player_rng.integers(3, 9) + (2 if acwr > 1.4 else 0), 1, 10)
                injury_rows.append(
                    InjuryEntry(
                        player=player,
                        date=d,
                        body_location=loc,
                        pain_intensity=pain,
                        is_chronic=bool(player_rng.random() < 0.15),
                        medical_attention=False,
                        time_loss_days=None,
                        description="Synthetischer Eintrag (Seed)",
                    )
                )

    return teams, coaches, players, cycle_rows, wellness_rows, training_rows, injury_rows
