from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_role
from app.models import User, UserRole, WellnessEntry
from app.schemas.wellness import WellnessEntryCreate, WellnessEntryResponse
from app.services.privacy import assert_coach_can_view_wellness

router = APIRouter(prefix="/api/wellness", tags=["wellness"])


@router.post("/", response_model=WellnessEntryResponse, status_code=status.HTTP_201_CREATED)
def create_wellness_entry(
    payload: WellnessEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> WellnessEntry:
    existing = (
        db.query(WellnessEntry)
        .filter(
            WellnessEntry.player_id == current_user.id,
            WellnessEntry.date == payload.date,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Wellness entry for this date already exists",
        )
    entry = WellnessEntry(player_id=current_user.id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/", response_model=list[WellnessEntryResponse])
def list_own_wellness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[WellnessEntry]:
    q = db.query(WellnessEntry).filter(WellnessEntry.player_id == current_user.id)
    if date_from is not None:
        q = q.filter(WellnessEntry.date >= date_from)
    if date_to is not None:
        q = q.filter(WellnessEntry.date <= date_to)
    return q.order_by(WellnessEntry.date.desc()).all()


@router.get("/{player_id}", response_model=list[WellnessEntryResponse])
def list_player_wellness_for_coach(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COACH)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[WellnessEntry]:
    assert_coach_can_view_wellness(db, current_user, player_id)
    q = db.query(WellnessEntry).filter(WellnessEntry.player_id == player_id)
    if date_from is not None:
        q = q.filter(WellnessEntry.date >= date_from)
    if date_to is not None:
        q = q.filter(WellnessEntry.date <= date_to)
    return q.order_by(WellnessEntry.date.desc()).all()
