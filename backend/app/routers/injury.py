from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_role
from app.models import InjuryEntry, User, UserRole
from app.schemas.injury import InjuryEntryCreate, InjuryEntryResponse

router = APIRouter(prefix="/api/injury", tags=["injury"])


@router.post("/", response_model=InjuryEntryResponse, status_code=status.HTTP_201_CREATED)
def create_injury_entry(
    payload: InjuryEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> InjuryEntry:
    entry = InjuryEntry(player_id=current_user.id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/", response_model=list[InjuryEntryResponse])
def list_own_injuries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[InjuryEntry]:
    q = db.query(InjuryEntry).filter(InjuryEntry.player_id == current_user.id)
    if date_from is not None:
        q = q.filter(InjuryEntry.date >= date_from)
    if date_to is not None:
        q = q.filter(InjuryEntry.date <= date_to)
    return q.order_by(InjuryEntry.date.desc(), InjuryEntry.id.desc()).all()
