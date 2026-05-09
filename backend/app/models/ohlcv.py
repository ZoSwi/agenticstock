from datetime import date

from sqlalchemy import Date, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OhlcvDaily(Base, TimestampMixin):
    __tablename__ = "ohlcv_daily"
    __table_args__ = (
        UniqueConstraint("ticker", "day", name="uq_ohlcv_ticker_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)

    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


Index("ix_ohlcv_ticker_day", OhlcvDaily.ticker, OhlcvDaily.day)

