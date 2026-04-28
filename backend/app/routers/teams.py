from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Team
from app.schemas.teams import TeamResponse

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("/", response_model=list[TeamResponse])
def list_teams(db: Session = Depends(get_db)) -> list[Team]:
    return db.query(Team).order_by(Team.name.asc()).all()
