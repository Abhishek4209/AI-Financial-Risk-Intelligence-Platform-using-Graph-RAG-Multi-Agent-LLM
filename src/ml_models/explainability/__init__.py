
"""Generic SHAP explanations for credit-risk and fraud pipelines."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


TREE_MODEL_ATTRS = ("feature_importances_", "tree_")


def _split_pipeline(
    model: Any,
) -> tuple[list[tuple[str, Any]], Any]:
    steps = getattr(model, "steps", None)
    if not steps:
        return [], model
    return steps[:-1], steps[-1][1]


def _transform_through(
    preprocessing_steps: list[tuple[str, Any]],
    frame: pd.DataFrame,
) -> tuple[np.ndarray, list[str]]:
    transformed: Any = frame
    feature_names = list(frame.columns)

    for _, step in preprocessing_steps:
        transformed = step.transform(transformed)
        width = (
            transformed.shape[1]
            if hasattr(transformed, "shape")
            else None
        )

        if width is not None and width != len(feature_names):
            get_names = getattr(step, "get_feature_names_out", None)
            if get_names is not None:
                try:
                    feature_names = list(get_names())
                except Exception:
                    pass

    dense = (
        transformed.toarray()
        if hasattr(transformed, "toarray")
        else np.asarray(transformed)
    )
    return dense, feature_names


def _is_tree_model(estimator: Any) -> bool:
    return any(
        hasattr(estimator, attr)
        for attr in TREE_MODEL_ATTRS
    )


def _resolve_background(
    preprocessing_steps: list[tuple[str, Any]],
    values: np.ndarray,
    background: pd.DataFrame | None,
) -> np.ndarray:
    if background is None:
        return np.zeros_like(values)

    if preprocessing_steps:
        background_values, _ = _transform_through(
            preprocessing_steps,
            background,
        )
        return background_values

    return background.to_numpy(dtype="float64")


def _compute_shap_values(
    estimator: Any,
    values: np.ndarray,
    background_values: np.ndarray,
    shap_module: Any,
) -> np.ndarray:
    if _is_tree_model(estimator):
        explanation = shap_module.TreeExplainer(estimator)(values)
        return np.asarray(
            getattr(explanation, "values", explanation)
        )

    try:
        explainer = shap_module.LinearExplainer(
            estimator,
            background_values,
        )
        return np.asarray(explainer.shap_values(values))
    except Exception:
        explainer = shap_module.Explainer(
            estimator.predict_proba,
            background_values,
        )
        return np.asarray(explainer(values).values)


def explain_prediction(
    model: Any,
    features: pd.DataFrame,
    *,
    background: pd.DataFrame | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Return the strongest positive and negative SHAP drivers for one row."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if features.empty:
        raise ValueError("features must contain at least one row")

    try:
        import shap
    except ImportError as exc:
        raise RuntimeError(
            "Install the 'shap' package to explain predictions"
        ) from exc

    preprocessing_steps, estimator = _split_pipeline(model)

    if preprocessing_steps:
        values, feature_names = _transform_through(
            preprocessing_steps,
            features,
        )
    else:
        values = features.to_numpy(dtype="float64")
        feature_names = list(features.columns)

    background_values = _resolve_background(
        preprocessing_steps,
        values,
        background,
    )

    shap_values = _compute_shap_values(
        estimator,
        values,
        background_values,
        shap,
    )

    if shap_values.ndim == 3:
        shap_values = shap_values[
            :,
            :,
            1 if shap_values.shape[2] > 1 else 0,
        ]

    if shap_values.ndim == 2 and shap_values.shape[0] != 1:
        shap_values = shap_values[:1]

    row = np.asarray(shap_values).reshape(-1)

    if len(row) != len(feature_names):
        raise ValueError(
            "SHAP output length does not match transformed feature names"
        )

    first_row = values.reshape(len(features), -1)[0]

    drivers = [
        {
            "feature": name,
            "feature_value": (
                float(first_row[index])
                if index < len(first_row)
                else None
            ),
            "shap_value": float(contribution),
            "direction": (
                "increases" if contribution >= 0 else "decreases"
            ),
        }
        for index, (name, contribution) in enumerate(
            zip(feature_names, row)
        )
    ]

    positive = sorted(
        (
            item for item in drivers
            if item["shap_value"] > 0
        ),
        key=lambda item: item["shap_value"],
        reverse=True,
    )[:top_k]

    negative = sorted(
        (
            item for item in drivers
            if item["shap_value"] < 0
        ),
        key=lambda item: item["shap_value"],
    )[:top_k]

    return positive + negative
