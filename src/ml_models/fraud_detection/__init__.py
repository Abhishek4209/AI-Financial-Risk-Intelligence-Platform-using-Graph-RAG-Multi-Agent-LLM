
"""Fraud-model inference; each dataset keeps its own feature schema."""

from __future__ import annotations

import math
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd

from src.preprocessing.feature_engineering import build_paysim_features
from src.ml_models.explainability import explain_prediction
from src.utils.constants import FRAUD_MODEL_FILES, MODEL_ROOT
from src.utils.logger import get_logger


DEFAULT_PAYSIM_THRESHOLD = 0.5
logger = get_logger(__name__)
IEEE_ENCODER_FILE = MODEL_ROOT / "Fraud_models" / "ieee_categorical_encoders.pkl"
IEEE_REQUIRED_FEATURES = (
    "TransactionAmt",
    "ProductCD",
    "card1",
    "card2",
    "card3",
    "card4",
    "card5",
    "card6",
)
IEEE_DERIVED_FEATURES = (
    "transaction_hour",
    "log_transaction_amt",
    "has_device_info",
    "email_domain_mismatch",
)


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


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def get_ieee_feature_schema(
    artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe the saved IEEE-CIS model inputs and training preprocessing."""
    model_artifact = (
        artifact if artifact is not None else load_fraud_artifact("ieee_cis")
    )
    feature_columns = [
        str(column)
        for column in model_artifact.get("feature_columns", [])
    ]
    if not feature_columns:
        raise ValueError("IEEE-CIS artifact has no recorded feature_columns.")

    missing = [
        column for column in IEEE_REQUIRED_FEATURES
        if column not in feature_columns
    ]
    if missing:
        raise ValueError(
            "IEEE-CIS model is missing expected transaction features: "
            f"{missing}"
        )

    encoders = _load_ieee_encoders()
    return {
        "dataset": "ieee_cis",
        "feature_count": len(feature_columns),
        "missing_value_sentinel": -999,
        "features": [
            {
                "name": str(column),
                "input_type": (
                    "category" if column in encoders else "number"
                ),
                "required": column in IEEE_REQUIRED_FEATURES,
                "derived": column in IEEE_DERIVED_FEATURES,
                "categories": (
                    [str(value) for value in encoders[column].classes_]
                    if column in encoders else []
                ),
            }
            for column in feature_columns
        ],
        "raw_inputs": [
            {
                "name": "TransactionDT",
                "input_type": "number",
                "required": True,
            },
            {
                "name": "DeviceInfo",
                "input_type": "text",
                "required": False,
            },
        ],
    }


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


def _add_shap_explanation(
    result: dict[str, Any],
    model: Any,
    frame: pd.DataFrame,
) -> dict[str, Any]:
    try:
        result["shap_drivers"] = explain_prediction(
            model,
            frame,
            top_k=3,
        )
    except Exception as exc:
        logger.exception("Fraud model SHAP explanation failed")
        result["shap_drivers"] = []
        result["shap_error"] = (
            f"SHAP evidence is unavailable: {exc}"
        )
    return result


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

    return _add_shap_explanation(
        _prediction_result("paysim", risk_score, threshold),
        model_artifact["model"],
        frame,
    )


def _build_ieee_frame(
    features: Mapping[str, Any],
    feature_columns: list[str],
) -> pd.DataFrame:
    """Apply the saved notebook preprocessing in the trained column order."""
    encoders = _load_ieee_encoders()
    prepared = dict(features)
    required = [
        column for column in IEEE_REQUIRED_FEATURES
        if column in feature_columns and _is_missing(prepared.get(column))
    ]
    if required:
        raise ValueError(
            "IEEE-CIS requires these transaction features: "
            f"{', '.join(required)}"
        )

    if not _is_missing(prepared.get("TransactionDT")):
        transaction_dt = _numeric_feature(
            "TransactionDT", prepared["TransactionDT"]
        )
        transaction_amount = _numeric_feature(
            "TransactionAmt", prepared["TransactionAmt"]
        )
        if transaction_dt < 0:
            raise ValueError("IEEE-CIS feature 'TransactionDT' must be non-negative.")
        if transaction_amount < 0:
            raise ValueError("IEEE-CIS feature 'TransactionAmt' must be non-negative.")

        prepared["transaction_hour"] = (transaction_dt / 3600) % 24
        prepared["log_transaction_amt"] = math.log1p(transaction_amount)
        prepared["has_device_info"] = int(
            not _is_missing(prepared.get("DeviceInfo"))
        )
        payer_email = _email_value(
            "P_emaildomain", prepared.get("P_emaildomain"), encoders
        )
        recipient_email = _email_value(
            "R_emaildomain", prepared.get("R_emaildomain"), encoders
        )
        prepared["email_domain_mismatch"] = int(
            payer_email != recipient_email
            or payer_email is None
            or recipient_email is None
        )
    elif any(column in feature_columns for column in IEEE_DERIVED_FEATURES):
        missing_derived = [
            column for column in IEEE_DERIVED_FEATURES
            if _is_missing(prepared.get(column))
        ]
        if missing_derived:
            raise ValueError(
                "IEEE-CIS needs TransactionDT to derive transaction_hour; "
                "DeviceInfo may be blank. Provide all pre-engineered "
                "features instead: "
                f"{', '.join(missing_derived)}"
            )

    encoded_values: dict[str, float] = {}
    for column in feature_columns:
        value = prepared.get(column)
        encoder = encoders.get(column)

        if encoder is not None:
            if _is_missing(value):
                value = "missing"

            if isinstance(value, str):
                try:
                    value = encoder.transform([value])[0]
                except ValueError as exc:
                    raise ValueError(
                        f"Unknown category {value!r} for IEEE-CIS feature "
                        f"{column!r}. Use a category from the saved training "
                        "encoder."
                    ) from exc
            else:
                category_code = _numeric_feature(column, value)
                classes = getattr(encoder, "classes_", None)
                if (
                    category_code == -1
                    and classes is not None
                    and "missing" in [str(category) for category in classes]
                ):
                    value = encoder.transform(["missing"])[0]
                else:
                    value = category_code

        if _is_missing(value):
            encoded_values[column] = float("nan")
            continue

        encoded = _numeric_feature(column, value)
        if encoder is not None:
            classes = getattr(encoder, "classes_", None)
            if classes is not None and (
                not encoded.is_integer()
                or encoded < 0
                or encoded >= len(classes)
            ):
                raise ValueError(
                    f"IEEE-CIS category code for {column!r} is invalid."
                )
        encoded_values[column] = encoded

    frame = pd.DataFrame(
        [encoded_values],
        columns=feature_columns,
    )
    return frame.fillna(-999)


def _numeric_feature(column: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"IEEE-CIS feature {column!r} must be numeric.")
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(
            f"IEEE-CIS feature {column!r} must be numeric."
        ) from exc
    if not math.isfinite(number):
        raise ValueError(
            f"IEEE-CIS feature {column!r} must be a finite number."
        )
    return number


def _email_value(
    column: str,
    value: Any,
    encoders: Mapping[str, Any],
) -> Any:
    encoder = encoders.get(column)
    if _is_missing(value):
        return None
    if isinstance(value, str):
        return None if value == "missing" else value

    classes = getattr(encoder, "classes_", None)
    if classes is not None:
        code = _numeric_feature(column, value)
        if (
            code == -1
            and "missing" in [str(category) for category in classes]
        ):
            return None
        if code.is_integer() and 0 <= code < len(classes):
            category = str(classes[int(code)])
            return None if category == "missing" else category
    return value


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
    if dataset == "ieee_cis":
        feature_columns = [str(column) for column in feature_columns]

    missing = [
        column for column in feature_columns
        if column not in engineered_features
    ]
    if missing and dataset != "ieee_cis":
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

    return _add_shap_explanation(
        _prediction_result(dataset, risk_score, threshold),
        model_artifact["model"],
        frame,
    )
