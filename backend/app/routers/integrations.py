"""Connect, sync and read wearable data (Whoop, Oura, Apple Health).

Route layout:

* ``/api/integrations/``                        - what is connected
* ``/api/integrations/{provider}/authorize``    - start the OAuth dance
* ``/api/integrations/callback/{provider}``     - OAuth return trip (browser)
* ``/api/integrations/oura/personal-token``     - connect Oura without OAuth
* ``/api/integrations/{provider}/sync``         - pull the last N days
* ``/api/integrations/{provider}``  (DELETE)    - disconnect
* ``/api/integrations/apple-health/token``      - issue the phone's push token
* ``/api/integrations/apple-health/ingest``     - the phone pushes here
* ``/api/integrations/daily``                   - the stored device data
"""

from __future__ import annotations

import os
import secrets
from datetime import date
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_role
from app.models import User, UserRole, WearableProvider
from app.schemas.integrations import (
    AuthorizeUrlResponse,
    IngestTokenResponse,
    IntegrationStatus,
    OuraPersonalTokenRequest,
    SuggestionResponse,
    SyncCycleRequest,
    SyncRequest,
    SyncResponse,
    WearableDailyResponse,
)
from app.services.privacy import assert_coach_can_view_wellness
from app.services.rate_limit import check_auth_rate_limit
from app.services.wearables import oura, whoop
from app.services.wearables import service as wearables
from app.services.wearables.base import TokenBundle, WearableAuthError, WearableError

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def _summary(summary: wearables.SyncSummary) -> SyncResponse:
    return SyncResponse(
        provider=summary.provider.value,
        days_written=summary.days_written,
        first_day=summary.first_day,
        last_day=summary.last_day,
        synced_at=summary.synced_at,
    )


def _wearable_http_error(exc: WearableError) -> HTTPException:
    """Map a provider failure onto a status the app can act on.

    A rejected Whoop or Oura token is not a VolleySync login problem, so it
    must not be a 401 - the app reads that as "your session ended" and would
    sign the player out for pasting the wrong Oura token.
    """
    code = (
        status.HTTP_409_CONFLICT
        if isinstance(exc, WearableAuthError)
        else status.HTTP_502_BAD_GATEWAY
    )
    return HTTPException(status_code=code, detail=str(exc))


@router.get("/", response_model=list[IntegrationStatus])
def list_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> list[dict[str, Any]]:
    return wearables.connection_status(db, current_user)


@router.post("/{provider}/authorize", response_model=AuthorizeUrlResponse)
def start_authorization(
    provider: str,
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> AuthorizeUrlResponse:
    target = wearables.parse_provider(provider)
    if not wearables.supports_oauth(target):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{target.value} is not set up for login on this server. "
                "Ask your coach to add the API credentials."
            ),
        )

    state = wearables.build_state_token(player_id=current_user.id, provider=target)
    callback = wearables.redirect_uri(target)
    url = (
        whoop.authorize_url(state=state, redirect_uri=callback)
        if target is WearableProvider.WHOOP
        else oura.authorize_url(state=state, redirect_uri=callback)
    )
    return AuthorizeUrlResponse(provider=target.value, authorize_url=url)


@router.get("/callback/{provider}")
def oauth_callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """The provider sends the player's browser back here after consent.

    Always ends in a redirect to the app - a player should never be left
    looking at raw JSON.
    """
    target = wearables.parse_provider(provider)

    def back(result: str, message: str | None = None) -> RedirectResponse:
        params = {"integration": target.value, "status": result}
        if message:
            params["message"] = message[:200]
        return RedirectResponse(
            url=f"{wearables.frontend_base_url()}/?{urlencode(params)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if error:
        # Whoop and Oura put the useful part in error_description/error_hint;
        # the bare code ("invalid_scope") does not say which scope.
        detail = " - ".join(
            part
            for part in (
                error,
                request.query_params.get("error_description"),
                request.query_params.get("error_hint"),
            )
            if part
        )
        return back("denied", detail)
    if not code or not state:
        return back("error", "missing authorization code")

    try:
        player_id = wearables.read_state_token(state, provider=target)
    except HTTPException as exc:
        return back("error", str(exc.detail))

    player = db.get(User, player_id)
    if player is None or player.role != UserRole.PLAYER:
        return back("error", "unknown player")

    callback = wearables.redirect_uri(target)
    try:
        bundle: TokenBundle = (
            whoop.exchange_code(code=code, redirect_uri=callback)
            if target is WearableProvider.WHOOP
            else oura.exchange_code(code=code, redirect_uri=callback)
        )
    except WearableError as exc:
        # Nothing was linked - usually a redirect URI that does not match the
        # one registered with the provider.
        return back("error", str(exc))

    connection = wearables.store_tokens(db, player_id=player.id, provider=target, bundle=bundle)
    try:
        wearables.sync_connection(db, connection)
    except WearableError as exc:
        # The link itself worked; keep the tokens so the player can retry the
        # first pull from the app instead of connecting all over again.
        return back("connected_with_warning", str(exc))

    return back("connected")


@router.post("/oura/personal-token", response_model=IntegrationStatus)
def connect_oura_personal_token(
    payload: OuraPersonalTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> dict[str, Any]:
    """Connect Oura with a personal access token - the retired fallback route."""
    wearables.assert_enabled(WearableProvider.OURA)
    ip = request.client.host if request.client else "unknown"
    check_auth_rate_limit(action="oura-token", key=f"{ip}:{current_user.id}")

    token = payload.token.strip()
    try:
        external_id = oura.verify_token(token)
    except WearableError as exc:
        raise _wearable_http_error(exc) from exc

    connection = wearables.store_tokens(
        db,
        player_id=current_user.id,
        provider=WearableProvider.OURA,
        bundle=TokenBundle(
            access_token=token,
            scope="personal-access-token",
            external_user_id=external_id,
        ),
    )
    try:
        wearables.sync_connection(db, connection)
    except WearableError:
        # Token is valid, the first pull can be retried from the app.
        pass

    status_rows = wearables.connection_status(db, current_user)
    return next(row for row in status_rows if row["provider"] == WearableProvider.OURA.value)


@router.post("/{provider}/sync", response_model=SyncResponse)
def sync_provider(
    provider: str,
    payload: SyncRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> SyncResponse:
    target = wearables.parse_provider(provider)
    connection = wearables.get_connection(db, player_id=current_user.id, provider=target)
    if not wearables.is_connected(connection):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{target.value} is not connected",
        )
    assert connection is not None

    days = payload.days if payload is not None else wearables.DEFAULT_SYNC_DAYS
    try:
        return _summary(wearables.sync_connection(db, connection, days=days))
    except WearableError as exc:
        raise _wearable_http_error(exc) from exc


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_provider(
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> None:
    target = wearables.parse_provider(provider)
    if not wearables.disconnect(db, player_id=current_user.id, provider=target):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{target.value} is not connected",
        )


@router.post("/apple-health/token", response_model=IngestTokenResponse)
def create_apple_health_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> IngestTokenResponse:
    """Issue a fresh ingest token. Shown once - calling again invalidates it."""
    wearables.assert_enabled(WearableProvider.APPLE_HEALTH)
    _, token = wearables.rotate_ingest_token(db, player_id=current_user.id)
    return IngestTokenResponse(ingest_token=token, ingest_url=wearables.ingest_url())


@router.post("/apple-health/ingest", response_model=SyncResponse)
def ingest_apple_health(
    payload: Any = Body(...),
    db: Session = Depends(get_db),
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> SyncResponse:
    """Receive health data pushed by an iOS shortcut or Health Auto Export.

    Authenticated with the player's ingest token rather than a JWT: the phone
    runs this unattended in the background and has no way to refresh a login.
    The token is accepted in a header, a bearer header or the query string,
    because the three shortcut apps each do it differently.
    """
    supplied = x_ingest_token or token
    if not supplied and authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:]
    if not supplied:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing ingest token",
        )

    wearables.assert_enabled(WearableProvider.APPLE_HEALTH)
    connection = wearables.resolve_ingest_token(db, supplied.strip())
    try:
        return _summary(wearables.ingest_apple_health(db, connection, payload))
    except WearableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post("/sync-all", response_model=dict)
def sync_all_connections(
    db: Session = Depends(get_db),
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> dict[str, int]:
    """Nightly refresh for every connected device, for a Render cron job."""
    expected = os.getenv("CRON_SECRET", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET is not configured",
        )
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret.strip(), expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret")
    return wearables.sync_all(db)


@router.get("/suggestion", response_model=SuggestionResponse)
def suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
    day: date | None = Query(default=None, alias="date"),
) -> dict[str, Any]:
    """What the wellness, training and cycle forms can prefill for one day.

    Suggestions only - nothing here is stored until the player presses save.
    """
    target_day = day or date.today()
    suggestion = wearables.suggestions(db, player_id=current_user.id, day=target_day)
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nothing to suggest for this date",
        )
    return suggestion


@router.put("/{provider}/cycle-sync", response_model=IntegrationStatus)
def set_cycle_sync(
    provider: str,
    payload: SyncCycleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> dict[str, Any]:
    """Allow or stop taking cycle data from one provider.

    Switching it off also deletes what that provider already delivered - the
    switch has to actually remove the data, not just hide it.
    """
    target = wearables.parse_provider(provider)
    wearables.set_sync_cycle(
        db, player_id=current_user.id, provider=target, enabled=payload.enabled
    )
    rows = wearables.connection_status(db, current_user)
    return next(row for row in rows if row["provider"] == target.value)


@router.get("/daily", response_model=list[WearableDailyResponse])
def list_own_daily(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
):
    return wearables.list_daily(db, player_id=current_user.id, date_from=date_from, date_to=date_to)


@router.get("/daily/{player_id}", response_model=list[WearableDailyResponse])
def list_player_daily_for_coach(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COACH)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
):
    # Device data is wellness data - it needs the same explicit consent.
    assert_coach_can_view_wellness(db, current_user, player_id)
    return wearables.list_daily(db, player_id=player_id, date_from=date_from, date_to=date_to)
