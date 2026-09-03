"""Relationship runtime.

Edges are the program:
- CONNECTS_TO opens a store handle
- AUTHENTICATES_WITH is the handshake
- INCLUDES are composed into the response
- No line means the request is refused
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .store import InMemoryGraph, Node, Rel


class HandshakeError(PermissionError):
    """Raised when a page has no right to talk to a store."""


class MissingLine(LookupError):
    """Raised when a required relationship does not exist."""


@dataclass
class Session:
    page: str
    database: str | None
    auth: str | None
    secure: bool
    includes: list[str] = field(default_factory=list)
    store: dict[str, Any] = field(default_factory=dict)


@dataclass
class OpenResult:
    ok: bool
    page: str
    includes: list[str]
    database: str | None = None
    auth: str | None = None
    secure: bool = False
    reason: str | None = None
    session: Session | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "ok": self.ok,
            "page": self.page,
            "includes": self.includes,
            "database": self.database,
            "auth": self.auth,
            "secure": self.secure,
            "reason": self.reason,
        }
        if self.session:
            data["session"] = {
                "page": self.session.page,
                "database": self.session.database,
                "auth": self.session.auth,
                "secure": self.session.secure,
                "includes": self.session.includes,
            }
        return data


class RelationshipEngine:
    """Walk the graph instead of generating boilerplate."""

    def __init__(self, graph: InMemoryGraph):
        self.graph = graph
        self.stores: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, Session] = {}

    def open_page(self, page_name: str, require_db: bool = True) -> OpenResult:
        page = self.graph.find_by_name("Page", page_name)
        if page is None:
            return OpenResult(ok=False, page=page_name, includes=[], reason=f"No Page named {page_name}")

        includes = self._includes(page)
        db_rel = self._first(page.id, "CONNECTS_TO")
        auth_rel = self._first(page.id, "AUTHENTICATES_WITH")

        if require_db and db_rel is None:
            return OpenResult(
                ok=False,
                page=page.props.get("name", page_name),
                includes=includes,
                reason="No CONNECTS_TO line. Draw a handshake first.",
            )

        database = self.graph.nodes[db_rel.dst] if db_rel else None
        auth = self.graph.nodes[auth_rel.dst] if auth_rel else None
        secure = bool(db_rel and db_rel.props.get("secure")) or bool(
            auth and auth.props.get("level") == "secure"
        )

        if secure and auth is None:
            return OpenResult(
                ok=False,
                page=page.props.get("name", page_name),
                includes=includes,
                database=database.props.get("name") if database else None,
                secure=True,
                reason="Secure connection requires AUTHENTICATES_WITH.",
            )

        if database:
            self.stores.setdefault(database.id, {})

        session = Session(
            page=page.props.get("name", page_name),
            database=database.props.get("name") if database else None,
            auth=auth.props.get("name") if auth else None,
            secure=secure,
            includes=includes,
            store=self.stores.get(database.id, {}) if database else {},
        )
        self.sessions[page.id] = session
        return OpenResult(
            ok=True,
            page=session.page,
            includes=includes,
            database=session.database,
            auth=session.auth,
            secure=secure,
            session=session,
        )

    def write(self, page_name: str, key: str, value: Any) -> dict[str, Any]:
        opened = self.open_page(page_name)
        if not opened.ok or not opened.session:
            raise HandshakeError(opened.reason or "handshake failed")
        opened.session.store[key] = value
        return {"ok": True, "page": opened.page, "database": opened.database, "key": key}

    def read(self, page_name: str, key: str) -> Any:
        opened = self.open_page(page_name)
        if not opened.ok or not opened.session:
            raise HandshakeError(opened.reason or "handshake failed")
        return opened.session.store.get(key)

    def render(self, page_name: str) -> dict[str, Any]:
        opened = self.open_page(page_name, require_db=False)
        return {
            "ok": opened.ok,
            "page": opened.page,
            "includes": opened.includes,
            "database": opened.database,
            "auth": opened.auth,
            "body": f"{opened.page} composed with {', '.join(opened.includes) or 'no includes'}",
            "reason": opened.reason,
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps({"graph": self.graph.snapshot(), "stores": self.stores}, indent=2), encoding="utf-8")
        return path

    def load(self, path: str | Path) -> None:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        self.graph.reset()
        for node in payload.get("graph", {}).get("nodes", []):
            label = node.get("label") or "Resource"
            props = {k: v for k, v in node.items() if k not in {"id", "label"}}
            self.graph.merge_node(label, props.get("name") or node["id"], props, node.get("id"))
        for rel in payload.get("graph", {}).get("relationships", []):
            self.graph.merge_rel(rel["from"], rel["type"], rel["to"], rel.get("props") or {})
        self.stores = payload.get("stores") or {}
        self.sessions.clear()

    def _includes(self, page: Node) -> list[str]:
        tagged = [
            (rel.props.get("order", 0), self.graph.nodes[rel.dst].props.get("name"))
            for rel in self.graph.rels
            if rel.src == page.id and rel.type == "INCLUDES" and rel.dst in self.graph.nodes
        ]
        tagged.sort(key=lambda item: (item[0], str(item[1])))
        return [name for _, name in tagged if name]

    def _first(self, src_id: str, rel_type: str) -> Rel | None:
        for rel in self.graph.rels:
            if rel.src == src_id and rel.type == rel_type:
                return rel
        return None
