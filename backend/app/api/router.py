from fastapi import APIRouter

from app.api.routes.ai import router as ai_router
from app.api.routes.news import router as news_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.stocks import router as stocks_router
from app.api.routes.system import router as system_router
from app.api.routes.watchlist import router as watchlist_router

api_router = APIRouter()

api_router.include_router(stocks_router, prefix="/stocks", tags=["stocks"])
api_router.include_router(news_router, prefix="/news", tags=["news"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(system_router, prefix="", tags=["system"])
api_router.include_router(watchlist_router, prefix="", tags=["watchlist"])
api_router.include_router(portfolio_router, prefix="", tags=["portfolio"])
