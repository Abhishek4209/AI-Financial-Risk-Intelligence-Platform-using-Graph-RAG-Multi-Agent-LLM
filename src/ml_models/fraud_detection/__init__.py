"""Fraud-model inference; each dataset keeps its own model and feature schema."""

from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd


from src.preprocessing.feature_engineering import build_paysim_features
from src.utils.constants import FRAUD_MODEL_FILES, MODEL_ROOT

DEFAULT_PAYSIM_THRESHOLD = 0.5



def _artifact_path(dataset: str, path: str | Path | None) -> Path:
        if path is not None:
                return Path(path).expanduser()
        relative = FRAUD_MODEL_FILES.get(dataset)
        if relative:
                notebook_path = MODEL_ROOT / relative
                if notebook_path.is_file():
                        return notebook_path
        return MODEL_ROOT / ("%s_random_forest.joblib" % dataset)



def _normalize_artifact(raw: Any, dataset: str) -> dict[str, Any]:
        """Wrap a bare pickled estimator into the same dict shape as other artifacts."""
        if isinstance(raw, Mapping) and "model" in raw:
                return dict(raw)
        feature_columns = list(getattr(raw, "feature_names_in_", []) or [])
        return {
                "model": raw,
                "feature_columns": feature_columns,
                "dataset": dataset,
                "threshold": DEFAULT_PAYSIM_THRESHOLD,
        }



@lru_cache(maxsize=8)
def load_fraud_artifact(dataset: str, path: str | Path | None = None) -> Mapping[str, Any]:
        """Load a notebook `.pkl` artifact or a `scripts/train.py` joblib artifact."""
        source = _artifact_path(dataset, path)
        if not source.is_file():
                raise FileNotFoundError("Fraud model artifact not found: %s" % source)
        if source.suffix == ".pkl":
                with source.open("rb") as artifact_file:
                        raw = pickle.load(artifact_file)
        else:
                raw = joblib.load(source)
        artifact = _normalize_artifact(raw, dataset)
        if "model" not in artifact:
                raise ValueError("Fraud artifact must contain a 'model': %s" % source)
        return artifact



def _score(model: Any, frame: pd.DataFrame) -> float:
        probabilities = model.predict_proba(frame)
        classes = list(getattr(model, "classes_", [0, 1]))
        try:
                positive_index = classes.index(1)
        except ValueError as exc:
                raise ValueError("Fraud model does not expose a positive class 1") from exc
        return float(probabilities[0][positive_index])

def predict_paysim_fraud_risk(transaction: Mapping[str, Any], *, artifact: Mapping[str, Any] | None = None) -> dict[str,
Any]:
        """Score a PaySim transaction using the notebook's exact feature engineering."""
        model_artifact = artifact if artifact is not None else load_fraud_artifact("paysim")
        feature_columns = model_artifact["feature_columns"]
        frame = build_paysim_features(transaction, feature_columns)
        risk_score = _score(model_artifact["model"], frame)
        threshold = float(model_artifact.get("threshold", DEFAULT_PAYSIM_THRESHOLD))
        return {
                "dataset": "paysim",
                "fraud_risk_score": risk_score,
                "threshold": threshold,
                "risk_level": "HIGH" if risk_score >= threshold else "BELOW_MODEL_THRESHOLD",
                "interpretation": "Model risk signal only; this does not establish fraud.",
        }



def predict_fraud_risk(engineered_features: Mapping[str, Any], dataset: str, *, artifact: Mapping[str, Any] | None =
None) -> dict[str, Any]:
        """Score an already-engineered feature vector against a non-PaySim fraud model."""
        model_artifact = artifact if artifact is not None else load_fraud_artifact(dataset)
        feature_columns = model_artifact.get("feature_columns")
        if not feature_columns:
                raise ValueError("Artifact for %r has no recorded feature_columns; pass --output from scripts/train.py"
% dataset)
        missing = [column for column in feature_columns if column not in engineered_features]
        if missing:
                raise ValueError("Missing required engineered features for %r: %s" % (dataset, missing))
        frame = pd.DataFrame([[engineered_features[column] for column in feature_columns]],
columns=list(feature_columns))
        risk_score = _score(model_artifact["model"], frame)
        threshold = float(model_artifact.get("threshold", DEFAULT_PAYSIM_THRESHOLD))
        return {
                "dataset": dataset,
                "fraud_risk_score": risk_score,
                "threshold": threshold,
                "risk_level": "HIGH" if risk_score >= threshold else "BELOW_MODEL_THRESHOLD",
                "interpretation": "Model risk signal only; this does not establish fraud.",
        }
