"""Wearable integrations plus the training fields the app always asked for.

Adds:
  * ``wearable_connections`` - one row per player and provider
  * ``wearable_daily``       - one row per player, day and provider
  * ``training_entries.jump_count`` / ``participation_status`` - re-added after
    migration 20260428_000004 dropped them while the form kept collecting them

Revision ID: 20261103_000006
Revises: 20260824_000005
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261103_000006"
down_revision = "20260824_000005"
branch_labels = None
depends_on = None

WEARABLE_PROVIDERS = ("whoop", "oura", "apple_health")


def _provider_enum() -> sa.Enum:
    return sa.Enum(*WEARABLE_PROVIDERS, name="wearable_provider")


def _provider_column_type(bind: sa.engine.Connection):
    """The column type to use once the enum type itself already exists.

    On Postgres every ``create_table`` would otherwise try to ``CREATE TYPE``
    again and the second table would fail with "type already exists".
    SQLite has no enum types and renders a VARCHAR with a CHECK constraint.
    """
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects import postgresql

        return postgresql.ENUM(*WEARABLE_PROVIDERS, name="wearable_provider", create_type=False)
    return _provider_enum()


def upgrade() -> None:
    bind = op.get_bind()
    # Create the type once up front; a no-op on dialects without enum types.
    _provider_enum().create(bind, checkfirst=True)
    provider_enum = _provider_column_type(bind)

    op.create_table(
        "wearable_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(length=512), nullable=True),
        sa.Column("external_user_id", sa.String(length=128), nullable=True),
        sa.Column("ingest_token_hash", sa.String(length=128), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=16), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id", "provider", name="uq_wearable_connections_player_provider"
        ),
    )
    op.create_index("ix_wearable_connections_id", "wearable_connections", ["id"], unique=False)
    op.create_index(
        "ix_wearable_connections_player_id", "wearable_connections", ["player_id"], unique=False
    )
    op.create_index(
        "ix_wearable_connections_ingest_token_hash",
        "wearable_connections",
        ["ingest_token_hash"],
        unique=False,
    )

    op.create_table(
        "wearable_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("sleep_score", sa.Integer(), nullable=True),
        sa.Column("readiness_score", sa.Integer(), nullable=True),
        sa.Column("hrv_ms", sa.Float(), nullable=True),
        sa.Column("resting_hr", sa.Float(), nullable=True),
        sa.Column("respiratory_rate", sa.Float(), nullable=True),
        sa.Column("strain", sa.Float(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("active_calories", sa.Float(), nullable=True),
        sa.Column("workout_minutes", sa.Float(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "player_id", "date", "provider", name="uq_wearable_daily_player_date_provider"
        ),
    )
    op.create_index("ix_wearable_daily_id", "wearable_daily", ["id"], unique=False)
    op.create_index("ix_wearable_daily_player_id", "wearable_daily", ["player_id"], unique=False)
    op.create_index("ix_wearable_daily_date", "wearable_daily", ["date"], unique=False)

    with op.batch_alter_table("training_entries") as batch_op:
        batch_op.add_column(sa.Column("jump_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("participation_status", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("training_entries") as batch_op:
        batch_op.drop_column("participation_status")
        batch_op.drop_column("jump_count")

    op.drop_index("ix_wearable_daily_date", table_name="wearable_daily")
    op.drop_index("ix_wearable_daily_player_id", table_name="wearable_daily")
    op.drop_index("ix_wearable_daily_id", table_name="wearable_daily")
    op.drop_table("wearable_daily")

    op.drop_index("ix_wearable_connections_ingest_token_hash", table_name="wearable_connections")
    op.drop_index("ix_wearable_connections_player_id", table_name="wearable_connections")
    op.drop_index("ix_wearable_connections_id", table_name="wearable_connections")
    op.drop_table("wearable_connections")

    _provider_enum().drop(op.get_bind(), checkfirst=True)
