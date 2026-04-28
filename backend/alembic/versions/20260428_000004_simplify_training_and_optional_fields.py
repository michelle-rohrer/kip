"""Simplify training entries and make entry fields optional.

Removes match/jump columns from training_entries.
Makes training, wellness, cycle, and injury fields nullable.

Revision ID: 20260428_000004
Revises: 20260428_000003
Create Date: 2026-04-28 23:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260428_000004"
down_revision = "20260428_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop removed columns from training_entries
    with op.batch_alter_table("training_entries") as batch_op:
        batch_op.drop_column("jump_count")
        batch_op.drop_column("sprint_times")
        batch_op.drop_column("match_stats")
        batch_op.drop_column("participation_status")

    # Make duration_min and intensity nullable in training_entries
    with op.batch_alter_table("training_entries") as batch_op:
        batch_op.alter_column("duration_min", nullable=True)
        batch_op.alter_column("intensity", nullable=True)

    # Make wellness fields nullable
    with op.batch_alter_table("wellness_entries") as batch_op:
        batch_op.alter_column("sleep_hours", nullable=True)
        batch_op.alter_column("sleep_quality", nullable=True)
        batch_op.alter_column("muscle_soreness", nullable=True)
        batch_op.alter_column("mental_energy", nullable=True)
        batch_op.alter_column("stress_level", nullable=True)
        batch_op.alter_column("motivation", nullable=True)

    # Make core cycle fields nullable
    with op.batch_alter_table("cycle_entries") as batch_op:
        batch_op.alter_column("cycle_day", nullable=True)
        batch_op.alter_column("phase", nullable=True)
        batch_op.alter_column("cycle_length", nullable=True)

    # Make pain_intensity and time_loss_days nullable in injury_entries
    with op.batch_alter_table("injury_entries") as batch_op:
        batch_op.alter_column("pain_intensity", nullable=True)
        batch_op.alter_column("time_loss_days", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("injury_entries") as batch_op:
        batch_op.alter_column("time_loss_days", nullable=False, server_default="0")
        batch_op.alter_column("pain_intensity", nullable=False)

    with op.batch_alter_table("cycle_entries") as batch_op:
        batch_op.alter_column("cycle_length", nullable=False)
        batch_op.alter_column("phase", nullable=False)
        batch_op.alter_column("cycle_day", nullable=False)

    with op.batch_alter_table("wellness_entries") as batch_op:
        batch_op.alter_column("motivation", nullable=False)
        batch_op.alter_column("stress_level", nullable=False)
        batch_op.alter_column("mental_energy", nullable=False)
        batch_op.alter_column("muscle_soreness", nullable=False)
        batch_op.alter_column("sleep_quality", nullable=False)
        batch_op.alter_column("sleep_hours", nullable=False)

    with op.batch_alter_table("training_entries") as batch_op:
        batch_op.alter_column("intensity", nullable=False)
        batch_op.alter_column("duration_min", nullable=False)

    with op.batch_alter_table("training_entries") as batch_op:
        batch_op.add_column(sa.Column("participation_status", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("match_stats", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("sprint_times", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("jump_count", sa.Integer(), nullable=True))
