"""Bolt adapter for Neo4j and Memgraph.

Same Cypher statements. Different defaults.
"""

from __future__ import annotations

import os
from typing import Any


DEFAULTS = {
    "neo4j": {"uri": "bolt://localhost:7687", "user": "neo4j", "password": "password"},
    "memgraph": {"uri": "bolt://localhost:7687", "user": "", "password": ""},
}


class BoltStore:
    def __init__(self, vendor: str = "neo4j", uri: str | None = None, user: str | None = None, password: str | None = None):
        vendor = (vendor or "neo4j").lower()
        if vendor not in DEFAULTS:
            raise ValueError("vendor must be neo4j or memgraph")
        base = DEFAULTS[vendor]
        self.vendor = vendor
        self.uri = uri or os.environ.get("GRAPHLang_BOLT_URI") or os.environ.get("NEO4J_URI") or base["uri"]
        self.user = user if user is not None else os.environ.get("NEO4J_USER", base["user"])
        self.password = password if password is not None else os.environ.get("NEO4J_PASSWORD", base["password"])
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("pip install neo4j  # official Bolt driver works for Neo4j and Memgraph") from exc
        auth = (self.user, self.password) if self.user else None
        self._driver = GraphDatabase.driver(self.uri, auth=auth)

    def close(self) -> None:
        self._driver.close()

    def run_statements(self, statements: list[dict[str, Any]]) -> list[Any]:
        results = []
        with self._driver.session() as session:
            for stmt in statements:
                cypher = stmt.get("cypher")
                if not cypher:
                    results.append({"skipped": stmt.get("action")})
                    continue
                # Memgraph rejects some Neo4j constraint IF NOT EXISTS variants;
                # still try, record the error, keep going.
                try:
                    records = session.run(cypher, stmt.get("params") or {})
                    results.append([r.data() for r in records])
                except Exception as exc:
                    results.append({"action": stmt.get("action"), "error": str(exc)})
        return results

    def ping(self) -> dict[str, Any]:
        with self._driver.session() as session:
            row = session.run("RETURN 1 AS ok").single()
        return {"vendor": self.vendor, "uri": self.uri, "ok": bool(row and row["ok"] == 1)}


# Back-compat name used by runtime.
class Neo4jGraph(BoltStore):
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None, vendor: str = "neo4j"):
        super().__init__(vendor=vendor, uri=uri, user=user, password=password)
