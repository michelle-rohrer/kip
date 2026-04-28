"""Create initial database schema.

Revision ID: 20260301_000001
Revises:
Create Date: 2026-03-01 00:00:01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260301_000001"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("player", "coach", name="user_role")
cycle_phase_enum = sa.Enum("menstruation", "follicular", "ovulation", "luteal", name="cycle_phase")
risk_level_enum = sa.Enum("green", "yellow", "red", name="risk_level")


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_teams_id", "teams", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "cycle_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("cycle_day", sa.Integer(), nullable=False),
        sa.Column("phase", cycle_phase_enum, nullable=False),
        sa.Column("cycle_length", sa.Integer(), nullable=False),
        sa.Column("pms_score", sa.Integer(), nullable=True),
        sa.Column("cramps", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("migraine", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fatigue", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("contraception_type", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("player_id", "date", name="uq_cycle_entries_player_date"),
    )
    op.create_index("ix_cycle_entries_id", "cycle_entries", ["id"], unique=False)
    op.create_index("ix_cycle_entries_player_id", "cycle_entries", ["player_id"], unique=False)

    op.create_table(
        "wellness_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=False),
        sa.Column("sleep_quality", sa.Integer(), nullable=False),
        sa.Column("muscle_soreness", sa.Integer(), nullable=False),
        sa.Column("mental_energy", sa.Integer(), nullable=False),
        sa.Column("stress_level", sa.Integer(), nullable=False),
        sa.Column("motivation", sa.Integer(), nullable=False),
        sa.Column("rpe_previous_day", sa.Integer(), nullable=True),
        sa.Column("free_text", sa.Text(), nullable=True),
        sa.UniqueConstraint("player_id", "date", name="uq_wellness_entries_player_date"),
    )
    op.create_index("ix_wellness_entries_id", "wellness_entries", ["id"], unique=False)
    op.create_index(
        "ix_wellness_entries_player_id", "wellness_entries", ["player_id"], unique=False
    )

    op.create_table(
        "training_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("jump_count", sa.Integer(), nullable=True),
        sa.Column("sprint_times", sa.JSON(), nullable=True),
        sa.Column("strength_values", sa.JSON(), nullable=True),
        sa.Column("match_stats", sa.JSON(), nullable=True),
    )
    op.create_index("ix_training_entries_id", "training_entries", ["id"], unique=False)
    op.create_index(
        "ix_training_entries_player_id", "training_entries", ["player_id"], unique=False
    )

    op.create_table(
        "injury_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("body_location", sa.String(length=255), nullable=False),
        sa.Column("pain_intensity", sa.Integer(), nullable=False),
        sa.Column("is_chronic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_injury_entries_id", "injury_entries", ["id"], unique=False)
    op.create_index("ix_injury_entries_player_id", "injury_entries", ["player_id"], unique=False)

    op.create_table(
        "privacy_consents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("coach_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("share_cycle_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("share_wellness_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("player_id", "coach_id", name="uq_privacy_consents_player_coach"),
    )
    op.create_index("ix_privacy_consents_id", "privacy_consents", ["id"], unique=False)
    op.create_index(
        "ix_privacy_consents_player_id", "privacy_consents", ["player_id"], unique=False
    )
    op.create_index("ix_privacy_consents_coach_id", "privacy_consents", ["coach_id"], unique=False)

    op.create_table(
        "risk_predictions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_level", risk_level_enum, nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("features_used", sa.JSON(), nullable=False),
    )
    op.create_index("ix_risk_predictions_id", "risk_predictions", ["id"], unique=False)
    op.create_index(
        "ix_risk_predictions_player_id", "risk_predictions", ["player_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_risk_predictions_player_id", table_name="risk_predictions")
    op.drop_index("ix_risk_predictions_id", table_name="risk_predictions")
    op.drop_table("risk_predictions")

    op.drop_index("ix_privacy_consents_coach_id", table_name="privacy_consents")
    op.drop_index("ix_privacy_consents_player_id", table_name="privacy_consents")
    op.drop_index("ix_privacy_consents_id", table_name="privacy_consents")
    op.drop_table("privacy_consents")

    op.drop_index("ix_injury_entries_player_id", table_name="injury_entries")
    op.drop_index("ix_injury_entries_id", table_name="injury_entries")
    op.drop_table("injury_entries")

    op.drop_index("ix_training_entries_player_id", table_name="training_entries")
    op.drop_index("ix_training_entries_id", table_name="training_entries")
    op.drop_table("training_entries")

    op.drop_index("ix_wellness_entries_player_id", table_name="wellness_entries")
    op.drop_index("ix_wellness_entries_id", table_name="wellness_entries")
    op.drop_table("wellness_entries")

    op.drop_index("ix_cycle_entries_player_id", table_name="cycle_entries")
    op.drop_index("ix_cycle_entries_id", table_name="cycle_entries")
    op.drop_table("cycle_entries")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_teams_id", table_name="teams")
    op.drop_table("teams")

    risk_level_enum.drop(op.get_bind(), checkfirst=True)
    cycle_phase_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
