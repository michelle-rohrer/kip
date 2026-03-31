from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user, require_role
from app.ml.predict import predict_current_risk, upsert_daily_prediction
from app.models import User, UserRole
from app.schemas.predictions import RiskPredictionResponse
from app.services.privacy import assert_coach_can_view_training, get_player_or_404

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/team", response_model=list[RiskPredictionResponse])
def get_team_predictions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COACH)),
):
    players = (
        db.query(User)
        .filter(
            User.team_id == current_user.team_id,
            User.role == UserRole.PLAYER,
        )
        .all()
    )
    out = []
    for p in players:
        # Reuse existing team/privacy checks used by training endpoints.
        get_player_or_404(db, p.id)
        result = predict_current_risk(db, player_id=p.id)
        out.append(upsert_daily_prediction(db, player_id=p.id, result=result))
    return out


@router.get("/{player_id}", response_model=RiskPredictionResponse)
def get_player_prediction(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.PLAYER:
        if current_user.id != player_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this player")
    elif current_user.role == UserRole.COACH:
        assert_coach_can_view_training(db, current_user, player_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = predict_current_risk(db, player_id=player_id)
    return upsert_daily_prediction(db, player_id=player_id, result=result)
