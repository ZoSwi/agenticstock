from sqlalchemy import Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PortfolioPosition(Base, TimestampMixin):
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_portfolio_user_ticker"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_cost: Mapped[float] = mapped_column(Float)


Index("ix_portfolio_user", PortfolioPosition.user_id)


class DecisionAudit(Base, TimestampMixin):
    __tablename__ = "decision_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    decision: Mapped[str] = mapped_column(String(64))
    confidence_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(64), default="stock_ai_outcome")


Index("ix_decision_audit_user_created", DecisionAudit.user_id, DecisionAudit.created_at)
