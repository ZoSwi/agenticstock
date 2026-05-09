from pydantic import BaseModel, Field

from app.schemas.common import Outlook, Probabilities, RiskLevel, TimeHorizonOutlook


class ModelStatus(BaseModel):
    source: str
    degraded: bool
    reason: str | None = None


class StockAnalysisResponse(BaseModel):
    ticker: str

    outlook: Outlook
    risk_level: RiskLevel
    volatility_detected: bool

    rise_probability: float = Field(ge=0, le=1)
    fall_probability: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)

    time_horizon: TimeHorizonOutlook

    growth_drivers: list[str]
    fall_drivers: list[str]

    suggested_action: str
    best_for: str
    watch_next: list[str]
    model_status: ModelStatus


class PredictionResponse(BaseModel):
    ticker: str
    outlook: Outlook
    risk_level: RiskLevel
    volatility_detected: bool
    probabilities: Probabilities
    time_horizon: TimeHorizonOutlook
    model_status: ModelStatus


class ReasonsResponse(BaseModel):
    ticker: str
    growth_drivers: list[str]
    fall_drivers: list[str]
    watch_next: list[str]
    suggested_action: str
    best_for: str
