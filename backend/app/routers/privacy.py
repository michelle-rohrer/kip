from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_role
from app.models import PrivacyConsent, User, UserRole
from app.schemas.privacy import PrivacyConsentResponse, PrivacyConsentUpsert
from app.services.privacy import assert_player_can_set_consent_for_coach

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


def _ensure_consents_for_team_coaches(db: Session, *, player: User) -> None:
    if player.team_id is None:
        return
    coaches = (
        db.query(User)
        .filter(
            User.team_id == player.team_id,
            User.role == UserRole.COACH,
        )
        .all()
    )
    existing_coach_ids = {
        cid
        for (cid,) in db.query(PrivacyConsent.coach_id)
        .filter(PrivacyConsent.player_id == player.id)
        .all()
    }
    now = datetime.now(timezone.utc)
    changed = False
    for coach in coaches:
        if coach.id in existing_coach_ids:
            continue
        db.add(
            PrivacyConsent(
                player_id=player.id,
                coach_id=coach.id,
                share_cycle_data=False,
                share_wellness_data=False,
                created_at=now,
                updated_at=now,
            )
        )
        changed = True
    if changed:
        db.commit()


@router.get("/consent", response_model=list[PrivacyConsentResponse])
def list_consents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> list[PrivacyConsentResponse]:
    _ensure_consents_for_team_coaches(db, player=current_user)
    rows = (
        db.query(PrivacyConsent, User.name)
        .join(User, User.id == PrivacyConsent.coach_id)
        .filter(PrivacyConsent.player_id == current_user.id)
        .order_by(User.name.asc(), PrivacyConsent.coach_id.asc())
        .all()
    )
    return [
        PrivacyConsentResponse(
            id=consent.id,
            player_id=consent.player_id,
            coach_id=consent.coach_id,
            coach_name=coach_name,
            share_cycle_data=consent.share_cycle_data,
            share_wellness_data=consent.share_wellness_data,
            created_at=consent.created_at,
            updated_at=consent.updated_at,
        )
        for consent, coach_name in rows
    ]


@router.put("/consent", response_model=PrivacyConsentResponse)
def upsert_consent(
    payload: PrivacyConsentUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> PrivacyConsent:
    assert_player_can_set_consent_for_coach(db, current_user, payload.coach_id)
    consent = (
        db.query(PrivacyConsent)
        .filter(
            PrivacyConsent.player_id == current_user.id,
            PrivacyConsent.coach_id == payload.coach_id,
        )
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if consent is None:
        consent = PrivacyConsent(
            player_id=current_user.id,
            coach_id=payload.coach_id,
            share_cycle_data=payload.share_cycle_data,
            share_wellness_data=payload.share_wellness_data,
            created_at=now,
            updated_at=now,
        )
        db.add(consent)
    else:
        consent.share_cycle_data = payload.share_cycle_data
        consent.share_wellness_data = payload.share_wellness_data
        consent.updated_at = now
    db.commit()
    db.refresh(consent)
    return consent
