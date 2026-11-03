"""Deriving cycle day and phase from recorded period days."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.wearables.base import normalise_flow
from app.services.wearables.cycle import (
    DEFAULT_CYCLE_LENGTH,
    estimate,
    estimate_cycle_length,
    period_starts,
)


def _bleed(start: date, days: int = 5) -> dict[date, str]:
    return {start + timedelta(days=i): "medium" for i in range(days)}


def test_a_period_start_is_the_first_day_of_a_run() -> None:
    flow = _bleed(date(2026, 10, 1)) | _bleed(date(2026, 10, 29))
    assert period_starts(flow) == [date(2026, 10, 1), date(2026, 10, 29)]


def test_a_quiet_day_inside_a_period_does_not_start_a_new_one() -> None:
    flow = {
        date(2026, 10, 1): "medium",
        date(2026, 10, 2): "light",
        # day 3 missing entirely
        date(2026, 10, 4): "light",
    }
    assert period_starts(flow) == [date(2026, 10, 1)]


def test_cycle_length_follows_her_own_rhythm() -> None:
    starts = [date(2026, 7, 1), date(2026, 7, 27), date(2026, 8, 22), date(2026, 9, 17)]
    # 26 days between each
    assert estimate_cycle_length(starts) == 26


def test_cycle_length_falls_back_to_the_default_without_history() -> None:
    assert estimate_cycle_length([date(2026, 10, 1)]) == DEFAULT_CYCLE_LENGTH
    assert estimate_cycle_length([]) == DEFAULT_CYCLE_LENGTH


def test_implausible_gaps_are_ignored() -> None:
    # A year-long gap is missing data, not a 365-day cycle.
    starts = [date(2025, 1, 1), date(2026, 9, 1), date(2026, 9, 29)]
    assert estimate_cycle_length(starts) == 28


def test_phases_across_one_cycle() -> None:
    flow = _bleed(date(2026, 10, 1)) | _bleed(date(2026, 10, 29))
    seen = {
        day: estimate(flow, on=date(2026, 10, day)).phase for day in (1, 3, 5, 9, 14, 15, 20, 27)
    }
    assert seen[1] == "menstruation"
    assert seen[5] == "menstruation"
    assert seen[9] == "follicular"
    assert seen[14] == "ovulation"
    assert seen[20] == "luteal"
    assert seen[27] == "luteal"


def test_cycle_day_counts_from_the_period_start() -> None:
    flow = _bleed(date(2026, 10, 1))
    assert estimate(flow, on=date(2026, 10, 1)).cycle_day == 1
    assert estimate(flow, on=date(2026, 10, 12)).cycle_day == 12


def test_no_estimate_without_any_recorded_period() -> None:
    assert estimate({}, on=date(2026, 10, 12)) is None


def test_no_estimate_when_the_data_simply_stopped() -> None:
    """Three months after the last period, a cycle day would be nonsense."""
    flow = _bleed(date(2026, 6, 1))
    assert estimate(flow, on=date(2026, 10, 12)) is None


def test_todays_flow_is_reported_back() -> None:
    flow = _bleed(date(2026, 10, 1))
    assert estimate(flow, on=date(2026, 10, 2)).flow == "medium"
    assert estimate(flow, on=date(2026, 10, 10)).flow is None


def test_flow_labels_from_different_exports() -> None:
    assert normalise_flow(2) == "light"
    assert normalise_flow("3") == "medium"
    assert normalise_flow("heavy") == "heavy"
    assert normalise_flow("stark") == "heavy"
    assert normalise_flow(True) == "medium"
    assert normalise_flow(False) is None
    assert normalise_flow("none") == "none"
    assert normalise_flow("") is None
    assert normalise_flow("voellig unbekannt") is None
