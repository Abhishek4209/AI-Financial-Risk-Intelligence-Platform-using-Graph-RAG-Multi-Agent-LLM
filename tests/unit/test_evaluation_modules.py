from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


def _load_module(name: str):
    source = Path(__file__).parents[2] / "src" / "evaluation" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"coverage_tests_{name}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


benchmark = _load_module("benchmark")
ragas_eval = _load_module("ragas_eval")


def test_benchmark_artifact_metrics_and_validation(monkeypatch, tmp_path):
    data_path = tmp_path / "holdout.csv"
    pd.DataFrame(
        {
            "feature": list(range(20)),
            "target": [0, 1] * 10,
        }
    ).to_csv(data_path, index=False)

    class Model:
        def predict_proba(self, frame):
            scores = frame["feature"].to_numpy() / 20
            return np.column_stack([1 - scores, scores])

    artifact = {
        "model": Model(),
        "data_path": str(data_path),
        "target_column": "target",
        "feature_columns": ["feature"],
        "threshold": 0.3,
        "test_size": 0.4,
        "random_state": 3,
        "dataset": "synthetic",
        "model_name": "fake-model",
    }
    monkeypatch.setattr(benchmark.joblib, "load", lambda path: artifact)
    result = benchmark.benchmark_artifact("model.joblib")
    assert result["dataset"] == "synthetic"
    assert result["model_name"] == "fake-model"
    assert 0 <= result["roc_auc"] <= 1
    assert 0 <= result["pr_auc"] <= 1
    assert 0 <= result["precision"] <= 1
    assert 0 <= result["recall"] <= 1
    assert 0 <= result["f1"] <= 1
    assert len(benchmark.benchmark_artifacts(["one", "two"])) == 2
    monkeypatch.setattr(benchmark.joblib, "load", lambda path: [])
    with pytest.raises(ValueError, match="expected"):
        benchmark._load_artifact("invalid.joblib")


def test_ragas_evaluation_supports_optional_ground_truth_and_missing_packages(monkeypatch):
    calls = []

    class Dataset:
        @classmethod
        def from_dict(cls, data):
            calls.append(("dataset", data))
            return data

    metric_names = {
        name: object()
        for name in (
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "faithfulness",
        )
    }
    datasets_module = types.ModuleType("datasets")
    datasets_module.Dataset = Dataset
    ragas_module = types.ModuleType("ragas")
    ragas_module.evaluate = lambda dataset, metrics: (
        calls.append(("evaluate", dataset, metrics))
        or {"faithfulness": 0.9}
    )
    metrics_module = types.ModuleType("ragas.metrics")
    for name, value in metric_names.items():
        setattr(metrics_module, name, value)
    monkeypatch.setitem(sys.modules, "datasets", datasets_module)
    monkeypatch.setitem(sys.modules, "ragas", ragas_module)
    monkeypatch.setitem(sys.modules, "ragas.metrics", metrics_module)

    basic = ragas_eval.evaluate_with_ragas(["q"], ["a"], [["context"]])
    assert basic == {"faithfulness": 0.9}
    assert len(calls[-1][2]) == 3
    extended = ragas_eval.evaluate_with_ragas(
        ["q"], ["a"], [["context"]], ["truth"]
    )
    assert calls[-2][1]["ground_truth"] == ["truth"]
    assert len(calls[-1][2]) == 4
    assert extended == {"faithfulness": 0.9}

    monkeypatch.setitem(sys.modules, "datasets", None)
    with pytest.raises(RuntimeError, match="Install"):
        ragas_eval.evaluate_with_ragas(["q"], ["a"], [["context"]])
