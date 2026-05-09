from __future__ import annotations

import asyncio
from datetime import datetime
import os
import time
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import yfinance as yf


DEFAULT_UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AMD",
    "AVGO",
    "NFLX",
    "INTC",
    "PLTR",
    "ADBE",
    "CSCO",
    "QCOM",
    "TXN",
    "MU",
    "ARM",
    "SHOP",
    "SNOW",
    "CRM",
    "ORCL",
    "NOW",
    "PANW",
    "CRWD",
    "MDB",
    "NET",
    "DDOG",
    "ZS",
    "SMCI",
    "MSTR",
    "COIN",
    "UBER",
    "ABNB",
    "PYPL",
    "SQ",
    "INTU",
    "AMAT",
    "LRCX",
    "KLAC",
    "ADI",
    "MRVL",
    "ASML",
    "ANET",
    "BKNG",
    "SBUX",
    "PEP",
    "KO",
    "WMT",
    "COST",
    "TGT",
    "HD",
    "LOW",
    "MCD",
    "NKE",
    "DIS",
    "CMCSA",
    "PFE",
    "MRK",
    "LLY",
    "JNJ",
    "UNH",
    "ABBV",
    "TMO",
    "DHR",
    "BMY",
    "AMGN",
    "GILD",
    "JPM",
    "BAC",
    "WFC",
    "GS",
    "MS",
    "C",
    "BLK",
    "SCHW",
    "SPGI",
    "ICE",
    "CME",
    "XOM",
    "CVX",
    "COP",
    "SLB",
    "OXY",
    "EOG",
    "MPC",
    "VLO",
    "PSX",
    "CAT",
    "DE",
    "BA",
    "GE",
    "HON",
    "UNP",
    "UPS",
    "FDX",
    "RTX",
    "LMT",
    "SPOT",
    "RBLX",
    "SNAP",
    "ROKU",
    "BABA",
    "NIO",
    "RIOT",
    "MARA",
    "SOFI",
    "HOOD",
    "RIVN",
    "LCID",
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
]

INDEX_SYMBOLS = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow 30": "^DJI",
    "Russell 2000": "^RUT",
    "VIX": "^VIX",
}

SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Consumer Discretionary": "XLY",
    "Industrials": "XLI",
    "Communication Services": "XLC",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
}


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _now_utc_et() -> tuple[datetime, datetime]:
    now_utc = datetime.utcnow().replace(microsecond=0)
    now_et = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0)
    return now_utc, now_et


def _market_status(now_et: datetime) -> str:
    if now_et.weekday() >= 5:
        return "closed"
    minutes = now_et.hour * 60 + now_et.minute
    open_mins = 9 * 60 + 30
    close_mins = 16 * 60
    return "open" if open_mins <= minutes < close_mins else "closed"


def empty_market_pulse(reason: str = "provider_timeout_or_error") -> dict:
    now_utc, now_et = _now_utc_et()
    alpha_configured = bool((os.environ.get("ALPHAVANTAGE_API_KEY") or "").strip())
    finnhub_configured = bool((os.environ.get("FINNHUB_API_KEY") or "").strip())
    return {
        "as_of_utc": f"{now_utc.isoformat()}Z",
        "as_of_et": now_et.isoformat(),
        "market_status": _market_status(now_et),
        "data_source": "none",
        "universe_size": 0,
        "market_breadth": {"advancers": 0, "decliners": 0, "unchanged": 0},
        "provider_status": {"finnhub": False, "alphavantage": False, "stooq": False, "yahoo": False},
        "provider_diagnostics": {
            "alphavantage": {"configured": alpha_configured, "ok": False, "rows": 0, "latency_ms": None, "score": 0.0, "error": reason},
            "finnhub": {"configured": finnhub_configured, "ok": False, "rows": 0, "latency_ms": None, "score": 0.0, "error": reason},
            "stooq": {"configured": True, "ok": False, "rows": 0, "latency_ms": None, "score": 0.0, "error": None},
            "yahoo": {"configured": True, "ok": False, "rows": 0, "latency_ms": None, "score": 0.0, "error": reason},
        },
        "degraded_reason": reason,
        "indices": [],
        "sector_leaders": [],
        "top_gainers": [],
        "top_losers": [],
        "most_active": [],
    }


def _load_universe() -> list[str]:
    raw = os.environ.get("MARKET_UNIVERSE", "").strip()
    if not raw:
        return DEFAULT_UNIVERSE
    out: list[str] = []
    for t in raw.split(","):
        s = t.upper().strip()
        if not s or s in out:
            continue
        out.append(s)
    return out[:200] if out else DEFAULT_UNIVERSE


def _extract_quote_rows(df: pd.DataFrame, tickers: list[str]) -> list[dict]:
    rows: list[dict] = []
    if df is None or df.empty:
        return rows
    if isinstance(df.columns, pd.MultiIndex):
        available = set(df.columns.get_level_values(0))
        for ticker in tickers:
            if ticker not in available:
                continue
            sub = df[ticker]
            close = sub.get("Close")
            volume = sub.get("Volume")
            if close is None:
                continue
            close = close.dropna()
            if len(close) < 2:
                continue
            last = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            if prev == 0:
                continue
            change = last - prev
            pct = (change / prev) * 100.0
            vol = float(volume.dropna().iloc[-1]) if volume is not None and not volume.dropna().empty else 0.0
            rows.append(
                {
                    "ticker": ticker,
                    "last": round(last, 4),
                    "change": round(change, 4),
                    "change_pct": round(pct, 4),
                    "volume": int(vol),
                }
            )
        return rows

    close = df.get("Close")
    volume = df.get("Volume")
    if close is None:
        return rows
    close = close.dropna()
    if len(close) < 2:
        return rows
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    if prev == 0:
        return rows
    change = last - prev
    pct = (change / prev) * 100.0
    vol = float(volume.dropna().iloc[-1]) if volume is not None and not volume.dropna().empty else 0.0
    ticker = tickers[0] if tickers else "UNKNOWN"
    rows.append(
        {
            "ticker": ticker,
            "last": round(last, 4),
            "change": round(change, 4),
            "change_pct": round(pct, 4),
            "volume": int(vol),
        }
    )
    return rows


def _download_daily_rows(tickers: list[str], period: str = "5d") -> list[dict]:
    if not tickers:
        return []
    all_rows: list[dict] = []
    seen: set[str] = set()

    for chunk in _chunked(tickers, 35):
        try:
            df = yf.download(
                tickers=chunk,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
            rows = _extract_quote_rows(df, chunk)
            for row in rows:
                if row["ticker"] in seen:
                    continue
                seen.add(row["ticker"])
                all_rows.append(row)
        except Exception:
            continue
    return all_rows


def _fetch_yahoo_fast_rows(tickers: list[str]) -> tuple[list[dict], dict]:
    state = {"configured": True, "ok": False, "rows": 0, "latency_ms": None, "error": None}
    started = time.perf_counter()
    rows: list[dict] = []
    limit = int(os.environ.get("MARKET_YAHOO_QUOTE_LIMIT", "80"))
    limit = max(10, min(160, limit))
    query = list(dict.fromkeys([t.upper().strip() for t in tickers if t and t.strip()]))[:limit]
    try:
        for chunk in _chunked(query, 25):
            tickers_obj = yf.Tickers(" ".join(chunk))
            for ticker in chunk:
                try:
                    t = tickers_obj.tickers.get(ticker)
                    if t is None:
                        continue
                    fi = getattr(t, "fast_info", None)
                    if not fi:
                        continue
                    last = float(fi.get("lastPrice") or fi.get("regularMarketPrice") or fi.get("currentPrice") or 0.0)
                    prev = float(fi.get("previousClose") or fi.get("regularMarketPreviousClose") or 0.0)
                    vol = int(float(fi.get("lastVolume") or fi.get("regularMarketVolume") or 0.0))
                    if last <= 0 or prev <= 0:
                        continue
                    change = last - prev
                    pct = (change / prev) * 100.0
                    rows.append(
                        {
                            "ticker": ticker,
                            "last": round(last, 4),
                            "change": round(change, 4),
                            "change_pct": round(pct, 4),
                            "volume": vol,
                        }
                    )
                except Exception:
                    continue
    except Exception as exc:
        state["error"] = f"yahoo_fast_failed:{exc.__class__.__name__}"

    state["latency_ms"] = int((time.perf_counter() - started) * 1000)
    state["rows"] = len(rows)
    state["ok"] = len(rows) > 0
    state["score"] = _provider_score(True, state["rows"], state["latency_ms"])
    if not rows and state["error"] is None:
        state["error"] = "empty_or_blocked"
    return rows, state


def _parse_alpha_pct(raw: str) -> float:
    s = str(raw or "").replace("%", "").replace("+", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def _parse_alpha_num(raw: str) -> float:
    s = str(raw or "").replace(",", "").replace("$", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def _merge_rows(base: list[dict], overlay: list[dict]) -> list[dict]:
    by_ticker = {r["ticker"]: dict(r) for r in base}
    for r in overlay:
        ticker = r.get("ticker")
        if not ticker:
            continue
        if ticker not in by_ticker:
            by_ticker[ticker] = dict(r)
            continue
        curr = by_ticker[ticker]
        curr["last"] = r.get("last", curr.get("last", 0.0))
        curr["change"] = r.get("change", curr.get("change", 0.0))
        curr["change_pct"] = r.get("change_pct", curr.get("change_pct", 0.0))
        curr["volume"] = int(max(float(curr.get("volume", 0.0)), float(r.get("volume", 0.0))))
    return list(by_ticker.values())


def _provider_score(configured: bool, rows: int, latency_ms: int | None) -> float:
    if not configured:
        return 0.0
    row_score = min(1.0, rows / 25.0)
    latency_score = 0.5 if latency_ms is None else max(0.0, 1.0 - (latency_ms / 6000.0))
    return round((0.7 * row_score) + (0.3 * latency_score), 4)


def _fetch_alpha_rows(tickers: list[str]) -> tuple[list[dict], dict]:
    key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    state = {"configured": bool(key), "ok": False, "rows": 0, "latency_ms": None, "error": None}
    if not key:
        state["error"] = "not_configured"
        state["score"] = 0.0
        return [], state

    started = time.perf_counter()
    rows: list[dict] = []
    try:
        with httpx.Client(timeout=15.0) as client:
            try:
                resp = client.get(
                    "https://www.alphavantage.co/query",
                    params={"function": "TOP_GAINERS_LOSERS", "apikey": key},
                )
                resp.raise_for_status()
                payload = resp.json()
                out: dict[str, dict] = {}
                for bucket in ("top_gainers", "top_losers", "most_actively_traded"):
                    for row in payload.get(bucket, []) or []:
                        ticker = str(row.get("ticker", "")).upper().strip()
                        if not ticker:
                            continue
                        price = _parse_alpha_num(row.get("price"))
                        pct = _parse_alpha_pct(row.get("change_percentage"))
                        volume = int(_parse_alpha_num(row.get("volume")))
                        if price <= 0:
                            continue
                        out[ticker] = {
                            "ticker": ticker,
                            "last": round(price, 4),
                            "change": round(price * (pct / 100.0), 4),
                            "change_pct": round(pct, 4),
                            "volume": volume,
                        }
                if out:
                    rows = list(out.values())
                else:
                    state["error"] = "top_gainers_losers_empty_or_limited"
            except Exception as exc:
                state["error"] = f"top_gainers_losers_failed:{exc.__class__.__name__}"

            if not rows:
                quote_limit = int(os.environ.get("MARKET_ALPHA_QUOTE_LIMIT", "12"))
                quote_limit = max(1, min(25, quote_limit))
                for ticker in tickers[:quote_limit]:
                    try:
                        resp = client.get(
                            "https://www.alphavantage.co/query",
                            params={"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": key},
                        )
                        resp.raise_for_status()
                        data = resp.json().get("Global Quote", {})
                        price = _parse_alpha_num(data.get("05. price"))
                        change = _parse_alpha_num(data.get("09. change"))
                        pct = _parse_alpha_pct(data.get("10. change percent"))
                        volume = int(_parse_alpha_num(data.get("06. volume")))
                        if price <= 0:
                            continue
                        rows.append(
                            {
                                "ticker": ticker,
                                "last": round(price, 4),
                                "change": round(change, 4),
                                "change_pct": round(pct, 4),
                                "volume": volume,
                            }
                        )
                    except Exception:
                        continue
    except Exception as exc:
        state["error"] = f"alpha_failed:{exc.__class__.__name__}"

    state["latency_ms"] = int((time.perf_counter() - started) * 1000)
    state["rows"] = len(rows)
    state["ok"] = len(rows) > 0
    state["score"] = _provider_score(state["configured"], state["rows"], state["latency_ms"])
    return rows, state


def _fetch_finnhub_rows(tickers: list[str], extras: list[str] | None = None) -> tuple[list[dict], dict]:
    key = os.environ.get("FINNHUB_API_KEY", "").strip()
    state = {"configured": bool(key), "ok": False, "rows": 0, "latency_ms": None, "error": None}
    if not key:
        state["error"] = "not_configured"
        state["score"] = 0.0
        return [], state

    rows: list[dict] = []
    started = time.perf_counter()
    quote_limit = int(os.environ.get("MARKET_FINNHUB_QUOTE_LIMIT", "20"))
    quote_limit = max(1, min(80, quote_limit))
    prioritized: list[str] = []
    if extras:
        for e in extras:
            ee = e.upper().strip()
            if ee and ee not in prioritized:
                prioritized.append(ee)
    for t in tickers:
        tt = t.upper().strip()
        if tt and tt not in prioritized:
            prioritized.append(tt)
    query_tickers = prioritized[:quote_limit]
    try:
        with httpx.Client(timeout=10.0) as client:
            for ticker in query_tickers:
                try:
                    resp = client.get(
                        "https://finnhub.io/api/v1/quote",
                        params={"symbol": ticker, "token": key},
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    price = float(payload.get("c") or 0.0)
                    prev = float(payload.get("pc") or 0.0)
                    if price <= 0 or prev <= 0:
                        continue
                    change = price - prev
                    pct = (change / prev) * 100.0 if prev else 0.0
                    rows.append(
                        {
                            "ticker": ticker,
                            "last": round(price, 4),
                            "change": round(change, 4),
                            "change_pct": round(pct, 4),
                            "volume": 0,
                        }
                    )
                except Exception:
                    continue
    except Exception as exc:
        state["error"] = f"finnhub_failed:{exc.__class__.__name__}"

    state["latency_ms"] = int((time.perf_counter() - started) * 1000)
    state["rows"] = len(rows)
    state["ok"] = len(rows) > 0
    state["score"] = _provider_score(state["configured"], state["rows"], state["latency_ms"])
    if not rows and state["error"] is None:
        state["error"] = "empty_or_rate_limited"
    return rows, state


def _fetch_stooq_rows(tickers: list[str], extras: list[str] | None = None) -> tuple[list[dict], dict]:
    state = {"configured": True, "ok": False, "rows": 0, "latency_ms": None, "error": None}
    rows: list[dict] = []
    started = time.perf_counter()
    limit = int(os.environ.get("MARKET_STOOQ_QUOTE_LIMIT", "30"))
    limit = max(10, min(80, limit))
    try:
        with httpx.Client(timeout=8.0) as client:
            query_tickers = tickers[:limit]
            if extras:
                for e in extras:
                    ee = e.upper().strip()
                    if ee and ee not in query_tickers:
                        query_tickers.append(ee)
            for ticker in query_tickers:
                sym = f"{ticker.lower()}.us"
                try:
                    resp = client.get("https://stooq.com/q/l/", params={"s": sym, "i": "d"})
                    resp.raise_for_status()
                    line = (resp.text or "").strip().splitlines()[0] if resp.text else ""
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 8:
                        continue
                    parsed_ticker = str(parts[0] or "").replace(".US", "").replace(".us", "").upper()
                    if not parsed_ticker or parsed_ticker == "N/D":
                        continue
                    open_px = float(parts[3]) if parts[3] and parts[3] != "N/D" else 0.0
                    close_px = float(parts[6]) if parts[6] and parts[6] != "N/D" else 0.0
                    vol = float(parts[7]) if parts[7] and parts[7] != "N/D" else 0.0
                    if close_px <= 0:
                        continue
                    change = close_px - open_px if open_px > 0 else 0.0
                    pct = ((change / open_px) * 100.0) if open_px > 0 else 0.0
                    rows.append(
                        {
                            "ticker": parsed_ticker,
                            "last": round(close_px, 4),
                            "change": round(change, 4),
                            "change_pct": round(pct, 4),
                            "volume": int(vol),
                        }
                    )
                except Exception:
                    continue
    except Exception as exc:
        state["error"] = f"stooq_failed:{exc.__class__.__name__}"

    state["latency_ms"] = int((time.perf_counter() - started) * 1000)
    state["rows"] = len(rows)
    state["ok"] = len(rows) > 0
    state["score"] = _provider_score(True, state["rows"], state["latency_ms"])
    if not rows and state["error"] is None:
        state["error"] = "empty_or_blocked"
    return rows, state


def _fetch_yahoo_rows(universe: list[str], include_universe: bool) -> tuple[list[dict], dict]:
    state = {"configured": True, "ok": False, "rows": 0, "latency_ms": None, "error": None}
    started = time.perf_counter()
    rows: list[dict] = []
    try:
        yahoo_watch: list[str]
        if include_universe:
            fallback_limit = int(os.environ.get("MARKET_YAHOO_FALLBACK_LIMIT", "45"))
            fallback_limit = max(20, min(90, fallback_limit))
            yahoo_watch = list(dict.fromkeys(universe[:fallback_limit] + list(SECTOR_ETFS.values()) + list(INDEX_SYMBOLS.values())))
        else:
            yahoo_watch = list(dict.fromkeys(list(SECTOR_ETFS.values()) + list(INDEX_SYMBOLS.values())))
        rows = _download_daily_rows(yahoo_watch, period="7d")
    except Exception as exc:
        state["error"] = f"yahoo_failed:{exc.__class__.__name__}"

    state["latency_ms"] = int((time.perf_counter() - started) * 1000)
    state["rows"] = len(rows)
    state["ok"] = len(rows) > 0
    state["score"] = _provider_score(True, state["rows"], state["latency_ms"])
    if not rows and state["error"] is None:
        state["error"] = "empty_or_blocked"
    return rows, state


def _build_market_pulse(limit: int) -> dict:
    limit = max(3, min(limit, 30))
    universe = _load_universe()

    enable_alpha = os.environ.get("MARKET_ENABLE_ALPHA", "true").strip().lower() in {"1", "true", "yes", "on"}
    enable_stooq = os.environ.get("MARKET_ENABLE_STOOQ", "false").strip().lower() in {"1", "true", "yes", "on"}

    alpha_rows, alpha_state = _fetch_alpha_rows(universe) if enable_alpha else ([], {"configured": False, "ok": False, "rows": 0, "latency_ms": 0, "score": 0.0, "error": "disabled"})
    index_proxy_extras = ["SPY", "QQQ", "DIA", "IWM", "VIXY"]
    finnhub_rows, finnhub_state = _fetch_finnhub_rows(universe, extras=index_proxy_extras)
    stooq_extras = ["SPY", "QQQ", "IWM", "DIA", *list(SECTOR_ETFS.values())]
    stooq_rows, stooq_state = _fetch_stooq_rows(universe, extras=stooq_extras) if enable_stooq else ([], {"configured": False, "ok": False, "rows": 0, "latency_ms": 0, "score": 0.0, "error": "disabled"})
    allow_yahoo_fallback = os.environ.get("ALLOW_YAHOO_FALLBACK", "false").strip().lower() in {"1", "true", "yes", "on"}
    yahoo_fast_rows: list[dict] = []
    yahoo_rows: list[dict] = []
    yahoo_fast_state = {"configured": True, "ok": False, "rows": 0, "latency_ms": 0, "score": 0.0, "error": "disabled"}
    yahoo_state = {"configured": True, "ok": False, "rows": 0, "latency_ms": 0, "score": 0.0, "error": "disabled"}
    if allow_yahoo_fallback:
        yahoo_quote_watch = list(
            dict.fromkeys(universe + list(SECTOR_ETFS.values()) + list(INDEX_SYMBOLS.values()) + ["SPY", "QQQ", "IWM", "DIA"])
        )
        yahoo_fast_rows, yahoo_fast_state = _fetch_yahoo_fast_rows(yahoo_quote_watch)
        # Pull broader daily rows only when all higher-priority providers are empty.
        yahoo_rows, yahoo_state = _fetch_yahoo_rows(
            universe,
            include_universe=not bool(alpha_rows or finnhub_rows or stooq_rows or yahoo_fast_rows),
        )

    quote_rows = _merge_rows(yahoo_rows, yahoo_fast_rows)
    quote_rows = _merge_rows(quote_rows, alpha_rows)
    quote_rows = _merge_rows(quote_rows, finnhub_rows)
    quote_rows = _merge_rows(quote_rows, stooq_rows)
    quote_rows = [r for r in quote_rows if r["ticker"] not in INDEX_SYMBOLS.values()]
    quote_lookup = {r["ticker"]: r for r in quote_rows}
    yahoo_lookup = {r["ticker"]: r for r in _merge_rows(yahoo_rows, yahoo_fast_rows)}

    gainers = sorted(quote_rows, key=lambda r: r["change_pct"], reverse=True)[:limit]
    losers = sorted(quote_rows, key=lambda r: r["change_pct"])[:limit]
    most_active = sorted(quote_rows, key=lambda r: r["volume"], reverse=True)[:limit]
    advancers = sum(1 for r in quote_rows if r["change_pct"] > 0)
    decliners = sum(1 for r in quote_rows if r["change_pct"] < 0)
    unchanged = max(0, len(quote_rows) - advancers - decliners)

    indices = []
    for name, symbol in INDEX_SYMBOLS.items():
        row = yahoo_lookup.get(symbol)
        if not row:
            continue
        indices.append(
            {
                "name": name,
                "symbol": symbol,
                "last": row["last"],
                "change": row["change"],
                "change_pct": row["change_pct"],
            }
        )
    proxy_map = {
        "S&P 500": "SPY",
        "Nasdaq": "QQQ",
        "Dow 30": "DIA",
        "Russell 2000": "IWM",
        "VIX": "VIXY",
    }
    missing_names = {i["name"] for i in indices}
    for name, symbol in proxy_map.items():
        if name in missing_names:
            continue
        row = quote_lookup.get(symbol)
        if not row:
            continue
        indices.append(
            {
                "name": name,
                "symbol": symbol,
                "last": row["last"],
                "change": row["change"],
                "change_pct": row["change_pct"],
            }
        )

    sector_rows = []
    for sector_name, etf in SECTOR_ETFS.items():
        row = quote_lookup.get(etf) or yahoo_lookup.get(etf)
        if not row:
            continue
        sector_rows.append(
            {
                "name": sector_name,
                "symbol": etf,
                "last": row["last"],
                "change": row["change"],
                "change_pct": row["change_pct"],
            }
        )
    sector_rows = sorted(sector_rows, key=lambda x: x["change_pct"], reverse=True)

    data_sources = []
    if finnhub_rows:
        data_sources.append("finnhub")
    if alpha_rows:
        data_sources.append("alphavantage")
    if stooq_rows:
        data_sources.append("stooq")
    if yahoo_fast_rows or yahoo_rows:
        data_sources.append("yahoo")

    now_utc, now_et = _now_utc_et()
    degraded_reason = None if quote_rows else "providers_returned_no_rows"
    return {
        "as_of_utc": f"{now_utc.isoformat()}Z",
        "as_of_et": now_et.isoformat(),
        "market_status": _market_status(now_et),
        "data_source": "+".join(data_sources) if data_sources else "none",
        "universe_size": len(quote_rows),
        "market_breadth": {
            "advancers": advancers,
            "decliners": decliners,
            "unchanged": unchanged,
        },
        "provider_status": {
            "finnhub": bool(finnhub_rows),
            "alphavantage": bool(alpha_rows),
            "stooq": bool(stooq_rows),
            "yahoo": bool(yahoo_fast_rows or yahoo_rows),
        },
        "provider_diagnostics": {
            "alphavantage": alpha_state,
            "finnhub": finnhub_state,
            "stooq": stooq_state,
            "yahoo": {
                "configured": True,
                "ok": bool((yahoo_fast_state.get("ok")) or (yahoo_state.get("ok"))),
                "rows": int((yahoo_fast_state.get("rows") or 0) + (yahoo_state.get("rows") or 0)),
                "latency_ms": (yahoo_fast_state.get("latency_ms") or 0) + (yahoo_state.get("latency_ms") or 0),
                "score": max(float(yahoo_fast_state.get("score") or 0.0), float(yahoo_state.get("score") or 0.0)),
                "error": yahoo_fast_state.get("error") or yahoo_state.get("error"),
            },
        },
        "degraded_reason": degraded_reason,
        "indices": indices,
        "sector_leaders": sector_rows[:8],
        "top_gainers": gainers,
        "top_losers": losers,
        "most_active": most_active,
    }


async def fetch_market_pulse(limit: int = 8) -> dict:
    timeout_s = max(3.0, float(os.environ.get("MARKET_FETCH_TIMEOUT_SECONDS", "8")))
    try:
        return await asyncio.wait_for(asyncio.to_thread(_build_market_pulse, limit), timeout=timeout_s)
    except Exception:
        return empty_market_pulse()
