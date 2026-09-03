"""
Test Harness - Property-Based Testing
Property-based testing for OREO GIR graphs.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional, TypeVar, Generic
from abc import ABC, abstractmethod
import random
import hashlib

from ..parser.gir import (
    Graph, Node, NodeKind, Edge, EdgeKind, Port, TypeRef,
    create_literal, create_variable, create_parameter, create_function,
    connect_data, connect_control, validate_graph,
    INT, BOOL, STRING, UNIT,
    ArithmeticOp, LogicOp, ComparisonOp,
)


T = TypeVar('T')


class Generator(Generic[T]):
    """Base generator for property-based testing."""
    
    def __init__(self):
        self.size = 10
    
    @abstractmethod
    def generate(self, size: int = None) -> T:
        pass
    
    def resize(self, size: int) -> 'Generator[T]':
        self.size = size
        return self


class IntGenerator(Generator[int]):
    def generate(self, size: int = None) -> int:
        s = size or self.size
        return random.randint(-s, s)


class BoolGenerator(Generator[bool]):
    def generate(self, size: int = None) -> bool:
        return random.choice([True, False])


class StringGenerator(Generator[str]):
    def generate(self, size: int = None) -> str:
        s = size or self.size
        length = random.randint(0, s)
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(chars) for _ in range(length))


class ListGenerator(Generator[List[T]]):
    def __init__(self, element_gen: Generator[T]):
        super().__init__()
        self.element_gen = element_gen
    
    def generate(self, size: int = None) -> List[T]:
        s = size or self.size
        length = random.randint(0, s)
        return [self.element_gen.generate(s) for _ in range(length)]


class DictGenerator(Generator[Dict[str, T]]):
    def __init__(self, key_gen: Generator[str], value_gen: Generator[T]):
        super().__init__()
        self.key_gen = key_gen
        self.value_gen = value_gen
    
    def generate(self, size: int = None) -> Dict[str, T]:
        s = size or self.size
        length = random.randint(0, s)
        result = {}
        for _ in range(length):
            result[self.key_gen.generate(s)] = self.value_gen.generate(s)
        return result


# GIR-specific generators

class LiteralNodeGenerator(Generator[Node]):
    """Generates random literal nodes."""
    
    def __init__(self):
        super().__init__()
        self.int_gen = IntGenerator()
        self.bool_gen = BoolGenerator()
        self.string_gen = StringGenerator()
    
    def generate(self, size: int = None) -> Node:
        kind = random.choice(['int', 'bool', 'string', 'float'])
        
        if kind == 'int':
            return create_literal(self.int_gen.generate(size), TypeRef("Int"))
        elif kind == 'bool':
            return create_literal(self.bool_gen.generate(size), TypeRef("Bool"))
        elif kind == 'string':
            return create_literal(self.string_gen.generate(size), TypeRef("String"))
        else:
            return create_literal(random.uniform(-size or 10, size or 10), TypeRef("Float"))


class ArithmeticNodeGenerator(Generator[Node]):
    """Generates random arithmetic operation nodes."""
    
    def __init__(self):
        super().__init__()
        self.literal_gen = LiteralNodeGenerator()
    
    def generate(self, size: int = None) -> Node:
        from ..parser.gir import ArithmeticNode, ArithmeticOp
        
        op = random.choice(list(ArithmeticOp))
        node = ArithmeticNode(op=op)
        
        # Add literal operands
        lhs = self.literal_gen.generate(size)
        rhs = self.literal_gen.generate(size)
        
        # Note: In real use, these would be connected via edges
        node.properties['lhs_value'] = lhs.properties.get('value')
        node.properties['rhs_value'] = rhs.properties.get('value')
        
        return node


class FunctionGenerator(Generator[Node]):
    """Generates random function nodes."""
    
    def __init__(self):
        super().__init__()
        self.literal_gen = LiteralNodeGenerator()
        self.arith_gen = ArithmeticNodeGenerator()
    
    def generate(self, size: int = None) -> Node:
        num_params = random.randint(0, 3)
        params = []
        
        for i in range(num_params):
            param_type = random.choice([TypeRef("Int"), TypeRef("Bool"), TypeRef("String")])
            params.append(create_parameter(f"param{i}", param_type))
        
        return_type = random.choice([TypeRef("Int"), TypeRef("Bool"), TypeRef("String"), TypeRef("Unit")])
        
        # Simple body - just return a literal or first param
        if params and random.random() < 0.5:
            body = create_literal(params[0].param_name, return_type)
        else:
            body = self.literal_gen.generate(size)
        
        return create_function(
            f"func_{random.randint(1000, 9999)}",
            params,
            return_type,
            body
        )


class GraphGenerator(Generator[Graph]):
    """Generates random GIR graphs."""
    
    def __init__(self):
        super().__init__()
        self.literal_gen = LiteralNodeGenerator()
        self.arith_gen = ArithmeticNodeGenerator()
        self.func_gen = FunctionGenerator()
    
    def generate(self, size: int = None) -> Graph:
        s = size or self.size
        graph = Graph(name=f"test_graph_{random.randint(1000, 9999)}")
        
        # Add some functions
        num_funcs = random.randint(1, min(5, s))
        for _ in range(num_funcs):
            func = self.func_gen.generate(s)
            graph.add_node(func)
        
        # Add some loose nodes
        num_nodes = random.randint(0, s)
        for _ in range(num_nodes):
            node_type = random.choice(['literal', 'arithmetic', 'variable'])
            if node_type == 'literal':
                node = self.literal_gen.generate(s)
            elif node_type == 'arithmetic':
                node = self.arith_gen.generate(s)
            else:
                node = create_variable(f"var_{random.randint(100, 999)}", TypeRef("Int"))
            graph.add_node(node)
        
        return graph


@dataclass
class PropertyTest:
    """A property test case."""
    name: str
    property_fn: Callable[[Graph], bool]
    generator: GraphGenerator
    num_tests: int = 100
    max_size: int = 50


@dataclass
class TestResult:
    """Result of a property test."""
    property_name: str
    passed: bool
    tests_run: int
    failed_example: Optional[Graph] = None
    error_message: str = ""
    shrunk_example: Optional[Graph] = None


class PropertyTestRunner:
    """Runs property-based tests."""
    
    def __init__(self):
        self.tests: List[PropertyTest] = []
    
    def add_test(self, test: PropertyTest):
        self.tests.append(test)
    
    def run_all(self) -> List[TestResult]:
        results = []
        for test in self.tests:
            result = self.run_test(test)
            results.append(result)
        return results
    
    def run_test(self, test: PropertyTest) -> TestResult:
        passed = 0
        failed_example = None
        error_message = ""
        
        for i in range(test.num_tests):
            size = random.randint(1, test.max_size)
            graph = test.generator.generate(size)
            
            try:
                if not test.property_fn(graph):
                    failed_example = graph
                    error_message = f"Property failed on test {i+1}"
                    break
                passed += 1
            except Exception as e:
                failed_example = graph
                error_message = f"Exception on test {i+1}: {str(e)}"
                break
        
        # Try to shrink failed example
        shrunk = None
        if failed_example:
            shrunk = self._shrink(failed_example, test.property_fn)
        
        return TestResult(
            property_name=test.name,
            passed=(failed_example is None),
            tests_run=passed + (1 if failed_example else 0),
            failed_example=failed_example,
            error_message=error_message,
            shrunk_example=shrunk,
        )
    
    def _shrink(self, graph: Graph, property_fn: Callable[[Graph], bool]) -> Optional[Graph]:
        """Attempt to shrink a failing example."""
        # Simplified shrinking - remove nodes one at a time
        nodes = list(graph.nodes.keys())
        
        for node_id in nodes:
            # Create copy without this node
            shrunk_graph = Graph(name=f"shrunk_{graph.name}")
            
            for nid, node in graph.nodes.items():
                if nid != node_id:
                    shrunk_graph.add_node(node)
            
            # Copy edges that don't reference removed node
            for edge in graph.edges:
                if edge.source != node_id and edge.target != node_id:
                    shrunk_graph.edges.append(edge)
            
            try:
                if not property_fn(shrunk_graph):
                    return shrunk_graph
            except:
                pass
        
        return None


# --- Built-in Properties ---

def property_graph_validates(graph: Graph) -> bool:
    """Property: All generated graphs should validate."""
    result = validate_graph(graph)
    return not result.has_errors()


def property_no_orphan_nodes(graph: Graph) -> bool:
    """Property: No completely disconnected nodes (unless module/function)."""
    for node in graph.nodes.values():
        if node.kind in (NodeKind.MODULE, NodeKind.FUNCTION):
            continue
        
        # Check if node has any edges
        has_edges = any(e.source == node.id or e.target == node.id for e in graph.edges)
        if not has_edges:
            # Check composition
            has_parent = any(e.target == node.id and e.kind == EdgeKind.COMPOSITION for e in graph.edges)
            has_children = any(e.source == node.id and e.kind == EdgeKind.COMPOSITION for e in graph.edges)
            if not has_parent and not has_children:
                return False
    return True


def property_function_has_body_or_external(graph: Graph) -> bool:
    """Property: Functions should have body or be marked external."""
    for node in graph.nodes.values():
        if node.kind == NodeKind.FUNCTION:
            from ..parser.gir import FunctionNode
            if isinstance(node, FunctionNode):
                if node.body is None and not node.properties.get('external', False):
                    return False
    return True


def property_no_self_loops(graph: Graph) -> bool:
    """Property: No edges from a node to itself."""
    for edge in graph.edges:
        if edge.source == edge.target:
            return False
    return True


def property_ports_match_edges(graph: Graph) -> bool:
    """Property: All edges reference valid ports."""
    for edge in graph.edges:
        if edge.kind == EdgeKind.DATA:
            source = graph.nodes.get(edge.source)
            target = graph.nodes.get(edge.target)
            
            if source and edge.source_port:
                if edge.source_port not in source.ports:
                    return False
            
            if target and edge.target_port:
                if edge.target_port not in target.ports:
                    return False
    return True


def create_standard_test_suite() -> PropertyTestRunner:
    """Create standard property test suite."""
    runner = PropertyTestRunner()
    generator = GraphGenerator()
    
    runner.add_test(PropertyTest(
        name="graph_validates",
        property_fn=property_graph_validates,
        generator=generator,
        num_tests=100,
    ))
    
    runner.add_test(PropertyTest(
        name="no_orphan_nodes",
        property_fn=property_no_orphan_nodes,
        generator=generator,
        num_tests=100,
    ))
    
    runner.add_test(PropertyTest(
        name="function_has_body",
        property_fn=property_function_has_body_or_external,
        generator=generator,
        num_tests=100,
    ))
    
    runner.add_test(PropertyTest(
        name="no_self_loops",
        property_fn=property_no_self_loops,
        generator=generator,
        num_tests=100,
    ))
    
    runner.add_test(PropertyTest(
        name="ports_match_edges",
        property_fn=property_ports_match_edges,
        generator=generator,
        num_tests=100,
    ))
    
    return runner


def run_property_tests() -> Dict[str, Any]:
    """Run all property tests and return summary."""
    runner = create_standard_test_suite()
    results = runner.run_all()
    
    summary = {
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "details": [],
    }
    
    for result in results:
        summary["details"].append({
            "property": result.property_name,
            "passed": result.passed,
            "tests_run": result.tests_run,
            "error": result.error_message if not result.passed else None,
        })
    
    return summary