"""Turn existing Python or Ruby files into graph nodes."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .parser import Intent, Ref


def import_python(path: str | Path) -> list[Intent]:
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_name = Path(path).stem
    nodes = [Ref(label="Resource", name=module_name, props={"kind": "module", "path": str(path)})]
    intents: list[Intent] = [Intent(action="create_node", nodes=nodes, raw=f"import {path}")]
    functions: list[Ref] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(
                Ref(
                    label="Function",
                    name=node.name,
                    props={"arity": len(node.args.args), "path": str(path), "language": "python"},
                )
            )
        elif isinstance(node, ast.ClassDef):
            functions.append(Ref(label="Service", name=node.name, props={"path": str(path), "language": "python"}))
    if functions:
        intents.append(Intent(action="create_node", nodes=functions, raw=f"import fn {path}"))
    return intents


def import_ruby(path: str | Path) -> list[Intent]:
    source = Path(path).read_text(encoding="utf-8")
    nodes = [Ref(label="Resource", name=Path(path).stem, props={"kind": "module", "path": str(path), "language": "ruby"})]
    for match in re.finditer(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_?!]*)", source, re.M):
        nodes.append(Ref(label="Function", name=match.group(1), props={"language": "ruby", "path": str(path)}))
    for match in re.finditer(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", source, re.M):
        nodes.append(Ref(label="Service", name=match.group(1), props={"language": "ruby", "path": str(path)}))
    return [Intent(action="create_node", nodes=nodes, raw=f"import {path}")]


def import_path(path: str | Path) -> list[Intent]:
    path = Path(path)
    if path.suffix == ".py":
        return import_python(path)
    if path.suffix in {".rb"}:
        return import_ruby(path)
    raise ValueError(f"No importer for {path.suffix}")
