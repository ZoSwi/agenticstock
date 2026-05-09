from __future__ import annotations

from datetime import datetime, timezone
import os
from urllib.parse import quote_plus

import feedparser
from dateutil import parser as dtparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


_analyzer = SentimentIntensityAnalyzer()

DEFAULT_RSS_SOURCES = ("google_news_rss", "yahoo_finance_rss")


def _published(entry: dict) -> datetime | None:
    for k in ("published", "updated"):
        v = entry.get(k)
        if not v:
            continue
        try:
            dt = dtparser.parse(v)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def _sentiment(text: str) -> float:
    s = _analyzer.polarity_scores(text or "")
    return float(s.get("compound", 0.0))


def _source_url(source: str, ticker: str) -> str | None:
    if source == "google_news_rss":
        q = quote_plus(f"{ticker} stock")
        return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    if source == "yahoo_finance_rss":
        return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    return None


def _enabled_sources() -> list[str]:
    raw = os.environ.get("NEWS_RSS_SOURCES", ",".join(DEFAULT_RSS_SOURCES)).strip()
    if not raw:
        return list(DEFAULT_RSS_SOURCES)
    out: list[str] = []
    for s in [x.strip() for x in raw.split(",") if x.strip()]:
        if s not in out:
            out.append(s)
    return out or list(DEFAULT_RSS_SOURCES)


def fetch_rss_items_for_ticker(ticker: str, limit: int = 25) -> list[dict]:
    items: list[dict] = []
    seen_urls: set[str] = set()
    for source in _enabled_sources():
        url = _source_url(source, ticker)
        if not url:
            continue
        feed = feedparser.parse(url)
        for e in (feed.entries or [])[:limit]:
            title = str(e.get("title", "")).strip()
            link = str(e.get("link", "")).strip()
            if not title or not link or link in seen_urls:
                continue
            seen_urls.add(link)
            items.append(
                {
                    "ticker": ticker,
                    "source": source,
                    "title": title,
                    "url": link,
                    "published_at": _published(e) or datetime.now(tz=timezone.utc),
                    "sentiment_compound": _sentiment(title),
                }
            )
    return items
