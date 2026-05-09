from __future__ import annotations

import os
import time

import httpx
import pandas as pd
import yfinance as yf


def _alpha_daily(ticker: str, period: str = "2y") -> pd.DataFrame:
    key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    if not key:
        return pd.DataFrame()

    # Keep a single compact call for reliability on free-tier keys.
    payload: dict = {}
    # Alpha Vantage free-tier can throttle burst traffic; retry once with backoff.
    for i in range(3):
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(
                    "https://www.alphavantage.co/query",
                    params={"function": "TIME_SERIES_DAILY", "symbol": ticker, "outputsize": "compact", "apikey": key},
                )
                resp.raise_for_status()
                payload = resp.json()
            series = payload.get("Time Series (Daily)") or {}
            if series:
                break

            # API-side informational responses include Note/Information/Error Message when throttled/invalid.
            if payload.get("Note") or payload.get("Information") or payload.get("Error Message"):
                if i < 2:
                    time.sleep(4.0 * (i + 1))
                    continue
            return pd.DataFrame()
        except Exception:
            if i < 2:
                time.sleep(2.0 * (i + 1))
                continue
            return pd.DataFrame()

    series = payload.get("Time Series (Daily)") or {}
    if not series:
        return pd.DataFrame()

    rows = []
    for d, v in series.items():
        try:
            rows.append(
                {
                    "day": pd.to_datetime(d),
                    "open": float(v["1. open"]),
                    "high": float(v["2. high"]),
                    "low": float(v["3. low"]),
                    "close": float(v["4. close"]),
                    "volume": float(v["5. volume"]),
                }
            )
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("day").set_index("day")
    return df[["open", "high", "low", "close", "volume"]].dropna().copy()


def _yahoo_daily(ticker: str, period: str = "2y") -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, auto_adjust=False)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[["open", "high", "low", "close", "volume"]].dropna().copy()


def _stooq_daily(ticker: str) -> pd.DataFrame:
    # Stooq offers free CSV history and is often more stable than Yahoo inside containers.
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get("https://stooq.com/q/d/l/", params={"s": f"{ticker.lower()}.us", "i": "d"})
            resp.raise_for_status()
            text = (resp.text or "").strip()
    except Exception:
        return pd.DataFrame()

    if not text or "No data" in text:
        return pd.DataFrame()
    try:
        from io import StringIO

        df = pd.read_csv(StringIO(text))
    except Exception:
        return pd.DataFrame()

    required = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "open": pd.to_numeric(df["Open"], errors="coerce"),
            "high": pd.to_numeric(df["High"], errors="coerce"),
            "low": pd.to_numeric(df["Low"], errors="coerce"),
            "close": pd.to_numeric(df["Close"], errors="coerce"),
            "volume": pd.to_numeric(df["Volume"], errors="coerce"),
        },
        index=pd.to_datetime(df["Date"], errors="coerce"),
    )
    out = out.dropna().sort_index()
    out.index = out.index.tz_localize(None)
    return out


def _backend_daily(ticker: str, days: int = 365) -> pd.DataFrame:
    base = os.environ.get("BACKEND_INTERNAL_URL", "http://backend:8000").strip()
    if not base:
        return pd.DataFrame()
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
                f"{base}/stocks/{ticker}/price-series",
                params={"days": max(120, min(365, days))},
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        return pd.DataFrame()

    points = payload.get("points") or []
    if not isinstance(points, list) or len(points) < 80:
        return pd.DataFrame()

    try:
        df = pd.DataFrame(points)
        df["day"] = pd.to_datetime(df["day"], errors="coerce")
        df = df.dropna(subset=["day"]).set_index("day").sort_index()
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        return df
    except Exception:
        return pd.DataFrame()


def fetch_ohlcv_daily(ticker: str, period: str = "2y") -> pd.DataFrame:
    # First choice: reuse backend provider orchestration, which is already hardened.
    df = _backend_daily(ticker, days=365)
    if df is not None and not df.empty:
        return df

    # Prefer Alpha Vantage (if configured) for better reliability in containerized runs.
    has_alpha = bool(os.environ.get("ALPHAVANTAGE_API_KEY", "").strip())
    allow_yahoo_fallback = os.environ.get("ALLOW_YAHOO_FALLBACK", "true").strip().lower() in {"1", "true", "yes"}

    df = _alpha_daily(ticker, period=period) if has_alpha else pd.DataFrame()
    if (df is None or df.empty) and allow_yahoo_fallback:
        df = _yahoo_daily(ticker, period=period)
    if df is None or df.empty:
        df = _stooq_daily(ticker)
    if df is None or df.empty:
        if has_alpha:
            raise ValueError(
                f"No data for ticker {ticker}; providers unavailable or rate-limited (Alpha Vantage/Yahoo/Stooq)"
            )
        raise ValueError(f"No data for ticker {ticker}; check provider access (Yahoo/Stooq) or configure ALPHAVANTAGE_API_KEY")
    return df
