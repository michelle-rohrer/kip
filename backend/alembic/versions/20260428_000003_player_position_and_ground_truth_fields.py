"""Add player position and ground-truth related fields.

Revision ID: 20260428_000003
Revises: 20260428_000002
Create Date: 2026-04-28 22:10:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260428_000003"
down_revision = "20260428_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("player_position", sa.String(length=32), nullable=True))

    with op.batch_alter_table("training_entries") as batch_op:
        batch_op.add_column(sa.Column("session_rpe", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("session_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("participation_status", sa.String(length=32), nullable=True))

    with op.batch_alter_table("injury_entries") as batch_op:
        batch_op.add_column(
            sa.Column("medical_attention", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("time_loss_days", sa.Integer(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("injury_entries") as batch_op:
        batch_op.alter_column("medical_attention", server_default=None)
        batch_op.alter_column("time_loss_days", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("injury_entries") as batch_op:
        batch_op.drop_column("time_loss_days")
        batch_op.drop_column("medical_attention")

    with op.batch_alter_table("training_entries") as batch_op:
        batch_op.drop_column("participation_status")
        batch_op.drop_column("session_type")
        batch_op.drop_column("session_rpe")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("player_position")
