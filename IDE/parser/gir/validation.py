"""
GIR (Graph Intermediate Representation) - Validation
Graph validation, type checking, and well-formedness checks.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Callable
from collections import defaultdict

from .nodes import Node, NodeKind, Port, TypeRef
from .edges import Graph, Edge, EdgeKind, DataEdge, ControlEdge, CompositionEdge
from .types import (
    Type, PrimitiveType, CompositeType, FunctionType, Effect, TypeVar,
    TypeVarType, ForAllType, AliasType, TypeScheme, TypeEnvironment,
    unify, UnificationError, check_type, TypeError,
    UNIT, BOOL, INT, FLOAT, STRING, ANY, NEVER,
    make_function, make_option, make_result,
    EFFECT_IO, EFFECT_STATE, EFFECT_EXCEPTION, EFFECT_ASYNC
)


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    message: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    location: Optional[Dict[str, Any]] = None  # file, line, col
    code: str = ""  # machine-readable error code
    
    def __str__(self):
        loc = f" at {self.location}" if self.location else ""
        node = f" (node {self.node_id[:8]})" if self.node_id else ""
        edge = f" (edge {self.edge_id[:8]})" if self.edge_id else ""
        return f"[{self.severity.value.upper()}]{loc}{node}{edge}: {self.message}"


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def add_error(self, message: str, node_id: str = None, edge_id: str = None, 
                  location: Dict = None, code: str = "") -> 'ValidationResult':
        self.issues.append(ValidationIssue(ValidationSeverity.ERROR, message, node_id, edge_id, location, code))
        return self
    
    def add_warning(self, message: str, node_id: str = None, edge_id: str = None,
                    location: Dict = None, code: str = "") -> 'ValidationResult':
        self.issues.append(ValidationIssue(ValidationSeverity.WARNING, message, node_id, edge_id, location, code))
        return self
    
    def add_info(self, message: str, node_id: str = None, edge_id: str = None,
                 location: Dict = None, code: str = "") -> 'ValidationResult':
        self.issues.append(ValidationIssue(ValidationSeverity.INFO, message, node_id, edge_id, location, code))
        return self
    
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)
    
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    def __bool__(self) -> bool:
        return not self.has_errors()
    
    def __str__(self) -> str:
        if not self.issues:
            return "ValidationResult: PASS"
        lines = [f"ValidationResult: {len(self.errors())} errors, {len(self.warnings())} warnings"]
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


class GraphValidator:
    """Validates GIR graphs for well-formedness and type correctness."""
    
    def __init__(self, graph: Graph):
        self.graph = graph
        self.result = ValidationResult()
        self.type_env = TypeEnvironment()
        self._node_types: Dict[str, Type] = {}  # node_id -> inferred type
    
    def validate(self) -> ValidationResult:
        """Run all validation passes."""
        self._validate_structure()
        self._validate_port_connections()
        self._validate_control_flow()
        self._validate_composition()
        self._validate_types()
        self._validate_effects()
        self._validate_contracts()
        self._validate_scopes()
        return self.result
    
    # --- Structure Validation ---
    
    def _validate_structure(self):
        """Basic graph structure checks."""
        # Every node must be reachable from a root (module or function)
        roots = [n for n in self.graph.nodes.values() 
                 if n.kind in (NodeKind.MODULE, NodeKind.FUNCTION)]
        
        if not roots and self.graph.nodes:
            self.result.add_warning(
                "Graph has no module or function root nodes",
                code="NO_ROOT"
            )
        
        # Check for orphaned nodes (not connected via composition)
        reachable = set()
        for root in roots:
            self._collect_reachable(root.id, reachable)
        
        for node_id, node in self.graph.nodes.items():
            if node_id not in reachable and node.kind not in (NodeKind.MODULE, NodeKind.FUNCTION):
                # Check if it's connected via data/control edges
                has_edges = any(e.source == node_id or e.target == node_id 
                               for e in self.graph.edges)
                if not has_edges:
                    self.result.add_warning(
                        f"Node '{node.name}' ({node.kind.value}) is unreachable",
                        node_id=node_id,
                        code="UNREACHABLE_NODE"
                    )
        
        # Check for duplicate node IDs (shouldn't happen with UUIDs)
        seen_ids = set()
        for node_id in self.graph.nodes:
            if node_id in seen_ids:
                self.result.add_error(
                    f"Duplicate node ID: {node_id}",
                    node_id=node_id,
                    code="DUPLICATE_NODE_ID"
                )
            seen_ids.add(node_id)
    
    def _collect_reachable(self, node_id: str, reachable: Set[str]):
        """Collect all nodes reachable via composition edges."""
        if node_id in reachable:
            return
        reachable.add(node_id)
        for edge in self.graph.edges:
            if edge.source == node_id and edge.kind == EdgeKind.COMPOSITION:
                self._collect_reachable(edge.target, reachable)
    
    # --- Port Connection Validation ---
    
    def _validate_port_connections(self):
        """Validate that all edge connections match port definitions."""
        for edge in self.graph.edges:
            source_node = self.graph.nodes.get(edge.source)
            target_node = self.graph.nodes.get(edge.target)
            
            if not source_node or not target_node:
                continue  # Already caught in basic validation
            
            # Check source port exists and is output
            if edge.source_port:
                source_port = source_node.ports.get(edge.source_port)
                if not source_port:
                    self.result.add_error(
                        f"Source port '{edge.source_port}' not found on node '{source_node.name}'",
                        edge_id=edge.id,
                        code="MISSING_SOURCE_PORT"
                    )
                elif source_port.is_input:
                    self.result.add_error(
                        f"Source port '{edge.source_port}' is an input port, not output",
                        edge_id=edge.id,
                        code="PORT_DIRECTION_MISMATCH"
                    )
            
            # Check target port exists and is input
            if edge.target_port:
                target_port = target_node.ports.get(edge.target_port)
                if not target_port:
                    self.result.add_error(
                        f"Target port '{edge.target_port}' not found on node '{target_node.name}'",
                        edge_id=edge.id,
                        code="MISSING_TARGET_PORT"
                    )
                elif not target_port.is_input:
                    self.result.add_error(
                        f"Target port '{edge.target_port}' is an output port, not input",
                        edge_id=edge.id,
                        code="PORT_DIRECTION_MISMATCH"
                    )
            
            # Check required ports are connected
            if edge.kind == EdgeKind.DATA:
                self._check_required_ports(source_node, target_node, edge)
    
    def _check_required_ports(self, source: Node, target: Node, edge: Edge):
        """Check that required input ports have connections."""
        # For target node, check all required input ports
        for port_name, port in target.ports.items():
            if port.is_input and port.is_required:
                # Check if this port has an incoming data edge
                has_connection = any(
                    e.target == target.id and e.target_port == port_name and e.kind == EdgeKind.DATA
                    for e in self.graph.edges
                )
                if not has_connection:
                    self.result.add_warning(
                        f"Required input port '{port_name}' on node '{target.name}' is not connected",
                        node_id=target.id,
                        code="UNCONNECTED_REQUIRED_PORT"
                    )
    
    # --- Control Flow Validation ---
    
    def _validate_control_flow(self):
        """Validate control flow structure."""
        for node in self.graph.nodes.values():
            if node.kind == NodeKind.IF:
                self._validate_if_node(node)
            elif node.kind == NodeKind.LOOP:
                self._validate_loop_node(node)
            elif node.kind == NodeKind.MATCH:
                self._validate_match_node(node)
            elif node.kind == NodeKind.TRY:
                self._validate_try_node(node)
            elif node.kind in (NodeKind.SEQUENCE, NodeKind.PARALLEL):
                self._validate_compound_node(node)
    
    def _validate_if_node(self, node: Node):
        """Validate if-then-else structure."""
        # Check condition port
        cond_port = node.ports.get("condition")
        if not cond_port:
            self.result.add_error(
                f"If node '{node.name}' missing condition port",
                node_id=node.id,
                code="MISSING_CONDITION_PORT"
            )
        
        # Check then/else ports have control edges
        then_edges = [e for e in self.graph.edges 
                     if e.source == node.id and e.target_port == "then" and e.kind == EdgeKind.CONTROL]
        if not then_edges:
            self.result.add_warning(
                f"If node '{node.name}' has no 'then' branch",
                node_id=node.id,
                code="MISSING_THEN_BRANCH"
            )
    
    def _validate_loop_node(self, node: Node):
        """Validate loop structure."""
        body_edges = [e for e in self.graph.edges 
                     if e.source == node.id and e.target_port == "body" and e.kind == EdgeKind.CONTROL]
        if not body_edges:
            self.result.add_warning(
                f"Loop node '{node.name}' has no body",
                node_id=node.id,
                code="EMPTY_LOOP_BODY"
            )
    
    def _validate_match_node(self, node: Node):
        """Validate match expression."""
        scrutinee_edges = [e for e in self.graph.edges 
                          if e.target == node.id and e.target_port == "scrutinee" and e.kind == EdgeKind.DATA]
        if not scrutinee_edges:
            self.result.add_error(
                f"Match node '{node.name}' has no scrutinee",
                node_id=node.id,
                code="MISSING_SCRUTINEE"
            )
    
    def _validate_try_node(self, node: Node):
        """Validate try-catch-finally."""
        try_edges = [e for e in self.graph.edges 
                    if e.target == node.id and e.target_port == "try" and e.kind == EdgeKind.CONTROL]
        if not try_edges:
            self.result.add_error(
                f"Try node '{node.name}' has no try block",
                node_id=node.id,
                code="MISSING_TRY_BLOCK"
            )
    
    def _validate_compound_node(self, node: Node):
        """Validate sequence/parallel nodes have children."""
        # These should have composition edges to child nodes
        children = self.graph.get_children(node.id)
        if not children:
            self.result.add_warning(
                f"{node.kind.value} node '{node.name}' has no children",
                node_id=node.id,
                code="EMPTY_COMPOUND"
            )
    
    # --- Composition Validation ---
    
    def _validate_composition(self):
        """Validate composition hierarchy."""
        # Each node should have at most one parent via composition
        parent_count = defaultdict(int)
        for edge in self.graph.edges:
            if edge.kind == EdgeKind.COMPOSITION:
                parent_count[edge.target] += 1
        
        for node_id, count in parent_count.items():
            if count > 1:
                self.result.add_error(
                    f"Node has {count} parents via composition edges",
                    node_id=node_id,
                    code="MULTIPLE_PARENTS"
                )
        
        # Check for cycles in composition
        visited = set()
        rec_stack = set()
        
        def check_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for edge in self.graph.edges:
                if edge.source == node_id and edge.kind == EdgeKind.COMPOSITION:
                    if edge.target not in visited:
                        if check_cycle(edge.target):
                            return True
                    elif edge.target in rec_stack:
                        self.result.add_error(
                            "Cycle detected in composition hierarchy",
                            node_id=node_id,
                            code="COMPOSITION_CYCLE"
                        )
                        return True
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.graph.nodes:
            if node_id not in visited:
                check_cycle(node_id)
    
    # --- Type Validation ---
    
    def _validate_types(self):
        """Type check the graph."""
        # Initialize type environment with built-ins
        self._setup_builtins()
        
        # Infer types for all nodes
        for node in self.graph.nodes.values():
            self._infer_node_type(node)
        
        # Check data edge type compatibility
        for edge in self.graph.edges:
            if edge.kind == EdgeKind.DATA:
                self._check_edge_type_compatibility(edge)
    
    def _setup_builtins(self):
        """Set up built-in types in environment."""
        self.type_env.define_type("Unit", UNIT)
        self.type_env.define_type("Bool", BOOL)
        self.type_env.define_type("Int", INT)
        self.type_env.define_type("Float", FLOAT)
        self.type_env.define_type("String", STRING)
        self.type_env.define_type("Any", ANY)
        self.type_env.define_type("Never", NEVER)
        
        # Built-in functions
        self.type_env.define("print", TypeScheme(
            [],
            make_function([STRING], UNIT, [EFFECT_IO])
        ))
        self.type_env.define("read_line", TypeScheme(
            [],
            make_function([], STRING, [EFFECT_IO])
        ))
    
    def _infer_node_type(self, node: Node) -> Optional[Type]:
        """Infer the type of a node."""
        if node.id in self._node_types:
            return self._node_types[node.id]
        
        node_type = None
        
        if node.kind == NodeKind.LITERAL:
            node_type = self._infer_literal_type(node)
        elif node.kind == NodeKind.VARIABLE:
            node_type = self._infer_variable_type(node)
        elif node.kind == NodeKind.PARAMETER:
            node_type = self._infer_parameter_type(node)
        elif node.kind in (NodeKind.ARITHMETIC, NodeKind.LOGIC, NodeKind.COMPARISON):
            node_type = self._infer_op_type(node)
        elif node.kind == NodeKind.CALL:
            node_type = self._infer_call_type(node)
        elif node.kind == NodeKind.FUNCTION:
            node_type = self._infer_function_type(node)
        elif node.kind == NodeKind.IF:
            node_type = self._infer_if_type(node)
        elif node.kind == NodeKind.SEQUENCE:
            node_type = self._infer_sequence_type(node)
        # ... more cases
        
        if node_type:
            self._node_types[node.id] = node_type
        
        return node_type
    
    def _infer_literal_type(self, node: Node) -> Type:
        from .nodes import LiteralNode
        if isinstance(node, LiteralNode) and node.literal_type:
            return self._typeref_to_type(node.literal_type)
        return ANY
    
    def _infer_variable_type(self, node: Node) -> Type:
        from .nodes import VariableNode
        if isinstance(node, VariableNode) and node.var_type:
            return self._typeref_to_type(node.var_type)
        # Look up in environment
        scheme = self.type_env.lookup(node.name if hasattr(node, 'var_name') else node.name)
        if scheme:
            return scheme.instantiate(lambda: TypeVar("_"))
        return ANY
    
    def _infer_parameter_type(self, node: Node) -> Type:
        from .nodes import ParameterNode
        if isinstance(node, ParameterNode) and node.param_type:
            return self._typeref_to_type(node.param_type)
        return ANY
    
    def _infer_op_type(self, node: Node) -> Type:
        from .nodes import ArithmeticNode, LogicNode, ComparisonNode
        if isinstance(node, ArithmeticNode):
            return INT  # Simplified
        elif isinstance(node, LogicNode):
            return BOOL
        elif isinstance(node, ComparisonNode):
            return BOOL
        return ANY
    
    def _infer_call_type(self, node: Node) -> Type:
        from .nodes import CallNode
        if isinstance(node, CallNode) and node.result_type:
            return self._typeref_to_type(node.result_type)
        return ANY
    
    def _infer_function_type(self, node: Node) -> Type:
        from .nodes import FunctionNode
        if isinstance(node, FunctionNode):
            param_types = [self._typeref_to_type(p.param_type) for p in node.params if p.param_type]
            ret_type = self._typeref_to_type(node.return_type) if node.return_type else UNIT
            effects = [self._parse_effect(e) for e in node.effects]
            return make_function(param_types, ret_type, effects)
        return ANY
    
    def _infer_if_type(self, node: Node) -> Type:
        # Type of if is the join of then/else branches
        # Simplified: return Any for now
        return ANY
    
    def _infer_sequence_type(self, node: Node) -> Type:
        # Type of sequence is type of last expression
        return ANY
    
    def _typeref_to_type(self, ref: TypeRef) -> Type:
        """Convert TypeRef to Type."""
        if ref.name == "Int":
            return INT
        elif ref.name == "Bool":
            return BOOL
        elif ref.name == "Float":
            return FLOAT
        elif ref.name == "String":
            return STRING
        elif ref.name == "Unit":
            return UNIT
        elif ref.name == "Any":
            return ANY
        elif ref.name == "Never":
            return NEVER
        # Handle generics
        if ref.type_args:
            args = [self._typeref_to_type(a) for a in ref.type_args]
            if ref.name == "Option":
                return make_option(args[0])
            elif ref.name == "Result":
                return make_result(args[0], args[1])
            elif ref.name == "Array":
                return CompositeType(CompositeKind.ARRAY, args)
            elif ref.name == "Map":
                return CompositeType(CompositeKind.MAP, args)
        return AliasType(ref.name, ref.type_args)
    
    def _parse_effect(self, effect_str: str) -> Effect:
        if effect_str == "IO":
            return EFFECT_IO
        elif effect_str == "State":
            return EFFECT_STATE
        elif effect_str == "Exception":
            return EFFECT_EXCEPTION
        elif effect_str == "Async":
            return EFFECT_ASYNC
        return Effect(effect_str)
    
    def _check_edge_type_compatibility(self, edge: DataEdge):
        """Check that source output type matches target input type."""
        source_node = self.graph.nodes.get(edge.source)
        target_node = self.graph.nodes.get(edge.target)
        
        if not source_node or not target_node:
            return
        
        source_type = self._node_types.get(edge.source)
        target_type = self._node_types.get(edge.target)
        
        if source_type and target_type:
            # Get port types
            source_port = source_node.ports.get(edge.source_port)
            target_port = target_node.ports.get(edge.target_port)
            
            if source_port and source_port.type:
                source_port_type = self._typeref_to_type(source_port.type)
            else:
                source_port_type = source_type
            
            if target_port and target_port.type:
                target_port_type = self._typeref_to_type(target_port.type)
            else:
                target_port_type = target_type
            
            # Check compatibility
            errors = check_type(target_port_type, source_port_type, 
                              f"Edge {edge.id[:8]} {source_node.name} -> {target_node.name}")
            for err in errors:
                self.result.add_error(err.message, edge_id=edge.id, code="TYPE_MISMATCH")
    
    # --- Effect Validation ---
    
    def _validate_effects(self):
        """Validate effect annotations and handling."""
        for node in self.graph.nodes.values():
            if node.kind == NodeKind.FUNCTION:
                self._validate_function_effects(node)
            elif node.kind in (NodeKind.IO, NodeKind.STATE, NodeKind.EXCEPTION, NodeKind.ASYNC):
                self._validate_effect_node(node)
    
    def _validate_function_effects(self, node: Node):
        from .nodes import FunctionNode
        if isinstance(node, FunctionNode):
            # Check that all effects in body are declared
            body_effects = self._collect_effects(node.id)
            declared_effects = set(node.effects)
            for effect in body_effects:
                if effect not in declared_effects:
                    self.result.add_warning(
                        f"Function '{node.func_name}' uses undeclared effect '{effect}'",
                        node_id=node.id,
                        code="UNDECLARED_EFFECT"
                    )
    
    def _collect_effects(self, node_id: str) -> Set[str]:
        """Collect all effects used in a subgraph."""
        effects = set()
        visited = set()
        
        def collect(nid: str):
            if nid in visited:
                return
            visited.add(nid)
            node = self.graph.nodes.get(nid)
            if not node:
                return
            
            if node.kind in (NodeKind.IO, NodeKind.STATE, NodeKind.EXCEPTION, NodeKind.ASYNC):
                effects.add(node.kind.value)
            
            # Traverse control flow
            for edge in self.graph.get_control_edges_from(nid):
                collect(edge.target)
            # Traverse data flow
            for edge in self.graph.get_data_edges_from(nid):
                collect(edge.target)
            # Traverse composition
            for child in self.graph.get_children(nid):
                collect(child.id)
        
        collect(node_id)
        return effects
    
    def _validate_effect_node(self, node: Node):
        """Validate effect node has proper handling."""
        # Check that effect nodes are within a function that declares the effect
        parent_func = self._find_enclosing_function(node.id)
        if parent_func:
            from .nodes import FunctionNode
            if isinstance(parent_func, FunctionNode):
                if node.kind.value not in parent_func.effects:
                    self.result.add_warning(
                        f"Effect node '{node.kind.value}' not declared in enclosing function",
                        node_id=node.id,
                        code="EFFECT_NOT_DECLARED"
                    )
    
    def _find_enclosing_function(self, node_id: str) -> Optional[Node]:
        """Find the enclosing function node via composition hierarchy."""
        current = node_id
        while current:
            parent = self.graph.get_parent(current)
            if parent and parent.kind == NodeKind.FUNCTION:
                return parent
            current = parent.id if parent else None
        return None
    
    # --- Contract Validation ---
    
    def _validate_contracts(self):
        """Validate preconditions, postconditions, invariants."""
        for node in self.graph.nodes.values():
            if node.kind == NodeKind.FUNCTION:
                self._validate_function_contracts(node)
            elif node.kind == NodeKind.CONTRACT:
                self._validate_contract_node(node)
    
    def _validate_function_contracts(self, node: Node):
        from .nodes import FunctionNode, ContractNode
        if isinstance(node, FunctionNode):
            for contract in node.contracts:
                # Contract expression should be boolean
                contract_type = self._node_types.get(contract.id)
                if contract_type and not self._is_bool_type(contract_type):
                    self.result.add_warning(
                        f"Contract expression should be boolean",
                        node_id=contract.id,
                        code="CONTRACT_NOT_BOOLEAN"
                    )
    
    def _validate_contract_node(self, node: Node):
        from .nodes import ContractNode
        if isinstance(node, ContractNode) and node.expression:
            expr_type = self._node_types.get(node.expression.id)
            if expr_type and not self._is_bool_type(expr_type):
                self.result.add_warning(
                    f"Contract expression should be boolean",
                    node_id=node.expression.id,
                    code="CONTRACT_NOT_BOOLEAN"
                )
    
    def _is_bool_type(self, type_: Type) -> bool:
        if isinstance(type_, PrimitiveType):
            return type_.kind == PrimitiveKind.BOOL
        return False
    
    # --- Scope Validation ---
    
    def _validate_scopes(self):
        """Validate variable scoping and binding."""
        # Build scope hierarchy
        scopes = self._build_scope_hierarchy()
        
        # Check variable references
        for node in self.graph.nodes.values():
            if node.kind == NodeKind.VARIABLE:
                self._validate_variable_reference(node, scopes)
    
    def _build_scope_hierarchy(self) -> Dict[str, List[str]]:
        """Build mapping from scope node to variables defined in it."""
        scopes = defaultdict(list)
        for node in self.graph.nodes.values():
            if node.kind == NodeKind.SCOPE:
                # Find variable definitions in this scope
                for child in self.graph.get_children(node.id):
                    if child.kind == NodeKind.VARIABLE:
                        scopes[node.id].append(child.name if hasattr(child, 'var_name') else child.name)
        return scopes
    
    def _validate_variable_reference(self, node: Node, scopes: Dict[str, List[str]]):
        from .nodes import VariableNode
        if isinstance(node, VariableNode):
            var_name = node.var_name
            # Find enclosing scope
            scope = self._find_enclosing_scope(node.id)
            if scope:
                # Check if variable is defined in this or parent scope
                found = False
                current_scope = scope
                while current_scope:
                    if var_name in scopes.get(current_scope.id, []):
                        found = True
                        break
                    current_scope = self.graph.get_parent(current_scope.id)
                if not found:
                    self.result.add_warning(
                        f"Variable '{var_name}' may be unbound",
                        node_id=node.id,
                        code="POSSIBLY_UNBOUND_VARIABLE"
                    )
    
    def _find_enclosing_scope(self, node_id: str) -> Optional[Node]:
        """Find enclosing scope node."""
        current = node_id
        while current:
            parent = self.graph.get_parent(current)
            if parent and parent.kind == NodeKind.SCOPE:
                return parent
            current = parent.id if parent else None
        return None


# --- Validation Entry Point ---

def validate_graph(graph: Graph) -> ValidationResult:
    """Validate a GIR graph."""
    validator = GraphValidator(graph)
    return validator.validate()


def validate_node(node: Node, graph: Graph) -> ValidationResult:
    """Validate a single node in context of graph."""
    validator = GraphValidator(graph)
    validator._infer_node_type(node)
    # Check edges connected to this node
    for edge in graph.edges:
        if edge.source == node.id or edge.target == node.id:
            if edge.kind == EdgeKind.DATA:
                validator._check_edge_type_compatibility(edge)
    return validator.result