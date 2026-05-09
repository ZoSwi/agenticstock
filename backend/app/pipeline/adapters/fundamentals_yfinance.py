from __future__ import annotations

from datetime import date

import yfinance as yf


def fetch_fundamentals_snapshot(ticker: str) -> dict:
    info = yf.Ticker(ticker).info or {}

    def f(key: str) -> float | None:
        v = info.get(key)
        try:
            if v is None:
                return None
            return float(v)
        except Exception:
            return None

    return {
        "ticker": ticker,
        "as_of": date.today(),
        "market_cap": f("marketCap"),
        "pe_ttm": f("trailingPE"),
        "forward_pe": f("forwardPE"),
        "profit_margins": f("profitMargins"),
        "operating_margins": f("operatingMargins"),
        "debt_to_equity": f("debtToEquity"),
        "revenue_growth": f("revenueGrowth"),
        "earnings_growth": f("earningsGrowth"),
    }

