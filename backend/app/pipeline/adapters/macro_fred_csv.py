from __future__ import annotations

from datetime import date

import httpx


SERIES_URLS = {
    # Effective Federal Funds Rate
    "DFF": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF",
    # 10-Year Treasury Constant Maturity Rate
    "DGS10": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10",
    # CPI (headline)
    "CPIAUCSL": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL",
}


async def fetch_series_latest(series: str) -> tuple[date, float]:
    url = SERIES_URLS[series]
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        lines = [l.strip() for l in resp.text.splitlines() if l.strip()]
        # header: DATE,VALUE
        for line in reversed(lines[1:]):
            parts = line.split(",")
            if len(parts) != 2:
                continue
            d, v = parts
            if v in {".", ""}:
                continue
            return (date.fromisoformat(d), float(v))
    raise RuntimeError(f"No usable values for series {series}")

