"""Remember when a provider has refused cycle data for this account.

Oura serves Cycle Insights to accounts that include it and refuses it for the
rest, so whether cycle data is possible differs per player. Recording what
actually happened lets the app stop offering a switch that cannot work,
without hardcoding an assumption about a whole provider.

Revision ID: 20261104_000010
Revises: 20261104_000009
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261104_000010"
down_revision = "20261104_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wearable_connections") as batch_op:
        batch_op.add_column(
            sa.Column("cycle_unavailable", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("wearable_connections") as batch_op:
        batch_op.drop_column("cycle_unavailable")
