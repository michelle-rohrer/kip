from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_role
from app.models import PrivacyConsent, User, UserRole
from app.schemas.privacy import PrivacyConsentResponse, PrivacyConsentUpsert
from app.services.privacy import assert_player_can_set_consent_for_coach

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.get("/consent", response_model=list[PrivacyConsentResponse])
def list_consents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLAYER)),
) -> list[PrivacyConsent]:
    return (
        db.query(PrivacyConsent)
        .filter(PrivacyConsent.player_id == current_user.id)
        .order_by(PrivacyConsent.coach_id.asc())
        .all()
    )


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
