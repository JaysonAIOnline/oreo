"""Say something or draw a line, mutate the graph, return optimized Cypher."""

from __future__ import annotations

from typing import Any

from .advise import Suggestion, accept_phrase, advise
from .audit import audit
from .shape import model as shape_model
from .emit import emit_app
from .engine import RelationshipEngine
from .llm import HybridParser
from .optimize import CypherOptimizer
from .parser import CypherCompiler, GraphTalk as _RuleTalk, Intent, IntentParser, Ref
from .queries import catalog as query_catalog
from .store import InMemoryGraph, Neo4jGraph
from .voice import narrate


class GraphRuntime:
    def __init__(self, use_llm: bool = True, llm_first: bool = False, neo4j: Neo4jGraph | None = None):
        self.parser = HybridParser(llm_first=llm_first) if use_llm else IntentParser()
        self.compiler = CypherCompiler()
        self.optimizer = CypherOptimizer(include_schema=True)
        self.graph = InMemoryGraph()
        self.neo4j = neo4j
        self.engine = RelationshipEngine(self.graph)
        self.pending: Suggestion | None = None

    def say(self, text: str) -> dict[str, Any]:
        if self.pending and accept_phrase(text):
            pack = list(self.pending.intents or [self.pending.intent])
            self.pending = None
            return self._commit(text, pack, accepted=True)
        intents = self.parser.parse(text)
        return self._commit(text, intents)

    def draw(self, src_name: str, dst_name: str, src_label: str | None = None, dst_label: str | None = None, secure: bool = True, purpose: str | None = None) -> dict[str, Any]:
        src = self._node(src_name, src_label)
        dst = self._node(dst_name, dst_label)
        from .lines import infer_intent

        intent = infer_intent(src.label, src.props.get("name", src_name), dst.label, dst.props.get("name", dst_name), secure=secure, purpose=purpose)
        return self._commit(intent.raw, [intent])

    def schema_cypher(self) -> list[dict[str, Any]]:
        from .optimize import SCHEMA_STATEMENTS

        return SCHEMA_STATEMENTS

    def _node(self, name: str, label: str | None):
        found = self.graph.find_by_name(label, name)
        if found:
            return found
        if label:
            return self.graph.merge_node(label, name)
        raise KeyError(f"No node named {name}. Speak it into existence first.")

    def _commit(self, text: str, intents: list[Intent], accepted: bool = False) -> dict[str, Any]:
        naive = self.compiler.compile(intents)
        optimized = self.optimizer.optimize(naive)
        applied = [self.graph.apply(intent) for intent in intents]
        neo4j_result = None
        if self.neo4j:
            neo4j_result = self.neo4j.run_statements(optimized["statements"])
        suggestions = advise(self.graph, extra=text)
        self.pending = suggestions[0] if suggestions else None
        report = audit(self.graph)
        result = {
            "input": text,
            "intents": [intent.to_dict() for intent in intents],
            "statements": naive,
            "optimized": optimized,
            "applied": applied,
            "neo4j": neo4j_result,
            "graph": self.graph.snapshot(),
            "ascii": self.graph.ascii(),
            "suggestions": [s.to_dict() for s in suggestions],
            "audit": report,
            "model": shape_model(self.graph),
            "accepted": accepted,
        }
        spoken = narrate(result)
        if accepted:
            spoken = "Okay — I added that. " + spoken
        if accepted or not report["ok"]:
            spoken = f"{spoken} {report['spoken']}"
        if self.pending:
            spoken = f"{spoken} {self.pending.spoken}" if spoken else self.pending.spoken
        result["spoken"] = spoken
        return result

    def audit(self) -> dict[str, Any]:
        report = audit(self.graph)
        report["ascii"] = self.graph.ascii()
        return report

    def model(self) -> dict[str, Any]:
        return shape_model(self.graph)

    def open(self, page_name: str):
        return self.engine.open_page(page_name)

    def write(self, page_name: str, key: str, value):
        return self.engine.write(page_name, key, value)

    def read(self, page_name: str, key: str):
        return self.engine.read(page_name, key)

    def query_languages(self):
        return query_catalog()

    def save(self, path: str):
        return self.engine.save(path)

    def load(self, path: str):
        return self.engine.load(path)

    def emit(self, dest: str):
        return emit_app(self.graph, dest)


GraphTalk = _RuleTalk
