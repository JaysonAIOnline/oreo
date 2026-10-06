"""
OREO architecture NL router.

Routes natural-language that is about *application architecture* (pages,
databases, auth handshakes, includes, microservices) to the OREO Architecture
package (parser/architecture). This complements parser/nl_parser/semantic_parser.py,
which targets computational programs (functions, control flow) in the GIR.

The architecture subsystem keeps its own graph store, relationship engine and
web visual editor, so this router intentionally does not depend on parser.gir
types — it is safe to import even when the GIR layer is not yet importable.
"""

from __future__ import annotations

from typing import Any

from ..architecture import (
    GraphRuntime,
    GraphTalk,
    HybridParser,
    Intent,
    InMemoryGraph,
    IntentParser,
)

__all__ = [
    "ArchitectureNLParser",
    "architecture_runtime",
    "parse_architecture",
    "query_languages",
]

# Simple utterance classifier: sentences about the architecture/modeling layer.
ARCHITECTURE_MARKERS = (
    "page",
    "pages",
    "database",
    " a db ",
    " db ",
    "neo4j",
    "auth",
    "handshake",
    "include",
    "header",
    "footer",
    "side panel",
    "microservice",
    "microservices",
    "talks to",
    "connect",
    "draw a line",
    "storefront",
    "fansite",
    "landing page",
    "dashboard",
    "checkout",
)


class ArchitectureNLParser:
    """Text -> Intent for the architecture subsystem, with optional LLM."""

    def __init__(self, use_llm: bool = True, llm_first: bool = False):
        self.parser = HybridParser(llm_first=llm_first) if use_llm else IntentParser()

    def parse(self, text: str) -> list[Intent]:
        return self.parser.parse(text)


def architecture_runtime(use_llm: bool = True) -> GraphRuntime:
    return GraphRuntime(use_llm=use_llm)


def parse_architecture(text: str, use_llm: bool = True, llm_first: bool = False) -> dict[str, Any]:
    runtime = architecture_runtime(use_llm=use_llm)
    parser = ArchitectureNLParser(use_llm=use_llm, llm_first=llm_first)
    intents = parser.parse(text)
    result = runtime._commit(text, intents)
    result["intents"] = [intent.to_dict() for intent in intents]
    return result


def query_languages() -> dict[str, Any]:
    from ..architecture import query_catalog

    return query_catalog()


def is_architecture_utterance(text: str) -> bool:
    lowered = f" {text.strip().lower()} "
    return any(marker in lowered for marker in ARCHITECTURE_MARKERS)
