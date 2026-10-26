"""Optional RAGAS-backed evaluation; lazily imported so the core app has no hard dependency."""
from __future__ import annotations
from typing import Any
def evaluate_with_ragas(questions: list[str], answers: list[str], contexts: list[list[str]], ground_truths:
 list[str] | None = None) -> dict[str, Any]:
    """Compute faithfulness, answer relevancy, and context precision/recall via RAGAS."""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
    except ImportError as exc:
        raise RuntimeError("Install ’ragas’ and ’datasets’ to run RAGAS evaluation") from exc
    data: dict[str, Any] = {"question": questions, "answer": answers, "contexts": contexts}
    metrics = [faithfulness, answer_relevancy, context_precision]
    if ground_truths is not None:
        data["ground_truth"] = ground_truths
        metrics.append(context_recall)
    dataset = Dataset.from_dict(data)
    result = evaluate(dataset, metrics=metrics)
    return dict(result)
