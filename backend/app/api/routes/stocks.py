from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import os
import time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
import json
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import yfinance as yf

from app.core.db import get_db
from app.core.redis import get_redis
from app.integrations.ml_service import fetch_prediction
from app.models.ohlcv import OhlcvDaily
from app.models.stock import Stock
from app.schemas.analysis import PredictionResponse, ReasonsResponse, StockAnalysisResponse
from app.schemas.common import Outlook, Probabilities, RiskLevel, TimeHorizonOutlook
from app.services.analysis import (
    augment_drivers_with_context,
    augment_drivers_with_snapshot,
    best_for_from,
    drivers_from,
    suggested_action_from,
    watch_next_contextual,
    watch_next_from,
)
from app.services.agent import render_analysis_markdown
from app.services.llm import enhance_answer_markdown, resolve_llm_provider
from app.services.market_pulse import DEFAULT_UNIVERSE, empty_market_pulse, fetch_market_pulse
from app.services.live_news import fetch_ticker_headlines
from app.services.signals import latest_fundamentals, latest_macro, latest_sector_trend, news_sentiment_window

router = APIRouter()

NAME_ALIASES = {
    "INTEL": "INTC",
    "ALPHABET": "GOOGL",
    "GOOGLE": "GOOGL",
    "MICROSOFT": "MSFT",
    "APPLE": "AAPL",
    "NVIDIA": "NVDA",
    "TESLA": "TSLA",
    "AMAZON": "AMZN",
    "META": "META",
    "FACEBOOK": "META",
}

MARKET_LIVE_MAX_AGE_SECONDS = max(5, int(os.environ.get("MARKET_LIVE_MAX_AGE_SECONDS", "90")))
MARKET_CACHE_SOFT_STALE_SECONDS = max(
    MARKET_LIVE_MAX_AGE_SECONDS,
    int(os.environ.get("MARKET_CACHE_SOFT_STALE_SECONDS", str(MARKET_LIVE_MAX_AGE_SECONDS * 8))),
)


def _market_status(now_et: datetime) -> str:
    if now_et.weekday() >= 5:
        return "closed"
    m = now_et.hour * 60 + now_et.minute
    return "open" if (9 * 60 + 30) <= m < (16 * 60) else "closed"


def _risk_pct_from_level(risk_level: str) -> float:
    rl = (risk_level or "").lower()
    if rl == "high":
        return 0.03
    if rl == "medium":
        return 0.018
    return 0.012


def _scenario_returns(outlook: str, risk_level: str) -> tuple[float, float, float]:
    rp = _risk_pct_from_level(risk_level)
    if outlook == "bullish":
        return (2.2 * rp, 0.7 * rp, -1.2 * rp)
    if outlook == "bearish":
        return (0.9 * rp, -0.5 * rp, -2.0 * rp)
    return (1.3 * rp, 0.1 * rp, -1.4 * rp)


def _parse_as_of_utc(payload: dict) -> datetime | None:
    raw = payload.get("as_of_utc")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None


def _is_fresh_payload(payload: dict, max_age_seconds: int = MARKET_LIVE_MAX_AGE_SECONDS) -> bool:
    as_of_utc = _parse_as_of_utc(payload)
    if not as_of_utc:
        return False
    now_utc = datetime.now(timezone.utc)
    age = (now_utc - as_of_utc).total_seconds()
    return 0 <= age <= max_age_seconds


def _payload_age_seconds(payload: dict) -> float | None:
    as_of_utc = _parse_as_of_utc(payload)
    if not as_of_utc:
        return None
    return (datetime.now(timezone.utc) - as_of_utc).total_seconds()


async def _market_pulse_from_db(db: AsyncSession, limit: int) -> dict:
    ranked = (
        select(
            OhlcvDaily.ticker,
            OhlcvDaily.day,
            OhlcvDaily.close,
            OhlcvDaily.volume,
            func.row_number().over(partition_by=OhlcvDaily.ticker, order_by=OhlcvDaily.day.desc()).label("rn"),
        )
        .where(OhlcvDaily.ticker.in_(DEFAULT_UNIVERSE))
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                ranked.c.ticker,
                ranked.c.day,
                ranked.c.close,
                ranked.c.volume,
                ranked.c.rn,
            ).where(ranked.c.rn <= 2)
        )
    ).all()

    grouped: dict[str, list] = defaultdict(list)
    for ticker, day, close, volume, rn in rows:
        grouped[ticker].append(
            {
                "day": day,
                "close": float(close),
                "volume": int(volume or 0),
                "rn": int(rn),
            }
        )

    quote_rows: list[dict] = []
    for ticker, pts in grouped.items():
        latest = next((p for p in pts if p["rn"] == 1), None)
        prev = next((p for p in pts if p["rn"] == 2), None)
        if not latest or not prev or prev["close"] == 0:
            continue
        ch = latest["close"] - prev["close"]
        pct = (ch / prev["close"]) * 100.0
        quote_rows.append(
            {
                "ticker": ticker,
                "last": round(latest["close"], 4),
                "change": round(ch, 4),
                "change_pct": round(pct, 4),
                "volume": latest["volume"],
            }
        )

    top_gainers = sorted(quote_rows, key=lambda r: r["change_pct"], reverse=True)[:limit]
    top_losers = sorted(quote_rows, key=lambda r: r["change_pct"])[:limit]
    most_active = sorted(quote_rows, key=lambda r: r["volume"], reverse=True)[:limit]
    advancers = sum(1 for r in quote_rows if r["change_pct"] > 0)
    decliners = sum(1 for r in quote_rows if r["change_pct"] < 0)
    unchanged = max(0, len(quote_rows) - advancers - decliners)

    proxy_index_map = {"S&P 500": "SPY", "Nasdaq": "QQQ", "Dow 30": "DIA", "Russell 2000": "IWM"}
    lookup = {r["ticker"]: r for r in quote_rows}
    indices = []
    for name, ticker in proxy_index_map.items():
        row = lookup.get(ticker)
        if not row:
            continue
        indices.append(
            {
                "name": name,
                "symbol": ticker,
                "last": row["last"],
                "change": row["change"],
                "change_pct": row["change_pct"],
            }
        )

    now_utc = datetime.utcnow().replace(microsecond=0)
    now_et = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0)
    return {
        "as_of_utc": f"{now_utc.isoformat()}Z",
        "as_of_et": now_et.isoformat(),
        "market_status": _market_status(now_et),
        "data_source": "db_snapshot",
        "universe_size": len(quote_rows),
        "market_breadth": {
            "advancers": advancers,
            "decliners": decliners,
            "unchanged": unchanged,
        },
        "provider_status": {"finnhub": False, "alphavantage": False, "yahoo": False},
        "provider_diagnostics": {
            "alphavantage": {"configured": False, "ok": False, "rows": 0, "latency_ms": None, "score": 0.0, "error": "db_snapshot"},
            "finnhub": {"configured": False, "ok": False, "rows": 0, "latency_ms": None, "score": 0.0, "error": "db_snapshot"},
            "yahoo": {"configured": True, "ok": False, "rows": 0, "latency_ms": None, "score": 0.0, "error": "db_snapshot"},
        },
        "degraded_reason": "db_snapshot_only",
        "indices": indices,
        "sector_leaders": [],
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "most_active": most_active,
    }


def _download_price_series_fallback(symbol: str, days: int) -> list[dict]:
    # Keep fallback bounded so one click feels responsive.
    period = "1y" if days > 120 else ("6mo" if days > 60 else "3mo")
    df = yf.download(
        tickers=symbol,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        return []
    points: list[dict] = []
    for day, row in df.tail(days).iterrows():
        try:
            points.append(
                {
                    "day": day.date().isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(float(row.get("Volume", 0.0) or 0.0)),
                }
            )
        except Exception:
            continue
    return points


def _download_intraday_fallback(symbol: str, session: str, resolution: str) -> list[dict]:
    period = "5d" if session == "5D" else "1d"
    interval = "1m" if resolution == "1" else "5m"
    try:
        df = yf.download(
            tickers=symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
            prepost=False,
        )
    except Exception:
        return []
    if df is None or df.empty:
        return []
    points: list[dict] = []
    for ts, row in df.iterrows():
        try:
            points.append(
                {
                    "day": ts.to_pydatetime().replace(tzinfo=None).isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(float(row.get("Volume", 0.0) or 0.0)),
                }
            )
        except Exception:
            continue
    return points


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append((v * alpha) + (out[-1] * (1.0 - alpha)))
    return out


def _technical_snapshot_from_rows(rows: list[OhlcvDaily]) -> dict | None:
    if len(rows) < 35:
        return None
    rows_sorted = sorted(rows, key=lambda r: r.day)
    closes = [float(r.close) for r in rows_sorted]
    highs = [float(r.high) for r in rows_sorted]
    lows = [float(r.low) for r in rows_sorted]
    if not closes:
        return None
    close = closes[-1]
    sma50_window = closes[-50:] if len(closes) >= 50 else closes
    sma50 = sum(sma50_window) / max(1, len(sma50_window))
    sma50_pct = ((close - sma50) / sma50) * 100.0 if sma50 else 0.0

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    macd_signal = _ema(macd_line, 9)
    macd = macd_line[-1] if macd_line else None
    macd_sig = macd_signal[-1] if macd_signal else None

    trs: list[float] = []
    prev_close = closes[0]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - prev_close), abs(lows[i] - prev_close))
        trs.append(tr)
        prev_close = closes[i]
    atr14 = None
    if len(trs) >= 14:
        atr14 = sum(trs[-14:]) / 14.0
    atr14_pct = ((atr14 / close) * 100.0) if atr14 and close else None

    return {
        "close": close,
        "sma50": sma50,
        "sma50_pct": sma50_pct,
        "macd": macd,
        "macd_signal": macd_sig,
        "atr14_pct": atr14_pct,
    }


def _fetch_finnhub_candles(symbol: str, days: int, resolution: str = "D", from_ts: int | None = None) -> list[dict]:
    key = (os.environ.get("FINNHUB_API_KEY") or "").strip()
    if not key:
        return []
    now = int(time.time())
    if from_ts is not None:
        frm = int(from_ts)
    elif resolution == "D":
        frm = int((datetime.utcnow() - timedelta(days=max(30, min(365, days + 10)))).timestamp())
    else:
        frm = int((datetime.utcnow() - timedelta(days=5)).timestamp())
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                "https://finnhub.io/api/v1/stock/candle",
                params={
                    "symbol": symbol,
                    "resolution": resolution,
                    "from": frm,
                    "to": now,
                    "token": key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    if data.get("s") != "ok":
        return []
    ts = data.get("t") or []
    op = data.get("o") or []
    hi = data.get("h") or []
    lo = data.get("l") or []
    cl = data.get("c") or []
    vo = data.get("v") or []
    out: list[dict] = []
    for i in range(min(len(ts), len(op), len(hi), len(lo), len(cl))):
        try:
            out.append(
                {
                    "day": datetime.utcfromtimestamp(int(ts[i])).isoformat()
                    if resolution != "D"
                    else datetime.utcfromtimestamp(int(ts[i])).date().isoformat(),
                    "open": float(op[i]),
                    "high": float(hi[i]),
                    "low": float(lo[i]),
                    "close": float(cl[i]),
                    "volume": int(float(vo[i])) if i < len(vo) else 0,
                }
            )
        except Exception:
            continue
    return out[-days:]


def _fetch_finnhub_quote(symbol: str) -> dict | None:
    key = (os.environ.get("FINNHUB_API_KEY") or "").strip()
    if not key:
        return None
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": symbol, "token": key},
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        return None
    price = float(payload.get("c") or 0.0)
    prev = float(payload.get("pc") or 0.0)
    if price <= 0 or prev <= 0:
        return None
    change = price - prev
    pct = (change / prev) * 100.0 if prev else 0.0
    return {
        "ticker": symbol,
        "last": round(price, 4),
        "change": round(change, 4),
        "change_pct": round(pct, 4),
        "volume": 0,
    }


def _fetch_finnhub_quote_detail(symbol: str) -> dict | None:
    key = (os.environ.get("FINNHUB_API_KEY") or "").strip()
    if not key:
        return None
    try:
        with httpx.Client(timeout=8.0) as client:
            quote_resp = client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": symbol, "token": key},
            )
            quote_resp.raise_for_status()
            q = quote_resp.json() or {}

            metric_resp = client.get(
                "https://finnhub.io/api/v1/stock/metric",
                params={"symbol": symbol, "metric": "all", "token": key},
            )
            metric_resp.raise_for_status()
            m_payload = metric_resp.json() or {}
    except Exception:
        return None

    metric = m_payload.get("metric") or {}
    last = float(q.get("c") or 0.0)
    prev = float(q.get("pc") or 0.0)
    if last <= 0 or prev <= 0:
        return None
    change = last - prev
    change_pct = (change / prev) * 100.0 if prev else 0.0
    return {
        "ticker": symbol,
        "last": round(last, 4),
        "change": round(change, 4),
        "change_pct": round(change_pct, 4),
        "open": float(q.get("o") or 0.0) or None,
        "high": float(q.get("h") or 0.0) or None,
        "low": float(q.get("l") or 0.0) or None,
        "prev_close": prev,
        "week_52_high": float(metric.get("52WeekHigh") or 0.0) or None,
        "week_52_low": float(metric.get("52WeekLow") or 0.0) or None,
        "timestamp": int(q.get("t") or 0) or None,
    }


def _fetch_finnhub_profile(symbol: str) -> dict | None:
    key = (os.environ.get("FINNHUB_API_KEY") or "").strip()
    if not key:
        return None
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(
                "https://finnhub.io/api/v1/stock/profile2",
                params={"symbol": symbol, "token": key},
            )
            resp.raise_for_status()
            payload = resp.json() or {}
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    name = str(payload.get("name") or "").strip() or None
    exchange = str(payload.get("exchange") or "").strip() or None
    return {"ticker": symbol, "name": name, "exchange": exchange}


def _search_finnhub_symbols(query: str, limit: int) -> list[dict]:
    key = (os.environ.get("FINNHUB_API_KEY") or "").strip()
    if not key or not query:
        return []
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(
                "https://finnhub.io/api/v1/search",
                params={"q": query, "token": key},
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        return []

    rows = payload.get("result") or []
    if not isinstance(rows, list):
        return []
    out: list[dict] = []
    for row in rows:
        symbol = str(row.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        out.append(
            {
                "ticker": symbol,
                "name": row.get("description"),
                "exchange": row.get("mic") or row.get("displaySymbol"),
                "sector": None,
            }
        )
        if len(out) >= limit:
            break
    return out


def _fetch_alpha_candles(symbol: str, days: int) -> list[dict]:
    key = (os.environ.get("ALPHAVANTAGE_API_KEY") or "").strip()
    if not key:
        return []
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "outputsize": "compact",
                    "apikey": key,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        return []
    series = payload.get("Time Series (Daily)") or {}
    if not isinstance(series, dict) or not series:
        return []
    out: list[dict] = []
    for day, vals in series.items():
        try:
            out.append(
                {
                    "day": day,
                    "open": float(vals.get("1. open")),
                    "high": float(vals.get("2. high")),
                    "low": float(vals.get("3. low")),
                    "close": float(vals.get("4. close")),
                    "volume": int(float(vals.get("5. volume") or 0.0)),
                }
            )
        except Exception:
            continue
    out.sort(key=lambda x: x["day"])
    return out[-days:]


def _fetch_twelvedata_candles(symbol: str, days: int) -> list[dict]:
    key = (os.environ.get("TWELVEDATA_API_KEY") or "").strip()
    if not key:
        return []
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://api.twelvedata.com/time_series",
                params={
                    "symbol": symbol,
                    "interval": "1day",
                    "outputsize": max(30, min(500, days + 20)),
                    "apikey": key,
                    "format": "JSON",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        return []
    values = payload.get("values") or []
    if not isinstance(values, list) or not values:
        return []
    out: list[dict] = []
    for row in values:
        try:
            day = str(row.get("datetime") or "").split(" ")[0]
            out.append(
                {
                    "day": day,
                    "open": float(row.get("open")),
                    "high": float(row.get("high")),
                    "low": float(row.get("low")),
                    "close": float(row.get("close")),
                    "volume": int(float(row.get("volume") or 0.0)),
                }
            )
        except Exception:
            continue
    out.sort(key=lambda x: x["day"])
    return out[-days:]


def _fetch_finnhub_recommendation(symbol: str) -> dict | None:
    key = (os.environ.get("FINNHUB_API_KEY") or "").strip()
    if not key:
        return None
    try:
        with httpx.Client(timeout=8.0) as client:
            rec = client.get(
                "https://finnhub.io/api/v1/stock/recommendation",
                params={"symbol": symbol, "token": key},
            )
            rec.raise_for_status()
            rows = rec.json() or []
    except Exception:
        return None
    if not isinstance(rows, list) or not rows:
        return None
    latest = rows[0] or {}
    previous = rows[1] if len(rows) > 1 else None
    buy = int(latest.get("buy") or 0) + int(latest.get("strongBuy") or 0)
    hold = int(latest.get("hold") or 0)
    sell = int(latest.get("sell") or 0) + int(latest.get("strongSell") or 0)
    total = max(1, buy + hold + sell)
    stance = "hold"
    if buy / total >= 0.55:
        stance = "buy"
    elif sell / total >= 0.45:
        stance = "sell"
    delta = None
    trend = "flat"
    if isinstance(previous, dict):
        p_buy = int(previous.get("buy") or 0) + int(previous.get("strongBuy") or 0)
        p_hold = int(previous.get("hold") or 0)
        p_sell = int(previous.get("sell") or 0) + int(previous.get("strongSell") or 0)
        p_total = max(1, p_buy + p_hold + p_sell)
        p_buy_ratio = p_buy / p_total
        buy_ratio = buy / total
        shift = round((buy_ratio - p_buy_ratio) * 100.0, 2)
        delta = {
            "buy_change": buy - p_buy,
            "hold_change": hold - p_hold,
            "sell_change": sell - p_sell,
            "buy_ratio_change_pct": shift,
        }
        if shift >= 2.5:
            trend = "upgraded"
        elif shift <= -2.5:
            trend = "downgraded"
    return {
        "as_of": latest.get("period"),
        "buy": buy,
        "hold": hold,
        "sell": sell,
        "consensus": stance,
        "trend": trend,
        "delta": delta,
    }


@router.get("/search")
async def search_stocks(
    q: str = Query(default="", max_length=32),
    limit: int = Query(default=10, ge=1, le=50),
    r=Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict:
    q = q.strip().upper()
    if not q:
        return {"results": []}
    q_effective = NAME_ALIASES.get(q, q)

    stmt = (
        select(Stock)
        .where(
            or_(
                Stock.ticker.ilike(f"{q}%"),
                Stock.ticker.ilike(f"{q_effective}%"),
                Stock.name.ilike(f"%{q}%"),
                Stock.name.ilike(f"%{q_effective}%"),
            )
        )
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    out: list[dict] = []
    seen: set[str] = set()
    for s in rows:
        t = (s.ticker or "").upper().strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append({"ticker": t, "name": s.name, "exchange": s.exchange, "sector": s.sector})
    if len(out) >= limit:
        return {"results": out[:limit]}

    # Fast fallback from cached live pulse so search works even if the stocks table is sparse.
    for k in ("market:live:v2:limit:30", "market:live:v2:limit:12"):
        if len(out) >= limit:
            break
        try:
            raw = await r.get(k)
            if not raw:
                continue
            payload = json.loads(raw)
            for bucket in ("top_gainers", "top_losers", "most_active"):
                for item in payload.get(bucket, []) or []:
                    t = str(item.get("ticker", "")).upper().strip()
                    if not t or t in seen:
                        continue
                    if not (t.startswith(q) or q in t or t.startswith(q_effective) or q_effective in t):
                        continue
                    seen.add(t)
                    out.append({"ticker": t, "name": None, "exchange": None, "sector": None})
                    if len(out) >= limit:
                        break
                if len(out) >= limit:
                    break
        except Exception:
            continue

    # Final static fallback from the configured/default universe.
    if len(out) < limit:
        for t in DEFAULT_UNIVERSE:
            tt = t.upper().strip()
            if tt in seen:
                continue
            if not (tt.startswith(q) or q in tt or tt.startswith(q_effective) or q_effective in tt):
                continue
            seen.add(tt)
            out.append({"ticker": tt, "name": None, "exchange": None, "sector": None})
            if len(out) >= limit:
                break

    # Provider-level search across wider market universe (not limited to pulse top movers).
    if len(out) < limit:
        try:
            remote = await asyncio.wait_for(asyncio.to_thread(_search_finnhub_symbols, q_effective, limit), timeout=6.0)
        except Exception:
            remote = []
        remote_by_ticker = {str(i.get("ticker", "")).upper().strip(): i for i in remote}
        # Enrich already-found rows with provider names/exchange when missing.
        for row in out:
            t = str(row.get("ticker", "")).upper().strip()
            remote_row = remote_by_ticker.get(t)
            if not remote_row:
                continue
            if not row.get("name"):
                row["name"] = remote_row.get("name")
            if not row.get("exchange"):
                row["exchange"] = remote_row.get("exchange")
        for item in remote:
            t = str(item.get("ticker", "")).upper().strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(item)
            if len(out) >= limit:
                break

    if not out and q_effective and len(q_effective) <= 12 and q_effective.replace("-", "").replace(".", "").isalnum():
        out.append({"ticker": q_effective, "name": None, "exchange": None, "sector": None})

    return {"results": out[:limit]}


@router.get("/market/live")
async def get_market_live(
    limit: int = Query(default=10, ge=3, le=30),
    force_refresh: bool = Query(default=False),
    r=Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        cache_key = f"market:live:v2:limit:{limit}"
        last_good_key = f"market:live:last_good:v1:limit:{limit}"
        if not force_refresh:
            cached = await r.get(cache_key)
            if cached:
                payload = json.loads(cached)
                age = _payload_age_seconds(payload)
                if _is_fresh_payload(payload):
                    return payload
                if age is not None and age <= MARKET_CACHE_SOFT_STALE_SECONDS:
                    payload["stale"] = True
                    payload["degraded_reason"] = payload.get("degraded_reason") or "serving_recent_cache"
                    return payload

        pulse = await fetch_market_pulse(limit=limit)
        if not pulse.get("indices"):
            idx_map = [("S&P 500", "SPY"), ("Nasdaq", "QQQ"), ("Dow 30", "DIA"), ("Russell 2000", "IWM"), ("VIX", "VIXY")]
            idx_rows: list[dict] = []
            for name, sym in idx_map:
                q = await asyncio.to_thread(_fetch_finnhub_quote, sym)
                if not q:
                    continue
                idx_rows.append(
                    {
                        "name": name,
                        "symbol": sym,
                        "last": q["last"],
                        "change": q["change"],
                        "change_pct": q["change_pct"],
                    }
                )
            if idx_rows:
                pulse["indices"] = idx_rows
        if pulse.get("universe_size", 0) == 0 or not _is_fresh_payload(pulse):
            last_good = await r.get(last_good_key)
            if last_good:
                fallback = json.loads(last_good)
                age = _payload_age_seconds(fallback)
                if _is_fresh_payload(fallback):
                    fallback["stale"] = True
                    return fallback
                if age is not None and age <= MARKET_CACHE_SOFT_STALE_SECONDS:
                    fallback["stale"] = True
                    fallback["degraded_reason"] = fallback.get("degraded_reason") or "serving_recent_last_good"
                    return fallback
            return empty_market_pulse("live_data_stale_or_unavailable")
        else:
            await r.setex(last_good_key, 60 * 60 * 24, json.dumps(pulse))
        await r.setex(cache_key, 60, json.dumps(pulse))
        return pulse
    except Exception:
        return empty_market_pulse("market_live_handler_error")


@router.get("/market/stream")
async def stream_market_live(
    limit: int = Query(default=10, ge=3, le=30),
    interval_seconds: int = Query(default=12, ge=5, le=60),
    r=Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    async def event_gen():
        while True:
            try:
                cache_key = f"market:live:v2:limit:{limit}"
                cached = await r.get(cache_key)
                if cached:
                    pulse = json.loads(cached)
                    age = _payload_age_seconds(pulse)
                    if not _is_fresh_payload(pulse) and not (age is not None and age <= MARKET_CACHE_SOFT_STALE_SECONDS):
                        pulse = await fetch_market_pulse(limit=limit)
                else:
                    pulse = await fetch_market_pulse(limit=limit)
                if pulse.get("universe_size", 0) == 0 or not _is_fresh_payload(pulse):
                    age = _payload_age_seconds(pulse)
                    if age is not None and age <= MARKET_CACHE_SOFT_STALE_SECONDS and pulse.get("universe_size", 0) > 0:
                        pulse["stale"] = True
                        pulse["degraded_reason"] = pulse.get("degraded_reason") or "serving_recent_stream_cache"
                    else:
                        pulse = empty_market_pulse("live_data_stale_or_unavailable")
                else:
                    await r.setex(cache_key, 60, json.dumps(pulse))
                yield f"event: pulse\ndata: {json.dumps(pulse)}\n\n"
            except Exception:
                yield f"event: pulse\ndata: {json.dumps(empty_market_pulse('stream_error'))}\n\n"
            await asyncio.sleep(interval_seconds)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/{ticker}/prediction", response_model=PredictionResponse)
async def get_prediction(ticker: str) -> PredictionResponse:
    pred = await fetch_prediction(ticker)
    return PredictionResponse(
        ticker=pred.ticker,
        outlook=Outlook(pred.outlook),
        risk_level=RiskLevel(pred.risk_level),
        volatility_detected=pred.volatility_detected,
        probabilities=Probabilities(
            rise_probability=pred.rise_probability,
            fall_probability=pred.fall_probability,
            confidence_score=pred.confidence_score,
        ),
        time_horizon=TimeHorizonOutlook(**pred.time_horizon),
        model_status={
            "source": pred.source,
            "degraded": pred.degraded,
            "reason": pred.degraded_reason,
        },
    )


@router.get("/{ticker}/reasons", response_model=ReasonsResponse)
async def get_reasons(ticker: str) -> ReasonsResponse:
    pred = await fetch_prediction(ticker)
    growth, fall = drivers_from(pred)
    if pred.degraded:
        growth = ["Live predictive model is temporarily unavailable; using a conservative neutral profile."]
        fall = [pred.degraded_reason or "Upstream data provider is temporarily unavailable."]
    return ReasonsResponse(
        ticker=pred.ticker,
        growth_drivers=growth,
        fall_drivers=fall,
        watch_next=watch_next_from(pred),
        suggested_action=suggested_action_from(pred),
        best_for=best_for_from(pred),
    )


@router.get("/{ticker}/analysis", response_model=StockAnalysisResponse)
async def get_analysis(
    ticker: str,
    r=Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> StockAnalysisResponse:
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    cache_key = f"analysis:v4:{ticker}"
    cached = await r.get(cache_key)
    if cached:
        return StockAnalysisResponse.model_validate(json.loads(cached))

    pred = await fetch_prediction(ticker)
    growth, fall = drivers_from(pred)
    quote_available = False
    news_count = None
    news_avg = None
    fund = None
    headlines: list[dict] = []
    technical = None
    if pred.degraded:
        growth = ["Live predictive model is temporarily unavailable; using a conservative neutral profile."]
        fall = [pred.degraded_reason or "Upstream data provider is temporarily unavailable."]

    # Optional enrichments from the daily pipeline (if available).
    try:
        price_rows = (
            await db.execute(
                select(OhlcvDaily)
                .where(OhlcvDaily.ticker == ticker)
                .order_by(OhlcvDaily.day.desc())
                .limit(120)
            )
        ).scalars().all()
        technical = _technical_snapshot_from_rows(list(price_rows))

        fund = await latest_fundamentals(db, ticker)
        news_count, news_avg = await news_sentiment_window(db, ticker, days=7)
        macro = await latest_macro(db)
        sector_name = (await db.execute(select(Stock.sector).where(Stock.ticker == ticker))).scalar_one_or_none()
        sector_row = await latest_sector_trend(db, sector_name) if sector_name else None
        growth, fall = augment_drivers_with_context(
            growth,
            fall,
            fundamentals={
                "revenue_growth": fund.revenue_growth,
                "earnings_growth": fund.earnings_growth,
                "profit_margins": fund.profit_margins,
                "debt_to_equity": fund.debt_to_equity,
                "pe_ttm": fund.pe_ttm,
            }
            if fund
            else None,
            news_avg_sentiment=news_avg,
            news_count=news_count,
            macro=macro,
            sector={"ret_20d": sector_row.ret_20d, "vol_20d": sector_row.vol_20d} if sector_row else None,
        )
    except Exception:
        pass
    try:
        headlines = await asyncio.wait_for(asyncio.to_thread(fetch_ticker_headlines, ticker, 12, 72), timeout=8.0)
    except Exception:
        headlines = []
    growth, fall = augment_drivers_with_snapshot(
        growth,
        fall,
        ticker=ticker,
        technical=technical,
        headlines=headlines,
    )

    try:
        pulse_raw = await r.get("market:live:v2:limit:30")
        if pulse_raw:
            pulse = json.loads(pulse_raw)
            for bucket in ("top_gainers", "top_losers", "most_active"):
                for row in pulse.get(bucket, []) or []:
                    if str(row.get("ticker", "")).upper() == ticker:
                        quote_available = True
                        break
                if quote_available:
                    break
    except Exception:
        quote_available = False

    watch_next = watch_next_contextual(
        pred,
        ticker=ticker,
        quote_available=quote_available,
        news_count=news_count,
        news_avg_sentiment=news_avg,
        fundamentals={
            "pe_ttm": getattr(fund, "pe_ttm", None),
            "debt_to_equity": getattr(fund, "debt_to_equity", None),
        }
        if fund
        else None,
    )

    analysis = StockAnalysisResponse(
        ticker=pred.ticker,
        outlook=Outlook(pred.outlook),
        rise_probability=pred.rise_probability,
        fall_probability=pred.fall_probability,
        confidence_score=pred.confidence_score,
        risk_level=RiskLevel(pred.risk_level),
        volatility_detected=pred.volatility_detected,
        time_horizon=TimeHorizonOutlook(**pred.time_horizon),
        growth_drivers=growth,
        fall_drivers=fall,
        suggested_action=suggested_action_from(pred),
        best_for=best_for_from(pred),
        watch_next=watch_next,
        model_status={
            "source": pred.source,
            "degraded": pred.degraded,
            "reason": pred.degraded_reason,
        },
    )
    await r.setex(cache_key, 600, json.dumps(analysis.model_dump()))
    return analysis


@router.get("/{ticker}/ai-outcome")
async def get_ai_outcome(
    ticker: str,
    user_type: str = Query(default="advanced", pattern="^(beginner|intermediate|advanced)$"),
    r=Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict:
    symbol = ticker.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    analysis = await get_analysis(symbol, r=r, db=db)
    structured = analysis.model_dump()
    draft = render_analysis_markdown(analysis, user_type)
    provider = resolve_llm_provider()

    answer = draft
    degraded = True
    if provider != "none":
        answer = await enhance_answer_markdown(
            draft_markdown=draft,
            structured=structured,
            user_type=user_type,
        )
        degraded = answer == draft

    prob_up = float(analysis.rise_probability or 0.0)
    prob_down = float(analysis.fall_probability or 0.0)
    prob_base = max(0.0, 1.0 - prob_up - prob_down)
    rbull, rbase, rbear = _scenario_returns(str(analysis.outlook), str(analysis.risk_level))
    expected_return = (prob_up * rbull) + (prob_base * rbase) + (prob_down * rbear)
    rr = abs(rbull / rbear) if rbear != 0 else 0.0
    horizon = analysis.time_horizon
    horizon_alignment = (
        (analysis.outlook == "bullish" and any(h == "bullish" for h in [horizon.short_term, horizon.medium_term, horizon.long_term]))
        or (analysis.outlook == "bearish" and any(h == "bearish" for h in [horizon.short_term, horizon.medium_term, horizon.long_term]))
        or (analysis.outlook == "neutral")
    )
    action = "wait"
    if analysis.outlook == "bullish" and analysis.risk_level in {"low", "medium"}:
        action = "stage-in long"
    elif analysis.outlook == "bearish":
        action = "reduce risk / avoid fresh long"
    elif analysis.outlook == "neutral":
        action = "wait for confirmation"

    confidence = float(analysis.confidence_score or 0.0)
    max_loss_capital_pct = 0.0075 if analysis.risk_level == "high" else (0.01 if analysis.risk_level == "medium" else 0.0125)

    return {
        "ticker": symbol,
        "provider": provider,
        "degraded": degraded,
        "answer_markdown": answer,
        "decision": {
            "bias": str(analysis.outlook),
            "action": action,
            "confidence_score": round(confidence, 4),
            "risk_level": str(analysis.risk_level),
            "expected_return_20d": round(expected_return, 6),
            "horizon_alignment_ok": horizon_alignment,
            "note": "Probabilistic model output; not personalized investment advice.",
        },
        "trade_plan": {
            "entry_style": "staggered entries only" if analysis.risk_level == "high" else "staggered or single entry",
            "stop_loss_pct": round(_risk_pct_from_level(str(analysis.risk_level)) * 100.0, 2),
            "target_pct": round(rbull * 100.0, 2),
            "risk_reward_ratio": round(rr, 2),
            "max_loss_per_position_pct_of_capital": round(max_loss_capital_pct * 100.0, 2),
        },
        "scenarios_20d": [
            {"name": "bull", "probability": round(prob_up, 4), "return_pct": round(rbull * 100.0, 2)},
            {"name": "base", "probability": round(prob_base, 4), "return_pct": round(rbase * 100.0, 2)},
            {"name": "bear", "probability": round(prob_down, 4), "return_pct": round(rbear * 100.0, 2)},
        ],
        "consistency": {
            "overall_outlook": str(analysis.outlook),
            "short_term": horizon.short_term,
            "medium_term": horizon.medium_term,
            "long_term": horizon.long_term,
            "aligned": horizon_alignment,
        },
    }


@router.get("/{ticker}/risk-engine")
async def get_risk_engine(
    ticker: str,
    capital: float = Query(default=100000.0, gt=0),
    risk_budget_pct: float = Query(default=0.01, gt=0, le=0.05),
    r=Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict:
    symbol = ticker.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    analysis = await get_analysis(symbol, r=r, db=db)
    risk_level = str(analysis.risk_level)
    stop_pct = _risk_pct_from_level(risk_level)
    rbull, _, rbear = _scenario_returns(str(analysis.outlook), risk_level)
    target_pct = max(0.005, rbull)
    reward_risk = abs(target_pct / rbear) if rbear != 0 else 0.0

    quote = None
    try:
        quote = await asyncio.wait_for(asyncio.to_thread(_fetch_finnhub_quote, symbol), timeout=4.0)
    except Exception:
        quote = None

    entry_price = float(quote.get("last")) if quote and quote.get("last") else None
    risk_budget_amount = capital * risk_budget_pct
    shares = 0.0
    max_notional = 0.0
    if entry_price and stop_pct > 0:
        risk_per_share = entry_price * stop_pct
        shares = risk_budget_amount / risk_per_share if risk_per_share > 0 else 0.0
        max_notional = shares * entry_price

    return {
        "ticker": symbol,
        "inputs": {
            "capital": round(capital, 4),
            "risk_budget_pct": round(risk_budget_pct, 6),
        },
        "market": {
            "entry_price": round(entry_price, 4) if entry_price is not None else None,
            "quote_source": "finnhub_quote" if entry_price is not None else "unavailable",
        },
        "risk_plan": {
            "risk_level": risk_level,
            "stop_loss_pct": round(stop_pct * 100.0, 3),
            "target_pct": round(target_pct * 100.0, 3),
            "reward_risk_ratio": round(reward_risk, 3),
            "risk_budget_amount": round(risk_budget_amount, 4),
            "position_shares": round(shares, 4) if shares > 0 else None,
            "max_notional": round(max_notional, 4) if max_notional > 0 else None,
        },
        "model_context": {
            "outlook": str(analysis.outlook),
            "confidence_score": float(analysis.confidence_score),
            "rise_probability": float(analysis.rise_probability),
            "fall_probability": float(analysis.fall_probability),
        },
    }


@router.get("/{ticker}/signals")
async def get_signals(
    ticker: str,
    r=Depends(get_redis),
) -> dict:
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    pred = await fetch_prediction(ticker)
    pulse = None
    cached = await r.get("market:live:v2:limit:30")
    if cached:
        pulse = json.loads(cached)

    current_quote = None
    if pulse:
        for bucket in ("top_gainers", "top_losers", "most_active"):
            for row in pulse.get(bucket, []) or []:
                if str(row.get("ticker", "")).upper() == ticker:
                    current_quote = row
                    break
            if current_quote:
                break
    if not current_quote:
        try:
            current_quote = await asyncio.wait_for(asyncio.to_thread(_fetch_finnhub_quote, ticker), timeout=4.0)
        except Exception:
            current_quote = None

    confidence = float(pred.confidence_score or 0.0)
    nowcast_regime = "risk_on" if pred.outlook == "bullish" else ("risk_off" if pred.outlook == "bearish" else "balanced")
    one_day = pred.outlook
    five_day = pred.time_horizon.get("short_term", "neutral")
    twenty_day = pred.time_horizon.get("medium_term", "neutral")

    return {
        "ticker": ticker,
        "current_update": {
            "as_of_et": (pulse or {}).get("as_of_et") or datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat(),
            "quote": current_quote,
            "market_status": (pulse or {}).get("market_status"),
        },
        "nowcast": {
            "regime": nowcast_regime,
            "risk_level": pred.risk_level,
            "volatility_detected": pred.volatility_detected,
            "confidence_score": confidence,
        },
        "forecast": {
            "horizon_1d": one_day,
            "horizon_5d": five_day,
            "horizon_20d": twenty_day,
            "prob_up": float(pred.rise_probability or 0.0),
            "prob_down": float(pred.fall_probability or 0.0),
        },
        "degraded": pred.degraded,
        "degraded_reason": pred.degraded_reason,
    }


@router.get("/{ticker}/price-series")
async def get_price_series(
    ticker: str,
    days: int = Query(default=60, ge=10, le=365),
    mode: str = Query(default="daily"),
    session: str = Query(default="1D"),
    resolution: str = Query(default="5"),
    db: AsyncSession = Depends(get_db),
    r=Depends(get_redis),
) -> dict:
    symbol = ticker.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    mode = (mode or "daily").lower()
    points: list[dict] = []
    if mode == "intraday":
        intraday_session = "5D" if str(session).upper() == "5D" else "1D"
        intraday_resolution = "1" if str(resolution) == "1" else "5"
        lookback_days = 5 if intraday_session == "5D" else 1
        from_ts = int((datetime.utcnow() - timedelta(days=lookback_days)).timestamp())
        try:
            points = await asyncio.wait_for(
                asyncio.to_thread(_fetch_finnhub_candles, symbol, 1500, intraday_resolution, from_ts),
                timeout=6.0,
            )
        except Exception:
            points = []
        if not points:
            try:
                points = await asyncio.wait_for(
                    asyncio.to_thread(_download_intraday_fallback, symbol, intraday_session, intraday_resolution),
                    timeout=8.0,
                )
            except Exception:
                points = []
    else:
        stmt = (
            select(OhlcvDaily)
            .where(OhlcvDaily.ticker == symbol)
            .order_by(OhlcvDaily.day.desc())
            .limit(days)
        )
        rows = (await db.execute(stmt)).scalars().all()
        points = [
            {
                "day": row.day.isoformat(),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": int(row.volume or 0),
            }
            for row in reversed(rows)
        ]
        if not points:
            try:
                points = await asyncio.wait_for(asyncio.to_thread(_fetch_finnhub_candles, symbol, days), timeout=6.0)
            except Exception:
                points = []
        if not points:
            try:
                points = await asyncio.wait_for(asyncio.to_thread(_fetch_twelvedata_candles, symbol, days), timeout=8.0)
            except Exception:
                points = []
        if not points:
            try:
                points = await asyncio.wait_for(asyncio.to_thread(_fetch_alpha_candles, symbol, days), timeout=8.0)
            except Exception:
                points = []
        if not points:
            try:
                points = await asyncio.wait_for(asyncio.to_thread(_download_price_series_fallback, symbol, days), timeout=8.0)
            except Exception:
                points = []

    live_quote = None
    cached = await r.get("market:live:v2:limit:30")
    if cached:
        pulse = json.loads(cached)
        for bucket in ("top_gainers", "top_losers", "most_active"):
            for row in pulse.get(bucket, []) or []:
                if str(row.get("ticker", "")).upper() == symbol:
                    live_quote = row
                    break
            if live_quote:
                break
    if not live_quote:
        try:
            live_quote = await asyncio.wait_for(asyncio.to_thread(_fetch_finnhub_quote, symbol), timeout=4.0)
        except Exception:
            live_quote = None

    series_high = max((p["high"] for p in points), default=None)
    series_low = min((p["low"] for p in points), default=None)
    latest_close = points[-1]["close"] if points else None
    prev_close = points[-2]["close"] if len(points) > 1 else None
    daily_change = None
    daily_change_pct = None
    if latest_close is not None and prev_close and prev_close != 0:
        daily_change = round(latest_close - prev_close, 4)
        daily_change_pct = round(((latest_close - prev_close) / prev_close) * 100.0, 4)

    return {
        "ticker": symbol,
        "points": points,
        "stats": {
            "series_high": series_high,
            "series_low": series_low,
            "latest_close": latest_close,
            "daily_change": daily_change,
            "daily_change_pct": daily_change_pct,
        },
        "live_quote": live_quote,
    }


@router.get("/{ticker}/analyst-view")
async def get_analyst_view(ticker: str) -> dict:
    symbol = ticker.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Invalid ticker")
    rec = await asyncio.to_thread(_fetch_finnhub_recommendation, symbol)
    if not rec:
        return {
            "ticker": symbol,
            "available": False,
            "consensus": None,
            "buy": 0,
            "hold": 0,
            "sell": 0,
            "as_of": None,
            "source": "finnhub",
            "trend": "flat",
            "delta": None,
        }
    return {"ticker": symbol, "available": True, "source": "finnhub", **rec}


@router.get("/{ticker}/profile")
async def get_stock_profile(ticker: str) -> dict:
    symbol = ticker.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Invalid ticker")
    prof = await asyncio.to_thread(_fetch_finnhub_profile, symbol)
    if not prof:
        return {"ticker": symbol, "name": None, "exchange": None}
    return prof


@router.get("/{ticker}/quote-detail")
async def get_quote_detail(ticker: str) -> dict:
    symbol = ticker.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Invalid ticker")
    detail = await asyncio.to_thread(_fetch_finnhub_quote_detail, symbol)
    if not detail:
        basic = await asyncio.to_thread(_fetch_finnhub_quote, symbol)
        if basic:
            return {
                "available": True,
                "ticker": symbol,
                "last": basic.get("last"),
                "change": basic.get("change"),
                "change_pct": basic.get("change_pct"),
                "open": None,
                "high": None,
                "low": None,
                "prev_close": None,
                "week_52_high": None,
                "week_52_low": None,
                "timestamp": None,
            }
        return {
            "ticker": symbol,
            "available": False,
            "last": None,
            "change": None,
            "change_pct": None,
            "open": None,
            "high": None,
            "low": None,
            "prev_close": None,
            "week_52_high": None,
            "week_52_low": None,
            "timestamp": None,
        }
    return {"available": True, **detail}
