from enum import Enum

from pydantic import BaseModel, Field


class Outlook(str, Enum):
    bullish = "bullish"
    neutral = "neutral"
    bearish = "bearish"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TimeHorizonOutlook(BaseModel):
    short_term: Outlook
    medium_term: Outlook
    long_term: Outlook


class Probabilities(BaseModel):
    rise_probability: float = Field(ge=0, le=1)
    fall_probability: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)

