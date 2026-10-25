"""Credit-risk inference for the independently trained Taiwan and Lending Club models."""

from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd


from src.preprocessing.feature_engineering import build_lending_features, derive_taiwan_features
from src.utils.constants import CREDIT_MODEL_FILES, MODEL_ROOT

# Matches the risk_band() cutoffs defined in the credit-risk training notebook.
RISK_BANDS = (
        (0.50, "HIGH"),
        (0.25, "MEDIUM"),
        (0.0, "LOW"),
)



def _artifact_path(dataset: str, path: str | Path | None) -> Path:
        if dataset not in CREDIT_MODEL_FILES:
                raise ValueError("dataset must be one of %s" % sorted(CREDIT_MODEL_FILES))
        if path is not None:
                return Path(path).expanduser()
        notebook_path = MODEL_ROOT / CREDIT_MODEL_FILES[dataset]
        if notebook_path.is_file():
                return notebook_path
        return MODEL_ROOT / ("%s_logistic_regression.joblib" % dataset)



@lru_cache(maxsize=4)
def load_credit_artifact(dataset: str, path: str | Path | None = None) -> Mapping[str, Any]:
        """Load the notebook `.pkl` artifact or the `scripts/train.py` joblib artifact."""
        source = _artifact_path(dataset, path)
        if not source.is_file():
                raise FileNotFoundError("Credit risk model artifact not found: %s" % source)
        if source.suffix == ".pkl":
                with source.open("rb") as artifact_file:
                        artifact = pickle.load(artifact_file)
        else:
                artifact = joblib.load(source)
        if not isinstance(artifact, Mapping) or "model" not in artifact:
                raise ValueError("Credit risk artifact must contain a 'model' entry: %s" % source)
        return artifact



def risk_band(probability: float) -> str:
        for threshold, label in RISK_BANDS:
                if probability >= threshold:
                        return label
        return "LOW"



def predict_credit_risk(record: Mapping[str, Any], dataset: str, *, artifact: Mapping[str, Any] | None = None) ->
dict[str, Any]:
        """Score one applicant record with the dataset's own model; never mixes datasets."""
        model_artifact = artifact if artifact is not None else load_credit_artifact(dataset)
        model = model_artifact["model"]
        feature_columns = model_artifact.get("feature_columns")

        if dataset == "taiwan":
                frame = derive_taiwan_features(pd.DataFrame([record]))
        elif dataset == "lending_club":
                if not feature_columns:
                        raise ValueError("Lending Club artifact is missing feature_columns")

                frame = build_lending_features(record, feature_columns)
        else:
                raise ValueError("dataset must be 'taiwan' or 'lending_club'")

        if feature_columns:
                missing = [column for column in feature_columns if column not in frame.columns]
                if missing:
                        raise ValueError("Model input is missing engineered features: %s" % missing)
                frame = frame[list(feature_columns)]

        probabilities = model.predict_proba(frame)
        classes = list(getattr(model, "classes_", [0, 1]))
        try:
                positive_index = classes.index(1)
        except ValueError as exc:
                raise ValueError("Credit model does not expose a positive class 1") from exc
        probability = float(probabilities[0][positive_index])
        band = risk_band(probability)
        return {
                "dataset": dataset,
                "default_probability": probability,
                "risk_band": band,
                "recommended_for_review": band != "LOW",
                "interpretation": "Model risk estimate for analyst review; it is not an automated lending decision.",
        }



def predict_credit_risk_batch(records: list[Mapping[str, Any]], dataset: str) -> list[dict[str, Any]]:
        artifact = load_credit_artifact(dataset)
        return [predict_credit_risk(record, dataset, artifact=artifact) for record in records]
