"""Carry workout type and menstrual flow in from the devices.

* ``wearable_connections.sync_cycle`` - per provider opt-in, because cycle data
  is the most sensitive category and a player may trust one app with it and
  not another. Defaults to off.
* ``wearable_daily.workout_sport``    - what the device called the session,
  used to pre-fill the session type.
* ``wearable_daily.menstrual_flow``   - only ever written when the opt-in above
  is on for that provider.

Revision ID: 20261103_000008
Revises: 20261103_000007
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261103_000008"
down_revision = "20261103_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wearable_connections") as batch_op:
        batch_op.add_column(
            sa.Column("sync_cycle", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    with op.batch_alter_table("wearable_daily") as batch_op:
        batch_op.add_column(sa.Column("workout_sport", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("menstrual_flow", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("wearable_daily") as batch_op:
        batch_op.drop_column("menstrual_flow")
        batch_op.drop_column("workout_sport")
    with op.batch_alter_table("wearable_connections") as batch_op:
        batch_op.drop_column("sync_cycle")
