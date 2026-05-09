from __future__ import annotations

import argparse
import os
from dataclasses import asdict, dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.data import fetch_ohlcv_daily
from app.features import FEATURE_COLUMNS, build_features, build_labels


@dataclass
class TrainResult:
    kind: str
    tickers: list[str]
    rows: int


class Ensemble:
    def __init__(self, a, b, w: float = 0.5):
        self.a = a
        self.b = b
        self.w = w

    def predict_proba(self, X_):
        pa = self.a.predict_proba(X_)[:, 1]
        pb = self.b.predict_proba(X_)[:, 1]
        p = self.w * pa + (1.0 - self.w) * pb
        return np.vstack([1.0 - p, p]).T


def _build_dataset(tickers: list[str]) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    used: list[str] = []
    for t in tickers:
        try:
            df = fetch_ohlcv_daily(t, period="10y")
            feats = build_features(df)
            y = build_labels(df).reindex(feats.index).dropna().astype(int)
            feats = feats.loc[y.index]
            x = feats[FEATURE_COLUMNS].to_numpy(dtype=float)
            if len(x) == 0:
                continue
            xs.append(x)
            ys.append(y.to_numpy(dtype=int))
            used.append(t)
        except Exception:
            continue
    if not xs:
        raise RuntimeError("No usable training data from configured tickers/providers")
    X = np.vstack(xs)
    Y = np.concatenate(ys)
    return X, Y


def train_and_save(model_dir: str, tickers: list[str]) -> TrainResult:
    X, y = _build_dataset(tickers)
    tscv = TimeSeriesSplit(n_splits=5)
    # For simplicity, train on full dataset; keep CV for later extension.
    _ = list(tscv.split(X))

    baseline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500)),
        ]
    )
    baseline.fit(X, y)

    xgb = XGBClassifier(
        n_estimators=250,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=42,
        eval_metric="logloss",
    )
    xgb.fit(X, y)

    ensemble = Ensemble(baseline, xgb, w=0.45)

    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(
        {"kind": "ensemble", "feature_names": FEATURE_COLUMNS, "model": ensemble},
        os.path.join(model_dir, "ensemble.joblib"),
    )
    joblib.dump({"feature_names": FEATURE_COLUMNS, "model": baseline}, os.path.join(model_dir, "baseline_lr.joblib"))
    joblib.dump({"feature_names": FEATURE_COLUMNS, "model": xgb}, os.path.join(model_dir, "xgb.joblib"))

    return TrainResult(kind="ensemble", tickers=tickers, rows=int(X.shape[0]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default=os.environ.get("MODEL_DIR", "./artifacts"))
    ap.add_argument(
        "--tickers",
        default="AAPL,MSFT,AMZN,GOOGL,NVDA,TSLA,META,JPM,UNH,XOM",
        help="Comma-separated tickers for training data",
    )
    args = ap.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    res = train_and_save(args.model_dir, tickers)
    print(asdict(res))


if __name__ == "__main__":
    main()
