"""Mark accounts that exist only for trying the app out.

A test account logs in and uses every screen like a real player, but it must
not appear in the coach's team overview and must not end up in the training
data - otherwise a few trial entries move the squad's averages and the model.

Revision ID: 20261103_000007
Revises: 20261103_000006
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261103_000007"
down_revision = "20261103_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_test_account",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_test_account")
