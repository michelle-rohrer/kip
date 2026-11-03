"""Apple Health / Apple Watch ingestion.

Apple deliberately has no cloud API for Health data - it never leaves the
phone unless the owner sends it. So instead of pulling, the phone pushes:
the player gets a personal ingest token and sets up either

* an **iOS shortcut** ("Kurzbefehl") with a daily automation that POSTs a few
  health values, or
* the **Health Auto Export** app, pointed at the same URL.

Both payload shapes are accepted here, plus a plain ``{"date": ..., ...}``
object so the endpoint can be tested with a single curl call.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.services.wearables.base import (
    DailyMetrics,
    WearableError,
    as_float,
    as_int,
    clamp_score,
    merge_days,
    normalise_flow,
)

PROVIDER = "apple_health"

# Health Auto Export metric identifier -> field on DailyMetrics.
_METRIC_FIELDS: dict[str, str] = {
    "heart_rate_variability": "hrv_ms",
    "resting_heart_rate": "resting_hr",
    "respiratory_rate": "respiratory_rate",
    "step_count": "steps",
    "active_energy": "active_calories",
    "apple_exercise_time": "workout_minutes",
    "sleep_analysis": "sleep_hours",
}

# Period tracking in the iPhone Health app. Only read when the player switched
# cycle sync on for Apple Health - see ``service.store_days``.
_FLOW_METRICS = {"menstrual_flow", "menstruation", "sexual_activity_menstrual_flow"}

# Keys accepted in the simple shortcut payload, mapped to the same fields.
_SIMPLE_FIELDS: dict[str, str] = {
    "sleep_hours": "sleep_hours",
    "sleep": "sleep_hours",
    "sleep_score": "sleep_score",
    "readiness": "readiness_score",
    "readiness_score": "readiness_score",
    "hrv": "hrv_ms",
    "hrv_ms": "hrv_ms",
    "heart_rate_variability": "hrv_ms",
    "resting_hr": "resting_hr",
    "resting_heart_rate": "resting_hr",
    "respiratory_rate": "respiratory_rate",
    "steps": "steps",
    "step_count": "steps",
    "active_calories": "active_calories",
    "active_energy": "active_calories",
    "workout_minutes": "workout_minutes",
    "exercise_minutes": "workout_minutes",
    "workout_sport": "workout_sport",
    "sport": "workout_sport",
    "menstrual_flow": "menstrual_flow",
    "menstruation": "menstrual_flow",
    "period": "menstrual_flow",
}

_INT_FIELDS = {"steps", "sleep_score", "readiness_score"}
_SCORE_FIELDS = {"sleep_score", "readiness_score"}


def _parse_day(value: Any) -> date | None:
    """Accept ``2026-11-03`` as well as ``2026-11-03 07:15:00 +0100``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _assign(target: DailyMetrics, field: str, value: Any) -> None:
    if field == "menstrual_flow":
        parsed: Any = normalise_flow(value)
    elif field == "workout_sport":
        parsed = str(value).strip()[:64] or None if value is not None else None
    elif field in _SCORE_FIELDS:
        parsed = clamp_score(value)
    elif field in _INT_FIELDS:
        parsed = as_int(value)
    else:
        parsed = as_float(value)
    if parsed is not None:
        setattr(target, field, parsed)


def _to_kcal(value: float | None, units: Any) -> float | None:
    """Health exports energy in kJ or kcal depending on the phone's settings."""
    if value is None:
        return None
    if isinstance(units, str) and units.strip().lower() in ("kj", "kilojoule", "kilojoules"):
        return round(value / 4.184, 1)
    return round(value, 1)


def _parse_metrics(metrics: list[Any]) -> list[DailyMetrics]:
    by_day: dict[date, DailyMetrics] = {}

    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        name = str(metric.get("name", "")).strip().lower()

        if name in _FLOW_METRICS:
            for sample in metric.get("data") or []:
                if not isinstance(sample, dict):
                    continue
                day = _parse_day(sample.get("date"))
                if day is None:
                    continue
                flow = normalise_flow(
                    sample.get("flow")
                    if sample.get("flow") is not None
                    else sample.get("value", sample.get("qty"))
                )
                if flow is not None:
                    entry = by_day.setdefault(
                        day, DailyMetrics(day=day, raw={"source": "apple_health"})
                    )
                    entry.menstrual_flow = flow
            continue

        field = _METRIC_FIELDS.get(name)
        if field is None:
            continue
        units = metric.get("units")

        for sample in metric.get("data") or []:
            if not isinstance(sample, dict):
                continue
            day = _parse_day(sample.get("date") or sample.get("sleepEnd"))
            if day is None:
                continue
            entry = by_day.setdefault(day, DailyMetrics(day=day, raw={"source": "apple_health"}))

            if field == "sleep_hours":
                # Health Auto Export reports sleep in hours, split by stage.
                asleep = as_float(sample.get("asleep"))
                if asleep is None:
                    stages = [
                        as_float(sample.get("core")),
                        as_float(sample.get("deep")),
                        as_float(sample.get("rem")),
                    ]
                    known = [value for value in stages if value is not None]
                    asleep = sum(known) if known else as_float(sample.get("qty"))
                if asleep is not None:
                    entry.sleep_hours = round(asleep, 2)
                continue

            quantity = as_float(sample.get("qty"))
            if quantity is None:
                quantity = as_float(sample.get("Avg") or sample.get("avg"))
            if field == "active_calories":
                quantity = _to_kcal(quantity, units)
            _assign(entry, field, quantity)

    return list(by_day.values())


def _workout_minutes(workout: dict[str, Any]) -> float | None:
    """Minutes of a single workout.

    Start and end are preferred because they are unambiguous. ``duration`` is
    only a fallback: Health Auto Export reports it in seconds, and guessing the
    unit from the magnitude would turn a long hike into six minutes.
    """
    start_text, end_text = workout.get("start"), workout.get("end")
    if isinstance(start_text, str) and isinstance(end_text, str):
        try:
            started = datetime.fromisoformat(start_text[:19].replace(" ", "T"))
            ended = datetime.fromisoformat(end_text[:19].replace(" ", "T"))
        except ValueError:
            pass
        else:
            minutes = (ended - started).total_seconds() / 60.0
            if minutes > 0:
                return minutes

    seconds = as_float(workout.get("duration"))
    return seconds / 60.0 if seconds and seconds > 0 else None


def _parse_workouts(workouts: list[Any]) -> list[DailyMetrics]:
    """Sum the day's workout minutes and remember the longest session's sport.

    The longest session is the one worth pre-filling a training entry with -
    a ten-minute walk should not relabel an evening of volleyball.
    """
    minutes_by_day: dict[date, float] = {}
    longest: dict[date, tuple[float, str]] = {}

    for workout in workouts:
        if not isinstance(workout, dict):
            continue
        day = _parse_day(workout.get("start") or workout.get("date"))
        if day is None:
            continue
        minutes = _workout_minutes(workout)
        if minutes is None:
            continue
        minutes_by_day[day] = minutes_by_day.get(day, 0.0) + minutes

        sport = workout.get("name") or workout.get("workoutActivityType") or workout.get("type")
        if isinstance(sport, str) and sport.strip():
            if day not in longest or minutes > longest[day][0]:
                longest[day] = (minutes, sport.strip()[:64])

    return [
        DailyMetrics(
            day=day,
            workout_minutes=round(minutes, 1),
            workout_sport=longest.get(day, (0.0, None))[1],
        )
        for day, minutes in minutes_by_day.items()
    ]


def _parse_simple(entry: dict[str, Any]) -> DailyMetrics | None:
    day = _parse_day(entry.get("date") or entry.get("day"))
    if day is None:
        return None
    metrics = DailyMetrics(day=day, raw={"source": "apple_health"})
    for key, value in entry.items():
        field = _SIMPLE_FIELDS.get(str(key).strip().lower())
        if field is not None:
            _assign(metrics, field, value)
    return metrics


def parse_payload(payload: Any) -> list[DailyMetrics]:
    """Turn any supported ingest body into one entry per day.

    Raises :class:`WearableError` when nothing usable was found, so the phone
    gets a clear error instead of a silent 200 that drops the data.
    """
    batches: list[list[DailyMetrics]] = []

    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            metrics = data.get("metrics")
            if isinstance(metrics, list):
                batches.append(_parse_metrics(metrics))
            workouts = data.get("workouts")
            if isinstance(workouts, list):
                batches.append(_parse_workouts(workouts))

        for key in ("days", "entries", "samples"):
            items = payload.get(key)
            if isinstance(items, list):
                batches.append(
                    [
                        parsed
                        for item in items
                        if isinstance(item, dict) and (parsed := _parse_simple(item)) is not None
                    ]
                )

        if not batches:
            single = _parse_simple(payload)
            if single is not None:
                batches.append([single])

    elif isinstance(payload, list):
        batches.append(
            [
                parsed
                for item in payload
                if isinstance(item, dict) and (parsed := _parse_simple(item)) is not None
            ]
        )

    days = [item for item in merge_days(batches) if item.has_values()]
    if not days:
        raise WearableError(
            "No usable health values found. Expected either a Health Auto Export "
            'payload or an object like {"date": "2026-11-03", "sleep_hours": 7.5}.'
        )
    return days
