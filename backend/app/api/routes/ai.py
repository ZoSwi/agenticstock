from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.stocks import get_analysis
from app.core.db import get_db
from app.core.redis import get_redis
from app.schemas.ai import AiQueryRequest, AiQueryResponse
from app.services.agent import render_analysis_markdown
from app.services.llm import enhance_answer_markdown, resolve_llm_provider
from app.utils.ticker import extract_tickers

router = APIRouter()


@router.post("/query", response_model=AiQueryResponse)
async def ai_query(
    req: AiQueryRequest,
    r=Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> AiQueryResponse:
    tickers = extract_tickers(req.query)
    if not tickers:
        raise HTTPException(
            status_code=400,
            detail="Please include a ticker in your question (e.g., 'Should I invest in TSLA?').",
        )

    if len(tickers) == 1:
        analysis = await get_analysis(tickers[0], r=r, db=db)
        structured = analysis.model_dump()
        md = render_analysis_markdown(analysis, req.user_type)
        if resolve_llm_provider() != "none":
            md = await enhance_answer_markdown(
                draft_markdown=md, structured=structured, user_type=req.user_type
            )
        return AiQueryResponse(answer_markdown=md, structured=structured)

    # Simple compare mode
    analyses = [await get_analysis(t, r=r, db=db) for t in tickers[:3]]
    body = "\n\n".join(render_analysis_markdown(a, req.user_type) for a in analyses)
    structured = {"mode": "compare", "items": [a.model_dump() for a in analyses]}
    if resolve_llm_provider() != "none":
        body = await enhance_answer_markdown(
            draft_markdown=body, structured=structured, user_type=req.user_type
        )
    return AiQueryResponse(answer_markdown=body, structured=structured)
