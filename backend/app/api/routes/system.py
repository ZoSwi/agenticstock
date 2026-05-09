from __future__ import annotations

import httpx
import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.redis import get_redis
from app.services.symbol_catalog import sync_symbol_catalog

router = APIRouter()


@router.get("/system/providers")
async def provider_health(r=Depends(get_redis)) -> dict:
    ml_reachable = False
    ml_model_loaded = False
    ml_detail: str | None = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ml_service_url}/health")
            resp.raise_for_status()
            ml_data = resp.json()
            ml_reachable = bool(ml_data.get("ok"))
            ml_model_loaded = bool(ml_data.get("model_loaded"))
            ml_detail = f"model_loaded={ml_model_loaded}"
    except Exception as exc:
        ml_reachable = False
        ml_model_loaded = False
        ml_detail = str(exc)

    alphavantage_configured = bool((settings.alphavantage_api_key or "").strip())
    finnhub_configured = bool((settings.finnhub_api_key or "").strip())
    news_api_configured = bool((settings.news_api_key or "").strip())
    overall_degraded = (not ml_reachable) or (not ml_model_loaded) or (not (alphavantage_configured or finnhub_configured))
    recommendations: list[str] = []
    if not (alphavantage_configured or finnhub_configured):
        recommendations.append("Set ALPHAVANTAGE_API_KEY or FINNHUB_API_KEY and restart services.")
    if not ml_model_loaded:
        recommendations.append("Train/load ML artifacts: docker compose run --rm ml python -m app.train")
    if not recommendations:
        recommendations.append("Providers look configured.")

    market_diag = None
    news_diag = None
    try:
        cached = await r.get("market:live:v2:limit:10")
        if cached:
            payload = json.loads(cached)
            market_diag = {
                "data_source": payload.get("data_source"),
                "universe_size": payload.get("universe_size", 0),
                "degraded_reason": payload.get("degraded_reason"),
                "provider_status": payload.get("provider_status", {}),
                "provider_diagnostics": payload.get("provider_diagnostics", {}),
                "as_of_et": payload.get("as_of_et"),
            }
    except Exception:
        market_diag = None

    try:
        cached_news = await r.get("news:live:v1:limit:20")
        if cached_news:
            payload = json.loads(cached_news)
            news_diag = {
                "count": payload.get("count", 0),
                "degraded": payload.get("degraded", True),
                "as_of_utc": payload.get("as_of_utc"),
                "source": payload.get("source"),
            }
    except Exception:
        news_diag = None

    if market_diag and int(market_diag.get("universe_size", 0)) == 0:
        recommendations.append("Live market universe is empty; add FINNHUB_API_KEY or wait for provider quota reset.")
    provider_quality = []
    if market_diag and market_diag.get("provider_diagnostics"):
        for name, diag in (market_diag.get("provider_diagnostics") or {}).items():
            provider_quality.append(
                {
                    "provider": name,
                    "score": float((diag or {}).get("score") or 0.0),
                    "rows": int((diag or {}).get("rows") or 0),
                    "ok": bool((diag or {}).get("ok")),
                    "error": (diag or {}).get("error"),
                }
            )
        provider_quality.sort(key=lambda x: x["score"], reverse=True)
    if news_diag and bool(news_diag.get("degraded")):
        recommendations.append("Live news feed is empty; check outbound RSS connectivity from backend container.")

    return {
        "overall_degraded": overall_degraded,
        "providers": {
            "ml_service": {"reachable": ml_reachable, "model_loaded": ml_model_loaded, "detail": ml_detail},
            "alphavantage": {"configured": alphavantage_configured},
            "finnhub": {"configured": finnhub_configured},
            "news_api": {"configured": news_api_configured},
        },
        "market_live": market_diag,
        "provider_quality": provider_quality,
        "news_live": news_diag,
        "recommendations": recommendations,
    }


@router.post("/system/symbols/sync")
async def sync_symbols(
    limit: int = 15000,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await sync_symbol_catalog(db, limit=max(1000, min(limit, 30000)))
    await db.commit()
    return {"ok": True, **result}
