"""Executable Function nodes.

A Function node with props.callable or a registered Python hook can run.
The graph decides *whether* it may run (CALLS / page handshake).
"""

from __future__ import annotations

from typing import Any, Callable

from .engine import HandshakeError
from .store import InMemoryGraph


class FunctionRuntime:
    def __init__(self, graph: InMemoryGraph):
        self.graph = graph
        self.registry: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        self.registry[name] = fn
        self.graph.merge_node("Function", name, {"callable": True})

    def call(self, name: str, page: str | None = None, **kwargs: Any) -> Any:
        if page:
            from .engine import RelationshipEngine

            opened = RelationshipEngine(self.graph).open_page(page, require_db=False)
            if not opened.ok:
                raise HandshakeError(opened.reason or "page cannot call functions")
        node = self.graph.find_by_name("Function", name)
        if node is None and name not in self.registry:
            raise LookupError(f"No Function named {name}")
        fn = self.registry.get(name)
        if fn is None:
            raise LookupError(f"Function {name} is in the graph but has no Python hook. Register it first.")
        return fn(**kwargs)
