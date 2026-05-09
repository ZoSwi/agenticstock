from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MacroIndicatorDaily(Base, TimestampMixin):
    __tablename__ = "macro_indicator_daily"
    __table_args__ = (UniqueConstraint("series", "day", name="uq_macro_series_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series: Mapped[str] = mapped_column(String(32), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float)


Index("ix_macro_series_day", MacroIndicatorDaily.series, MacroIndicatorDaily.day)

