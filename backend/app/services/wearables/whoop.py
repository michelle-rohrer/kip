"""Whoop integration (OAuth 2.0 + Whoop Developer API v2).

Whoop has no personal-token option, so this needs a (free) developer app at
https://developer.whoop.com with the API URL of this backend registered as
redirect URI. Without ``WHOOP_CLIENT_ID``/``WHOOP_CLIENT_SECRET`` the provider
simply reports itself as not configured and the UI hides the connect button.

Endpoint shapes drift between API versions, so every field is read defensively
and the untouched payload is kept in ``raw``.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.services.wearables.base import (
    DailyMetrics,
    TokenBundle,
    WearableAuthError,
    WearableError,
    as_float,
    as_int,
    clamp_score,
    merge_days,
)

PROVIDER = "whoop"
DEFAULT_API_BASE = "https://api.prod.whoop.com"
# Exactly the scopes the four endpoints below need - nothing more. "read:profile"
# used to be in here and was never called; Whoop rejects the whole authorisation
# with invalid_scope when an app has not enabled a requested scope, so asking for
# something unused costs a working connection for no benefit.
# Override with WHOOP_SCOPES if Whoop renames them.
DEFAULT_SCOPES = "read:recovery read:cycles read:sleep read:workout offline"


def scopes() -> str:
    return os.getenv("WHOOP_SCOPES", DEFAULT_SCOPES).strip() or DEFAULT_SCOPES


REQUEST_TIMEOUT = 30.0
PAGE_LIMIT = 25
MAX_PAGES = 20


def api_base() -> str:
    return os.getenv("WHOOP_API_BASE", DEFAULT_API_BASE).rstrip("/")


def client_id() -> str:
    return os.getenv("WHOOP_CLIENT_ID", "").strip()


def client_secret() -> str:
    return os.getenv("WHOOP_CLIENT_SECRET", "").strip()


def is_configured() -> bool:
    return bool(client_id() and client_secret())


def authorize_url(*, state: str, redirect_uri: str) -> str:
    query = urlencode(
        {
            "client_id": client_id(),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes(),
            "state": state,
        }
    )
    return f"{api_base()}/oauth/oauth2/auth?{query}"


def _token_request(form: dict[str, str]) -> TokenBundle:
    url = f"{api_base()}/oauth/oauth2/token"
    try:
        response = httpx.post(url, data=form, timeout=REQUEST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise WearableError(f"Whoop is not reachable: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text[:300]
        if response.status_code in (400, 401):
            raise WearableAuthError(f"Whoop rejected the token request: {detail}")
        raise WearableError(f"Whoop token request failed ({response.status_code}): {detail}")

    payload: dict[str, Any] = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise WearableError("Whoop returned no access token")

    expires_in = as_int(payload.get("expires_in")) or 3600
    return TokenBundle(
        access_token=access_token,
        refresh_token=payload.get("refresh_token"),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        scope=payload.get("scope") or scopes(),
        external_user_id=(
            str(payload["user_id"]) if payload.get("user_id") not in (None, "") else None
        ),
    )


def exchange_code(*, code: str, redirect_uri: str) -> TokenBundle:
    return _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id(),
            "client_secret": client_secret(),
            "redirect_uri": redirect_uri,
        }
    )


def refresh_access_token(refresh_token: str) -> TokenBundle:
    return _token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id(),
            "client_secret": client_secret(),
            "scope": "offline",
        }
    )


def _parse_instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _local_day(value: Any, offset: Any) -> date | None:
    """Whoop timestamps are UTC; ``timezone_offset`` says where the player was.

    Without applying it, a late-evening session in Europe lands on the wrong
    calendar day for anybody west of UTC - and the whole app is keyed by day.
    """
    instant = _parse_instant(value)
    if instant is None:
        return None
    if isinstance(offset, str) and len(offset) >= 6 and offset[0] in "+-":
        try:
            sign = 1 if offset[0] == "+" else -1
            hours, minutes = int(offset[1:3]), int(offset[4:6])
            instant = instant + sign * timedelta(hours=hours, minutes=minutes)
        except ValueError:
            pass
    return instant.date()


def _get_records(*, path: str, access_token: str, start: date, end: date) -> list[dict[str, Any]]:
    url = f"{api_base()}{path}"
    params: dict[str, Any] = {
        "start": f"{start.isoformat()}T00:00:00.000Z",
        # Whoop treats ``end`` as exclusive, so ask for the day after the range.
        "end": f"{(end + timedelta(days=1)).isoformat()}T00:00:00.000Z",
        "limit": PAGE_LIMIT,
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    records: list[dict[str, Any]] = []

    for _ in range(MAX_PAGES):
        try:
            response = httpx.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        except httpx.HTTPError as exc:
            raise WearableError(f"Whoop is not reachable: {exc}") from exc

        if response.status_code in (401, 403):
            raise WearableAuthError("Whoop access was revoked - please reconnect")
        if response.status_code == 429:
            raise WearableError("Whoop rate limit reached - try again later")
        if response.status_code >= 400:
            raise WearableError(f"Whoop request failed ({response.status_code}) for {path}")

        payload = response.json()
        page = payload.get("records") if isinstance(payload, dict) else None
        records.extend(item for item in (page or []) if isinstance(item, dict))

        next_token = payload.get("next_token") if isinstance(payload, dict) else None
        if not next_token:
            break
        params["nextToken"] = next_token

    return records


def _recovery_days(records: list[dict[str, Any]]) -> list[DailyMetrics]:
    out: list[DailyMetrics] = []
    for record in records:
        day = _local_day(record.get("created_at") or record.get("updated_at"), None)
        if day is None:
            continue
        score = record.get("score") or {}
        out.append(
            DailyMetrics(
                day=day,
                readiness_score=clamp_score(score.get("recovery_score")),
                hrv_ms=as_float(score.get("hrv_rmssd_milli")),
                resting_hr=as_float(score.get("resting_heart_rate")),
                raw={"recovery": record},
            )
        )
    return out


def _sleep_days(records: list[dict[str, Any]]) -> list[DailyMetrics]:
    out: list[DailyMetrics] = []
    for record in records:
        if record.get("nap") is True:
            continue
        # The night counts for the day the player wakes up on.
        day = _local_day(record.get("end"), record.get("timezone_offset"))
        if day is None:
            continue
        score = record.get("score") or {}
        stages = score.get("stage_summary") or {}
        in_bed = as_float(stages.get("total_in_bed_time_milli"))
        awake = as_float(stages.get("total_awake_time_milli")) or 0.0
        sleep_hours = None
        if in_bed is not None:
            sleep_hours = round(max(in_bed - awake, 0.0) / 3_600_000, 2)
        out.append(
            DailyMetrics(
                day=day,
                sleep_hours=sleep_hours,
                sleep_score=clamp_score(score.get("sleep_performance_percentage")),
                respiratory_rate=as_float(score.get("respiratory_rate")),
                raw={"sleep": record},
            )
        )
    return out


def _cycle_days(records: list[dict[str, Any]]) -> list[DailyMetrics]:
    out: list[DailyMetrics] = []
    for record in records:
        day = _local_day(record.get("start"), record.get("timezone_offset"))
        if day is None:
            continue
        score = record.get("score") or {}
        kilojoule = as_float(score.get("kilojoule"))
        out.append(
            DailyMetrics(
                day=day,
                strain=as_float(score.get("strain")),
                active_calories=round(kilojoule / 4.184, 1) if kilojoule is not None else None,
                raw={"cycle": record},
            )
        )
    return out


def _workout_days(records: list[dict[str, Any]]) -> list[DailyMetrics]:
    """Day totals plus the longest session's sport, for the training prefill."""
    minutes_by_day: dict[date, float] = {}
    longest: dict[date, tuple[float, str]] = {}

    for record in records:
        day = _local_day(record.get("start"), record.get("timezone_offset"))
        started = _parse_instant(record.get("start"))
        ended = _parse_instant(record.get("end"))
        if day is None or started is None or ended is None:
            continue
        minutes = (ended - started).total_seconds() / 60.0
        if minutes <= 0:
            continue
        minutes_by_day[day] = minutes_by_day.get(day, 0.0) + minutes

        sport = record.get("sport_name") or record.get("sport")
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


def fetch_daily(*, access_token: str, start: date, end: date) -> list[DailyMetrics]:
    recovery = _get_records(
        path="/developer/v2/recovery", access_token=access_token, start=start, end=end
    )
    sleep = _get_records(
        path="/developer/v2/activity/sleep", access_token=access_token, start=start, end=end
    )
    cycles = _get_records(
        path="/developer/v2/cycle", access_token=access_token, start=start, end=end
    )
    workouts = _get_records(
        path="/developer/v2/activity/workout", access_token=access_token, start=start, end=end
    )
    return merge_days(
        [
            _recovery_days(recovery),
            _sleep_days(sleep),
            _cycle_days(cycles),
            _workout_days(workouts),
        ]
    )
