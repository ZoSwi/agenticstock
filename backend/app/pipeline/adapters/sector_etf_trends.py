from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import yfinance as yf


SECTOR_ETFS = {
    "technology": "XLK",
    "financials": "XLF",
    "healthcare": "XLV",
    "consumer_discretionary": "XLY",
    "consumer_staples": "XLP",
    "industrials": "XLI",
    "energy": "XLE",
    "materials": "XLB",
    "utilities": "XLU",
    "real_estate": "XLRE",
    "communication_services": "XLC",
}


def _compute(df: pd.DataFrame) -> dict:
    c = df["Close"].astype(float)
    ret_5d = float(c.pct_change(5).iloc[-1])
    ret_20d = float(c.pct_change(20).iloc[-1])
    vol_20d = float(c.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252))
    return {"ret_5d": ret_5d, "ret_20d": ret_20d, "vol_20d": vol_20d}


def fetch_sector_trends(as_of: date | None = None) -> list[dict]:
    as_of = as_of or date.today()
    out: list[dict] = []
    for sector, etf in SECTOR_ETFS.items():
        hist = yf.Ticker(etf).history(period="6mo", auto_adjust=False)
        if hist is None or hist.empty or len(hist) < 25:
            continue
        metrics = _compute(hist)
        out.append({"sector": sector, "day": as_of, **metrics})
    return out

