import asyncio
from datetime import datetime
import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.db import engine
from app.core.redis import get_redis
from app.models import Base  # noqa: F401
from app.models.stock import Stock
from app.services.live_news import fetch_global_headlines
from app.services.market_pulse import fetch_market_pulse
from app.services.symbol_catalog import sync_symbol_catalog

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker


app = FastAPI(
    title="AI Stock Intelligence Agent API",
    version="0.1.0",
)

allowed_origins_raw = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

_warmers_task: asyncio.Task | None = None
_symbol_sync_task: asyncio.Task | None = None


async def _warm_live_caches_loop() -> None:
    interval_seconds = max(20, int(os.environ.get("LIVE_WARM_INTERVAL_SECONDS", "75")))
    while True:
        try:
            r = await get_redis()
            for limit in (10, 20):
                pulse = await fetch_market_pulse(limit=limit)
                await r.setex(f"market:live:v2:limit:{limit}", 60, json.dumps(pulse))
            headlines = await asyncio.to_thread(fetch_global_headlines, 20, 24)
            payload = {
                "as_of_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "source": "rss_aggregated",
                "count": len(headlines),
                "degraded": len(headlines) == 0,
                "headlines": [
                    {
                        "source": h.get("source"),
                        "title": h.get("title"),
                        "url": h.get("url"),
                        "published_at": h.get("published_at").isoformat().replace("+00:00", "Z"),
                    }
                    for h in headlines
                ],
            }
            news_ttl = max(30, int(os.environ.get("NEWS_LIVE_MAX_AGE_SECONDS", "300")))
            await r.setex("news:live:v1:limit:20", news_ttl, json.dumps(payload))
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)


async def _symbol_sync_background() -> None:
    session_local = async_sessionmaker(engine, expire_on_commit=False)
    async with session_local() as session:
        try:
            await asyncio.wait_for(sync_symbol_catalog(session, limit=12000), timeout=25.0)
            await session.commit()
        except Exception:
            await session.rollback()


@app.on_event("startup")
async def _startup() -> None:
    # Local-friendly: ensure tables exist. In production, run Alembic migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Seed a small searchable universe for the demo UI.
        seed = [
            {"ticker": "AAPL", "name": "Apple Inc."},
            {"ticker": "MSFT", "name": "Microsoft Corporation"},
            {"ticker": "NVDA", "name": "NVIDIA Corporation"},
            {"ticker": "TSLA", "name": "Tesla, Inc."},
            {"ticker": "AMZN", "name": "Amazon.com, Inc."},
            {"ticker": "GOOGL", "name": "Alphabet Inc."},
            {"ticker": "META", "name": "Meta Platforms, Inc."},
        ]
        stmt = insert(Stock).values(seed).on_conflict_do_nothing(index_elements=["ticker"])
        await conn.execute(stmt)

    # Optional wider US symbol catalog bootstrap (best effort, non-fatal).
    if os.environ.get("AUTO_SYNC_SYMBOLS_ON_STARTUP", "false").strip().lower() in {"1", "true", "yes", "on"}:
        global _symbol_sync_task
        if _symbol_sync_task is None or _symbol_sync_task.done():
            _symbol_sync_task = asyncio.create_task(_symbol_sync_background())

    global _warmers_task
    if _warmers_task is None or _warmers_task.done():
        _warmers_task = asyncio.create_task(_warm_live_caches_loop())


@app.on_event("shutdown")
async def _shutdown() -> None:
    global _warmers_task
    if _warmers_task and not _warmers_task.done():
        _warmers_task.cancel()
        try:
            await _warmers_task
        except Exception:
            pass
    _warmers_task = None
    global _symbol_sync_task
    if _symbol_sync_task and not _symbol_sync_task.done():
        _symbol_sync_task.cancel()
        try:
            await _symbol_sync_task
        except Exception:
            pass
    _symbol_sync_task = None


@app.get("/health")
async def health() -> dict:
    return {"ok": True}
