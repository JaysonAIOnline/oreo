"""Spoken replies for GraphLang actions."""

from __future__ import annotations

from typing import Any


def narrate(result: dict[str, Any]) -> str:
    intents = result.get("intents") or ([result["intent"]] if result.get("intent") else [])
    actions = [i.get("action") for i in intents if i]
    graph = result.get("graph") or {}
    rels = graph.get("relationships") or []
    pages = [n.get("name") for n in graph.get("nodes", []) if n.get("label") == "Page"]
    if "connect_with_auth" in actions or "connect" in actions:
        src = (intents[0].get("source") or {}).get("name")
        dst = (intents[0].get("target") or {}).get("name")
        said = (intents[0].get("raw") or "").strip()
        if said and not said.startswith("draw "):
            return f"{src} to {dst} is now {said}."
        return f"Handshake drawn. {src} now talks to {dst} with secure auth."
    if "include_all" in actions or "include" in actions:
        return "Includes attached. Header and footer ride with the pages."
    if "set_purpose" in actions:
        node = (intents[0].get("target") or {}).get("name")
        why = intents[0].get("raw")
        return f"{node} is for {why}."
    if "create_node" in actions:
        names = [n.get("name") for n in (intents[0].get("nodes") or [])]
        if names:
            return f"{names[-1]} is on the canvas. Tell me what it is for."
        return f"Structure is up. {len(pages)} pages are on the canvas."
    if "disconnect" in actions:
        return "Line removed. That page can no longer reach the database."
    if actions:
        return f"Done. {actions[0].replace('_', ' ')}."
    if rels:
        return f"Graph has {len(rels)} live lines."
    return "Graph Lang is listening."
