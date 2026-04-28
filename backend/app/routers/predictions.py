from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user, require_role
from app.ml.predict import predict_current_risk, upsert_daily_prediction
from app.ml.train import load_training_status
from app.models import InjuryEntry, TrainingEntry, User, UserRole
from app.schemas.predictions import ModelTrainingStatusResponse, RiskPredictionResponse
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
        result = predict_current_risk(db, player_id=p.id, player_position=p.player_position)
        prediction = upsert_daily_prediction(db, player_id=p.id, result=result)
        latest_training = (
            db.query(TrainingEntry)
            .filter(TrainingEntry.player_id == p.id)
            .order_by(desc(TrainingEntry.date), desc(TrainingEntry.id))
            .first()
        )
        latest_injury = (
            db.query(InjuryEntry)
            .filter(InjuryEntry.player_id == p.id)
            .order_by(desc(InjuryEntry.date), desc(InjuryEntry.id))
            .first()
        )
        out.append(
            RiskPredictionResponse.model_validate(prediction, from_attributes=True).model_copy(
                update={
                    "player_name": p.name,
                    "player_position": p.player_position,
                    "latest_training_date": latest_training.date if latest_training else None,
                    "latest_session_rpe": latest_training.session_rpe if latest_training else None,
                    "latest_session_type": (
                        latest_training.session_type if latest_training else None
                    ),
                    "latest_participation_status": (
                        getattr(latest_training, "participation_status", None)
                        if latest_training
                        else None
                    ),
                    "latest_injury_date": latest_injury.date if latest_injury else None,
                    "latest_pain_intensity": (
                        latest_injury.pain_intensity if latest_injury else None
                    ),
                    "latest_medical_attention": (
                        latest_injury.medical_attention if latest_injury else None
                    ),
                    "latest_time_loss_days": (
                        latest_injury.time_loss_days if latest_injury else None
                    ),
                }
            )
        )
    return out


@router.get("/model-status", response_model=ModelTrainingStatusResponse)
def get_model_training_status(_: User = Depends(get_current_user)):
    status_payload = load_training_status()
    if status_payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No model training status available yet",
        )
    return ModelTrainingStatusResponse(**status_payload)


@router.get("/{player_id}", response_model=RiskPredictionResponse)
def get_player_prediction(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.PLAYER:
        if current_user.id != player_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="No access to this player"
            )
    elif current_user.role == UserRole.COACH:
        assert_coach_can_view_training(db, current_user, player_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    player = db.query(User).filter(User.id == player_id).one_or_none()
    result = predict_current_risk(
        db, player_id=player_id, player_position=player.player_position if player else None
    )
    return upsert_daily_prediction(db, player_id=player_id, result=result)
