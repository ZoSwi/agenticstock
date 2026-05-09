from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser


GLOBAL_RSS_SOURCES: dict[str, str] = {
    "cnbc_markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "reuters_markets": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
    "yahoo_finance_top": "https://finance.yahoo.com/news/rssindex",
}


def _published(entry: dict) -> datetime:
    for key in ("published", "updated"):
        value = entry.get(key)
        if not value:
            continue
        try:
            dt = parsedate_to_datetime(str(value))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return datetime.now(tz=timezone.utc)


def _clean_text(value: str | None) -> str:
    return (value or "").replace("\n", " ").replace("\r", " ").strip()


def _ingest_feed(url: str, source: str, limit: int) -> list[dict]:
    payload = feedparser.parse(url)
    items: list[dict] = []
    for entry in (payload.entries or [])[:limit]:
        title = _clean_text(entry.get("title"))
        link = _clean_text(entry.get("link"))
        if not title or not link:
            continue
        items.append(
            {
                "source": source,
                "title": title,
                "url": link,
                "published_at": _published(entry),
            }
        )
    return items


def _dedupe_sort(items: list[dict], max_age_hours: int, limit: int) -> list[dict]:
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(hours=max_age_hours)
    seen: set[str] = set()
    output: list[dict] = []
    for item in sorted(items, key=lambda i: i["published_at"], reverse=True):
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        if item["published_at"] < cutoff:
            continue
        output.append(item)
        if len(output) >= limit:
            break
    return output


def fetch_global_headlines(limit: int = 25, max_age_hours: int = 24) -> list[dict]:
    rows: list[dict] = []
    per_source = max(8, min(20, limit))
    for source, url in GLOBAL_RSS_SOURCES.items():
        try:
            rows.extend(_ingest_feed(url, source, per_source))
        except Exception:
            continue
    return _dedupe_sort(rows, max_age_hours=max_age_hours, limit=limit)


def fetch_ticker_headlines(ticker: str, limit: int = 25, max_age_hours: int = 72) -> list[dict]:
    symbol = ticker.upper().strip()
    if not symbol:
        return []

    query = quote_plus(f"{symbol} stock")
    sources = {
        "google_news_rss": f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
        "yahoo_finance_rss": f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US",
        "cnbc_search": f"https://www.cnbc.com/id/10000664/device/rss/rss.html?symbol={symbol}",
    }
    rows: list[dict] = []
    per_source = max(10, min(25, limit))
    for source, url in sources.items():
        try:
            rows.extend(_ingest_feed(url, source, per_source))
        except Exception:
            continue
    return _dedupe_sort(rows, max_age_hours=max_age_hours, limit=limit)
