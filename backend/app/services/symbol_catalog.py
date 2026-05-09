from __future__ import annotations

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"


def _normalize_ticker(raw: str) -> str:
    return (raw or "").upper().strip().replace("/", "-")


async def fetch_us_symbol_catalog(limit: int = 15000) -> list[dict]:
    async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "AgenticPI/0.1 support@example.com"}) as client:
        resp = await client.get(SEC_TICKERS_URL)
        resp.raise_for_status()
        payload = resp.json()

    rows = payload.get("data") or []
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 4:
            continue
        ticker = _normalize_ticker(str(row[2] or ""))
        name = str(row[1] or "").strip() or None
        exchange = str(row[0] or "").strip() or "US"
        if not ticker:
            continue
        out.append({"ticker": ticker, "name": name, "exchange": exchange, "sector": None})
        if len(out) >= limit:
            break
    return out


async def sync_symbol_catalog(session: AsyncSession, limit: int = 15000) -> dict:
    rows = await fetch_us_symbol_catalog(limit=limit)
    if not rows:
        return {"fetched": 0, "upserted": 0}

    stmt = insert(Stock).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker"],
        set_={
            "name": stmt.excluded.name,
            "exchange": stmt.excluded.exchange,
        },
    )
    res = await session.execute(stmt)
    return {"fetched": len(rows), "upserted": int(res.rowcount or 0)}
