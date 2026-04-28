import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    PLAYER = "player"
    COACH = "coach"


class CyclePhase(str, enum.Enum):
    MENSTRUATION = "menstruation"
    FOLLICULAR = "follicular"
    OVULATION = "ovulation"
    LUTEAL = "luteal"


class RiskLevel(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [item.value for item in enum_cls]


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="team")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values),
        nullable=False,
    )
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    team: Mapped[Team | None] = relationship(back_populates="users")
    cycle_entries: Mapped[list["CycleEntry"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    wellness_entries: Mapped[list["WellnessEntry"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    training_entries: Mapped[list["TrainingEntry"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    injury_entries: Mapped[list["InjuryEntry"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    risk_predictions: Mapped[list["RiskPrediction"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    given_privacy_consents: Mapped[list["PrivacyConsent"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
        foreign_keys="PrivacyConsent.player_id",
    )
    received_privacy_consents: Mapped[list["PrivacyConsent"]] = relationship(
        back_populates="coach",
        cascade="all, delete-orphan",
        foreign_keys="PrivacyConsent.coach_id",
    )


class CycleEntry(Base):
    __tablename__ = "cycle_entries"
    __table_args__ = (UniqueConstraint("player_id", "date", name="uq_cycle_entries_player_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    cycle_day: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[CyclePhase] = mapped_column(
        Enum(CyclePhase, name="cycle_phase", values_callable=enum_values),
        nullable=False,
    )
    cycle_length: Mapped[int] = mapped_column(Integer, nullable=False)
    pms_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cramps: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    migraine: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fatigue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contraception_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    player: Mapped[User] = relationship(back_populates="cycle_entries")


class WellnessEntry(Base):
    __tablename__ = "wellness_entries"
    __table_args__ = (
        UniqueConstraint("player_id", "date", name="uq_wellness_entries_player_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    sleep_hours: Mapped[float] = mapped_column(Float, nullable=False)
    sleep_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    muscle_soreness: Mapped[int] = mapped_column(Integer, nullable=False)
    mental_energy: Mapped[int] = mapped_column(Integer, nullable=False)
    stress_level: Mapped[int] = mapped_column(Integer, nullable=False)
    motivation: Mapped[int] = mapped_column(Integer, nullable=False)
    rpe_previous_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    player: Mapped[User] = relationship(back_populates="wellness_entries")


class TrainingEntry(Base):
    __tablename__ = "training_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    jump_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sprint_times: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strength_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    match_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    player: Mapped[User] = relationship(back_populates="training_entries")


class InjuryEntry(Base):
    __tablename__ = "injury_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    body_location: Mapped[str] = mapped_column(String(255), nullable=False)
    pain_intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_chronic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    player: Mapped[User] = relationship(back_populates="injury_entries")


class PrivacyConsent(Base):
    __tablename__ = "privacy_consents"
    __table_args__ = (
        UniqueConstraint("player_id", "coach_id", name="uq_privacy_consents_player_coach"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    share_cycle_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_wellness_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    player: Mapped[User] = relationship(
        back_populates="given_privacy_consents", foreign_keys=[player_id]
    )
    coach: Mapped[User] = relationship(
        back_populates="received_privacy_consents", foreign_keys=[coach_id]
    )


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level", values_callable=enum_values),
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    features_used: Mapped[dict] = mapped_column(JSON, nullable=False)

    player: Mapped[User] = relationship(back_populates="risk_predictions")
