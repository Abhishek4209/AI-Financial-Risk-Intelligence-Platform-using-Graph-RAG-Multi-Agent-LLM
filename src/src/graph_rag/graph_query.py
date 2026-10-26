"""Cypher queries for relationship-based risk investigation, per architecture.md."""
from __future__ import annotations
from typing import Any
from src.graph_rag.neo4j_loader import run_query
def find_connected_customers(customer_id: str, *, max_hops: int = 2) -> list[dict[str, Any]]:
    """Find customers reachable through shared accounts or transactions."""
    if max_hops < 1:
        raise ValueError("max_hops must be at least 1")
    return run_query(
        "MATCH (origin:Customer {id: $customer_id})-[*1..%d]-(other:Customer) "
        "WHERE other.id <> $customer_id "
        "RETURN DISTINCT other.id AS customer_id, other AS properties" % max_hops,
        {"customer_id": customer_id},
    )
def fan_out_transactions(account_id: str) -> list[dict[str, Any]]:
    """Count distinct recipients for an account; large fan-out can indicate layering."""
    return run_query(
        "MATCH (origin:Account {id: $account_id})-[:SENT]->(:Transaction)-[:RECEIVED_BY]->(destination:
Account) "
        "RETURN destination.id AS destination_account, count(*) AS transaction_count "
        "ORDER BY transaction_count DESC",
        {"account_id": account_id},
    )
def fan_in_transactions(account_id: str) -> list[dict[str, Any]]:
    """Count distinct senders to an account; large fan-in can indicate structuring."""
    return run_query(
        "MATCH (origin:Account)-[:SENT]->(:Transaction)-[:RECEIVED_BY]->(destination:Account {id: $acco
unt_id}) "
        "RETURN origin.id AS origin_account, count(*) AS transaction_count "
        "ORDER BY transaction_count DESC",
        {"account_id": account_id},
    )
def suspicious_transaction_chains(account_id: str, *, max_hops: int = 4) -> list[dict[str, Any]]:
    """Find multi-hop transaction chains starting from an account; flags for review, not proof of laundering
."""
    if max_hops < 2:
        raise ValueError("max_hops must be at least 2")
    return run_query(
        "MATCH path = (origin:Account {id: $account_id})-[:SENT|RECEIVED_BY*2..%d]->(destination:Account
) "
        "WHERE destination.id <> $account_id "
        "RETURN [node IN nodes(path) WHERE node:Account | node.id] AS account_chain, length(path) AS hop
s "
        "ORDER BY hops DESC LIMIT 25" % max_hops,
        {"account_id": account_id},
    )
def customer_documents(customer_id: str) -> list[dict[str, Any]]:
    return run_query(
        "MATCH (c:Customer {id: $customer_id})-[:HAS_DOCUMENT]->(d:Document) RETURN d AS document",
        {"customer_id": customer_id},
    )
