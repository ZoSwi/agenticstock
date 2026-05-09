"""fundamentals + news + macro + sector tables

Revision ID: 0002_fund_news_macro_sector
Revises: 0001_init
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_fund_news_macro_sector"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fundamentals_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column("pe_ttm", sa.Float(), nullable=True),
        sa.Column("forward_pe", sa.Float(), nullable=True),
        sa.Column("profit_margins", sa.Float(), nullable=True),
        sa.Column("operating_margins", sa.Float(), nullable=True),
        sa.Column("debt_to_equity", sa.Float(), nullable=True),
        sa.Column("revenue_growth", sa.Float(), nullable=True),
        sa.Column("earnings_growth", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("ticker", "as_of", name="uq_fund_ticker_asof"),
    )
    op.create_index("ix_fund_ticker_asof", "fundamentals_snapshots", ["ticker", "as_of"])

    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sentiment_compound", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("source", "url", name="uq_news_source_url"),
    )
    op.create_index("ix_news_ticker_published", "news_items", ["ticker", "published_at"])

    op.create_table(
        "macro_indicator_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("series", sa.String(length=32), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("series", "day", name="uq_macro_series_day"),
    )
    op.create_index("ix_macro_series_day", "macro_indicator_daily", ["series", "day"])

    op.create_table(
        "sector_trend_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sector", sa.String(length=64), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("ret_5d", sa.Float(), nullable=True),
        sa.Column("ret_20d", sa.Float(), nullable=True),
        sa.Column("vol_20d", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("sector", "day", name="uq_sector_day"),
    )
    op.create_index("ix_sector_day", "sector_trend_daily", ["sector", "day"])


def downgrade() -> None:
    op.drop_index("ix_sector_day", table_name="sector_trend_daily")
    op.drop_table("sector_trend_daily")
    op.drop_index("ix_macro_series_day", table_name="macro_indicator_daily")
    op.drop_table("macro_indicator_daily")
    op.drop_index("ix_news_ticker_published", table_name="news_items")
    op.drop_table("news_items")
    op.drop_index("ix_fund_ticker_asof", table_name="fundamentals_snapshots")
    op.drop_table("fundamentals_snapshots")

