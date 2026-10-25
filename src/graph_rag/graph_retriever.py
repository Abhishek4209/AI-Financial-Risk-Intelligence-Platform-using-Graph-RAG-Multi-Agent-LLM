"""Combine graph evidence with vector retrieval for relationship-aware RAG."""

from __future__ import annotations

from typing import Any

from src.graph_rag.graph_query import fan_in_transactions, fan_out_transactions, find_connected_customers
from src.vectordb import search as vector_search



def retrieve_graph_evidence(customer_id: str, account_id: str | None = None) -> dict[str, Any]:
        """Gather relationship evidence; flags patterns for investigation, not conclusions."""
        evidence: dict[str, Any] = {
                "connected_customers": find_connected_customers(customer_id),
        }
        if account_id:
                evidence["fan_out"] = fan_out_transactions(account_id)
                evidence["fan_in"] = fan_in_transactions(account_id)
        return evidence



def retrieve_hybrid_evidence(query: str, customer_id: str, *, account_id: str | None = None, top_k: int = 5) ->
dict[str, Any]:
        """Return vector-retrieved document chunks alongside graph relationship evidence."""
        return {
                "documents": vector_search(query, top_k=top_k),
                "graph": retrieve_graph_evidence(customer_id, account_id),
        }
