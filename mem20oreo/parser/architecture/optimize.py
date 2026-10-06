"""Cypher optimizer for GraphLang.

Goals:
- one write per intent-batch instead of many tiny MERGEs
- drop creates that a later MERGE already covers
- add uniqueness constraints / name indexes
- keep reads separate from writes
- leave parameters intact
"""

from __future__ import annotations

import hashlib
from typing import Any


SCHEMA_STATEMENTS = [
    {
        "action": "schema",
        "cypher": "CREATE CONSTRAINT page_id IF NOT EXISTS FOR (p:Page) REQUIRE p.id IS UNIQUE",
        "params": {},
    },
    {
        "action": "schema",
        "cypher": "CREATE CONSTRAINT database_id IF NOT EXISTS FOR (d:Database) REQUIRE d.id IS UNIQUE",
        "params": {},
    },
    {
        "action": "schema",
        "cypher": "CREATE CONSTRAINT auth_id IF NOT EXISTS FOR (a:Auth) REQUIRE a.id IS UNIQUE",
        "params": {},
    },
    {
        "action": "schema",
        "cypher": "CREATE CONSTRAINT include_id IF NOT EXISTS FOR (i:Include) REQUIRE i.id IS UNIQUE",
        "params": {},
    },
    {
        "action": "schema",
        "cypher": "CREATE INDEX page_name IF NOT EXISTS FOR (p:Page) ON (p.name)",
        "params": {},
    },
    {
        "action": "schema",
        "cypher": "CREATE INDEX database_name IF NOT EXISTS FOR (d:Database) ON (d.name)",
        "params": {},
    },
]


WRITE_ACTIONS = {
    "create_node",
    "connect",
    "connect_with_auth",
    "connect_all",
    "connect_all_with_auth",
    "include",
    "include_all",
    "disconnect",
    "disconnect_auth",
    "schema",
    "batch_create",
}


class CypherOptimizer:
    def __init__(self, include_schema: bool = True):
        self.include_schema = include_schema
        self._schema_emitted = False

    def optimize(self, statements: list[dict[str, Any]]) -> dict[str, Any]:
        original = [s for s in statements if s.get("cypher")]
        dropped: list[str] = []

        covered_ids = self._ids_covered_by_connect(original)
        kept: list[dict[str, Any]] = []
        creates: list[dict[str, Any]] = []

        for stmt in original:
            if stmt.get("action") == "create_node":
                node_id = (stmt.get("params") or {}).get("id")
                if node_id and node_id in covered_ids:
                    dropped.append(f"create_node {node_id} covered by later MERGE")
                    continue
                creates.append(stmt)
                continue
            if creates:
                kept.extend(self._batch_creates(creates))
                creates = []
            kept.append(self._normalize(stmt))
        if creates:
            kept.extend(self._batch_creates(creates))

        kept = self._dedupe(kept, dropped)
        prelude: list[dict[str, Any]] = []
        if self.include_schema and not self._schema_emitted and any(s.get("action") in WRITE_ACTIONS for s in kept):
            prelude = [self._normalize(s) for s in SCHEMA_STATEMENTS]
            self._schema_emitted = True

        optimized = prelude + kept
        write_original = len(original)
        write_optimized = len(kept)
        return {
            "original_count": write_original,
            "optimized_count": write_optimized,
            "schema_count": len(prelude),
            "dropped": dropped,
            "saved": max(write_original - write_optimized, 0),
            "statements": optimized,
            "script": self.to_script(optimized),
        }

    def to_script(self, statements: list[dict[str, Any]]) -> str:
        chunks = []
        for stmt in statements:
            cypher = stmt.get("cypher")
            if not cypher:
                continue
            params = stmt.get("params") or {}
            header = f"// {stmt.get('action')} {params}"
            chunks.append(header + "\n" + cypher)
        return "\n;\n\n".join(chunks) + ("\n;" if chunks else "")

    def _batch_creates(self, creates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(creates) == 1:
            return [self._normalize(creates[0])]

        by_label: dict[str, list[dict[str, Any]]] = {}
        for stmt in creates:
            params = stmt.get("params") or {}
            label = self._label_from_create(stmt)
            by_label.setdefault(label, []).append(params)

        batched = []
        for label, rows in by_label.items():
            if len(rows) == 1:
                batched.append(self._normalize(creates[[self._label_from_create(s) for s in creates].index(label)]))
                continue
            batched.append(
                {
                    "action": "batch_create",
                    "cypher": self._unwind_for(label),
                    "params": {"rows": rows},
                }
            )
        return batched

    def _unwind_for(self, label: str) -> str:
        if label == "Page":
            return (
                "UNWIND $rows AS n\n"
                "MERGE (p:Page {id: n.id})\n"
                "ON CREATE SET p.name = n.name, p.path = n.path, p.type = n.type, p.created_at = datetime()\n"
                "ON MATCH SET p.name = coalesce(n.name, p.name), p.path = coalesce(n.path, p.path)"
            )
        if label == "Database":
            return (
                "UNWIND $rows AS n\n"
                "MERGE (d:Database {id: n.id})\n"
                "ON CREATE SET d.name = n.name, d.engine = n.engine, d.host = n.host, d.port = n.port, d.created_at = datetime()\n"
                "ON MATCH SET d.name = coalesce(n.name, d.name), d.engine = coalesce(n.engine, d.engine)"
            )
        if label == "Auth":
            return (
                "UNWIND $rows AS n\n"
                "MERGE (a:Auth {id: n.id})\n"
                "ON CREATE SET a.name = n.name, a.method = n.method, a.level = n.level, "
                "a.requires_https = n.requires_https, a.created_at = datetime()"
            )
        return (
            "UNWIND $rows AS n\n"
            "MERGE (i:Include {id: n.id})\n"
            "ON CREATE SET i.name = n.name, i.path = n.path, i.created_at = datetime()\n"
            "ON MATCH SET i.name = coalesce(n.name, i.name)"
        )

    def _label_from_create(self, stmt: dict[str, Any]) -> str:
        cypher = stmt.get("cypher") or ""
        for label in ("Page", "Database", "Auth", "Include"):
            if f":{label}" in cypher:
                return label
        return "Include"

    def _ids_covered_by_connect(self, statements: list[dict[str, Any]]) -> set[str]:
        covered: set[str] = set()
        for stmt in statements:
            if stmt.get("action") not in {"connect", "connect_with_auth", "include"}:
                continue
            params = stmt.get("params") or {}
            for key in ("page_id", "db_id", "auth_id"):
                if params.get(key):
                    covered.add(params[key])
            for inc in params.get("includes") or []:
                if inc.get("id"):
                    covered.add(inc["id"])
        return covered

    def _dedupe(self, statements: list[dict[str, Any]], dropped: list[str]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for stmt in statements:
            fingerprint = hashlib.sha1(
                f"{stmt.get('action')}|{stmt.get('cypher')}|{stmt.get('params')}".encode()
            ).hexdigest()
            if fingerprint in seen:
                dropped.append(f"duplicate {stmt.get('action')}")
                continue
            seen.add(fingerprint)
            unique.append(stmt)
        return unique

    def _normalize(self, stmt: dict[str, Any]) -> dict[str, Any]:
        cypher = "\n".join(line.rstrip() for line in (stmt.get("cypher") or "").splitlines()).strip()
        return {**stmt, "cypher": cypher}
