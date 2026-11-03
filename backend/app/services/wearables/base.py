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
    workout_sport: str | None = None
    menstrual_flow: str | None = None
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
        "workout_sport",
        "menstrual_flow",
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


FLOW_LEVELS = ("none", "light", "medium", "heavy")

# What the different exports call a period day. Numbers come from Apple Health
# (1 = unspecified, 2 = light, 3 = medium, 4 = heavy), words from everything else.
_FLOW_ALIASES: dict[str, str] = {
    "1": "light",
    "2": "light",
    "3": "medium",
    "4": "heavy",
    "5": "heavy",
    "0": "none",
    "none": "none",
    "nonflow": "none",
    "no": "none",
    "false": "none",
    "unspecified": "light",
    "light": "light",
    "leicht": "light",
    "medium": "medium",
    "moderate": "medium",
    "mittel": "medium",
    "heavy": "heavy",
    "stark": "heavy",
    "true": "medium",
    "yes": "medium",
}


def normalise_flow(value: Any) -> str | None:
    """Map whatever a device calls a period day onto none/light/medium/heavy."""
    if value is None or isinstance(value, bool) and value is False:
        return None
    if value is True:
        return "medium"
    text = str(value).strip().lower()
    if not text:
        return None
    if text in _FLOW_ALIASES:
        return _FLOW_ALIASES[text]
    # "2.0" and the like
    try:
        return _FLOW_ALIASES[str(int(float(text)))]
    except (ValueError, KeyError):
        return None


# Device sport labels that mean "this was the volleyball session", so the app
# can pre-fill the session type instead of guessing.
_TEAM_SPORTS = {"volleyball", "beach_volleyball", "beach volleyball", "handball", "basketball"}
_STRENGTH_SPORTS = {"weightlifting", "strength", "functional_strength_training", "krafttraining"}
_RECOVERY_SPORTS = {"yoga", "stretching", "pilates", "mobility", "walking", "meditation"}


def session_type_for(sport: str | None) -> str | None:
    """Our session type for a device sport label, or None when unsure.

    Returning None on purpose when the sport is unknown: a bike ride is not a
    volleyball session, and quietly calling it "team" would feed the model a
    training that never happened.
    """
    if not sport:
        return None
    key = sport.strip().lower().replace("-", "_")
    if key in _TEAM_SPORTS:
        return "team"
    if key in _STRENGTH_SPORTS:
        return "strength"
    if key in _RECOVERY_SPORTS:
        return "recovery"
    return None


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
