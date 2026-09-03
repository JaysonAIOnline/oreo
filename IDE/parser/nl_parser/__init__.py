"""
OREO Natural Language Parser package.

Two complementary NL front-ends:
- semantic_parser.py: NL -> computational GIR (functions, control flow).
- architecture_router.py: NL -> Architecture model (pages, databases, auth
  handshakes, includes) via parser.architecture.
"""

from .architecture_router import (
    ArchitectureNLParser,
    architecture_runtime,
    is_architecture_utterance,
    parse_architecture,
    query_languages,
)
from .semantic_parser import NLParser, parse_nl, parse_nl_to_json

__all__ = [
    "ArchitectureNLParser",
    "NLParser",
    "architecture_runtime",
    "is_architecture_utterance",
    "parse_architecture",
    "parse_nl",
    "parse_nl_to_json",
    "query_languages",
]
