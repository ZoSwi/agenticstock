from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SectorTrendDaily(Base, TimestampMixin):
    __tablename__ = "sector_trend_daily"
    __table_args__ = (UniqueConstraint("sector", "day", name="uq_sector_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sector: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)

    ret_5d: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    vol_20d: Mapped[float | None] = mapped_column(Float, nullable=True)


Index("ix_sector_day", SectorTrendDaily.sector, SectorTrendDaily.day)

