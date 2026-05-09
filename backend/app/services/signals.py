from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fundamentals import FundamentalsSnapshot
from app.models.macro import MacroIndicatorDaily
from app.models.news import NewsItem
from app.models.sector import SectorTrendDaily


async def latest_fundamentals(db: AsyncSession, ticker: str) -> FundamentalsSnapshot | None:
    stmt = select(FundamentalsSnapshot).where(FundamentalsSnapshot.ticker == ticker).order_by(
        FundamentalsSnapshot.as_of.desc()
    )
    return (await db.execute(stmt)).scalars().first()


async def news_sentiment_window(db: AsyncSession, ticker: str, days: int = 7) -> tuple[int, float | None]:
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(func.count(NewsItem.id), func.avg(NewsItem.sentiment_compound))
        .where(NewsItem.ticker == ticker, NewsItem.published_at.is_not(None), NewsItem.published_at >= since)
        .where(NewsItem.sentiment_compound.is_not(None))
    )
    row = (await db.execute(stmt)).one()
    count = int(row[0] or 0)
    avg = float(row[1]) if row[1] is not None else None
    return count, avg


async def latest_macro(db: AsyncSession) -> dict[str, float]:
    out: dict[str, float] = {}
    for series in ("DFF", "DGS10", "CPIAUCSL"):
        stmt = select(MacroIndicatorDaily).where(MacroIndicatorDaily.series == series).order_by(
            MacroIndicatorDaily.day.desc()
        )
        row = (await db.execute(stmt)).scalars().first()
        if row:
            out[series] = float(row.value)
    return out


async def latest_sector_trend(db: AsyncSession, sector: str) -> SectorTrendDaily | None:
    stmt = (
        select(SectorTrendDaily)
        .where(SectorTrendDaily.sector == sector)
        .order_by(desc(SectorTrendDaily.day))
    )
    return (await db.execute(stmt)).scalars().first()

