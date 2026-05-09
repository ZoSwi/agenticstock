from __future__ import annotations

import asyncio
import os

from sqlalchemy import select
from app.pipeline.ingest_ohlcv import ingest
from app.pipeline.adapters.fundamentals_yfinance import fetch_fundamentals_snapshot
from app.pipeline.adapters.macro_fred_csv import SERIES_URLS, fetch_series_latest
from app.pipeline.adapters.news_rss_sentiment import fetch_rss_items_for_ticker
from app.pipeline.adapters.sector_etf_trends import fetch_sector_trends

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.fundamentals import FundamentalsSnapshot
from app.models.macro import MacroIndicatorDaily
from app.models.news import NewsItem
from app.models.sector import SectorTrendDaily
from app.models.watchlist import WatchlistItem


def _configured_tickers() -> list[str]:
    tickers = os.environ.get("TICKERS", "AAPL,MSFT,NVDA,TSLA,AMZN,GOOGL").split(",")
    return [t.strip().upper() for t in tickers if t.strip()]


async def _resolve_tickers(session) -> list[str]:
    tickers = set(_configured_tickers())
    watchlist_rows = (
        await session.execute(select(WatchlistItem.ticker).distinct())
    ).scalars().all()
    for ticker in watchlist_rows:
        if ticker:
            tickers.add(ticker.strip().upper())
    return sorted(tickers)


async def _upsert_news(session, tickers: list[str], per_source_limit: int = 25) -> int:
    news_rows: list[dict] = []
    for t in tickers:
        try:
            news_rows.extend(fetch_rss_items_for_ticker(t, limit=per_source_limit))
        except Exception:
            continue
    if not news_rows:
        return 0
    stmt = insert(NewsItem).values(news_rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["source", "url"])
    res = await session.execute(stmt)
    return res.rowcount or 0


async def run_daily() -> dict:
    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    ohlcv = {"tickers": [], "rows_inserted": 0}
    fundamentals_upserted = 0
    news_upserted = 0
    macro_upserted = 0
    sector_upserted = 0

    async with SessionLocal() as session:
        tickers = await _resolve_tickers(session)
        ohlcv = await ingest(tickers)

        # Fundamentals (per-ticker snapshot)
        fund_rows = []
        for t in tickers:
            try:
                fund_rows.append(fetch_fundamentals_snapshot(t))
            except Exception:
                continue
        if fund_rows:
            stmt = insert(FundamentalsSnapshot).values(fund_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker", "as_of"],
                set_={k: getattr(stmt.excluded, k) for k in fund_rows[0].keys() if k not in {"ticker", "as_of"}},
            )
            res = await session.execute(stmt)
            fundamentals_upserted += res.rowcount or 0

        # News + sentiment (RSS)
        news_upserted += await _upsert_news(session, tickers=tickers, per_source_limit=25)

        # Macro (FRED CSV, latest points)
        macro_rows: list[dict] = []
        for series in SERIES_URLS.keys():
            try:
                d, v = await fetch_series_latest(series)
                macro_rows.append({"series": series, "day": d, "value": v})
            except Exception:
                continue
        if macro_rows:
            stmt = insert(MacroIndicatorDaily).values(macro_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["series", "day"],
                set_={"value": stmt.excluded.value},
            )
            res = await session.execute(stmt)
            macro_upserted += res.rowcount or 0

        # Sector ETF trends
        try:
            sector_rows = fetch_sector_trends()
        except Exception:
            sector_rows = []
        if sector_rows:
            stmt = insert(SectorTrendDaily).values(sector_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["sector", "day"],
                set_={
                    "ret_5d": stmt.excluded.ret_5d,
                    "ret_20d": stmt.excluded.ret_20d,
                    "vol_20d": stmt.excluded.vol_20d,
                },
            )
            res = await session.execute(stmt)
            sector_upserted += res.rowcount or 0

        await session.commit()

    await engine.dispose()

    return {
        "tickers": ohlcv["tickers"],
        "ohlcv": ohlcv,
        "fundamentals": {"upserted": fundamentals_upserted},
        "news": {"inserted": news_upserted},
        "macro": {"upserted": macro_upserted},
        "sector": {"upserted": sector_upserted},
    }


async def run_live_feed_only() -> dict:
    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    inserted = 0
    tickers: list[str] = []
    async with SessionLocal() as session:
        tickers = await _resolve_tickers(session)
        inserted = await _upsert_news(session, tickers=tickers, per_source_limit=25)
        await session.commit()

    await engine.dispose()
    return {"tickers": tickers, "news": {"inserted": inserted}}


def main() -> None:
    print(asyncio.run(run_daily()))


if __name__ == "__main__":
    main()
