from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os

from fastapi import APIRouter, Depends, Query

from app.core.redis import get_redis
from app.services.live_news import fetch_global_headlines, fetch_ticker_headlines

router = APIRouter()

NEWS_LIVE_MAX_AGE_SECONDS = max(30, int(os.environ.get("NEWS_LIVE_MAX_AGE_SECONDS", "300")))


def _iso_utc_now() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _serialize_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        out.append(
            {
                "source": row.get("source"),
                "title": row.get("title"),
                "url": row.get("url"),
                "published_at": row.get("published_at").astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )
    return out


def _relevance_score(ticker: str, title: str, source: str) -> int:
    t = (title or "").upper()
    score = 40
    if ticker and ticker.upper() in t:
        score += 30
    if any(k in t for k in ("EARNINGS", "GUIDANCE", "UPGRADE", "DOWNGRADE", "TARGET", "FORECAST")):
        score += 20
    if "yahoo_finance_rss" in (source or "").lower():
        score += 5
    if "google_news_rss" in (source or "").lower():
        score += 5
    return max(0, min(100, score))


def _is_fresh(payload: dict, max_age_seconds: int = NEWS_LIVE_MAX_AGE_SECONDS) -> bool:
    as_of = payload.get("as_of_utc")
    if not as_of:
        return False
    try:
        ts = datetime.fromisoformat(str(as_of).replace("Z", "+00:00"))
    except Exception:
        return False
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return 0 <= age <= max_age_seconds


@router.get("/live")
async def get_live_news(
    limit: int = Query(default=20, ge=5, le=60),
    force_refresh: bool = Query(default=False),
    r=Depends(get_redis),
) -> dict:
    cache_key = f"news:live:v1:limit:{limit}"
    if not force_refresh:
        cached = await r.get(cache_key)
        if cached:
            payload = json.loads(cached)
            if _is_fresh(payload):
                return payload

    rows = await asyncio.to_thread(fetch_global_headlines, limit, 24)
    payload = {
        "as_of_utc": _iso_utc_now(),
        "source": "rss_aggregated",
        "count": len(rows),
        "degraded": len(rows) == 0,
        "headlines": _serialize_rows(rows),
    }
    await r.setex(cache_key, NEWS_LIVE_MAX_AGE_SECONDS, json.dumps(payload))
    return payload


@router.get("/{ticker}")
async def get_ticker_news(
    ticker: str,
    limit: int = Query(default=20, ge=5, le=60),
    force_refresh: bool = Query(default=False),
    r=Depends(get_redis),
) -> dict:
    symbol = ticker.upper().strip()
    cache_key = f"news:ticker:v1:{symbol}:limit:{limit}"
    if not force_refresh:
        cached = await r.get(cache_key)
        if cached:
            payload = json.loads(cached)
            if _is_fresh(payload):
                return payload

    rows = await asyncio.to_thread(fetch_ticker_headlines, symbol, limit, 72)
    payload = {
        "ticker": symbol,
        "as_of_utc": _iso_utc_now(),
        "source": "rss_aggregated",
        "count": len(rows),
        "degraded": len(rows) == 0,
        "headlines": [
            {
                **h,
                "relevance": _relevance_score(symbol, h.get("title", ""), h.get("source", "")),
            }
            for h in _serialize_rows(rows)
        ],
    }
    await r.setex(cache_key, NEWS_LIVE_MAX_AGE_SECONDS, json.dumps(payload))
    return payload
