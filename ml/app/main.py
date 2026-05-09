from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from app.data import fetch_ohlcv_daily
from app.inference import predict_direction
from app.model import ModelRegistry


MODEL_DIR = os.environ.get("MODEL_DIR", "/app/artifacts")
registry = ModelRegistry(MODEL_DIR)

app = FastAPI(title="AI Stock Intelligence ML Service", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "model_loaded": registry.load() is not None}


@app.get("/predict/{ticker}")
async def predict(ticker: str) -> dict:
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    try:
        df = fetch_ohlcv_daily(ticker)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    artifacts = registry.load()
    pred = predict_direction(df, artifacts)
    return {"ticker": ticker, **pred}

