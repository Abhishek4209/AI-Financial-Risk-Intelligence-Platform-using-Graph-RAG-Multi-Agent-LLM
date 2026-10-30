"""Evaluate a saved risk-model artifact on its reproducible held-out split."""
import argparse
import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
def _normalize(value):
    return " ".join(str(value).strip().lower().split())
def _get_target(frame, artifact):
    target_column = artifact["target_column"]
    if target_column not in frame.columns:
        raise ValueError("Target column %r is missing from evaluation data" % target_column)
    if artifact["dataset"] == "lending_club":
        status = frame[target_column].astype("string").str.strip().str.lower()
        good = status.eq("fully paid")
        bad = status.str.contains(r"charged off|default", na=False)
        keep = good | bad
        return frame.loc[keep].copy(), bad.loc[keep].astype("int8")
    raw = frame[target_column]
    positive = artifact.get("source_positive_label")
    values = list(pd.unique(raw.dropna()))
    if positive is None:
        positive = "1" if artifact["dataset"] == "taiwan" else None
    if positive is None:
        candidates = [value for value in values if _normalize(value) in {
            "1", "true", "yes", "y", "default", "bad", "fraud", "charged off"
        }]
        positive = candidates[0] if candidates else max(values, key=_normalize)
    positive_value = next((value for value in values if _normalize(value) == _normalize(positive)), N
one)
    if positive_value is None:
        raise ValueError("Positive target label %r is absent from evaluation data" % positive)
    keep = raw.notna()
    labels = raw.loc[keep].map(lambda value: int(_normalize(value) == _normalize(positive_value)))
    return frame.loc[keep].copy(), labels.astype("int8")
def evaluate(artifact_path, data_path):
    artifact = joblib.load(artifact_path)
    if not isinstance(artifact, dict) or "model" not in artifact:
        raise ValueError("Artifact does not contain the expected model package")
    csv_path = Path(data_path or artifact["data_path"]).expanduser().resolve()
    frame = pd.read_csv(csv_path, low_memory=False)
    frame, labels = _get_target(frame, artifact)
    missing = [column for column in artifact["feature_columns"] if column not in frame.columns]
    if missing:
        raise ValueError("Evaluation data is missing model features: %s" % missing)
    features = frame[artifact["feature_columns"]]
    stratify = labels if labels.nunique() == 2 and labels.value_counts().min() >= 2 else None
    if stratify is None:
        raise ValueError("Both classes need at least two rows in evaluation data")
    _, x_test, _, y_test = train_test_split(
        features,
        labels,
        test_size=artifact.get("test_size", 0.2),
        random_state=artifact.get("random_state", 42),
        stratify=stratify,
    )
    model = artifact["model"]
    probabilities = model.predict_proba(x_test)[:, 1]
    threshold = float(artifact.get("threshold", 0.5))
    predictions = (probabilities >= threshold).astype("int8")
    return {
        "dataset": artifact.get("dataset"),
        "task": artifact.get("task"),
        "artifact": str(Path(artifact_path).resolve()),
        "evaluation_data": str(csv_path),
        "rows": int(len(y_test)),
        "threshold": threshold,
        "metrics": {
            "roc_auc": float(roc_auc_score(y_test, probabilities)),
            "pr_auc": float(average_precision_score(y_test, probabilities)),
            "precision": float(precision_score(y_test, predictions, zero_division=0)),
            "recall": float(recall_score(y_test, predictions, zero_division=0)),
            "f1": float(f1_score(y_test, predictions, zero_division=0)),
            "brier_score": float(brier_score_loss(y_test, probabilities)),
            "confusion_matrix": confusion_matrix(y_test, predictions, labels=[0, 1]).tolist(),
        },
        "caveat": "Metrics are decision-support evidence, not proof of fairness or production readiness.",
    }
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Artifact created by scripts/train.py")
    parser.add_argument("--data-path", help="CSV used for training; defaults to the path recorded in the ar
tifact")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()
    report = evaluate(args.model, args.data_path)
    rendered = json.dumps(report, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
if __name__ == "__main__":
    main()
