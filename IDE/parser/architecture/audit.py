"""Syntax and completeness audits run on every build."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .store import InMemoryGraph


ALLOWED_LABELS = {"Page", "Database", "Auth", "Include", "Function", "Service", "Resource"}
ALLOWED_RELS = {"CONNECTS_TO", "AUTHENTICATES_WITH", "INCLUDES", "CALLS"}
SECURE_HINTS = ("secure", "auth", "login", "checkout", "pay", "account", "admin", "private")


@dataclass
class Finding:
    kind: str  # syntax | completeness
    severity: str  # error | warning | info
    code: str
    spoken: str
    node: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "code": self.code,
            "spoken": self.spoken,
            "node": self.node,
            "details": self.details,
        }


def _name(node) -> str:
    return str(node.props.get("name") or node.id)


def _blob(node) -> str:
    return f"{_name(node)} {node.props.get('purpose') or ''}".lower()


def audit(graph: InMemoryGraph) -> dict[str, Any]:
    findings: list[Finding] = []
    nodes = graph.nodes
    rels = graph.rels

    for node in nodes.values():
        if node.label not in ALLOWED_LABELS:
            findings.append(Finding("syntax", "error", "bad_label", f"{_name(node)} has an unknown kind {node.label}.", _name(node)))
        if node.label == "Page" and not node.props.get("path"):
            findings.append(Finding("syntax", "warning", "page_path", f"{_name(node)} has no path yet.", _name(node)))
        if node.label == "Database" and not node.props.get("engine"):
            findings.append(Finding("syntax", "info", "db_engine", f"{_name(node)} has no engine set. I can assume neo4j.", _name(node)))
        if node.label == "Auth" and not node.props.get("method"):
            findings.append(Finding("syntax", "warning", "auth_method", f"{_name(node)} is auth without a method.", _name(node)))

    names = [_name(n).lower() for n in nodes.values()]
    dupes = {n for n in names if names.count(n) > 1}
    for dupe in dupes:
        findings.append(Finding("syntax", "warning", "duplicate_name", f"Two things are both called {dupe}.", dupe))

    for rel in rels:
        if rel.src not in nodes or rel.dst not in nodes:
            findings.append(Finding("syntax", "error", "dangling", "A line points at something that is not on the canvas."))
            continue
        if rel.type not in ALLOWED_RELS:
            findings.append(Finding("syntax", "error", "bad_rel", f"{rel.type} is not a GraphLang line.", nodes[rel.src].props.get("name")))
            continue
        src, dst = nodes[rel.src], nodes[rel.dst]
        if rel.type == "CONNECTS_TO" and dst.label != "Database":
            findings.append(Finding("syntax", "error", "connects_target", f"{_name(src)} talks-to must land on a database.", _name(src)))
        if rel.type == "AUTHENTICATES_WITH" and dst.label != "Auth":
            findings.append(Finding("syntax", "error", "auth_target", f"{_name(src)} secure path must land on Auth.", _name(src)))
        if rel.type == "INCLUDES" and dst.label != "Include":
            findings.append(Finding("syntax", "error", "include_target", f"{_name(src)} can only include an Include node.", _name(src)))
        if rel.type == "CONNECTS_TO" and rel.props.get("secure") and not any(
            r.src == rel.src and r.type == "AUTHENTICATES_WITH" for r in rels
        ):
            findings.append(Finding("syntax", "error", "secure_without_auth", f"{_name(src)} is marked secure but has no auth line.", _name(src)))

    pages = [n for n in nodes.values() if n.label == "Page"]
    dbs = [n for n in nodes.values() if n.label == "Database"]
    services = [n for n in nodes.values() if n.label == "Service"]
    includes = [n for n in nodes.values() if n.label == "Include"]

    for page in pages:
        has_db = any(r.src == page.id and r.type == "CONNECTS_TO" for r in rels)
        has_auth = any(r.src == page.id and r.type == "AUTHENTICATES_WITH" for r in rels)
        has_inc = any(r.src == page.id and r.type == "INCLUDES" for r in rels)
        if not has_db:
            findings.append(Finding("completeness", "warning", "page_no_db", f"{_name(page)} has no database line.", _name(page)))
        if any(h in _blob(page) for h in SECURE_HINTS) and not has_auth:
            findings.append(Finding("completeness", "error", "needs_secure_path", f"{_name(page)} should be secure and is not finished.", _name(page)))
        if includes and not has_inc:
            findings.append(Finding("completeness", "info", "page_no_include", f"{_name(page)} is missing Header/Footer.", _name(page)))

    if pages and not dbs:
        findings.append(Finding("completeness", "error", "no_database", "Pages exist and there is still no database."))

    have = { _name(n).lower() for n in nodes.values() }
    if {"shop", "store", "cart", "product", "catalog"} & have or "storefront" in " ".join(_blob(n) for n in nodes.values()):
        for piece in ("Checkout", "MainDB", "PictureStore"):
            if piece.lower() not in have and not any(piece.lower() == n for n in have):
                findings.append(Finding("completeness", "warning", "storefront_gap", f"Storefront is incomplete without {piece}.", piece))
    if {"fan", "band", "artist", "fandom"} & have or any("fan" in _blob(n) for n in nodes.values()):
        for piece in ("Forum", "MailingList", "Login"):
            if piece.lower() not in have:
                findings.append(Finding("completeness", "warning", "fansite_gap", f"Fan site is incomplete without {piece}.", piece))

    for service in services:
        used = any(r.dst == service.id or r.src == service.id for r in rels)
        if not used:
            findings.append(Finding("completeness", "info", "lonely_service", f"{_name(service)} is on the canvas but nothing talks to it yet.", _name(service)))

    for inc in includes:
        used = any(r.dst == inc.id and r.type == "INCLUDES" for r in rels)
        if not used:
            findings.append(Finding("completeness", "info", "lonely_include", f"{_name(inc)} is not included by any page.", _name(inc)))

    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    ok = errors == 0
    if not findings:
        spoken = "Audit is clean. Syntax and completeness both look good."
    elif ok:
        spoken = f"Audit passed syntax. {warnings} completeness notes."
    else:
        spoken = f"Audit found {errors} syntax or completeness errors and {warnings} notes."
        top = next((f.spoken for f in findings if f.severity == "error"), None)
        if top:
            spoken += " " + top

    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "spoken": spoken,
        "findings": [f.to_dict() for f in findings],
    }
