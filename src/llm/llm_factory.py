
"""LLM provider factory: OpenAI, local Hugging Face, or Ollama, matching the RAG notebook's fallback chain."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Callable


def get_llm(provider: str | None = None) -> Callable[[str], str]:
    """Return a `generate(prompt) -> str` callable for the configured provider."""
    selected = (provider or os.getenv("LLM_PROVIDER", "huggingface")).lower()

    if selected == "openai":
        return _openai_generate
    if selected == "ollama":
        return _ollama_generate
    if selected == "huggingface":
        return _huggingface_generate

    raise ValueError(
        "LLM_PROVIDER must be 'openai', 'ollama', or 'huggingface'"
    )


def _openai_generate(prompt: str) -> str:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Install langchain-openai to use the OpenAI provider"
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY to use the OpenAI provider")

    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4.1-mini"),
        temperature=0,
    )
    response = llm.invoke(prompt)
    return str(getattr(response, "content", response))


def _ollama_generate(prompt: str) -> str:
    import requests

    base_url = os.getenv(
        "OLLAMA_BASE_URL", "http://localhost:11434"
    ).rstrip("/")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.1")

    response = requests.post(
        "%s/api/chat" % base_url,
        json={
            "model": model_name,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()

    try:
        return str(body["message"]["content"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            "Ollama returned an unexpected chat response"
        ) from exc


@lru_cache(maxsize=2)
def _load_seq2seq_model(model_name: str) -> tuple[Any, Any]:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model.eval()

    return tokenizer, model


def _huggingface_generate(prompt: str) -> str:
    try:
        tokenizer, model = _load_seq2seq_model(
            os.getenv("HF_REPORT_MODEL", "google/flan-t5-small")
        )
    except ImportError as exc:
        raise RuntimeError(
            "Install transformers to use local Hugging Face generation"
        ) from exc

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    generated_tokens = model.generate(
        **inputs,
        max_new_tokens=200,
        do_sample=False,
    )

    return str(
        tokenizer.decode(
            generated_tokens[0],
            skip_special_tokens=True,
        )
    )
