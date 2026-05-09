from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FundamentalsSnapshot(Base, TimestampMixin):
    __tablename__ = "fundamentals_snapshots"
    __table_args__ = (UniqueConstraint("ticker", "as_of", name="uq_fund_ticker_asof"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)

    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    pe_ttm: Mapped[float | None] = mapped_column(Float, nullable=True)
    forward_pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_margins: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_margins: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    earnings_growth: Mapped[float | None] = mapped_column(Float, nullable=True)


Index("ix_fund_ticker_asof", FundamentalsSnapshot.ticker, FundamentalsSnapshot.as_of)

