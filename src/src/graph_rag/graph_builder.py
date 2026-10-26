"""Build the Customer -> Account -> Transaction -> Document graph described in architecture.md."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from src.graph_rag.neo4j_loader import run_query
CONSTRAINTS = (
    "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
)
def ensure_constraints() -> None:
    for statement in CONSTRAINTS:
        run_query(statement)
def upsert_customer(customer_id: str, properties: Mapping[str, Any] | None = None) -> None:
    run_query(
        "MERGE (c:Customer {id: $id}) SET c += $properties",
        {"id": customer_id, "properties": dict(properties or {})},
    )
def upsert_account(account_id: str, customer_id: str, properties: Mapping[str, Any] | None = None) -> None
:
    run_query(
        "MATCH (c:Customer {id: $customer_id}) "
        "MERGE (a:Account {id: $account_id}) SET a += $properties "
        "MERGE (c)-[:OWNS]->(a)",
        {"customer_id": customer_id, "account_id": account_id, "properties": dict(properties or {})},
    )
def upsert_transaction(transaction_id: str, from_account_id: str, to_account_id: str | None, properties: Ma
pping[str, Any] | None = None) -> None:
    run_query(
        "MATCH (origin:Account {id: $from_account_id}) "
        "MERGE (t:Transaction {id: $transaction_id}) SET t += $properties "
        "MERGE (origin)-[:SENT]->(t)",
        {"from_account_id": from_account_id, "transaction_id": transaction_id, "properties": dict(propertie
s or {})},
    )
    if to_account_id:
        run_query(
            "MATCH (t:Transaction {id: $transaction_id}), (destination:Account {id: $to_account_id}) "
            "MERGE (t)-[:RECEIVED_BY]->(destination)",
            {"transaction_id": transaction_id, "to_account_id": to_account_id},
        )
def link_document_to_customer(document_id: str, customer_id: str, properties: Mapping[str, Any] | None = No
ne) -> None:
    run_query(
        "MATCH (c:Customer {id: $customer_id}) "
        "MERGE (d:Document {id: $document_id}) SET d += $properties "
        "MERGE (c)-[:HAS_DOCUMENT]->(d)",
        {"customer_id": customer_id, "document_id": document_id, "properties": dict(properties or {})},
    )
def build_transaction_graph(transactions: Sequence[Mapping[str, Any]]) -> int:
    """Load a batch of transactions into Neo4j; accounts/customers must already exist."""
    count = 0
    for transaction in transactions:
        upsert_transaction(
            str(transaction["transaction_id"]),
            str(transaction["from_account_id"]),
            str(transaction["to_account_id"]) if transaction.get("to_account_id") else None,
            {key: value for key, value in transaction.items() if key not in {"transaction_id", "from_accou
nt_id", "to_account_id"}},
        )
        count += 1
    return count
