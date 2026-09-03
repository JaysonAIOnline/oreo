"""Graph stores for GraphLang.

InMemoryGraph runs here with no extra install.
Neo4jGraph uses the official driver when available.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from .parser import Intent, Ref, stable_id


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


@dataclass
class Node:
    id: str
    label: str
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class Rel:
    src: str
    type: str
    dst: str
    props: dict[str, Any] = field(default_factory=dict)


class InMemoryGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.rels: list[Rel] = []
        self.last_result: Any = None

    def reset(self) -> None:
        self.nodes.clear()
        self.rels.clear()
        self.last_result = None

    def merge_node(self, label: str, name: str, props: dict[str, Any] | None = None, node_id: str | None = None) -> Node:
        nid = node_id or stable_id(label, name)
        incoming = dict(props or {})
        incoming.setdefault("name", name)
        if nid in self.nodes:
            node = self.nodes[nid]
            for key, value in incoming.items():
                if value is not None:
                    node.props[key] = value
            return node
        incoming.setdefault("created_at", _now())
        node = Node(id=nid, label=label, props=incoming)
        self.nodes[nid] = node
        return node

    def merge_rel(self, src_id: str, rel_type: str, dst_id: str, props: dict[str, Any] | None = None) -> Rel:
        incoming = dict(props or {})
        for rel in self.rels:
            if rel.src == src_id and rel.type == rel_type and rel.dst == dst_id:
                rel.props.update({k: v for k, v in incoming.items() if v is not None})
                return rel
        incoming.setdefault("created_at", _now())
        rel = Rel(src=src_id, type=rel_type, dst=dst_id, props=incoming)
        self.rels.append(rel)
        return rel

    def delete_rel(self, src_id: str, rel_type: str, dst_id: str | None = None) -> int:
        before = len(self.rels)
        kept: list[Rel] = []
        for rel in self.rels:
            match_src = rel.src == src_id
            match_type = rel.type == rel_type
            match_dst = dst_id is None or rel.dst == dst_id
            if match_src and match_type and match_dst:
                continue
            kept.append(rel)
        self.rels = kept
        return before - len(kept)

    def find_by_name(self, label: str | None, name: str) -> Node | None:
        wanted = name.lower()
        for node in self.nodes.values():
            if label and node.label != label:
                continue
            if str(node.props.get("name", "")).lower() == wanted or node.id == name:
                return node
        return None

    def apply(self, intent: Intent) -> Any:
        action = intent.action
        if action == "create_node":
            created = [self.merge_node(n.label, n.name, n.props, n.id) for n in intent.nodes]
            self.last_result = [n.id for n in created]
            return self.last_result

        if action == "set_purpose":
            target = self._resolve(intent.target, intent.target.label if intent.target else None)
            if target is None and intent.target:
                target = self.merge_node(intent.target.label, intent.target.name, intent.target.props, intent.target.id)
            if target:
                target.props["purpose"] = (intent.target.props.get("purpose") if intent.target else None) or intent.raw
            self.last_result = {"node": target.props.get("name") if target else None, "purpose": target.props.get("purpose") if target else None}
            return self.last_result

        if action in {"connect", "connect_with_auth"}:
            return self._connect(intent, with_auth=action == "connect_with_auth")

        if action in {"connect_all", "connect_all_with_auth"}:
            return self._connect_all(intent, with_auth=action == "connect_all_with_auth")

        if action in {"include", "include_all"}:
            return self._include(intent, all_pages=action == "include_all")

        if action == "query_neighbors":
            db = self._resolve(intent.target, "Database")
            rows = []
            if db:
                for rel in self.rels:
                    if rel.type == "CONNECTS_TO" and rel.dst == db.id:
                        src = self.nodes[rel.src]
                        auth = self._auth_for(src.id)
                        includes = [
                            self.nodes[r.dst].props.get("name")
                            for r in self.rels
                            if r.src == src.id and r.type == "INCLUDES"
                        ]
                        rows.append(
                            {
                                "node": src.props.get("name"),
                                "label": src.label,
                                "secure": rel.props.get("secure"),
                                "auth": auth,
                                "includes": includes,
                            }
                        )
            self.last_result = rows
            return rows

        if action == "query_auth":
            page = self._resolve(intent.source, "Page")
            self.last_result = {"page": page.props.get("name") if page else None, "auth": self._auth_for(page.id) if page else []}
            return self.last_result

        if action == "impact":
            target = self._resolve(intent.target, None)
            if not target:
                self.last_result = {"error": "not found"}
                return self.last_result
            inbound = [
                {"from": self.nodes[r.src].props.get("name"), "rel": r.type}
                for r in self.rels
                if r.dst == target.id
            ]
            outbound = [
                {"to": self.nodes[r.dst].props.get("name"), "rel": r.type}
                for r in self.rels
                if r.src == target.id
            ]
            self.last_result = {"target": target.props.get("name"), "inbound": inbound, "outbound": outbound}
            return self.last_result

        if action == "lint":
            missing = [
                node.props.get("name")
                for node in self.nodes.values()
                if node.label == "Page" and not any(r.src == node.id and r.type == "CONNECTS_TO" for r in self.rels)
            ]
            self.last_result = missing
            return missing

        if action == "disconnect":
            src = self._resolve(intent.source, "Page")
            dst = self._resolve(intent.target, "Database")
            deleted = 0
            if src and dst:
                deleted = self.delete_rel(src.id, "CONNECTS_TO", dst.id)
            self.last_result = {"deleted": deleted}
            return self.last_result

        if action == "disconnect_auth":
            src = self._resolve(intent.source, "Page")
            deleted = self.delete_rel(src.id, "AUTHENTICATES_WITH") if src else 0
            self.last_result = {"deleted": deleted}
            return self.last_result

        self.last_result = {"unknown": intent.raw}
        return self.last_result

    def _connect(self, intent: Intent, with_auth: bool) -> dict[str, Any]:
        page_ref = intent.source or Ref(label="Page", name="Landing")
        db_ref = intent.target or Ref(label="Database", name="MainDB")
        page = self.merge_node("Page", page_ref.name, page_ref.props, page_ref.id)
        db = self.merge_node("Database", db_ref.name, db_ref.props, db_ref.id)
        self.merge_rel(
            page.id,
            "CONNECTS_TO",
            db.id,
            {
                "secure": with_auth,
                "auth_method": (intent.auth.props.get("method") if intent.auth else None),
                "purpose": intent.raw if intent.raw and not str(intent.raw).startswith("draw ") else None,
            },
        )
        auth_name = None
        if with_auth:
            auth_ref = intent.auth or Ref(
                label="Auth",
                name="SecureJWT",
                props={"method": "jwt", "level": "secure", "requires_https": True},
            )
            auth = self.merge_node("Auth", auth_ref.name, auth_ref.props, auth_ref.id)
            self.merge_rel(page.id, "AUTHENTICATES_WITH", auth.id, {"required": True, "roles": intent.roles})
            auth_name = auth.props.get("name")
        result = {"page": page.props.get("name"), "database": db.props.get("name"), "auth": auth_name}
        self.last_result = result
        return result

    def _connect_all(self, intent: Intent, with_auth: bool) -> list[dict[str, Any]]:
        pages = [n for n in self.nodes.values() if n.label == "Page"]
        results = []
        for page in pages:
            clone = Intent(
                action="connect_with_auth" if with_auth else "connect",
                source=Ref(label="Page", name=page.props.get("name", page.id), id=page.id),
                target=intent.target,
                auth=intent.auth,
                roles=intent.roles,
            )
            results.append(self._connect(clone, with_auth))
        self.last_result = results
        return results

    def _include(self, intent: Intent, all_pages: bool) -> list[dict[str, Any]]:
        pages = [n for n in self.nodes.values() if n.label == "Page"]
        if not all_pages:
            page = self._resolve(intent.source, "Page")
            if page is None and intent.source:
                page = self.merge_node("Page", intent.source.name, intent.source.props, intent.source.id)
            pages = [page] if page else []
        results = []
        for page in pages:
            for order, inc_ref in enumerate(intent.includes):
                inc = self.merge_node("Include", inc_ref.name, inc_ref.props, inc_ref.id)
                self.merge_rel(page.id, "INCLUDES", inc.id, {"order": order})
                results.append({"page": page.props.get("name"), "include": inc.props.get("name"), "order": order})
        self.last_result = results
        return results

    def _resolve(self, ref: Ref | None, label: str | None) -> Node | None:
        if ref is None:
            return None
        by_id = self.nodes.get(ref.resolved_id())
        if by_id:
            return by_id
        return self.find_by_name(label or ref.label, ref.name)

    def _auth_for(self, page_id: str) -> list[str]:
        names = []
        for rel in self.rels:
            if rel.src == page_id and rel.type == "AUTHENTICATES_WITH":
                names.append(self.nodes[rel.dst].props.get("name"))
        return names

    def snapshot(self) -> dict[str, Any]:
        return {
            "nodes": [
                {"id": n.id, "label": n.label, **n.props}
                for n in sorted(self.nodes.values(), key=lambda n: (n.label, n.id))
            ],
            "relationships": [
                {
                    "from": r.src,
                    "from_name": self.nodes[r.src].props.get("name"),
                    "type": r.type,
                    "to": r.dst,
                    "to_name": self.nodes[r.dst].props.get("name"),
                    "props": r.props,
                }
                for r in self.rels
            ],
        }

    def ascii(self) -> str:
        lines = ["GRAPH"]
        by_label: dict[str, list[Node]] = {}
        for node in self.nodes.values():
            by_label.setdefault(node.label, []).append(node)
        for label, nodes in sorted(by_label.items()):
            names = ", ".join(str(n.props.get("name")) for n in sorted(nodes, key=lambda n: n.id))
            lines.append(f"  {label}: {names}")
        lines.append("  RELS:")
        if not self.rels:
            lines.append("    (none)")
        for rel in self.rels:
            src = self.nodes[rel.src].props.get("name")
            dst = self.nodes[rel.dst].props.get("name")
            extra = ""
            if rel.type == "CONNECTS_TO" and rel.props.get("secure"):
                extra = " {secure}"
            lines.append(f"    {src} -[{rel.type}{extra}]-> {dst}")
        return "\n".join(lines)


class Neo4jGraph:
    """Thin Cypher executor. Requires `pip install neo4j` and NEO4J_URI."""

    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("neo4j driver is not installed. pip install neo4j") from exc

        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

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
                records = session.run(cypher, stmt.get("params") or {})
                results.append([r.data() for r in records])
        return results

    def snapshot(self) -> dict[str, Any]:
        with self._driver.session() as session:
            nodes = session.run("MATCH (n) RETURN labels(n) AS labels, n.id AS id, n.name AS name, properties(n) AS props").data()
            rels = session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN a.id AS from, type(r) AS type, b.id AS to, properties(r) AS props, a.name AS from_name, b.name AS to_name
                """
            ).data()
        return {"nodes": nodes, "relationships": rels}
