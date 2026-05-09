from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.watchlist import WatchlistItem

router = APIRouter()


class WatchlistAddRequest(BaseModel):
    user_id: str = Field(default="demo", max_length=64)
    ticker: str = Field(min_length=1, max_length=16)


@router.post("/watchlist")
async def add_watchlist_item(req: WatchlistAddRequest, db: AsyncSession = Depends(get_db)) -> dict:
    ticker = req.ticker.upper().strip()
    item = WatchlistItem(user_id=req.user_id, ticker=ticker)
    db.add(item)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        # idempotent add: if it already exists, just return ok
    return {"ok": True, "ticker": ticker}


@router.get("/watchlist")
async def get_watchlist(
    user_id: str = Query(default="demo", max_length=64),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(WatchlistItem).where(WatchlistItem.user_id == user_id).order_by(WatchlistItem.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return {"user_id": user_id, "tickers": [r.ticker for r in rows]}


@router.delete("/watchlist")
async def remove_watchlist_item(
    user_id: str = Query(default="demo", max_length=64),
    ticker: str = Query(min_length=1, max_length=16),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ticker = ticker.upper().strip()
    stmt = delete(WatchlistItem).where(WatchlistItem.user_id == user_id, WatchlistItem.ticker == ticker)
    await db.execute(stmt)
    await db.commit()
    return {"ok": True}

