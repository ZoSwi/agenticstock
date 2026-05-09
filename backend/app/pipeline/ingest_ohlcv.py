from __future__ import annotations

import asyncio
import os
from datetime import date

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.ohlcv import OhlcvDaily


def _fetch(ticker: str, period: str = "2y") -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[["open", "high", "low", "close", "volume"]].dropna().copy()


async def ingest(tickers: list[str]) -> dict:
    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    inserted = 0
    async with SessionLocal() as session:
        for t in tickers:
            data = _fetch(t)
            if data.empty:
                continue
            rows = []
            for idx, r in data.iterrows():
                day = date(idx.year, idx.month, idx.day)
                rows.append(
                    {
                        "ticker": t,
                        "day": day,
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                        "volume": float(r["volume"]),
                    }
                )
            stmt = insert(OhlcvDaily).values(rows)
            stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "day"])
            res = await session.execute(stmt)
            inserted += res.rowcount or 0
        await session.commit()

    await engine.dispose()
    return {"tickers": tickers, "rows_inserted": inserted}


def main() -> None:
    tickers = os.environ.get("TICKERS", "AAPL,MSFT,NVDA,TSLA").split(",")
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    print(asyncio.run(ingest(tickers)))


if __name__ == "__main__":
    main()

