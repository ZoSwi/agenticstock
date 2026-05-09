from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.ohlcv import OhlcvDaily
from app.models.portfolio import DecisionAudit, PortfolioPosition

router = APIRouter()


class PositionUpsertRequest(BaseModel):
    user_id: str = Field(default="demo", max_length=64)
    ticker: str = Field(min_length=1, max_length=16)
    quantity: float = Field(gt=0)
    avg_cost: float = Field(gt=0)


def _latest_close(rows: list[OhlcvDaily]) -> float | None:
    if not rows:
        return None
    latest = max(rows, key=lambda r: r.day)
    return float(latest.close)


@router.post("/portfolio/positions")
async def upsert_position(req: PositionUpsertRequest, db: AsyncSession = Depends(get_db)) -> dict:
    ticker = req.ticker.upper().strip()
    stmt = select(PortfolioPosition).where(
        PortfolioPosition.user_id == req.user_id,
        PortfolioPosition.ticker == ticker,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.quantity = float(req.quantity)
        existing.avg_cost = float(req.avg_cost)
    else:
        db.add(
            PortfolioPosition(
                user_id=req.user_id,
                ticker=ticker,
                quantity=float(req.quantity),
                avg_cost=float(req.avg_cost),
            )
        )
    await db.commit()
    return {"ok": True, "ticker": ticker}


@router.get("/portfolio/positions")
async def get_positions(
    user_id: str = Query(default="demo", max_length=64),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        await db.execute(
            select(PortfolioPosition)
            .where(PortfolioPosition.user_id == user_id)
            .order_by(PortfolioPosition.created_at.desc())
        )
    ).scalars().all()
    return {
        "user_id": user_id,
        "positions": [
            {
                "ticker": r.ticker,
                "quantity": float(r.quantity),
                "avg_cost": float(r.avg_cost),
            }
            for r in rows
        ],
    }


@router.delete("/portfolio/positions")
async def delete_position(
    user_id: str = Query(default="demo", max_length=64),
    ticker: str = Query(min_length=1, max_length=16),
    db: AsyncSession = Depends(get_db),
) -> dict:
    symbol = ticker.upper().strip()
    await db.execute(
        delete(PortfolioPosition).where(
            PortfolioPosition.user_id == user_id,
            PortfolioPosition.ticker == symbol,
        )
    )
    await db.commit()
    return {"ok": True}


@router.get("/portfolio/summary")
async def get_portfolio_summary(
    user_id: str = Query(default="demo", max_length=64),
    db: AsyncSession = Depends(get_db),
) -> dict:
    positions = (
        await db.execute(select(PortfolioPosition).where(PortfolioPosition.user_id == user_id))
    ).scalars().all()
    tickers = sorted({p.ticker for p in positions})
    close_map: dict[str, float | None] = {t: None for t in tickers}
    if tickers:
        price_rows = (
            await db.execute(
                select(OhlcvDaily)
                .where(OhlcvDaily.ticker.in_(tickers))
                .order_by(OhlcvDaily.ticker, OhlcvDaily.day.desc())
            )
        ).scalars().all()
        grouped: dict[str, list[OhlcvDaily]] = {}
        for row in price_rows:
            grouped.setdefault(row.ticker, []).append(row)
        for t in tickers:
            close_map[t] = _latest_close(grouped.get(t, []))

    items: list[dict] = []
    market_value = 0.0
    cost_basis = 0.0
    for p in positions:
        qty = float(p.quantity)
        avg = float(p.avg_cost)
        px = close_map.get(p.ticker)
        cost = qty * avg
        mv = qty * px if px is not None else 0.0
        upl = mv - cost if px is not None else None
        upl_pct = ((mv - cost) / cost) if (px is not None and cost > 0) else None
        cost_basis += cost
        market_value += mv if px is not None else 0.0
        items.append(
            {
                "ticker": p.ticker,
                "quantity": qty,
                "avg_cost": avg,
                "last_price": px,
                "cost_basis": round(cost, 4),
                "market_value": round(mv, 4) if px is not None else None,
                "unrealized_pl": round(upl, 4) if upl is not None else None,
                "unrealized_pl_pct": round(upl_pct, 6) if upl_pct is not None else None,
            }
        )

    total_upl = market_value - cost_basis
    total_upl_pct = (total_upl / cost_basis) if cost_basis > 0 else 0.0
    return {
        "user_id": user_id,
        "positions": items,
        "totals": {
            "cost_basis": round(cost_basis, 4),
            "market_value": round(market_value, 4),
            "unrealized_pl": round(total_upl, 4),
            "unrealized_pl_pct": round(total_upl_pct, 6),
        },
    }


class AuditEventRequest(BaseModel):
    user_id: str = Field(default="demo", max_length=64)
    ticker: str = Field(min_length=1, max_length=16)
    decision: str = Field(min_length=1, max_length=64)
    confidence_score: float = Field(ge=0, le=1)
    risk_level: str = Field(pattern="^(low|medium|high)$")
    source: str = Field(default="stock_ai_outcome", max_length=64)


@router.post("/audit/events")
async def create_audit_event(req: AuditEventRequest, db: AsyncSession = Depends(get_db)) -> dict:
    evt = DecisionAudit(
        user_id=req.user_id,
        ticker=req.ticker.upper().strip(),
        decision=req.decision.strip(),
        confidence_score=float(req.confidence_score),
        risk_level=req.risk_level,
        source=req.source,
    )
    db.add(evt)
    await db.commit()
    return {"ok": True, "id": evt.id}


@router.get("/audit/events")
async def get_audit_events(
    user_id: str = Query(default="demo", max_length=64),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        await db.execute(
            select(DecisionAudit)
            .where(DecisionAudit.user_id == user_id)
            .order_by(DecisionAudit.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "user_id": user_id,
        "events": [
            {
                "id": r.id,
                "ticker": r.ticker,
                "decision": r.decision,
                "confidence_score": float(r.confidence_score),
                "risk_level": r.risk_level,
                "source": r.source,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
