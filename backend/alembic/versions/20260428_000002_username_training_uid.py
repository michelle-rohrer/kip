"""Add username and training UID to users.

Revision ID: 20260428_000002
Revises: 20260301_000001
Create Date: 2026-04-28 21:40:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260428_000002"
down_revision = "20260301_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("training_uid", sa.String(length=64), nullable=True))

    op.execute("UPDATE users SET username = email WHERE username IS NULL")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", existing_type=sa.String(length=64), nullable=False)
        batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=True)
        batch_op.create_index("ix_users_username", ["username"], unique=True)
        batch_op.create_index("ix_users_training_uid", ["training_uid"], unique=True)
        batch_op.create_unique_constraint("uq_users_username", ["username"])
        batch_op.create_unique_constraint("uq_users_training_uid", ["training_uid"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_training_uid", type_="unique")
        batch_op.drop_constraint("uq_users_username", type_="unique")
        batch_op.drop_index("ix_users_training_uid")
        batch_op.drop_index("ix_users_username")
        batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=False)
        batch_op.drop_column("training_uid")
        batch_op.drop_column("username")
