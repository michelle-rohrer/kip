from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_role
from app.models import TrainingEntry, User, UserRole
from app.schemas.training import TrainingEntryCreate, TrainingEntryResponse
from app.services.privacy import assert_coach_can_view_training

router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/", response_model=TrainingEntryResponse, status_code=status.HTTP_201_CREATED)
def create_training_entry(
    payload: TrainingEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> TrainingEntry:
    entry = TrainingEntry(player_id=current_user.id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/", response_model=list[TrainingEntryResponse])
def list_own_training(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[TrainingEntry]:
    q = db.query(TrainingEntry).filter(TrainingEntry.player_id == current_user.id)
    if date_from is not None:
        q = q.filter(TrainingEntry.date >= date_from)
    if date_to is not None:
        q = q.filter(TrainingEntry.date <= date_to)
    return q.order_by(TrainingEntry.date.desc(), TrainingEntry.id.desc()).all()


@router.get("/{player_id}", response_model=list[TrainingEntryResponse])
def list_player_training_for_coach(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COACH)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[TrainingEntry]:
    assert_coach_can_view_training(db, current_user, player_id)
    q = db.query(TrainingEntry).filter(TrainingEntry.player_id == player_id)
    if date_from is not None:
        q = q.filter(TrainingEntry.date >= date_from)
    if date_to is not None:
        q = q.filter(TrainingEntry.date <= date_to)
    return q.order_by(TrainingEntry.date.desc(), TrainingEntry.id.desc()).all()
