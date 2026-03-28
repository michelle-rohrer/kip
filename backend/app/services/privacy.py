from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import PrivacyConsent, User, UserRole


def get_player_or_404(db: Session, player_id: int) -> User:
    user = db.get(User, player_id)
    if user is None or user.role != UserRole.PLAYER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return user


def assert_same_team(coach: User, player: User) -> None:
    if coach.team_id is None or player.team_id is None or coach.team_id != player.team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this player",
        )


def assert_coach_can_view_wellness(db: Session, coach: User, player_id: int) -> User:
    player = get_player_or_404(db, player_id)
    assert_same_team(coach, player)
    consent = (
        db.query(PrivacyConsent)
        .filter(
            PrivacyConsent.player_id == player_id,
            PrivacyConsent.coach_id == coach.id,
        )
        .one_or_none()
    )
    if consent is None or not consent.share_wellness_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wellness data not shared with this coach",
        )
    return player


def assert_coach_can_view_cycle(db: Session, coach: User, player_id: int) -> User:
    player = get_player_or_404(db, player_id)
    assert_same_team(coach, player)
    consent = (
        db.query(PrivacyConsent)
        .filter(
            PrivacyConsent.player_id == player_id,
            PrivacyConsent.coach_id == coach.id,
        )
        .one_or_none()
    )
    if consent is None or not consent.share_cycle_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cycle data not shared with this coach",
        )
    return player


def assert_coach_can_view_training(db: Session, coach: User, player_id: int) -> User:
    player = get_player_or_404(db, player_id)
    assert_same_team(coach, player)
    return player


def assert_player_can_set_consent_for_coach(db: Session, player: User, coach_id: int) -> User:
    coach = db.get(User, coach_id)
    if coach is None or coach.role != UserRole.COACH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid coach")
    assert_same_team(coach, player)
    return coach
