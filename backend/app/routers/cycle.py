from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_role
from app.models import CycleEntry, User, UserRole
from app.schemas.cycle import CycleEntryCreate, CycleEntryResponse, CycleEstimateResponse
from app.services.cycle import estimate_for, fill_in
from app.services.privacy import assert_coach_can_view_cycle

router = APIRouter(prefix="/api/cycle", tags=["cycle"])


@router.post("/", response_model=CycleEntryResponse, status_code=status.HTTP_201_CREATED)
def create_cycle_entry(
    payload: CycleEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> CycleEntry:
    existing = (
        db.query(CycleEntry)
        .filter(
            CycleEntry.player_id == current_user.id,
            CycleEntry.date == payload.date,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cycle entry for this date already exists",
        )
    entry = CycleEntry(player_id=current_user.id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/", response_model=CycleEntryResponse)
def upsert_cycle_entry(
    payload: CycleEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> CycleEntry:
    """Save a cycle day, overwriting an earlier entry for the same date."""
    entry = (
        db.query(CycleEntry)
        .filter(
            CycleEntry.player_id == current_user.id,
            CycleEntry.date == payload.date,
        )
        .one_or_none()
    )
    # Derive cycle day, phase and length from her recorded period days when
    # she left them empty. Anything she typed herself is left untouched.
    values = fill_in(db, player_id=current_user.id, payload=payload.model_dump())
    if entry is None:
        entry = CycleEntry(player_id=current_user.id, **values)
        db.add(entry)
    else:
        for field, value in values.items():
            setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/estimate", response_model=CycleEstimateResponse)
def estimate_cycle(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
    day: date | None = Query(default=None, alias="date"),
    flow: str | None = Query(default=None),
) -> CycleEstimateResponse:
    """Which cycle day and phase ``date`` falls on, from her period history.

    Lets the form show what it would save before she saves it, so a wrong
    estimate can be corrected rather than silently accepted.
    """
    target = day or date.today()
    # The form passes what the player just ticked, so the preview reflects it
    # before anything is saved.
    estimate = estimate_for(db, player_id=current_user.id, day=target, flow=flow)
    if estimate is None:
        return CycleEstimateResponse(date=target, available=False)
    return CycleEstimateResponse(
        date=target,
        available=True,
        cycle_day=estimate.cycle_day,
        phase=estimate.phase,
        cycle_length=estimate.cycle_length,
        period_start=estimate.period_start,
        flow=estimate.flow,
    )


@router.get("/", response_model=list[CycleEntryResponse])
def list_own_cycle_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[CycleEntry]:
    q = db.query(CycleEntry).filter(CycleEntry.player_id == current_user.id)
    if date_from is not None:
        q = q.filter(CycleEntry.date >= date_from)
    if date_to is not None:
        q = q.filter(CycleEntry.date <= date_to)
    return q.order_by(CycleEntry.date.desc()).all()


@router.get("/{player_id}", response_model=list[CycleEntryResponse])
def list_player_cycle_for_coach(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COACH)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[CycleEntry]:
    assert_coach_can_view_cycle(db, current_user, player_id)
    q = db.query(CycleEntry).filter(CycleEntry.player_id == player_id)
    if date_from is not None:
        q = q.filter(CycleEntry.date >= date_from)
    if date_to is not None:
        q = q.filter(CycleEntry.date <= date_to)
    return q.order_by(CycleEntry.date.desc()).all()
