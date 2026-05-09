from __future__ import annotations

from dataclasses import dataclass
import json

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.redis import get_redis
from app.services.market_pulse import fetch_market_pulse


@dataclass(frozen=True)
class MlPrediction:
    ticker: str
    rise_probability: float
    fall_probability: float
    confidence_score: float
    risk_level: str
    outlook: str
    volatility_detected: bool
    time_horizon: dict
    top_positive_features: list[str]
    top_negative_features: list[str]
    source: str
    degraded: bool
    degraded_reason: str | None = None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _outlook_from_prob(p_up: float) -> str:
    if p_up >= 0.56:
        return "bullish"
    if p_up <= 0.44:
        return "bearish"
    return "neutral"


def _risk_from_move(abs_pct: float) -> str:
    if abs_pct >= 4.0:
        return "high"
    if abs_pct >= 2.0:
        return "medium"
    return "low"


def _horizon_from_move(pct: float) -> dict:
    if abs(pct) < 0.6:
        short = "neutral"
    else:
        short = "bullish" if pct > 0 else "bearish"
    if abs(pct) < 1.2:
        medium = "neutral"
    else:
        medium = "bullish" if pct > 0 else "bearish"
    if abs(pct) < 1.8:
        long = "neutral"
    else:
        long = "bullish" if pct > 0 else "bearish"
    return {"short_term": short, "medium_term": medium, "long_term": long}


def _default_fallback_prediction(ticker: str) -> MlPrediction:
    return MlPrediction(
        ticker=ticker.upper(),
        rise_probability=0.5,
        fall_probability=0.5,
        confidence_score=0.4,
        risk_level="medium",
        outlook="neutral",
        volatility_detected=False,
        time_horizon={"short_term": "neutral", "medium_term": "neutral", "long_term": "neutral"},
        top_positive_features=["Baseline heuristic signal is active while live feeds recover."],
        top_negative_features=["Confidence is moderated because provider coverage is temporarily limited."],
        source="baseline_heuristic",
        degraded=True,
        degraded_reason="ml_model_unavailable_using_baseline_heuristic",
    )


async def _fallback_prediction(ticker: str) -> MlPrediction:
    symbol = ticker.upper()
    try:
        r = await get_redis()
        cached_payload = None
        # Prefer larger cached live universes when available.
        for lim in (30, 20, 12, 10, 8):
            raw = await r.get(f"market:live:v2:limit:{lim}")
            if not raw:
                continue
            p = json.loads(raw)
            if int(p.get("universe_size", 0)) <= 0:
                continue
            cached_payload = p
            break

        payload = cached_payload
        if payload is None:
            # If cache is cold/expired, fetch live pulse once and reuse it.
            payload = await fetch_market_pulse(limit=12)
            if int(payload.get("universe_size", 0)) > 0:
                await r.setex("market:live:v2:limit:12", 60, json.dumps(payload))
            else:
                payload = None

        if payload:

            row = None
            for bucket in ("top_gainers", "top_losers", "most_active"):
                for item in payload.get(bucket, []) or []:
                    if str(item.get("ticker", "")).upper() == symbol:
                        row = item
                        break
                if row:
                    break

            if row:
                pct = float(row.get("change_pct") or 0.0)
                abs_pct = abs(pct)
                p_up = _clamp(0.5 + (pct / 20.0), 0.2, 0.8)
                p_down = 1.0 - p_up
                confidence = _clamp(abs_pct / 12.0, 0.35, 0.82)
                return MlPrediction(
                    ticker=symbol,
                    rise_probability=round(p_up, 4),
                    fall_probability=round(p_down, 4),
                    confidence_score=round(confidence, 4),
                    risk_level=_risk_from_move(abs_pct),
                    outlook=_outlook_from_prob(p_up),
                    volatility_detected=abs_pct >= 3.0,
                    time_horizon=_horizon_from_move(pct),
                    top_positive_features=[
                        f"Live market feed shows {symbol} move of {pct:+.2f}% in current session snapshot."
                    ],
                    top_negative_features=["Signal is heuristic-only (live flow based), not model-trained output."],
                    source="live_heuristic",
                    degraded=True,
                    degraded_reason="ml_model_unavailable_using_live_heuristic",
                )

            breadth = payload.get("market_breadth") or {}
            adv = float(breadth.get("advancers") or 0.0)
            dec = float(breadth.get("decliners") or 0.0)
            total = max(1.0, adv + dec + float(breadth.get("unchanged") or 0.0))
            skew = (adv - dec) / total
            p_up = _clamp(0.5 + (0.15 * skew), 0.42, 0.58)
            p_down = 1.0 - p_up
            return MlPrediction(
                ticker=symbol,
                rise_probability=round(p_up, 4),
                fall_probability=round(p_down, 4),
                confidence_score=0.42,
                risk_level="medium",
                outlook=_outlook_from_prob(p_up),
                volatility_detected=False,
                time_horizon={"short_term": "neutral", "medium_term": "neutral", "long_term": "neutral"},
                top_positive_features=["Using market breadth tilt as fallback while model data recovers."],
                top_negative_features=["Ticker-specific quote was not found in live buckets; breadth proxy applied."],
                source="live_breadth_proxy",
                degraded=True,
                degraded_reason="ml_model_unavailable_using_market_breadth_proxy",
            )
    except Exception:
        pass
    return _default_fallback_prediction(symbol)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
async def fetch_prediction(ticker: str) -> MlPrediction:
    symbol = ticker.upper()
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{settings.ml_service_url}/predict/{symbol}")
            resp.raise_for_status()
            data = resp.json()
            return MlPrediction(
                ticker=data["ticker"],
                rise_probability=data["rise_probability"],
                fall_probability=data["fall_probability"],
                confidence_score=data["confidence_score"],
                risk_level=data["risk_level"],
                outlook=data["outlook"],
                volatility_detected=data["volatility_detected"],
                time_horizon=data["time_horizon"],
                top_positive_features=data.get("top_positive_features", []),
                top_negative_features=data.get("top_negative_features", []),
                source="ml_service",
                degraded=False,
                degraded_reason=None,
            )
        except (httpx.HTTPStatusError, httpx.RequestError):
            return await _fallback_prediction(symbol)
