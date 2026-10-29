
"""Fraud-model inference; each dataset keeps its own feature schema."""

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
IEEE_ENCODER_FILE = MODEL_ROOT / "Fraud_models" / "ieee_categorical_encoders.pkl"


def _artifact_path(
    dataset: str,
    path: str | Path | None,
) -> Path:
    """Resolve the model artifact path for a dataset."""
    if path is not None:
        return Path(path).expanduser()

    relative = FRAUD_MODEL_FILES.get(dataset)
    if relative:
        candidate = MODEL_ROOT / relative
        if candidate.is_file():
            return candidate

    return MODEL_ROOT / f"{dataset}_random_forest.joblib"


def _normalize_artifact(raw: Any, dataset: str) -> dict[str, Any]:
    """Wrap a bare estimator in the project's artifact dictionary."""
    if isinstance(raw, Mapping) and "model" in raw:
        return dict(raw)

    feature_names = getattr(raw, "feature_names_in_", None)
    return {
        "model": raw,
        "feature_columns": (
            list(feature_names) if feature_names is not None else []
        ),
        "dataset": dataset,
        "threshold": DEFAULT_PAYSIM_THRESHOLD,
    }


@lru_cache(maxsize=8)
def load_fraud_artifact(
    dataset: str,
    path: str | Path | None = None,
) -> Mapping[str, Any]:
    """Load a pickle artifact or a joblib training artifact."""
    source = _artifact_path(dataset, path)

    if not source.is_file():
        raise FileNotFoundError(
            f"Fraud model artifact not found: {source}"
        )

    if source.suffix.lower() == ".pkl":
        with source.open("rb") as artifact_file:
            raw = pickle.load(artifact_file)
    else:
        raw = joblib.load(source)

    artifact = _normalize_artifact(raw, dataset)
    if "model" not in artifact:
        raise ValueError(
            f"Fraud artifact must contain a 'model': {source}"
        )

    return artifact


@lru_cache(maxsize=2)
def _load_ieee_encoders() -> Mapping[str, Any]:
    """Load the categorical encoders saved during IEEE-CIS training."""
    if not IEEE_ENCODER_FILE.is_file():
        raise FileNotFoundError(
            "IEEE-CIS categorical encoders were not found at "
            f"{IEEE_ENCODER_FILE}. Run the updated training notebook "
            "and save the encoders before using raw categorical values."
        )

    with IEEE_ENCODER_FILE.open("rb") as encoder_file:
        encoders = pickle.load(encoder_file)

    if not isinstance(encoders, Mapping):
        raise ValueError("IEEE-CIS encoder file must contain a mapping.")

    return encoders


def _score(model: Any, frame: pd.DataFrame) -> float:
    """Return the model probability for positive class 1."""
    probabilities = model.predict_proba(frame)
    classes = list(getattr(model, "classes_", [0, 1]))

    try:
        positive_index = classes.index(1)
    except ValueError as exc:
        raise ValueError(
            "Fraud model does not expose a positive class 1."
        ) from exc

    return float(probabilities[0][positive_index])


def _get_threshold(artifact: Mapping[str, Any]) -> float:
    """Get and validate the configured decision threshold."""
    threshold = float(
        artifact.get("threshold", DEFAULT_PAYSIM_THRESHOLD)
    )
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Model threshold must be between 0 and 1.")
    return threshold


def _prediction_result(
    dataset: str,
    risk_score: float,
    threshold: float,
) -> dict[str, Any]:
    """Build a consistent response for a fraud prediction."""
    return {
        "dataset": dataset,
        "fraud_risk_score": risk_score,
        "threshold": threshold,
        "risk_level": (
            "HIGH" if risk_score >= threshold
            else "BELOW_MODEL_THRESHOLD"
        ),
        "interpretation": (
            "Model risk signal only; this does not establish fraud."
        ),
    }


def predict_paysim_fraud_risk(
    transaction: Mapping[str, Any],
    *,
    artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Score a PaySim transaction using its own feature builder."""
    model_artifact = (
        artifact if artifact is not None else load_fraud_artifact("paysim")
    )

    feature_columns = model_artifact.get("feature_columns")
    if not feature_columns:
        raise ValueError(
            "PaySim artifact has no recorded feature_columns."
        )

    # PaySim preprocessing is intentionally unchanged.
    frame = build_paysim_features(transaction, feature_columns)
    risk_score = _score(model_artifact["model"], frame)
    threshold = _get_threshold(model_artifact)

    return _prediction_result("paysim", risk_score, threshold)


def _build_ieee_frame(
    features: Mapping[str, Any],
    feature_columns: list[str],
) -> pd.DataFrame:
    """Build a numeric IEEE-CIS frame and encode raw string categories."""
    frame = pd.DataFrame(
        [{column: features[column] for column in feature_columns}],
        columns=feature_columns,
    )

    # Apply the saved training encoders only to string-valued categories.
    # Numeric values are assumed to already be encoded.
    encoders = _load_ieee_encoders() if any(
        isinstance(features.get(column), str)
        for column in feature_columns
        if column in features
    ) else {}

    for column in feature_columns:
        value = features[column]

        if column in encoders and isinstance(value, str):
            encoder = encoders[column]
            try:
                frame.at[0, column] = encoder.transform([value])[0]
            except ValueError as exc:
                raise ValueError(
                    f"Unknown category {value!r} for IEEE-CIS feature "
                    f"{column!r}. Use the same category mapping as training."
                ) from exc

    for column in frame.columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame.fillna(-999)


def predict_fraud_risk(
    engineered_features: Mapping[str, Any],
    dataset: str,
    *,
    artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Score an engineered feature vector using the selected dataset model."""
    model_artifact = (
        artifact
        if artifact is not None
        else load_fraud_artifact(dataset)
    )

    feature_columns = model_artifact.get("feature_columns")
    if not feature_columns:
        raise ValueError(
            f"Artifact for {dataset!r} has no recorded feature_columns."
        )

    missing = [
        column for column in feature_columns
        if column not in engineered_features
    ]
    if missing:
        raise ValueError(
            f"Missing required engineered features for {dataset!r}: "
            f"{missing[:20]}"
        )

    if dataset == "ieee_cis":
        frame = _build_ieee_frame(
            engineered_features,
            list(feature_columns),
        )
    else:
        frame = pd.DataFrame(
            [
                {
                    column: engineered_features[column]
                    for column in feature_columns
                }
            ],
            columns=list(feature_columns),
        )

    risk_score = _score(model_artifact["model"], frame)
    threshold = _get_threshold(model_artifact)

    return _prediction_result(dataset, risk_score, threshold)
