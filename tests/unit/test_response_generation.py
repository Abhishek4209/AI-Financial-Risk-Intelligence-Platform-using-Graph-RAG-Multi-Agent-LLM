from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from src.llm import llm_factory, prompt_templates, response_generator


def _install_module(monkeypatch, name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def _doc(text, **metadata):
    return SimpleNamespace(page_content=text, metadata=metadata)


def test_response_formatting_keyword_and_support_helpers():
    docs = [
        _doc("  Fraud controls monitor suspicious transactions.  ", source_file="RBI.pdf", page=2),
        _doc("   ", source="empty.pdf"),
        _doc("Credit lending controls reduce borrower defaults.", source="credit.pdf"),
    ]
    context = response_generator.format_context(docs, max_chars_per_doc=100)
    assert "[Evidence 1 | Source: RBI.pdf, page 2]" in context
    assert "Fraud controls monitor suspicious transactions." in context
    assert "Evidence 3 | Source: credit.pdf" in context
    assert response_generator.format_context([]) == ""
    with pytest.raises(ValueError, match="at least 1"):
        response_generator.format_context(docs, max_chars_per_doc=0)
    assert response_generator._available_sources(docs) == [
        "RBI.pdf, page 2",
        "empty.pdf",
        "credit.pdf",
    ]
    assert response_generator._document_source(
        _doc(
            "section content",
            source_file="report.pdf",
            section="Cybersecurity",
            page=55,
            page_label="56",
        )
    ) == "report.pdf, section Cybersecurity, page 56"
    assert response_generator._keywords("Fraud, controls and RBI policies!") == {
        "fraud", "control", "rbi", "policie"
    }
    assert response_generator._is_classification_question("List categories of fraud")
    assert not response_generator._is_classification_question("Explain this")
    assert response_generator._is_incomplete_answer("")
    assert response_generator._is_incomplete_answer("By using the controls")
    assert response_generator._is_incomplete_answer("Controls and")
    assert not response_generator._is_incomplete_answer("Controls reduce losses.")
    assert response_generator._answer_supported_by_evidence(
        "Fraud controls monitor transactions",
        [_doc("Fraud controls monitor suspicious transactions.")],
    )
    assert not response_generator._answer_supported_by_evidence(
        "Fraud", [_doc("unrelated")]
    )
    assert response_generator._extract_evidence_fallback(
        "What categories of fraud prevention are described?",
        [
            _doc(
                "The fraud program is\n"
                "divided into prevention and monitoring categories. "
                "Both categories address suspicious transactions."
            )
        ],
    ).startswith("The fraud program is divided into")
    assert response_generator._extract_evidence_fallback("the and of", docs) is None
    assert response_generator._attach_missing_citations(
        "Grounded answer.", ["RBI.pdf"]
    ).endswith("- RBI.pdf")
    assert response_generator._attach_missing_citations(
        "See [Source 1].", ["RBI.pdf"]
    ) == "See [Source 1]."
    assert response_generator._attach_missing_citations("", ["RBI.pdf"]) == ""


def test_generate_answer_returns_not_found_or_empty_text_results():
    assert response_generator.generate_answer("question", []) == {
        "answer": "The information was not found in the available retrieved sources.",
        "sources": [],
        "grounded": False,
    }
    empty_text = response_generator.generate_answer(
        "question", [_doc("  ", source_file="empty.pdf")]
    )
    assert empty_text["grounded"] is False
    assert "usable text" in empty_text["answer"]
    assert empty_text["sources"] == ["empty.pdf"]


def test_generate_answer_accepts_supported_llm_result_and_adds_citation(monkeypatch):
    calls = []
    answer = "Fraud controls monitor suspicious transactions and reduce losses."
    monkeypatch.setattr(
        response_generator,
        "get_llm",
        lambda provider: lambda prompt: calls.append((provider, prompt)) or answer,
    )
    docs = [
        _doc(
            "Fraud controls monitor suspicious transactions and reduce losses.",
            source_file="RBI_guidance.pdf",
            page=5,
        )
    ]
    result = response_generator.generate_answer("How do fraud controls reduce losses?", docs, provider="local")
    assert result["grounded"] is True
    assert result["answer_method"] == "llm"
    assert result["sources"] == ["RBI_guidance.pdf, page 5"]
    assert result["answer"].endswith("- RBI_guidance.pdf, page 5")
    assert len(calls) == 1
    assert "Question: How do fraud controls reduce losses?" in calls[0][1]


def test_generate_answer_retries_then_uses_grounded_classification_fallback(monkeypatch):
    calls = []
    replies = iter(["unusable", "still fragmentary"])

    def generate(prompt):
        calls.append(prompt)
        return next(replies)

    monkeypatch.setattr(response_generator, "get_llm", lambda provider: generate)
    docs = [
        _doc(
            "Fraud controls are divided into prevention and monitoring categories. "
            "These practices reduce suspicious transaction losses.",
            source_file="policy.pdf",
        )
    ]
    result = response_generator.generate_answer("What categories of fraud controls are used?", docs)
    assert len(calls) == 2
    assert "Answer the question using only the evidence" in calls[1]
    assert result["answer_method"] == "evidence_extraction"
    assert "divided into prevention and monitoring categories" in result["answer"]
    assert result["answer"].endswith("- policy.pdf")


def test_generate_answer_reports_generation_errors_without_relevant_fallback(monkeypatch):
    monkeypatch.setattr(
        response_generator,
        "get_llm",
        lambda provider: (_ for _ in ()).throw(RuntimeError("model unavailable")),
    )
    result = response_generator.generate_answer(
        "What does this liquidity rule require?",
        [_doc("A general paragraph with no matching policy terms.", source="document.pdf")],
    )
    assert result["grounded"] is False
    assert result["error"] == "RuntimeError: model unavailable"
    assert "no sufficiently relevant complete sentence" in result["answer"]


def test_generate_answer_uses_extracted_sentence_after_bad_output(monkeypatch):
    responses = iter(["fragmentary", "unsupported claim"])
    monkeypatch.setattr(
        response_generator,
        "get_llm",
        lambda provider: lambda prompt: next(responses),
    )
    answer = response_generator.generate_answer(
        "How are liquidity risks managed?",
        [
            _doc(
                "Liquidity risks are managed through regular cash flow monitoring and funding controls.",
                source="risk.pdf",
            )
        ],
    )
    assert answer["answer_method"] == "evidence_extraction"
    assert "Liquidity risks are managed" in answer["answer"]


def test_llm_provider_factory_and_openai_ollama_huggingface(monkeypatch):
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        llm_factory.get_llm("other")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm_factory._openai_generate("prompt")

    openai_calls = []
    _install_module(
        monkeypatch,
        "langchain_openai",
        ChatOpenAI=lambda **kwargs: SimpleNamespace(
            invoke=lambda prompt: openai_calls.append((kwargs, prompt))
            or SimpleNamespace(content="answer")
        ),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    assert llm_factory.get_llm("OPENAI")("prompt") == "answer"
    assert openai_calls[0][0] == {"model": "test-model", "temperature": 0}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "local answer"}}

    post_calls = []
    _install_module(
        monkeypatch,
        "requests",
        post=lambda url, **kwargs: post_calls.append((url, kwargs)) or Response(),
    )
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test/")
    monkeypatch.setenv("OLLAMA_MODEL", "tiny")
    assert llm_factory.get_llm("ollama")("question") == "local answer"
    assert post_calls[0][0] == "http://ollama.test/api/chat"

    class BadResponse(Response):
        def json(self):
            return {}

    _install_module(
        monkeypatch,
        "requests",
        post=lambda *args, **kwargs: BadResponse(),
    )
    with pytest.raises(RuntimeError, match="unexpected chat response"):
        llm_factory._ollama_generate("question")

    class Tokenizer:
        @classmethod
        def from_pretrained(cls, name):
            return cls()

        def __call__(self, prompt, **kwargs):
            return {"input_ids": [1]}

        def decode(self, tokens, **kwargs):
            return " generated answer "

    class Model:
        def __init__(self):
            self.evaluated = False

        @classmethod
        def from_pretrained(cls, name):
            return cls()

        def eval(self):
            self.evaluated = True

        def generate(self, **kwargs):
            return [[1]]

    model_module = types.ModuleType("transformers")
    model_module.AutoTokenizer = Tokenizer
    model_module.AutoModelForSeq2SeqLM = Model
    monkeypatch.setitem(sys.modules, "transformers", model_module)
    llm_factory._load_seq2seq_model.cache_clear()
    try:
        assert llm_factory.get_llm("huggingface")("prompt") == "generated answer"
        assert llm_factory._load_seq2seq_model("test-model")[1].evaluated
    finally:
        llm_factory._load_seq2seq_model.cache_clear()


def test_prompt_templates_supply_safe_defaults():
    rag = prompt_templates.render_rag_prompt("question", "")
    assert "No evidence was retrieved" in rag
    assert "only the supplied evidence" in rag
    fraud = prompt_templates.render_fraud_prompt(
        "TRANSFER", 100, 0.8, "HIGH", "", ""
    )
    assert "No SHAP factors available" in fraud
    assert "No regulatory evidence retrieved" in fraud
    credit = prompt_templates.render_credit_prompt(
        "taiwan", 0.2, "LOW", "age increases risk"
    )
    assert "Applicant dataset: taiwan" in credit
