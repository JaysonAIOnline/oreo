"""Translate the graph into a growing geometric model.

Nodes add solids. Lines add struts. Closed triangles add faces.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

from .store import InMemoryGraph


LABEL_SOLID = {
    "Page": "prism",
    "Database": "cylinder",
    "Auth": "diamond",
    "Include": "plate",
    "Function": "sphere",
    "Service": "hex",
    "Resource": "sphere",
}

LABEL_Z = {
    "Page": 0,
    "Include": -30,
    "Database": 55,
    "Auth": 90,
    "Function": 20,
    "Service": 40,
    "Resource": 10,
}


def _name(node) -> str:
    return str(node.props.get("name") or node.id)


def layout(graph: InMemoryGraph) -> dict[str, tuple[float, float, float]]:
    groups: dict[str, list] = {}
    for node in graph.nodes.values():
        groups.setdefault(node.label, []).append(node)
    columns = ["Page", "Database", "Auth", "Include", "Service", "Function", "Resource"]
    xs = {"Page": 0, "Database": 180, "Auth": 300, "Include": 80, "Service": 240, "Function": 120, "Resource": 40}
    pos = {}
    for label in columns:
        for i, node in enumerate(groups.get(label, [])):
            pos[node.id] = (float(xs.get(label, 0)), float(i * 90), float(LABEL_Z.get(label, 0)))
    return pos


def model(graph: InMemoryGraph) -> dict[str, Any]:
    pos = layout(graph)
    solids = []
    for node in graph.nodes.values():
        x, y, z = pos[node.id]
        solids.append(
            {
                "id": node.id,
                "name": _name(node),
                "label": node.label,
                "kind": LABEL_SOLID.get(node.label, "sphere"),
                "at": [x, y, z],
                "secure": any(
                    r.src == node.id and r.type == "AUTHENTICATES_WITH" for r in graph.rels
                ),
                "purpose": node.props.get("purpose"),
            }
        )
    struts = []
    for rel in graph.rels:
        if rel.src not in pos or rel.dst not in pos:
            continue
        struts.append(
            {
                "type": rel.type,
                "from": list(pos[rel.src]),
                "to": list(pos[rel.dst]),
                "from_name": _name(graph.nodes[rel.src]),
                "to_name": _name(graph.nodes[rel.dst]),
                "secure": bool(rel.props.get("secure")) or rel.type == "AUTHENTICATES_WITH",
                "purpose": rel.props.get("purpose"),
            }
        )
    # A closed three-node loop becomes a face — the shape gains a facet.
    neighbors: dict[str, set[str]] = {nid: set() for nid in pos}
    for rel in graph.rels:
        neighbors.setdefault(rel.src, set()).add(rel.dst)
        neighbors.setdefault(rel.dst, set()).add(rel.src)
    faces = []
    ids = list(pos)
    for a, b, c in combinations(ids, 3):
        if b in neighbors[a] and c in neighbors[a] and c in neighbors[b]:
            faces.append({"points": [list(pos[a]), list(pos[b]), list(pos[c])]})
    return {
        "solids": solids,
        "struts": struts,
        "faces": faces,
        "stats": {
            "solids": len(solids),
            "struts": len(struts),
            "faces": len(faces),
        },
        "spoken": (
            f"The model has {len(solids)} solids and {len(struts)} struts"
            + (f", with {len(faces)} facets where lines close." if faces else ".")
        ),
    }
