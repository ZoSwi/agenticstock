"""init tables

Revision ID: 0001_init
Revises:
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stocks",
        sa.Column("ticker", sa.String(length=16), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("exchange", sa.String(length=64), nullable=True),
        sa.Column("sector", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_stocks_ticker", "stocks", ["ticker"])

    op.create_table(
        "ohlcv_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("ticker", "day", name="uq_ohlcv_ticker_day"),
    )
    op.create_index("ix_ohlcv_ticker_day", "ohlcv_daily", ["ticker", "day"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("user_id", "ticker", name="uq_watchlist_user_ticker"),
    )
    op.create_index("ix_watchlist_user", "watchlist_items", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_watchlist_user", table_name="watchlist_items")
    op.drop_table("watchlist_items")
    op.drop_index("ix_ohlcv_ticker_day", table_name="ohlcv_daily")
    op.drop_table("ohlcv_daily")
    op.drop_index("ix_stocks_ticker", table_name="stocks")
    op.drop_table("stocks")

