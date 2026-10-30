
"""End-to-end PaySim fraud investigation with SHAP, Pinecone, and Ollama."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests


DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "models"
    / "Fraud_models"
    / "paysim_fraud_model.pkl"
)
DEFAULT_DOCUMENTS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "raw" / "Documents"
)
DEFAULT_VECTOR_STORE_PATH = (
    Path(__file__).resolve().parents[2]
    / "vector_store"
    / "financial_rag_faiss"
)

RAW_TRANSACTION_FIELDS = (
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
)

TRANSACTION_TYPES = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER")


def load_model_artifact(
    path: str | Path = DEFAULT_MODEL_PATH,
) -> Mapping[str, Any]:
    """Load the trusted PaySim artifact exported by its training notebook."""
    with Path(path).open("rb") as artifact_file:
        artifact = pickle.load(artifact_file)

    if not isinstance(artifact, Mapping) or not {
        "model",
        "feature_columns",
    } <= artifact.keys():
        raise ValueError(
            "Model artifact must contain 'model' and 'feature_columns'."
        )

    return artifact


def build_feature_frame(
    transaction: Mapping[str, Any],
    feature_columns: Sequence[str],
) -> pd.DataFrame:
    """Recreate the feature engineering used to train the saved PaySim model."""
    missing_fields = [
        field for field in RAW_TRANSACTION_FIELDS if field not in transaction
    ]
    if missing_fields:
        raise ValueError(
            f"Missing required PaySim fields: {', '.join(missing_fields)}"
        )

    transaction_type = str(transaction["type"]).upper()
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError(
            f"Unsupported transaction type {transaction_type!r}; expected one of "
            f"{', '.join(TRANSACTION_TYPES)}."
        )

    step = float(transaction["step"])
    amount = float(transaction["amount"])
    old_origin = float(transaction["oldbalanceOrg"])
    new_origin = float(transaction["newbalanceOrig"])
    old_destination = float(transaction["oldbalanceDest"])
    new_destination = float(transaction["newbalanceDest"])

    numeric_values = (
        step,
        amount,
        old_origin,
        new_origin,
        old_destination,
        new_destination,
    )

    if not all(np.isfinite(value) for value in numeric_values):
        raise ValueError("PaySim numeric fields must be finite numbers.")

    if step < 0 or any(value < 0 for value in numeric_values[1:]):
        raise ValueError("Step, amount, and balance fields must be non-negative.")

    if not step.is_integer():
        raise ValueError("PaySim step must be an integer.")

    values: dict[str, float | int] = {
        "step": step,
        "hour": step % 24,
        "day": step // 24,
        "amount": amount,
        "oldbalanceOrg": old_origin,
        "newbalanceOrig": new_origin,
        "oldbalanceDest": old_destination,
        "newbalanceDest": new_destination,
        "origin_balance_error": abs(old_origin - amount - new_origin),
        "destination_balance_error": abs(
            old_destination + amount - new_destination
        ),
        "origin_zero_after": int(new_origin == 0),
        "destination_zero_before": int(old_destination == 0),
        "amount_to_origin_balance": (
            amount / old_origin if old_origin > 0 else 0
        ),
    }

    values.update(
        {
            f"type_{kind}": int(transaction_type == kind)
            for kind in TRANSACTION_TYPES
        }
    )

    unknown_features = [
        column for column in feature_columns if column not in values
    ]
    if unknown_features:
        raise ValueError(
            "The artifact requests unsupported PaySim features: "
            + ", ".join(unknown_features)
        )

    return pd.DataFrame(
        [[values[column] for column in feature_columns]],
        columns=list(feature_columns),
        dtype="float32",
    )


def explain_with_shap(
    model: Any,
    features: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Return the largest positive and negative SHAP drivers for the fraud class."""
    try:
        import shap
    except ImportError as exc:
        raise RuntimeError(
            "Install the 'shap' package to explain fraud predictions."
        ) from exc

    explanation = shap.TreeExplainer(model)(features)
    values = getattr(explanation, "values", explanation)

    if isinstance(values, list):
        values = values[1] if len(values) > 1 else values[0]

    shap_values = np.asarray(values)

    if shap_values.ndim == 3:
        shap_values = shap_values[
            :, :, 1 if shap_values.shape[2] > 1 else 0
        ]

    if shap_values.ndim == 2:
        shap_values = shap_values[0]

    if shap_values.ndim != 1 or len(shap_values) != len(features.columns):
        raise ValueError("SHAP returned values that do not match the model features.")

    drivers = [
        {
            "feature": column,
            "feature_value": float(features.iloc[0][column]),
            "shap_value": float(contribution),
            "direction": "increases" if contribution >= 0 else "decreases",
        }
        for column, contribution in zip(features.columns, shap_values)
    ]

    positive = sorted(
        (item for item in drivers if item["shap_value"] > 0),
        key=lambda item: item["shap_value"],
        reverse=True,
    )[:3]

    negative = sorted(
        (item for item in drivers if item["shap_value"] < 0),
        key=lambda item: item["shap_value"],
    )[:3]

    return positive + negative


@lru_cache(maxsize=1)
def _build_embeddings() -> Any:
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:
        raise RuntimeError(
            "Install langchain-huggingface to create vector embeddings."
        ) from exc

    return HuggingFaceEmbeddings(
        model_name=os.getenv(
            "RAG_EMBEDDING_MODEL",
            "BAAI/bge-small-en-v1.5",
        ),
        model_kwargs={"device": os.getenv("EMBEDDING_DEVICE", "cpu")},
        encode_kwargs={"normalize_embeddings": True},
    )


def index_regulatory_documents(
    documents_dir: str | Path = DEFAULT_DOCUMENTS_PATH,
) -> dict[str, int]:
    """Chunk local PDF/HTML guidance into FAISS or an existing Pinecone index."""
    backend = os.getenv("RAG_VECTOR_BACKEND", "faiss").lower()

    try:
        from bs4 import BeautifulSoup
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:
        raise RuntimeError(
            "Install langchain-community and langchain-text-splitters "
            "to index documents."
        ) from exc

    root = Path(documents_dir)
    configured_organizations = os.getenv(
    "RAG_DOCUMENT_ORGANIZATIONS",
    "FATF,RBI,SEBI,American_Express",
    )
    

    allowed_organizations = {
        organization.strip().casefold()
        for organization in configured_organizations.split(",")
        if organization.strip()
    }
    include_all_organizations = "all" in allowed_organizations
    loaded_documents = []

    for path in sorted(root.rglob("*")):
        suffix = path.suffix.lower()

        if not path.is_file() or suffix not in {".pdf", ".html", ".htm"}:
            continue

        relative_path = path.relative_to(root)
        organization = (
            relative_path.parts[0]
            if len(relative_path.parts) > 1
            else "Unknown"
        )

        if (
            not include_all_organizations
            and organization.casefold() not in allowed_organizations
        ):
            continue

        print(f"Loading {organization} source: {path.name}", flush=True)

        if suffix == ".pdf":
            file_documents = PyPDFLoader(str(path)).load()
        else:
            soup = BeautifulSoup(
                path.read_bytes(),
                features="html.parser",
            )
            file_documents = [
                Document(
                    page_content=soup.get_text(separator="\n"),
                    metadata={},
                )
            ]

        for document in file_documents:
            document.metadata.update(
                {
                    "source_file": path.name,
                    "file_path": str(path),
                    "organization": organization,
                }
            )

        loaded_documents.extend(file_documents)
        print(
            f"Loaded {len(loaded_documents)} pages/documents so far.",
            flush=True,
        )

    if not loaded_documents:
        raise ValueError(f"No PDF or HTML documents found under {root}.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(loaded_documents)

    print(f"Creating {backend} index for {len(chunks)} chunks.", flush=True)

    if backend == "faiss":
        from langchain_community.vectorstores import FAISS

        vector_store = FAISS.from_documents(chunks, _build_embeddings())
        print("Embeddings created; saving FAISS index.", flush=True)
        vector_store.save_local(
            os.getenv(
                "LOCAL_VECTOR_STORE_PATH",
                str(DEFAULT_VECTOR_STORE_PATH),
            )
        )

    elif backend == "pinecone":
        index_name = os.getenv("PINECONE_INDEX_NAME")

        if not os.getenv("PINECONE_API_KEY") or not index_name:
            raise RuntimeError(
                "Set PINECONE_API_KEY and PINECONE_INDEX_NAME "
                "to index with Pinecone."
            )

        try:
            from langchain_pinecone import PineconeVectorStore
        except ImportError as exc:
            raise RuntimeError(
                "Install langchain-pinecone to use Pinecone."
            ) from exc

        vector_store = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=_build_embeddings(),
        )

        chunk_ids = [
            hashlib.sha256(
                (
                    f"{chunk.metadata.get('file_path')}|"
                    f"{chunk.metadata.get('page')}|"
                    f"{chunk.page_content}"
                ).encode("utf-8")
            ).hexdigest()
            for chunk in chunks
        ]

        vector_store.add_documents(chunks, ids=chunk_ids)

    else:
        raise ValueError(
            "RAG_VECTOR_BACKEND must be 'faiss' or 'pinecone'."
        )

    return {"documents": len(loaded_documents), "chunks": len(chunks)}


def retrieve_local_faiss_evidence(
    query: str,
    top_k: int = 5,
) -> list[Any]:
    """Retrieve chunks from the project's local FAISS index, creating it if needed."""
    from langchain_community.vectorstores import FAISS

    vector_store_path = Path(
        os.getenv(
            "LOCAL_VECTOR_STORE_PATH",
            str(DEFAULT_VECTOR_STORE_PATH),
        )
    )

    if not (vector_store_path / "index.faiss").exists():
        index_regulatory_documents()

    vector_store = FAISS.load_local(
        str(vector_store_path),
        _build_embeddings(),
        allow_dangerous_deserialization=True,
    )

    return vector_store.similarity_search(query, k=top_k)


def retrieve_pinecone_evidence(
    query: str,
    top_k: int = 5,
) -> list[Any]:
    """Retrieve regulatory chunks from an already-populated Pinecone index."""
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if not api_key or not index_name:
        raise RuntimeError(
            "Set PINECONE_API_KEY and PINECONE_INDEX_NAME to enable retrieval."
        )

    try:
        from langchain_pinecone import PineconeVectorStore
    except ImportError as exc:
        raise RuntimeError(
            "Install langchain-pinecone to enable retrieval."
        ) from exc

    vector_store = PineconeVectorStore.from_existing_index(
        index_name=index_name,
        embedding=_build_embeddings(),
    )

    return vector_store.similarity_search(query, k=top_k)


def retrieve_regulatory_evidence(
    query: str,
    top_k: int = 5,
) -> list[Any]:
    """Use the configured local or hosted vector database backend."""
    backend = os.getenv("RAG_VECTOR_BACKEND", "faiss").lower()

    if backend == "faiss":
        return retrieve_local_faiss_evidence(query, top_k)

    if backend == "pinecone":
        return retrieve_pinecone_evidence(query, top_k)

    raise ValueError(
        "RAG_VECTOR_BACKEND must be 'faiss' or 'pinecone'."
    )


def _format_evidence(
    documents: Sequence[Any],
) -> list[dict[str, Any]]:
    evidence = []

    for document in documents:
        if isinstance(document, Mapping):
            text = str(
                document.get("page_content", document.get("text", ""))
            )
            metadata = document.get("metadata", {})
        else:
            text = str(getattr(document, "page_content", ""))
            metadata = getattr(document, "metadata", {})

        page = metadata.get("page")
        if isinstance(page, int):
            page += 1

        evidence.append(
            {
                "source": (
                    metadata.get("source_file")
                    or metadata.get("source")
                    or metadata.get("file_path")
                    or "Unknown source"
                ),
                "organization": metadata.get("organization"),
                "page": page,
                "text": text[:2000],
            }
        )

    return evidence


def _json_compatible(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, Mapping):
        return {
            str(key): _json_compatible(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]

    return value


def build_regulatory_query(
    transaction: Mapping[str, Any],
    risk_score: float,
    drivers: Sequence[Mapping[str, Any]],
) -> str:
    reason_names = ", ".join(
        item["feature"] for item in drivers[:5]
    ) or "no dominant SHAP drivers"

    return (
        f"PaySim transaction type {transaction['type']} has model fraud risk score "
        f"{risk_score:.4f}. Model factors: {reason_names}. Retrieve applicable fraud "
        "monitoring, AML/KYC, investigation, and reporting guidance for analyst review."
    )


def generate_ollama_report(context: Mapping[str, Any]) -> str:
    """Generate a local analyst-support summary grounded in supplied evidence."""
    base_url = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434",
    ).rstrip("/")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.1")

    response = requests.post(
        f"{base_url}/api/chat",
        json={
            "model": model_name,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a financial risk analyst assistant. Treat the model output as a "
                        "risk signal, never proof of fraud. Explain only the supplied SHAP factors. "
                        "Use regulatory evidence only when it is present; do not invent rules or "
                        "citations. State when retrieved evidence is insufficient. Recommend human "
                        "review rather than an automated adverse decision."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        _json_compatible(context),
                        ensure_ascii=True,
                    ),
                },
            ],
        },
        timeout=120,
    )

    response.raise_for_status()
    body = response.json()

    try:
        return str(body["message"]["content"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            "Ollama returned an unexpected chat response."
        ) from exc


def generate_huggingface_report(
    context: Mapping[str, Any],
) -> str:
    """Generate a local report with the Hugging Face pipeline used by the RAG notebook."""
    try:
        tokenizer, model = _load_huggingface_seq2seq_model(
            os.getenv("HF_REPORT_MODEL", "google/flan-t5-small")
        )
    except ImportError as exc:
        raise RuntimeError(
            "Install transformers to use local Hugging Face generation."
        ) from exc

    transaction = _json_compatible(context.get("transaction", {}))
    model_details = context.get("model", {})

    prompt_lines = [
        "Write a short analyst interpretation in plain English, not JSON. Treat the model "
        "score as a risk signal, not proof. Do not invent facts or rules. Recommend human review.",
        f"Transaction type: {transaction.get('type')}; amount: {transaction.get('amount')}",
        f"Risk level: {model_details.get('risk_level')}; fraud score: "
        f"{model_details.get('fraud_risk_score')}; threshold: {model_details.get('threshold')}",
        "Top model factors:",
    ]

    prompt_lines.extend(
        f"- {item['feature']}: {item['direction']} risk, "
        f"SHAP {item['shap_value']:+.3f}"
        for item in list(context.get("shap_drivers", []))[:4]
    )

    prompt_lines.append("Regulatory evidence:")

    for item in list(context.get("regulatory_evidence", []))[:2]:
        source = item.get("source", "Unknown source")
        organization = item.get("organization")

        if organization:
            source = f"{organization}: {source}"

        prompt_lines.append(
            f"- {source}: {str(item.get('text', ''))[:350]}"
        )

    prompt_lines.append("Interpret these facts in 2 concise sentences:")
    prompt = "\n".join(prompt_lines)

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    generated_tokens = model.generate(
        **inputs,
        max_new_tokens=180,
        do_sample=False,
    )

    return str(
        tokenizer.decode(
            generated_tokens[0],
            skip_special_tokens=True,
        )
    )


@lru_cache(maxsize=2)
def _load_huggingface_seq2seq_model(
    model_name: str,
) -> tuple[Any, Any]:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model.eval()

    return tokenizer, model


def _usable_generated_summary(summary: str) -> str | None:
    cleaned = summary.strip()
    lowered = cleaned.lower()

    invalid_markers = (
        '"feature":',
        '"shap_value":',
        '"direction":',
        "{",
        "}",
        "regulatory evidence:",
        "top model factors:",
    )

    if len(cleaned) < 15 or len(cleaned) > 400 or any(
        marker in lowered for marker in invalid_markers
    ):
        return None

    return cleaned


def _render_investigation_report(
    context: Mapping[str, Any],
    generated_summary: str | None,
) -> str:
    transaction = context["transaction"]
    model = context["model"]

    lines = [
        "## Transaction Investigation Summary",
        "",
        f"- Transaction: {transaction.get('transaction_id', 'Not provided')}",
        f"- Type: {transaction['type']} | Amount: {float(transaction['amount']):,.2f}",
        f"- Model risk signal: {model['risk_level']}",
        f"- Fraud score: {model['fraud_risk_score']:.6f} | "
        f"Model threshold: {model['threshold']:.6f}",
        "",
        "### Top Model Factors",
    ]

    drivers = list(context.get("shap_drivers", []))

    if drivers:
        lines.extend(
            f"- {item['feature'].replace('_', ' ')} = "
            f"{item['feature_value']:.4f}: {item['direction']} the model score "
            f"(SHAP {item['shap_value']:+.4f})"
            for item in drivers
        )
    else:
        lines.append("- No SHAP factors were returned.")

    lines.extend(["", "### Retrieved Evidence"])
    evidence = list(context.get("regulatory_evidence", []))[:5]

    if evidence:
        for item in evidence:
            source = item["source"]

            if item.get("page") is not None:
                source += f", page {item['page']}"

            if item.get("organization"):
                source = f"{item['organization']}: {source}"

            excerpt = " ".join(str(item.get("text", "")).split())[:450]
            lines.extend([f"- **{source}**", f"  {excerpt}"])
    else:
        lines.append(
            "- No regulatory evidence was retrieved; evidence is insufficient."
        )

    lines.extend(["", "### Analyst Interpretation"])

    if generated_summary:
        lines.append(generated_summary)
    elif model["risk_level"] == "HIGH":
        lines.append(
            "The model score is at or above its stored threshold and warrants analyst review. "
            "Retrieved guidance provides context; it does not confirm fraud."
        )
    else:
        lines.append(
            "The model score is below its stored threshold. This is not proof that the "
            "transaction is legitimate; review the transaction and retrieved guidance in context."
        )

    lines.extend(
        [
            "",
            "> The fraud score is a model risk signal, not proof of fraud. Apply relevant "
            "policies and human review before making decisions.",
        ]
    )

    return "\n".join(lines)


def investigate_transaction(
    transaction: Mapping[str, Any],
    *,
    artifact: Mapping[str, Any] | None = None,
    documents: Sequence[Any] | None = None,
    explain: Callable[
        [Any, pd.DataFrame],
        list[dict[str, Any]],
    ] = explain_with_shap,
    retrieve: Callable[[str], Sequence[Any]] | None = None,
    generate_report: Callable[[Mapping[str, Any]], str] | None = None,
) -> dict[str, Any]:
    """Run PaySim inference -> SHAP -> regulatory evidence -> analyst report."""
    model_artifact = artifact if artifact is not None else load_model_artifact()
    model = model_artifact["model"]
    feature_columns = model_artifact["feature_columns"]

    features = build_feature_frame(transaction, feature_columns)
    probabilities = model.predict_proba(features)
    classes = list(getattr(model, "classes_", [0, 1]))

    try:
        fraud_class_index = classes.index(1)
    except ValueError as exc:
        raise ValueError(
            "Fraud model artifact does not contain class 1."
        ) from exc

    risk_score = float(probabilities[0][fraud_class_index])
    threshold = float(model_artifact.get("threshold", 0.5))
    risk_level = (
        "HIGH" if risk_score >= threshold else "BELOW_MODEL_THRESHOLD"
    )

    drivers = explain(model, features)
    query = build_regulatory_query(transaction, risk_score, drivers)
    retrieval_function = retrieve or retrieve_regulatory_evidence

    retrieved_documents = (
        list(documents)
        if documents is not None
        else list(retrieval_function(query))
    )
    evidence = _format_evidence(retrieved_documents)

    report_context = {
        "transaction": {
            field: transaction[field]
            for field in RAW_TRANSACTION_FIELDS
        },
        "model": {
            "name": "PaySim fraud detection model",
            "fraud_risk_score": risk_score,
            "threshold": threshold,
            "risk_level": risk_level,
            "interpretation": (
                "Model risk signal only; this does not establish fraud."
            ),
        },
        "shap_drivers": drivers,
        "regulatory_evidence": evidence,
    }

    if generate_report is None:
        provider = os.getenv(
            "RISK_REPORT_PROVIDER",
            "huggingface",
        ).lower()

        if provider == "huggingface":
            report_generator = generate_huggingface_report
        elif provider == "ollama":
            report_generator = generate_ollama_report
        else:
            raise ValueError(
                "RISK_REPORT_PROVIDER must be 'huggingface' or 'ollama'."
            )
    else:
        report_generator = generate_report

    report_generation_warning = None

    try:
        raw_summary = report_generator(report_context)
    except Exception as exc:
        raw_summary = ""
        report_generation_warning = (
            f"Report model unavailable: {type(exc).__name__}: {exc}"
        )

    report_summary = _usable_generated_summary(raw_summary)

    if (
        report_summary is None
        and raw_summary.strip()
        and report_generation_warning is None
    ):
        report_generation_warning = (
            "Local model output was not a usable analyst summary; "
            "used the structured fallback."
        )

    report = _render_investigation_report(
        report_context,
        report_summary,
    )

    return {
        "transaction_id": transaction.get("transaction_id"),
        "model": report_context["model"],
        "shap_drivers": drivers,
        "retrieval_query": query,
        "evidence": evidence,
        "report": report,
        "report_summary": report_summary,
        "report_generation_warning": report_generation_warning,
        "human_review_required": risk_level == "HIGH",
    }
