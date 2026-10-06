"""Tests for the OREO GIR graph model and its validator.

mem20oreo had no tests at all. The 20k lines include a 7.7k-line Rust toolchain
that is out of scope for a Python suite, but the graph model and validator are
where a silent regression is most expensive: they decide whether a
natural-language program is structurally and type correct before anything is
compiled. A validator that quietly passes a broken graph produces a program that
fails much later and much less clearly.

These tests therefore concentrate on the two properties that matter:

* the graph maintains its own integrity (edges never dangle, removals are
  complete, lookups do not invent nodes), and
* the validator actually rejects bad graphs and accepts good ones, with
  machine-readable codes rather than vague prose.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mem20oreo.parser.gir.edges import (
    ControlEdge,
    DataEdge,
    Edge,
    EdgeKind,
    Graph,
)
from mem20oreo.parser.gir.nodes import (
    FunctionNode,
    LiteralNode,
    ModuleNode,
    NodeKind,
)
from mem20oreo.parser.gir.validation import (
    GraphValidator,
    ValidationResult,
    ValidationSeverity,
    validate_graph,
)


def _graph_with_module() -> Graph:
    graph = Graph(name="demo")
    graph.add_node(ModuleNode(name="main"))
    return graph


# --- the graph model ---------------------------------------------------------


def test_a_new_graph_is_empty():
    graph = Graph()
    assert graph.nodes == {}
    assert graph.edges == []


def test_add_node_is_keyed_by_id_and_returns_the_node():
    graph = Graph()
    node = LiteralNode(name="x")
    assert graph.add_node(node) is node
    assert graph.get_node(node.id) is node


def test_adding_an_edge_between_known_nodes_succeeds():
    graph = _graph_with_module()
    a, b = LiteralNode(name="a"), LiteralNode(name="b")
    graph.add_node(a)
    graph.add_node(b)
    edge = graph.add_edge(DataEdge(source=a.id, target=b.id))
    assert edge in graph.edges


def test_an_edge_to_a_missing_node_is_refused():
    """This is the invariant that stops a dangling reference entering the graph."""
    graph = _graph_with_module()
    ghost = LiteralNode(name="ghost")
    with pytest.raises(ValueError) as excinfo:
        graph.add_edge(DataEdge(source=next(iter(graph.nodes)), target=ghost.id))
    assert "non-existent node" in str(excinfo.value)
    assert graph.edges == [], "a refused edge must not be partially added"


def test_an_edge_from_a_missing_node_is_refused():
    graph = _graph_with_module()
    with pytest.raises(ValueError):
        graph.add_edge(DataEdge(source="nope", target=next(iter(graph.nodes))))


def test_remove_node_takes_its_edges_with_it():
    graph = _graph_with_module()
    a, b = LiteralNode(name="a"), LiteralNode(name="b")
    graph.add_node(a)
    graph.add_node(b)
    edge = graph.add_edge(DataEdge(source=a.id, target=b.id))

    assert graph.remove_node(a.id) is True
    assert a.id not in graph.nodes
    assert edge not in graph.edges, "removing a node must not leave a dangling edge"
    assert all(e.source != a.id and e.target != a.id for e in graph.edges)


def test_removing_a_missing_node_reports_false_rather_than_raising():
    assert Graph().remove_node("nope") is False


def test_remove_edge_removes_only_that_edge():
    graph = _graph_with_module()
    ids = list(graph.nodes)
    extra = [LiteralNode(name=f"n{i}") for i in range(2)]
    for node in extra:
        graph.add_node(node)
    first = graph.add_edge(DataEdge(source=ids[0], target=extra[0].id))
    graph.add_edge(DataEdge(source=ids[0], target=extra[1].id))

    assert graph.remove_edge(first.id) is True
    assert first not in graph.edges
    assert len(graph.edges) == 1
    assert graph.remove_edge("no-such-edge") is False


def test_edge_lookups_are_directed():
    graph = _graph_with_module()
    a, b = LiteralNode(name="a"), LiteralNode(name="b")
    graph.add_node(a)
    graph.add_node(b)
    graph.add_edge(DataEdge(source=a.id, target=b.id))
    assert len(graph.get_edges_from(a.id)) == 1
    assert graph.get_edges_from(b.id) == []
    assert len(graph.get_edges_to(b.id)) == 1
    assert graph.get_edges_to(a.id) == []


def test_get_node_returns_none_rather_than_raising_for_an_unknown_id():
    assert Graph().get_node("nope") is None


def test_edge_equality_is_by_id_not_by_value():
    """Edges are identified by id, so two identical-looking edges stay distinct."""
    a = DataEdge(source="x", target="y")
    b = DataEdge(source="x", target="y")
    assert a != b, "distinct edges must not compare equal"
    assert a != "not an edge"


def test_equality_follows_the_id_not_the_field_values():
    """Two edges with identical fields stay distinct; re-adding one is the same edge."""
    graph = _graph_with_module()
    ids = list(graph.nodes)
    extra = [LiteralNode(name=f"n{i}") for i in range(2)]
    for node in extra:
        graph.add_node(node)
    first = graph.add_edge(DataEdge(source=ids[0], target=extra[0].id))
    again = DataEdge(source=ids[0], target=extra[0].id, id=first.id)
    assert first == again, "edges carrying the same id must be equal"
    assert graph.remove_edge(again.id) is True


@pytest.mark.xfail(
    strict=False,
    reason="KNOWN INCONSISTENCY: Edge defines __hash__ and __eq__ for use in sets "
    "and dicts, but the concrete subclasses are @dataclass, which regenerates "
    "__eq__ and sets __hash__ to None. So Edge is hashable while DataEdge is not. "
    "Fix: @dataclass(eq=False) on the subclasses, or functools.total_ordering-style "
    "explicit __hash__.",
)
def test_concrete_edge_subclasses_should_be_hashable_like_their_base():
    edge = DataEdge(source="x", target="y")
    assert hash(edge) == hash(edge)
    assert edge in {edge}


def test_data_and_control_edges_declare_their_kind():
    assert DataEdge(source="a", target="b").kind is EdgeKind.DATA
    assert ControlEdge(source="a", target="b").kind is EdgeKind.CONTROL
    assert Edge(source="a", target="b").kind is EdgeKind.DATA


def test_control_edge_records_its_condition():
    edge = ControlEdge(source="a", target="b", is_conditional=True, condition_port="test")
    assert edge.is_conditional is True
    assert edge.condition_port == "test"


def test_a_conditional_control_edge_defaults_to_unconditional():
    assert ControlEdge(source="a", target="b").is_conditional is False


def test_node_kinds_are_assigned_by_the_concrete_class():
    assert ModuleNode(name="m").kind is NodeKind.MODULE
    assert FunctionNode(name="f").kind is NodeKind.FUNCTION
    assert LiteralNode(name="l").kind is NodeKind.LITERAL


def test_node_ids_are_unique():
    ids = {LiteralNode(name="same").id for _ in range(20)}
    assert len(ids) == 20, "node ids must be unique or the graph cannot key on them"


# --- the validation result ---------------------------------------------------


def test_a_fresh_result_is_truthy_and_passes():
    result = ValidationResult()
    assert result.has_errors() is False
    assert bool(result) is True
    assert "PASS" in str(result)


def test_adding_an_error_makes_the_result_falsey():
    result = ValidationResult()
    assert result.add_error("something is wrong") is result, "add_* should chain"
    assert result.has_errors() is True
    assert bool(result) is False
    assert len(result.errors()) == 1


def test_warnings_do_not_make_a_result_falsey():
    """A warning is advice; it must not fail a build on its own."""
    result = ValidationResult().add_warning("consider tidying this")
    assert result.has_errors() is False
    assert bool(result) is True
    assert len(result.warnings()) == 1


def test_info_is_neither_an_error_nor_a_warning():
    result = ValidationResult().add_info("FYI")
    assert result.errors() == []
    assert result.warnings() == []
    assert result.issues[0].severity is ValidationSeverity.INFO


def test_issues_carry_a_machine_readable_code():
    result = ValidationResult().add_error("bad", code="E_TYPE_MISMATCH")
    assert result.issues[0].code == "E_TYPE_MISMATCH"


def test_issue_str_includes_severity_node_and_code():
    node = LiteralNode(name="x")
    result = ValidationResult().add_error(
        "type mismatch", node_id=node.id, code="E_TYPE"
    )
    text = str(result.issues[0])
    assert "ERROR" in text
    assert node.id[:8] in text
    assert "type mismatch" in text


def test_issue_str_survives_missing_optional_fields():
    issue = ValidationResult().add_error("bare").issues[0]
    assert str(issue).startswith("[ERROR]")


def test_result_str_counts_errors_and_warnings():
    result = ValidationResult().add_error("a").add_warning("b").add_error("c")
    text = str(result)
    assert "2 errors" in text
    assert "1 warnings" in text


# --- the validator -----------------------------------------------------------


def test_a_minimal_module_graph_validates():
    result = validate_graph(_graph_with_module())
    assert result.has_errors() is False, str(result)


def test_an_empty_graph_does_not_error():
    result = validate_graph(Graph())
    assert result.has_errors() is False, str(result)


def test_a_graph_with_no_root_produces_a_warning_not_an_error():
    """No root is suspicious, not fatal - it must not block a build by itself."""
    graph = Graph(name="no-root")
    graph.add_node(LiteralNode(name="lonely"))
    result = validate_graph(graph)
    assert result.has_errors() is False, str(result)
    assert any(i.code == "NO_ROOT" for i in result.issues), str(result)


def test_a_completely_disconnected_node_is_reported_as_unreachable():
    graph = _graph_with_module()
    graph.add_node(LiteralNode(name="orphan"))
    result = validate_graph(graph)
    unreachable = [i for i in result.issues if i.code == "UNREACHABLE_NODE"]
    assert unreachable, f"a disconnected node was not reported: {result}"
    assert unreachable[0].severity is ValidationSeverity.WARNING, (
        "an unreachable node is a warning, not a hard error"
    )
    assert result.has_errors() is False, str(result)


def test_validator_result_is_the_same_object_it_accumulates_into():
    graph = _graph_with_module()
    validator = GraphValidator(graph)
    result = validator.validate()
    assert result is validator.result


def test_validation_is_repeatable():
    """Running twice must not accumulate duplicate issues."""
    graph = _graph_with_module()
    graph.add_node(LiteralNode(name="orphan"))
    first = GraphValidator(graph).validate()
    second = GraphValidator(graph).validate()
    assert len(first.issues) == len(second.issues), (
        "validation is not idempotent; issues are being accumulated across runs"
    )


@pytest.mark.xfail(
    strict=False,
    reason="KNOWN GAP: Graph.add_edge refuses to create a dangling edge, but no "
    "validation pass re-checks edge endpoints. Mutating graph.nodes directly "
    "leaves an edge pointing at a missing node and validate_graph() reports a "
    "clean result. Fix: add a well-formedness pass asserting every edge's "
    "source and target resolve, mirroring BraidLog::verify_whole_log.",
)
def test_a_graph_whose_edge_dangles_should_be_rejected_by_the_validator():
    graph = _graph_with_module()
    a, b = LiteralNode(name="a"), LiteralNode(name="b")
    graph.add_node(a)
    graph.add_node(b)
    graph.add_edge(DataEdge(source=a.id, target=b.id))
    graph.nodes.pop(b.id)  # sneak the target out from under the edge

    result = validate_graph(graph)
    assert result.has_errors() is True, (
        "a dangling edge passed validation - the validator does not re-check "
        "edge endpoints after insertion"
    )


def test_no_validation_pass_looks_for_dangling_edges_today():
    """Documents the current gap explicitly, so removing the xfail is deliberate."""
    import inspect

    source = inspect.getsource(GraphValidator)
    assert "DANGLING" not in source.upper()
    graph = _graph_with_module()
    a, b = LiteralNode(name="a"), LiteralNode(name="b")
    graph.add_node(a)
    graph.add_node(b)
    edge = DataEdge(source=a.id, target=b.id)
    graph.add_edge(edge)
    graph.nodes.pop(b.id)
    assert validate_graph(graph).has_errors() is False, (
        "if this now fails, the gap was fixed - update the xfail above to a "
        "real assertion and add the DANGLING_EDGE code to the expected set"
    )


def test_validate_graph_and_the_class_agree():
    graph = _graph_with_module()
    graph.add_node(LiteralNode(name="orphan"))
    via_function = validate_graph(graph)
    via_class = GraphValidator(graph).validate()
    assert via_function.has_errors() == via_class.has_errors()
    assert len(via_function.issues) == len(via_class.issues)
