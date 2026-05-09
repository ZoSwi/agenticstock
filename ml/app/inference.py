from __future__ import annotations

import numpy as np
import pandas as pd

from app.features import FEATURE_COLUMNS, build_features, latest_feature_vector
from app.model import ModelArtifacts


def _risk_level(atr_pct: float) -> str:
    if atr_pct >= 0.045:
        return "high"
    if atr_pct >= 0.025:
        return "medium"
    return "low"


def _outlook(p_up: float) -> str:
    if p_up >= 0.6:
        return "bullish"
    if p_up <= 0.4:
        return "bearish"
    return "neutral"


def _time_horizon_from(features: pd.DataFrame) -> dict:
    # Simple horizon proxy using multi-window returns. Direction only.
    last = features.tail(1).iloc[0]
    short = "bullish" if last["ret_5d"] > 0 else "bearish"
    med = "bullish" if last["ret_20d"] > 0 else "bearish"
    long = "bullish" if last["sma_50_ratio"] > 0 else "bearish"
    # soften to neutral if close to zero
    if abs(float(last["ret_5d"])) < 0.01:
        short = "neutral"
    if abs(float(last["ret_20d"])) < 0.02:
        med = "neutral"
    if abs(float(last["sma_50_ratio"])) < 0.02:
        long = "neutral"
    return {"short_term": short, "medium_term": med, "long_term": long}


def _feature_contrib_names(
    artifacts: ModelArtifacts | None, x: np.ndarray, feature_names: list[str]
) -> tuple[list[str], list[str]]:
    if artifacts is None:
        return [], []

    model = artifacts.model
    names = artifacts.feature_names or feature_names
    # Works for sklearn linear models; for trees we return feature importance.
    if hasattr(model, "coef_"):
        coef = np.asarray(getattr(model, "coef_"))[0]
        contrib = coef * x[0]
        order = np.argsort(contrib)
        neg = [f"{names[i]} (pressure)" for i in order[:3]]
        pos = [f"{names[i]} (support)" for i in order[-3:][::-1]]
        return pos, neg
    if hasattr(model, "feature_importances_"):
        imp = np.asarray(getattr(model, "feature_importances_"))
        order = np.argsort(imp)
        top = [names[i] for i in order[-3:][::-1]]
        return [f"{t} (importance)" for t in top], []
    return [], []


def predict_direction(
    ohlcv: pd.DataFrame,
    artifacts: ModelArtifacts | None,
) -> dict:
    feats = build_features(ohlcv)
    x, names = latest_feature_vector(feats)
    atr_pct = float(feats.tail(1)["atr_14_pct"].iloc[0])
    risk = _risk_level(atr_pct)
    volatility_detected = atr_pct >= 0.04

    if artifacts is not None and hasattr(artifacts.model, "predict_proba"):
        p_up = float(artifacts.model.predict_proba(x)[0][1])
        confidence = float(abs(p_up - 0.5) * 2.0)  # 0..1 distance from 0.5
    else:
        # Safe fallback heuristic (no trained artifact): momentum + mean reversion blend.
        last = feats.tail(1).iloc[0]
        score = float(0.9 * last["ret_20d"] + 0.6 * last["sma_20_ratio"] + 0.3 * (last["rsi_14"] - 0.5))
        p_up = float(np.clip(0.5 + score, 0.05, 0.95))
        confidence = float(np.clip(abs(p_up - 0.5) * 2.0, 0.05, 0.8))

    p_down = float(1.0 - p_up)
    outlook = _outlook(p_up)
    time_horizon = _time_horizon_from(feats)
    pos, neg = _feature_contrib_names(artifacts, x, FEATURE_COLUMNS)

    return {
        "rise_probability": p_up,
        "fall_probability": p_down,
        "confidence_score": confidence,
        "risk_level": risk,
        "outlook": outlook,
        "volatility_detected": volatility_detected,
        "time_horizon": time_horizon,
        "top_positive_features": pos,
        "top_negative_features": neg,
    }

