"""Shared types for the wearable providers.

Every provider reduces its own payload to a list of :class:`DailyMetrics` -
one per calendar day - so the rest of the app never has to know whether a
number came from Whoop, Oura or Apple Health.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class DailyMetrics:
    """One day of device data, already normalised to the app's units."""

    day: date
    sleep_hours: float | None = None
    sleep_score: int | None = None
    readiness_score: int | None = None
    hrv_ms: float | None = None
    resting_hr: float | None = None
    respiratory_rate: float | None = None
    strain: float | None = None
    steps: int | None = None
    active_calories: float | None = None
    workout_minutes: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    METRIC_FIELDS = (
        "sleep_hours",
        "sleep_score",
        "readiness_score",
        "hrv_ms",
        "resting_hr",
        "respiratory_rate",
        "strain",
        "steps",
        "active_calories",
        "workout_minutes",
    )

    def has_values(self) -> bool:
        return any(getattr(self, name) is not None for name in self.METRIC_FIELDS)

    def merge(self, other: DailyMetrics) -> None:
        """Fill blanks from ``other`` without overwriting what we already have.

        Providers expose the same day through several endpoints (Oura splits
        sleep, readiness and activity), so days get merged as they arrive.
        """
        for name in self.METRIC_FIELDS:
            if getattr(self, name) is None:
                setattr(self, name, getattr(other, name))
        for key, value in other.raw.items():
            self.raw.setdefault(key, value)


@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scope: str | None = None
    external_user_id: str | None = None


class WearableError(RuntimeError):
    """A provider call failed in a way the player can act on."""


class WearableAuthError(WearableError):
    """The stored token is no longer valid - the player has to reconnect."""


def as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if result != result else result  # drop NaN


def as_int(value: Any) -> int | None:
    result = as_float(value)
    return None if result is None else int(round(result))


def clamp_score(value: Any) -> int | None:
    """Provider scores are percentages; keep them inside 0-100."""
    result = as_int(value)
    if result is None:
        return None
    return max(0, min(100, result))


def merge_days(batches: list[list[DailyMetrics]]) -> list[DailyMetrics]:
    """Collapse several per-endpoint lists into one entry per day."""
    merged: dict[date, DailyMetrics] = {}
    for batch in batches:
        for item in batch:
            existing = merged.get(item.day)
            if existing is None:
                merged[item.day] = item
            else:
                existing.merge(item)
    return [merged[key] for key in sorted(merged)]
