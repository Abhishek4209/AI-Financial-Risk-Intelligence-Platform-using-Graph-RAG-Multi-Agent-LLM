"""Neo4j driver access for the optional Graph RAG layer."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any



@lru_cache(maxsize=1)
def get_neo4j_driver() -> Any:
        try:
                from neo4j import GraphDatabase
        except ImportError as exc:
                raise RuntimeError("Install the 'neo4j' package to use Graph RAG") from exc
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        if not uri or not password:
                raise RuntimeError("Set NEO4J_URI and NEO4J_PASSWORD to use Graph RAG")
        return GraphDatabase.driver(uri, auth=(user, password))



def run_query(query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Run a read or write Cypher query and return records as plain dicts."""
        driver = get_neo4j_driver()
        with driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]



def verify_connectivity() -> bool:
        try:
                get_neo4j_driver().verify_connectivity()
                return True
        except Exception:
                return False
