from __future__ import annotations

import os
from dataclasses import dataclass

import joblib
import numpy as np


@dataclass(frozen=True)
class ModelArtifacts:
    model: object
    feature_names: list[str]
    kind: str


class ModelRegistry:
    def __init__(self, model_dir: str) -> None:
        self.model_dir = model_dir
        self._cache: ModelArtifacts | None = None

    def load(self) -> ModelArtifacts | None:
        if self._cache is not None:
            return self._cache

        candidates = [
            ("ensemble.joblib", "ensemble"),
            ("xgb.joblib", "xgb"),
            ("baseline_lr.joblib", "baseline_lr"),
        ]
        for filename, default_kind in candidates:
            path = os.path.join(self.model_dir, filename)
            if not os.path.exists(path):
                continue
            try:
                payload = joblib.load(path)
                self._cache = ModelArtifacts(
                    model=payload["model"],
                    feature_names=list(payload["feature_names"]),
                    kind=str(payload.get("kind", default_kind)),
                )
                return self._cache
            except Exception:
                continue
        return None


def sigmoid(z: float) -> float:
    return float(1.0 / (1.0 + np.exp(-z)))
