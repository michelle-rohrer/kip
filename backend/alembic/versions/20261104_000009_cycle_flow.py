"""Record the period itself, so the rest of the cycle can be derived.

The form asked for cycle day, phase and cycle length - three numbers a player
has to work out herself, every day. What she actually knows is whether she has
her period. This column stores that; the derivation lives in
``app.services.wearables.cycle``.

Revision ID: 20261104_000009
Revises: 20261103_000008
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261104_000009"
down_revision = "20261103_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cycle_entries") as batch_op:
        batch_op.add_column(sa.Column("menstrual_flow", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("cycle_entries") as batch_op:
        batch_op.drop_column("menstrual_flow")
