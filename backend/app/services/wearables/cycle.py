"""Turn recorded period days into a cycle day and phase.

Devices report *flow per day*; the app's cycle entry wants a cycle day and a
phase. Deriving one from the other is estimation, not measurement, so the rules
here are deliberately simple and explained:

* A **period start** is a day with flow whose previous day had none.
* The **cycle length** is the median gap between the last few period starts -
  the player's own rhythm rather than a textbook 28 - and only when at least
  two starts are known.
* **Ovulation** is placed 14 days before the *next* expected period, because
  the luteal phase is the stable part of the cycle while the follicular phase
  is what varies between people.

Everything here is a suggestion the player confirms. Nothing is written to her
cycle entries without her pressing save.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

DEFAULT_CYCLE_LENGTH = 28
MIN_CYCLE_LENGTH = 20
MAX_CYCLE_LENGTH = 45
DEFAULT_PERIOD_LENGTH = 5
# A gap below this is the same period with a quiet day in it, not a new one.
MIN_GAP_BETWEEN_STARTS = 10


@dataclass(frozen=True)
class CycleEstimate:
    cycle_day: int
    phase: str
    cycle_length: int
    period_start: date
    flow: str | None


def period_starts(flow_by_day: dict[date, str]) -> list[date]:
    """Days where a period begins, oldest first."""
    bleeding = sorted(day for day, flow in flow_by_day.items() if flow and flow != "none")
    starts: list[date] = []
    for day in bleeding:
        previous = day - timedelta(days=1)
        if previous in flow_by_day and flow_by_day[previous] not in (None, "none"):
            continue  # middle of a period
        if starts and (day - starts[-1]).days < MIN_GAP_BETWEEN_STARTS:
            continue  # a quiet day inside the same period
        starts.append(day)
    return starts


def estimate_cycle_length(starts: list[date]) -> int:
    """Her own median cycle length, or the textbook default if unknown."""
    if len(starts) < 2:
        return DEFAULT_CYCLE_LENGTH
    gaps = [
        (later - earlier).days
        for earlier, later in zip(starts, starts[1:])
        if MIN_CYCLE_LENGTH <= (later - earlier).days <= MAX_CYCLE_LENGTH
    ]
    if not gaps:
        return DEFAULT_CYCLE_LENGTH
    # Only the last six cycles: a length from two years ago says little about now.
    return int(round(median(gaps[-6:])))


def period_length(flow_by_day: dict[date, str], start: date) -> int:
    """How many days this period actually lasted, counted from its start."""
    length = 0
    day = start
    while flow_by_day.get(day) not in (None, "none"):
        length += 1
        day += timedelta(days=1)
    return length or DEFAULT_PERIOD_LENGTH


def phase_for(cycle_day: int, cycle_length: int, bleeding_days: int) -> str:
    """Which phase a cycle day falls into."""
    if cycle_day <= max(bleeding_days, 1):
        return "menstruation"
    ovulation_day = max(cycle_length - 14, 10)
    if cycle_day < ovulation_day - 1:
        return "follicular"
    if cycle_day <= ovulation_day + 1:
        return "ovulation"
    return "luteal"


def estimate(flow_by_day: dict[date, str], *, on: date) -> CycleEstimate | None:
    """Estimate the cycle state for ``on``, or None when there is no basis.

    Returns None rather than a guess when the most recent period start is so
    far back that the estimate would be meaningless - better no suggestion
    than a confidently wrong one.
    """
    starts = period_starts(flow_by_day)
    past_starts = [start for start in starts if start <= on]
    if not past_starts:
        return None

    last_start = past_starts[-1]
    cycle_day = (on - last_start).days + 1
    cycle_length = estimate_cycle_length(starts)

    # Two cycles without a single recorded period day means the data stopped,
    # not that she is on day 70.
    if cycle_day > cycle_length * 2:
        return None

    return CycleEstimate(
        cycle_day=cycle_day,
        phase=phase_for(cycle_day, cycle_length, period_length(flow_by_day, last_start)),
        cycle_length=cycle_length,
        period_start=last_start,
        flow=flow_by_day.get(on),
    )
