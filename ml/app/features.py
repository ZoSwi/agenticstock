from __future__ import annotations

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import AverageTrueRange


FEATURE_COLUMNS = [
    "ret_5d",
    "ret_20d",
    "sma_20_ratio",
    "sma_50_ratio",
    "rsi_14",
    "macd",
    "macd_signal",
    "atr_14_pct",
    "vol_20_z",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    v = df["volume"].astype(float)

    out = pd.DataFrame(index=df.index)
    out["ret_5d"] = c.pct_change(5)
    out["ret_20d"] = c.pct_change(20)

    sma20 = SMAIndicator(close=c, window=20).sma_indicator()
    sma50 = SMAIndicator(close=c, window=50).sma_indicator()
    out["sma_20_ratio"] = (c / sma20) - 1.0
    out["sma_50_ratio"] = (c / sma50) - 1.0

    out["rsi_14"] = RSIIndicator(close=c, window=14).rsi() / 100.0

    macd = MACD(close=c, window_slow=26, window_fast=12, window_sign=9)
    out["macd"] = macd.macd()
    out["macd_signal"] = macd.macd_signal()

    atr = AverageTrueRange(high=h, low=l, close=c, window=14).average_true_range()
    out["atr_14_pct"] = atr / c

    vol20 = v.rolling(20).mean()
    vol_std = v.rolling(60).std()
    out["vol_20_z"] = (vol20 - vol20.rolling(60).mean()) / (vol_std.replace(0, np.nan))

    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    return out


def build_labels(df: pd.DataFrame, horizon_days: int = 20) -> pd.Series:
    c = df["close"].astype(float)
    fwd_ret = c.shift(-horizon_days) / c - 1.0
    y = (fwd_ret > 0).astype(int)
    return y


def latest_feature_vector(features: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    x = features.tail(1)[FEATURE_COLUMNS].to_numpy(dtype=float)
    return x, FEATURE_COLUMNS

