from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NewsItem(Base, TimestampMixin):
    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("source", "url", name="uq_news_source_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    ticker: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sentiment_compound: Mapped[float | None] = mapped_column(Float, nullable=True)


Index("ix_news_ticker_published", NewsItem.ticker, NewsItem.published_at)

