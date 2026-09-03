"""
OREO Architecture package.

Natural-language + visual modeling of application architecture (pages,
databases, auth handshakes, includes) backed by an in-memory or Neo4j/Memgraph
property graph. This is OREO's NL+visual subsystem: intents are the source of
truth; Cypher/GQL/HTML are projections.

Merged from the GraphLang checkpoint into OREO as parser/architecture/.
"""

from .engine import HandshakeError, RelationshipEngine
from .llm import HybridParser, OpenAICompatClient, ParaphraseLexicon
from .optimize import CypherOptimizer
from .parser import ConversationContext, CypherCompiler, GraphTalk, Intent, IntentParser
from .queries import catalog as query_catalog
from .runtime import GraphRuntime
from .store import InMemoryGraph, Neo4jGraph

__all__ = [
    "ConversationContext",
    "CypherCompiler",
    "CypherOptimizer",
    "GraphRuntime",
    "GraphTalk",
    "HandshakeError",
    "HybridParser",
    "InMemoryGraph",
    "Intent",
    "IntentParser",
    "Neo4jGraph",
    "OpenAICompatClient",
    "ParaphraseLexicon",
]
