import enum
from datetime import date, datetime, timezone

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


class WearableProvider(str, enum.Enum):
    """Sources a player can link so sleep/recovery data arrives on its own."""

    WHOOP = "whoop"
    OURA = "oura"
    APPLE_HEALTH = "apple_health"


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [item.value for item in enum_cls]


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="team")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values),
        nullable=False,
    )
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    training_uid: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    player_position: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # A test account uses the app exactly like a real player, but stays out of
    # the coach's team overview and out of the training data - otherwise every
    # trial entry would skew the squad's numbers and the model.
    is_test_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
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
    wearable_connections: Mapped[list["WearableConnection"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    wearable_days: Mapped[list["WearableDaily"]] = relationship(
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
    cycle_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phase: Mapped[CyclePhase | None] = mapped_column(
        Enum(CyclePhase, name="cycle_phase", values_callable=enum_values),
        nullable=True,
    )
    cycle_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "none" | "light" | "medium" | "heavy". The one thing a player actually
    # knows without counting: whether she has her period today. Cycle day,
    # phase and length are derived from a run of these.
    menstrual_flow: Mapped[str | None] = mapped_column(String(16), nullable=True)
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
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    muscle_soreness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mental_energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe_previous_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    player: Mapped[User] = relationship(back_populates="wellness_entries")


class TrainingEntry(Base):
    __tablename__ = "training_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intensity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # The training form has always asked how a player took part; the column
    # was dropped from the schema by accident and every answer was silently
    # discarded. Jump count is deliberately not here - nothing in the setup
    # can count jumps, so asking for it would only invite guesses.
    participation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    strength_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    player: Mapped[User] = relationship(back_populates="training_entries")


class InjuryEntry(Base):
    __tablename__ = "injury_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    body_location: Mapped[str] = mapped_column(String(255), nullable=False)
    pain_intensity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_chronic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    medical_attention: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Nullable since migration 20260428_000004 - the model still claimed NOT
    # NULL, so tests (create_all) and production (migrated) disagreed on
    # whether an injury without a known absence could be saved at all.
    time_loss_days: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
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
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
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


class RefreshSession(Base):
    """Server-side state for one refresh token.

    Keeping this in the database (instead of process memory) means a deploy or
    restart no longer signs everybody out, and logout stays effective.
    """

    __tablename__ = "refresh_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class WearableConnection(Base):
    """One player's link to one wearable provider.

    OAuth tokens are stored encrypted (see ``app.services.crypto``) because a
    leaked Whoop/Oura token would expose far more health data than this app
    ever collects itself. Apple Health has no cloud API, so instead of tokens
    we keep the hash of an ingest token that the iOS shortcut sends along.
    """

    __tablename__ = "wearable_connections"
    __table_args__ = (
        UniqueConstraint("player_id", "provider", name="uq_wearable_connections_player_provider"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[WearableProvider] = mapped_column(
        Enum(WearableProvider, name="wearable_provider", values_callable=enum_values),
        nullable=False,
    )
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scope: Mapped[str | None] = mapped_column(String(512), nullable=True)
    external_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ingest_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # Cycle data is the most sensitive category in the app, so taking it from a
    # device is off until the player turns it on - per provider, because she
    # may well trust one app with it and not another.
    sync_cycle: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Set once the provider has actually refused cycle data for this account.
    # Learned, not assumed: Oura serves it to accounts that include Cycle
    # Insights and refuses it for the rest, so the answer differs per player.
    cycle_unavailable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    player: Mapped[User] = relationship(back_populates="wearable_connections")


class WearableDaily(Base):
    """One provider's summary for one player on one calendar day.

    Kept separate from ``WellnessEntry`` on purpose: the wellness entry is what
    the player reports about herself, this is what a device measured. Mixing
    them would make it impossible to tell later which number came from where.
    """

    __tablename__ = "wearable_daily"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "date", "provider", name="uq_wearable_daily_player_date_provider"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    provider: Mapped[WearableProvider] = mapped_column(
        Enum(WearableProvider, name="wearable_provider", values_callable=enum_values),
        nullable=False,
    )
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    readiness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    strain: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    workout_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    # What the device called the session ("volleyball", "weightlifting", ...).
    # Used to pre-fill the session type, never to decide anything on its own.
    workout_sport: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # "none" | "light" | "medium" | "heavy" - only ever written when the player
    # switched cycle sync on for that provider.
    menstrual_flow: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    player: Mapped[User] = relationship(back_populates="wearable_days")
