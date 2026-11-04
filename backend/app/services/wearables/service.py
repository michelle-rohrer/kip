"""Connection handling and sync orchestration for all wearable providers."""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, WearableConnection, WearableDaily, WearableProvider
from app.services.crypto import decrypt_secret, encrypt_secret, hash_ingest_token
from app.services.wearables import apple_health, oura, whoop
from app.services.wearables.base import (
    DailyMetrics,
    TokenBundle,
    WearableAuthError,
    WearableError,
    session_type_for,
)
from app.services.wearables.cycle import estimate as cycle_estimate

logger = logging.getLogger(__name__)

DEFAULT_SYNC_DAYS = 14
MAX_SYNC_DAYS = 60
STATE_TOKEN_MINUTES = 10
_STATE_TOKEN_TYPE = "wearable_state"
_TOKEN_REFRESH_MARGIN = timedelta(minutes=2)


@dataclass(frozen=True)
class SyncSummary:
    provider: WearableProvider
    days_written: int
    first_day: date | None
    last_day: date | None
    synced_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------ helpers


def parse_provider(value: str) -> WearableProvider:
    """Accept both ``apple_health`` and the URL-friendly ``apple-health``."""
    normalised = value.strip().lower().replace("-", "_")
    try:
        return WearableProvider(normalised)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider '{value}'",
        ) from exc


def api_base_url() -> str:
    return os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def frontend_base_url() -> str:
    configured = os.getenv("FRONTEND_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    # Fall back to the first allowed CORS origin - in practice that is the app.
    origins = [
        origin.strip().rstrip("/")
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    return origins[0] if origins else "http://localhost:5173"


def redirect_uri(provider: WearableProvider) -> str:
    return f"{api_base_url()}/api/integrations/callback/{provider.value}"


def ingest_url() -> str:
    return f"{api_base_url()}/api/integrations/apple-health/ingest"


def is_configured(provider: WearableProvider) -> bool:
    if provider is WearableProvider.WHOOP:
        return whoop.is_configured()
    if provider is WearableProvider.OURA:
        return oura.is_configured()
    return True


def supports_oauth(provider: WearableProvider) -> bool:
    if provider is WearableProvider.WHOOP:
        return whoop.is_configured()
    if provider is WearableProvider.OURA:
        return oura.is_oauth_configured()
    return False


# ------------------------------------------------------------- state tokens


def build_state_token(*, player_id: int, provider: WearableProvider) -> str:
    from app.services.auth import JWT_ALGORITHM, JWT_SECRET_KEY

    now = _now()
    payload = {
        "sub": str(player_id),
        "provider": provider.value,
        "type": _STATE_TOKEN_TYPE,
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=STATE_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def read_state_token(token: str, *, provider: WearableProvider) -> int:
    from app.services.auth import JWT_ALGORITHM, JWT_SECRET_KEY

    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="The connection link expired - please start again in the app.",
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise invalid from exc
    if payload.get("type") != _STATE_TOKEN_TYPE or payload.get("provider") != provider.value:
        raise invalid
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise invalid from exc


# -------------------------------------------------------------- connections


def get_connection(
    db: Session, *, player_id: int, provider: WearableProvider
) -> WearableConnection | None:
    return db.execute(
        select(WearableConnection).where(
            WearableConnection.player_id == player_id,
            WearableConnection.provider == provider,
        )
    ).scalar_one_or_none()


def _upsert_connection(
    db: Session, *, player_id: int, provider: WearableProvider
) -> WearableConnection:
    connection = get_connection(db, player_id=player_id, provider=provider)
    if connection is None:
        connection = WearableConnection(player_id=player_id, provider=provider)
        db.add(connection)
    return connection


def store_tokens(
    db: Session,
    *,
    player_id: int,
    provider: WearableProvider,
    bundle: TokenBundle,
) -> WearableConnection:
    connection = _upsert_connection(db, player_id=player_id, provider=provider)
    connection.access_token = encrypt_secret(bundle.access_token)
    if bundle.refresh_token:
        connection.refresh_token = encrypt_secret(bundle.refresh_token)
    connection.token_expires_at = bundle.expires_at
    connection.scope = bundle.scope
    if bundle.external_user_id:
        connection.external_user_id = bundle.external_user_id
    connection.last_error = None
    # A new authorisation may carry different scopes or a changed plan, so what
    # we learned about the old one no longer applies.
    connection.cycle_unavailable = False
    connection.updated_at = _now()
    db.commit()
    db.refresh(connection)
    return connection


def rotate_ingest_token(db: Session, *, player_id: int) -> tuple[WearableConnection, str]:
    """Create a fresh Apple Health ingest token; the old one stops working."""
    token = secrets.token_urlsafe(32)
    connection = _upsert_connection(db, player_id=player_id, provider=WearableProvider.APPLE_HEALTH)
    connection.ingest_token_hash = hash_ingest_token(token)
    connection.last_error = None
    connection.updated_at = _now()
    db.commit()
    db.refresh(connection)
    return connection, token


def resolve_ingest_token(db: Session, token: str) -> WearableConnection:
    connection = db.execute(
        select(WearableConnection).where(
            WearableConnection.provider == WearableProvider.APPLE_HEALTH,
            WearableConnection.ingest_token_hash == hash_ingest_token(token),
        )
    ).scalar_one_or_none()
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown ingest token",
        )
    return connection


def disconnect(db: Session, *, player_id: int, provider: WearableProvider) -> bool:
    """Remove the link. Already synced days stay - they are the player's data."""
    connection = get_connection(db, player_id=player_id, provider=provider)
    if connection is None:
        return False
    db.delete(connection)
    db.commit()
    return True


def is_connected(connection: WearableConnection | None) -> bool:
    if connection is None:
        return False
    if connection.provider is WearableProvider.APPLE_HEALTH:
        return connection.ingest_token_hash is not None
    return connection.access_token is not None


# --------------------------------------------------------------- sync logic


def _ensure_fresh_access_token(db: Session, connection: WearableConnection) -> str:
    access_token = decrypt_secret(connection.access_token)
    expires_at = _aware(connection.token_expires_at)
    needs_refresh = expires_at is not None and expires_at - _TOKEN_REFRESH_MARGIN <= _now()

    if access_token and not needs_refresh:
        return access_token

    refresh_token = decrypt_secret(connection.refresh_token)
    if not refresh_token:
        if access_token:
            # Oura personal access tokens never expire and have no refresh token.
            return access_token
        raise WearableAuthError("The connection expired - please reconnect the device")

    if connection.provider is WearableProvider.WHOOP:
        bundle = whoop.refresh_access_token(refresh_token)
    elif connection.provider is WearableProvider.OURA:
        bundle = oura.refresh_access_token(refresh_token)
    else:
        raise WearableAuthError("This provider cannot refresh tokens")

    store_tokens(db, player_id=connection.player_id, provider=connection.provider, bundle=bundle)
    return bundle.access_token


def store_days(
    db: Session,
    *,
    player_id: int,
    provider: WearableProvider,
    days: list[DailyMetrics],
    allow_cycle: bool = False,
) -> int:
    """Upsert one row per day, never erasing a value with a later ``None``.

    Cycle data is dropped on the floor unless the player switched it on for
    this provider. Filtering here rather than at the parsers means no payload
    shape can sneak it past the opt-in.
    """
    written = 0
    for item in days:
        if not allow_cycle:
            item.menstrual_flow = None
        if not item.has_values():
            continue
        row = db.execute(
            select(WearableDaily).where(
                WearableDaily.player_id == player_id,
                WearableDaily.date == item.day,
                WearableDaily.provider == provider,
            )
        ).scalar_one_or_none()
        if row is None:
            row = WearableDaily(player_id=player_id, date=item.day, provider=provider)
            db.add(row)
        for field in DailyMetrics.METRIC_FIELDS:
            value = getattr(item, field)
            if value is not None:
                setattr(row, field, value)
        if item.raw:
            merged: dict[str, Any] = dict(row.raw or {})
            merged.update(item.raw)
            row.raw = merged
        row.synced_at = _now()
        written += 1
    db.commit()
    return written


def sync_connection(
    db: Session, connection: WearableConnection, *, days: int = DEFAULT_SYNC_DAYS
) -> SyncSummary:
    """Pull the last ``days`` days from the provider and store them.

    Apple Health is push-only, so "syncing" it just reports what the phone has
    already delivered instead of failing.
    """
    window = max(1, min(days, MAX_SYNC_DAYS))
    end = date.today()
    start = end - timedelta(days=window - 1)

    if connection.provider is WearableProvider.APPLE_HEALTH:
        rows = (
            db.execute(
                select(WearableDaily)
                .where(
                    WearableDaily.player_id == connection.player_id,
                    WearableDaily.provider == WearableProvider.APPLE_HEALTH,
                    WearableDaily.date >= start,
                )
                .order_by(WearableDaily.date.asc())
            )
            .scalars()
            .all()
        )
        return SyncSummary(
            provider=connection.provider,
            days_written=len(rows),
            first_day=rows[0].date if rows else None,
            last_day=rows[-1].date if rows else None,
            synced_at=_aware(connection.last_sync_at) or _now(),
        )

    skipped: list[str] = []
    try:
        access_token = _ensure_fresh_access_token(db, connection)
        if connection.provider is WearableProvider.WHOOP:
            fetched = whoop.fetch_daily(access_token=access_token, start=start, end=end)
        else:
            fetched = oura.fetch_daily(
                access_token=access_token,
                start=start,
                end=end,
                with_cycle=connection.sync_cycle,
                skipped=skipped,
            )
    except WearableError as exc:
        connection.last_sync_status = "failed"
        connection.last_error = str(exc)[:500]
        connection.updated_at = _now()
        db.commit()
        raise

    written = store_days(
        db,
        player_id=connection.player_id,
        provider=connection.provider,
        days=fetched,
        allow_cycle=connection.sync_cycle,
    )
    now = _now()
    connection.last_sync_at = now
    connection.last_sync_status = "ok"

    # Learning that this account cannot deliver cycle data is worth keeping:
    # the app then stops offering a switch that leads nowhere. The consent is
    # withdrawn with it, so no dormant permission is left lying around for the
    # most sensitive category in the app.
    if "daily_cycle_phases" in skipped:
        connection.cycle_unavailable = True
        connection.sync_cycle = False
        skipped = [item for item in skipped if item != "daily_cycle_phases"]

    # Any other refused collection means data is quietly missing. Saying so
    # beats leaving the player to wonder where her workouts went.
    # Machine-readable on purpose: the app turns this into a sentence in her
    # own language instead of showing her a raw collection name.
    connection.last_error = f"unavailable:{','.join(sorted(skipped))}" if skipped else None
    connection.updated_at = now
    db.commit()

    stored_days = sorted(item.day for item in fetched if item.has_values())
    return SyncSummary(
        provider=connection.provider,
        days_written=written,
        first_day=stored_days[0] if stored_days else None,
        last_day=stored_days[-1] if stored_days else None,
        synced_at=now,
    )


def ingest_apple_health(db: Session, connection: WearableConnection, payload: Any) -> SyncSummary:
    days = apple_health.parse_payload(payload)
    written = store_days(
        db,
        player_id=connection.player_id,
        provider=WearableProvider.APPLE_HEALTH,
        days=days,
        allow_cycle=connection.sync_cycle,
    )
    now = _now()
    connection.last_sync_at = now
    connection.last_sync_status = "ok"
    connection.last_error = None
    connection.updated_at = now
    db.commit()
    stored_days = sorted(item.day for item in days)
    return SyncSummary(
        provider=WearableProvider.APPLE_HEALTH,
        days_written=written,
        first_day=stored_days[0] if stored_days else None,
        last_day=stored_days[-1] if stored_days else None,
        synced_at=now,
    )


def sync_all(db: Session, *, days: int = DEFAULT_SYNC_DAYS) -> dict[str, int]:
    """Nightly job entry point: refresh every pull-based connection.

    One broken connection must not stop the others, so failures are counted
    and logged rather than raised.
    """
    connections = (
        db.execute(
            select(WearableConnection).where(
                WearableConnection.provider.in_([WearableProvider.WHOOP, WearableProvider.OURA])
            )
        )
        .scalars()
        .all()
    )
    succeeded = failed = 0
    for connection in connections:
        try:
            sync_connection(db, connection, days=days)
            succeeded += 1
        except (WearableError, HTTPException) as exc:
            failed += 1
            logger.warning(
                "wearable sync failed for player=%s provider=%s: %s",
                connection.player_id,
                connection.provider.value,
                exc,
            )
    return {"connections": len(connections), "succeeded": succeeded, "failed": failed}


# ------------------------------------------------------------------ reading


def list_daily(
    db: Session,
    *,
    player_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 120,
) -> list[WearableDaily]:
    query = select(WearableDaily).where(WearableDaily.player_id == player_id)
    if date_from is not None:
        query = query.where(WearableDaily.date >= date_from)
    if date_to is not None:
        query = query.where(WearableDaily.date <= date_to)
    query = query.order_by(WearableDaily.date.desc()).limit(limit)
    return list(db.execute(query).scalars().all())


# Whoop reports strain on a 0-21 scale; the app asks for intensity on 1-10.
WHOOP_MAX_STRAIN = 21.0


def intensity_from_strain(strain: float | None) -> int | None:
    if strain is None:
        return None
    return max(1, min(10, round(strain / WHOOP_MAX_STRAIN * 10)))


def _wellness_from(rows: list[WearableDaily]) -> dict[str, Any] | None:
    """Sleep and recovery numbers for the wellness form.

    Sleep quality is a 1-10 scale in this app while providers report 0-100,
    so a sleep score becomes a rounded tenth of itself.
    """
    out: dict[str, Any] = {}
    for row in rows:
        if out.get("sleep_hours") is None and row.sleep_hours is not None:
            out["sleep_hours"] = round(row.sleep_hours, 1)
        if out.get("sleep_quality") is None and row.sleep_score is not None:
            out["sleep_quality"] = max(1, min(10, round(row.sleep_score / 10)))
        if out.get("readiness_score") is None and row.readiness_score is not None:
            out["readiness_score"] = row.readiness_score
        if out.get("hrv_ms") is None and row.hrv_ms is not None:
            out["hrv_ms"] = round(row.hrv_ms, 1)
        if out.get("resting_hr") is None and row.resting_hr is not None:
            out["resting_hr"] = round(row.resting_hr, 1)
        if out.get("strain") is None and row.strain is not None:
            out["strain"] = round(row.strain, 1)
    return out or None


def _training_from(rows: list[WearableDaily]) -> dict[str, Any] | None:
    """A training entry the player can confirm, never one that is saved for her.

    Intensity only comes along when the device measured strain. Session type
    only when the sport is one we recognise - a bike ride must not arrive
    pre-labelled as a volleyball session.
    """
    minutes = next((r.workout_minutes for r in rows if r.workout_minutes), None)
    if not minutes or minutes < 10:
        return None

    sport = next((r.workout_sport for r in rows if r.workout_sport), None)
    strain = next((r.strain for r in rows if r.strain is not None), None)
    return {
        "duration_min": int(round(minutes)),
        "intensity": intensity_from_strain(strain),
        "session_type": session_type_for(sport),
        "sport": sport,
    }


def _cycle_from(
    db: Session, *, player_id: int, day: date, rows: list[WearableDaily]
) -> dict[str, Any] | None:
    """Cycle day and phase, derived from the period days a device reported."""
    # Deliberately not limited to days with flow: the useful answer is mostly
    # about the days *between* periods.
    history = (
        db.execute(
            select(WearableDaily.date, WearableDaily.menstrual_flow)
            .where(
                WearableDaily.player_id == player_id,
                WearableDaily.menstrual_flow.is_not(None),
                WearableDaily.date <= day,
                WearableDaily.date >= day - timedelta(days=400),
            )
            .order_by(WearableDaily.date.asc())
        )
        .tuples()
        .all()
    )
    if not history:
        return None

    flow_by_day = {row_date: flow for row_date, flow in history if flow}
    estimate = cycle_estimate(flow_by_day, on=day)
    if estimate is None:
        return None
    return {
        "cycle_day": estimate.cycle_day,
        "phase": estimate.phase,
        "cycle_length": estimate.cycle_length,
        "flow": estimate.flow,
    }


def suggestions(db: Session, *, player_id: int, day: date) -> dict[str, Any] | None:
    """Everything the forms can prefill for ``day`` from device data.

    One call so the app does not have to ask three times for the same day.
    Each section is absent when the devices had nothing to say about it.
    """
    rows = (
        db.execute(
            select(WearableDaily)
            .where(WearableDaily.player_id == player_id, WearableDaily.date == day)
            .order_by(WearableDaily.synced_at.desc())
        )
        .scalars()
        .all()
    )

    wellness = _wellness_from(rows)
    training = _training_from(rows)
    cycle = _cycle_from(db, player_id=player_id, day=day, rows=rows)
    if not (wellness or training or cycle):
        return None

    return {
        "date": day,
        "sources": [row.provider.value for row in rows],
        "wellness": wellness,
        "training": training,
        "cycle": cycle,
    }


def set_sync_cycle(
    db: Session, *, player_id: int, provider: WearableProvider, enabled: bool
) -> WearableConnection:
    """Turn cycle sync on or off for one provider.

    Switching it off also removes the cycle data already taken from that
    provider - "stop using this" has to mean the data goes too, otherwise the
    switch is only cosmetic.
    """
    connection = get_connection(db, player_id=player_id, provider=provider)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{provider.value} is not connected",
        )
    if enabled and connection.cycle_unavailable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{provider.value} has refused cycle data for this account - "
                "switching this on would not deliver anything."
            ),
        )
    connection.sync_cycle = enabled
    connection.updated_at = _now()
    if not enabled:
        for row in (
            db.execute(
                select(WearableDaily).where(
                    WearableDaily.player_id == player_id,
                    WearableDaily.provider == provider,
                    WearableDaily.menstrual_flow.is_not(None),
                )
            )
            .scalars()
            .all()
        ):
            row.menstrual_flow = None
    db.commit()
    db.refresh(connection)
    return connection


def connection_status(db: Session, player: User) -> list[dict[str, Any]]:
    """One status row per provider, including the ones nobody connected yet."""
    rows = []
    for provider in WearableProvider:
        connection = get_connection(db, player_id=player.id, provider=provider)
        last_day = db.execute(
            select(WearableDaily.date)
            .where(
                WearableDaily.player_id == player.id,
                WearableDaily.provider == provider,
            )
            .order_by(WearableDaily.date.desc())
            .limit(1)
        ).scalar_one_or_none()
        rows.append(
            {
                "provider": provider.value,
                "connected": is_connected(connection),
                "configured": is_configured(provider),
                "supports_oauth": supports_oauth(provider),
                "sync_cycle": bool(connection.sync_cycle) if connection else False,
                # False only once the provider has actually refused it.
                "cycle_available": not (connection.cycle_unavailable if connection else False),
                "last_sync_at": _aware(connection.last_sync_at) if connection else None,
                "last_sync_status": connection.last_sync_status if connection else None,
                "last_error": connection.last_error if connection else None,
                "last_data_date": last_day,
            }
        )
    return rows
