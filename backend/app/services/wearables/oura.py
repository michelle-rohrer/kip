"""Oura integration (Oura API v2).

Two ways in, because they suit different people:

* **OAuth** - the way in. Needs a registered Oura application; enabled as soon
  as ``OURA_CLIENT_ID``/``OURA_CLIENT_SECRET`` are set.
* **Personal access token** - kept as a fallback for players who still hold
  one. Oura stopped issuing new tokens and will switch the old ones off, so
  this is no longer offered as a route to anybody who does not already have
  one.

Oura already reports a local calendar ``day`` per record, so unlike Whoop there
is no timezone maths to do here.
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
    normalise_flow,
)

PROVIDER = "oura"
DEFAULT_API_BASE = "https://api.ouraring.com"
DEFAULT_AUTH_BASE = "https://cloud.ouraring.com"
# Only what the collections below actually need. "session" was in here and is
# never read - see the Whoop lesson: an unused scope buys nothing and can cost
# the whole authorisation. Override with OURA_SCOPES if Oura renames them.
DEFAULT_SCOPES = "personal daily heartrate workout"


def scopes() -> str:
    return os.getenv("OURA_SCOPES", DEFAULT_SCOPES).strip() or DEFAULT_SCOPES


REQUEST_TIMEOUT = 30.0
MAX_PAGES = 20


def api_base() -> str:
    return os.getenv("OURA_API_BASE", DEFAULT_API_BASE).rstrip("/")


def auth_base() -> str:
    return os.getenv("OURA_AUTH_BASE", DEFAULT_AUTH_BASE).rstrip("/")


def client_id() -> str:
    return os.getenv("OURA_CLIENT_ID", "").strip()


def client_secret() -> str:
    return os.getenv("OURA_CLIENT_SECRET", "").strip()


def is_oauth_configured() -> bool:
    return bool(client_id() and client_secret())


def is_configured() -> bool:
    """Oura needs a registered application.

    This used to return True unconditionally because a personal access token
    always worked. Oura has since stopped issuing new ones, so presenting that
    as a route would send every new player to a page where she cannot get a
    token. Existing tokens still work and the endpoint still accepts them,
    but the app no longer advertises it as the way in.
    """
    return is_oauth_configured()


def authorize_url(*, state: str, redirect_uri: str) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id(),
            "redirect_uri": redirect_uri,
            "scope": scopes(),
            "state": state,
        }
    )
    return f"{auth_base()}/oauth/authorize?{query}"


def _token_request(form: dict[str, str]) -> TokenBundle:
    url = f"{api_base()}/oauth/token"
    try:
        response = httpx.post(url, data=form, timeout=REQUEST_TIMEOUT)
    except httpx.HTTPError as exc:
        raise WearableError(f"Oura is not reachable: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text[:300]
        if response.status_code in (400, 401):
            raise WearableAuthError(f"Oura rejected the token request: {detail}")
        raise WearableError(f"Oura token request failed ({response.status_code}): {detail}")

    payload: dict[str, Any] = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise WearableError("Oura returned no access token")

    expires_in = as_int(payload.get("expires_in")) or 86400
    return TokenBundle(
        access_token=access_token,
        refresh_token=payload.get("refresh_token"),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        scope=payload.get("scope") or scopes(),
    )


def exchange_code(*, code: str, redirect_uri: str) -> TokenBundle:
    return _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id(),
            "client_secret": client_secret(),
        }
    )


def refresh_access_token(refresh_token: str) -> TokenBundle:
    return _token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id(),
            "client_secret": client_secret(),
        }
    )


def verify_token(access_token: str) -> str | None:
    """Check a pasted personal access token and return the Oura user id."""
    url = f"{api_base()}/v2/usercollection/personal_info"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise WearableError(f"Oura is not reachable: {exc}") from exc

    if response.status_code in (401, 403):
        raise WearableAuthError("This Oura token is not valid")
    if response.status_code >= 400:
        raise WearableError(f"Oura request failed ({response.status_code})")

    payload = response.json()
    value = payload.get("id") if isinstance(payload, dict) else None
    return str(value) if value not in (None, "") else None


def _get_documents(
    *,
    collection: str,
    access_token: str,
    start: date,
    end: date,
    skipped: list[str] | None = None,
) -> list[dict[str, Any]]:
    url = f"{api_base()}/v2/usercollection/{collection}"
    params: dict[str, Any] = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    documents: list[dict[str, Any]] = []

    for _ in range(MAX_PAGES):
        try:
            response = httpx.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        except httpx.HTTPError as exc:
            raise WearableError(f"Oura is not reachable: {exc}") from exc

        if response.status_code in (401, 403):
            raise WearableAuthError("Oura access was revoked - please reconnect")
        if response.status_code == 429:
            raise WearableError("Oura rate limit reached - try again later")
        if response.status_code == 404:
            # The scope for this collection was not granted. The rest still
            # syncs, but the caller has to be able to say so - silently
            # returning nothing means the data is missing forever and nobody
            # ever learns why.
            if skipped is not None and collection not in skipped:
                skipped.append(collection)
            return []
        if response.status_code >= 400:
            raise WearableError(f"Oura request failed ({response.status_code}) for {collection}")

        payload = response.json()
        page = payload.get("data") if isinstance(payload, dict) else None
        documents.extend(item for item in (page or []) if isinstance(item, dict))

        next_token = payload.get("next_token") if isinstance(payload, dict) else None
        if not next_token:
            break
        params["next_token"] = next_token

    return documents


def _parse_day(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _daily_sleep_days(documents: list[dict[str, Any]]) -> list[DailyMetrics]:
    out: list[DailyMetrics] = []
    for document in documents:
        day = _parse_day(document.get("day"))
        if day is None:
            continue
        out.append(
            DailyMetrics(
                day=day,
                sleep_score=clamp_score(document.get("score")),
                raw={"daily_sleep": document},
            )
        )
    return out


def _readiness_days(documents: list[dict[str, Any]]) -> list[DailyMetrics]:
    out: list[DailyMetrics] = []
    for document in documents:
        day = _parse_day(document.get("day"))
        if day is None:
            continue
        out.append(
            DailyMetrics(
                day=day,
                readiness_score=clamp_score(document.get("score")),
                raw={"daily_readiness": document},
            )
        )
    return out


def _sleep_detail_days(documents: list[dict[str, Any]]) -> list[DailyMetrics]:
    """Use the main night per day - naps would distort HRV and sleep length."""
    best_per_day: dict[date, dict[str, Any]] = {}
    for document in documents:
        day = _parse_day(document.get("day"))
        if day is None:
            continue
        if document.get("type") in ("rest", "late_nap"):
            continue
        duration = as_float(document.get("total_sleep_duration")) or 0.0
        current = best_per_day.get(day)
        if current is None or duration > (as_float(current.get("total_sleep_duration")) or 0.0):
            best_per_day[day] = document

    out: list[DailyMetrics] = []
    for day, document in best_per_day.items():
        seconds = as_float(document.get("total_sleep_duration"))
        out.append(
            DailyMetrics(
                day=day,
                sleep_hours=round(seconds / 3600, 2) if seconds else None,
                hrv_ms=as_float(document.get("average_hrv")),
                resting_hr=as_float(
                    document.get("lowest_heart_rate") or document.get("average_heart_rate")
                ),
                respiratory_rate=as_float(document.get("average_breath")),
                raw={"sleep": document},
            )
        )
    return out


def _activity_days(documents: list[dict[str, Any]]) -> list[DailyMetrics]:
    out: list[DailyMetrics] = []
    for document in documents:
        day = _parse_day(document.get("day"))
        if day is None:
            continue
        out.append(
            DailyMetrics(
                day=day,
                steps=as_int(document.get("steps")),
                active_calories=as_float(document.get("active_calories")),
                raw={"daily_activity": document},
            )
        )
    return out


def _workout_days(documents: list[dict[str, Any]]) -> list[DailyMetrics]:
    """Day totals plus the longest session's activity, for the training prefill."""
    minutes_by_day: dict[date, float] = {}
    longest: dict[date, tuple[float, str]] = {}

    for document in documents:
        day = _parse_day(document.get("day"))
        start_text = document.get("start_datetime")
        end_text = document.get("end_datetime")
        if day is None or not isinstance(start_text, str) or not isinstance(end_text, str):
            continue
        try:
            started = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
            ended = datetime.fromisoformat(end_text.replace("Z", "+00:00"))
        except ValueError:
            continue
        minutes = (ended - started).total_seconds() / 60.0
        if minutes <= 0:
            continue
        minutes_by_day[day] = minutes_by_day.get(day, 0.0) + minutes

        activity = document.get("activity") or document.get("label")
        if isinstance(activity, str) and activity.strip():
            if day not in longest or minutes > longest[day][0]:
                longest[day] = (minutes, activity.strip()[:64])

    return [
        DailyMetrics(
            day=day,
            workout_minutes=round(minutes, 1),
            workout_sport=longest.get(day, (0.0, None))[1],
        )
        for day, minutes in minutes_by_day.items()
    ]


def _cycle_days(documents: list[dict[str, Any]]) -> list[DailyMetrics]:
    """Oura Cycle Insights, when the account has it.

    The endpoint is missing for accounts without the feature; the caller turns
    a 404 into an empty list, so this simply contributes nothing then.
    """
    out: list[DailyMetrics] = []
    for document in documents:
        day = _parse_day(document.get("day"))
        if day is None:
            continue
        flow = normalise_flow(document.get("period_flow") or document.get("flow"))
        if flow is None and str(document.get("cycle_phase", "")).lower() == "menstrual":
            flow = "medium"
        if flow is None:
            continue
        out.append(DailyMetrics(day=day, menstrual_flow=flow, raw={"daily_cycle_phases": document}))
    return out


def fetch_daily(
    *,
    access_token: str,
    start: date,
    end: date,
    with_cycle: bool = False,
    skipped: list[str] | None = None,
) -> list[DailyMetrics]:
    """Pull the day summaries. Collections Oura refuses land in ``skipped``."""

    def collect(collection: str) -> list[dict[str, Any]]:
        return _get_documents(
            collection=collection,
            access_token=access_token,
            start=start,
            end=end,
            skipped=skipped,
        )

    batches = [
        _sleep_detail_days(collect("sleep")),
        _daily_sleep_days(collect("daily_sleep")),
        _readiness_days(collect("daily_readiness")),
        _activity_days(collect("daily_activity")),
        _workout_days(collect("workout")),
    ]
    if with_cycle:
        # Cycle Insights is not part of every Oura account; a 404 comes back as
        # an empty list, so this is simply skipped where it is unavailable.
        batches.append(_cycle_days(collect("daily_cycle_phases")))
    return merge_days(batches)
