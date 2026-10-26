"""Compare saved classifier artifacts on the same reproducible held-out split as scripts/evaluate.py."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import joblib
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
def _load_artifact(path: str | Path) -> dict[str, Any]:
    artifact = joblib.load(path)
    if not isinstance(artifact, dict) or "model" not in artifact:
        raise ValueError("Artifact does not contain the expected ’model’ entry: %s" % path)
    return artifact
def benchmark_artifact(path: str | Path, *, data_path: str | Path | None = None) -> dict[str, Any]:
    artifact = _load_artifact(path)
    csv_path = Path(data_path or artifact["data_path"])
    frame = pd.read_csv(csv_path, low_memory=False)
    target_column = artifact["target_column"]
    labels = frame[target_column]
    features = frame[artifact["feature_columns"]]
    _, x_test, _, y_test = train_test_split(
        features, labels, test_size=artifact.get("test_size", 0.2),
        random_state=artifact.get("random_state", 42), stratify=labels,
    )
    probabilities = artifact["model"].predict_proba(x_test)[:, 1]
    threshold = float(artifact.get("threshold", 0.5))
    predictions = (probabilities >= threshold).astype(int)
    return {
        "artifact": str(Path(path).resolve()),
        "dataset": artifact.get("dataset"),
        "model_name": artifact.get("model_name"),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
    }
def benchmark_artifacts(paths: list[str | Path]) -> pd.DataFrame:
    """Produce a comparison table across multiple domain-specific model artifacts."""
    rows = [benchmark_artifact(path) for path in paths]
    return pd.DataFrame(rows)
