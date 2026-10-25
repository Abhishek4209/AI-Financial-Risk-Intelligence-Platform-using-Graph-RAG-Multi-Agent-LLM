"""Risk Agent: credit-risk scoring with SHAP evidence, per architecture.md."""

from __future__ import annotations

from typing import Any

from src.ml_models.credit_risk import load_credit_artifact, predict_credit_risk
from src.ml_models.explainability import explain_prediction
from src.preprocessing.feature_engineering import build_lending_features, derive_taiwan_features
import pandas as pd



def assess_credit_risk(record: dict[str, Any], dataset: str) -> dict[str, Any]:
        """Score an applicant and attach SHAP evidence; never an automated lending decision."""
        artifact = load_credit_artifact(dataset)
        prediction = predict_credit_risk(record, dataset, artifact=artifact)

        feature_columns = artifact.get("feature_columns")
        if dataset == "taiwan":
                features = derive_taiwan_features(pd.DataFrame([record]))
        else:
                features = build_lending_features(record, feature_columns)
        if feature_columns:
                features = features[list(feature_columns)]

        try:
                drivers = explain_prediction(artifact["model"], features)
        except RuntimeError:
                drivers = []

        return {
                "agent": "risk_agent",
                "prediction": prediction,
                "shap_drivers": drivers,
                "human_review_required": prediction["recommended_for_review"],
        }
