"""
GIR (Graph Intermediate Representation) - Node Definitions
Core node types for the OREO language graph representation.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from uuid import uuid4


class NodeKind(Enum):
    """Categories of nodes in the GIR."""
    # Value nodes - represent data
    LITERAL = "literal"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    CONSTANT = "constant"
    
    # Operation nodes - compute values
    ARITHMETIC = "arithmetic"
    LOGIC = "logic"
    COMPARISON = "comparison"
    CAST = "cast"
    CALL = "call"
    INDEX = "index"
    FIELD_ACCESS = "field_access"
    
    # Control flow nodes
    IF = "if"
    LOOP = "loop"
    MATCH = "match"
    TRY = "try"
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    BREAK = "break"
    CONTINUE = "continue"
    RETURN = "return"
    
    # Type nodes
    PRIMITIVE_TYPE = "primitive_type"
    COMPOSITE_TYPE = "composite_type"
    FUNCTION_TYPE = "function_type"
    EFFECT_TYPE = "effect_type"
    GENERIC_TYPE = "generic_type"
    
    # Effect nodes
    IO = "io"
    STATE = "state"
    EXCEPTION = "exception"
    ASYNC = "async"
    RESOURCE = "resource"
    
    # Meta nodes
    CONTRACT = "contract"
    ANNOTATION = "annotation"
    DOCUMENTATION = "documentation"
    SOURCE_MAP = "source_map"
    
    # Module/scope nodes
    MODULE = "module"
    FUNCTION = "function"
    SCOPE = "scope"


class ArithmeticOp(Enum):
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    MOD = "mod"
    POW = "pow"
    NEG = "neg"


class LogicOp(Enum):
    AND = "and"
    OR = "or"
    NOT = "not"
    XOR = "xor"


class ComparisonOp(Enum):
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"


@dataclass
class Port:
    """A typed connection point on a node."""
    name: str
    type: Optional["TypeRef"] = None
    is_input: bool = True
    is_required: bool = True
    default_value: Optional[Any] = None
    description: str = ""
    
    def __hash__(self):
        return hash((self.name, self.is_input))


@dataclass
class TypeRef:
    """Reference to a type (can be forward reference)."""
    name: str
    type_args: List["TypeRef"] = field(default_factory=list)
    is_mutable: bool = False
    effects: List[str] = field(default_factory=list)
    
    def __str__(self):
        args = f"[{', '.join(str(a) for a in self.type_args)}]" if self.type_args else ""
        mut = "mut " if self.is_mutable else ""
        eff = f" [{', '.join(self.effects)}]" if self.effects else ""
        return f"{mut}{self.name}{args}{eff}"


@dataclass
class Node:
    """Base node in the GIR."""
    # Defaulted so concrete subclasses (which set their own kind in
    # __post_init__) can be constructed without passing it.
    kind: NodeKind = NodeKind.LITERAL
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    ports: Dict[str, Port] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    source_location: Optional[Dict[str, Any]] = None  # file, line, col, nl_text
    parent: Optional["Node"] = None  # for hierarchical graphs
    
    def add_port(self, port: Port) -> "Node":
        self.ports[port.name] = port
        return self
    
    def get_port(self, name: str) -> Optional[Port]:
        return self.ports.get(name)
    
    def input_ports(self) -> List[Port]:
        return [p for p in self.ports.values() if p.is_input]
    
    def output_ports(self) -> List[Port]:
        return [p for p in self.ports.values() if not p.is_input]
    
    def __hash__(self):
        return hash(self.id)


# --- Value Nodes ---

@dataclass
class LiteralNode(Node):
    value: Any = None
    literal_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.LITERAL
        if self.literal_type:
            self.add_port(Port("value", self.literal_type, is_input=False))
            self.add_port(Port("result", self.literal_type, is_input=False))


@dataclass
class VariableNode(Node):
    var_name: str = ""
    var_type: Optional[TypeRef] = None
    is_mutable: bool = False
    
    def __post_init__(self):
        self.kind = NodeKind.VARIABLE
        if self.var_type:
            self.add_port(Port("output", self.var_type, is_input=False))
            self.add_port(Port("value", self.var_type, is_input=True))  # for assignment
            self.add_port(Port("result", self.var_type, is_input=False))


@dataclass
class ParameterNode(Node):
    param_name: str = ""
    param_type: Optional[TypeRef] = None
    default_value: Optional[Any] = None
    
    def __post_init__(self):
        self.kind = NodeKind.PARAMETER
        if self.param_type:
            self.add_port(Port("value", self.param_type, is_input=False))
            self.add_port(Port("result", self.param_type, is_input=False))


@dataclass
class ConstantNode(Node):
    const_name: str = ""
    const_type: Optional[TypeRef] = None
    value: Any = None
    
    def __post_init__(self):
        self.kind = NodeKind.CONSTANT
        if self.const_type:
            self.add_port(Port("value", self.const_type, is_input=False))
            self.add_port(Port("result", self.const_type, is_input=False))


# --- Operation Nodes ---

@dataclass
class ArithmeticNode(Node):
    op: ArithmeticOp = ArithmeticOp.ADD
    result_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.ARITHMETIC
        self.add_port(Port("lhs", TypeRef("Int"), is_input=True))
        self.add_port(Port("rhs", TypeRef("Int"), is_input=True))
        self.add_port(Port("result", self.result_type or TypeRef("Any"), is_input=False))


@dataclass
class LogicNode(Node):
    op: LogicOp = LogicOp.AND
    result_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.LOGIC
        self.add_port(Port("lhs", TypeRef("Bool"), is_input=True))
        if self.op != LogicOp.NOT:
            self.add_port(Port("rhs", TypeRef("Bool"), is_input=True))
        self.add_port(Port("result", self.result_type or TypeRef("Any"), is_input=False))


@dataclass
class ComparisonNode(Node):
    op: ComparisonOp = ComparisonOp.EQ
    result_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.COMPARISON
        self.add_port(Port("lhs", TypeRef("Int"), is_input=True))
        self.add_port(Port("rhs", TypeRef("Int"), is_input=True))
        self.add_port(Port("result", self.result_type or TypeRef("Any"), is_input=False))


@dataclass
class CastNode(Node):
    target_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.CAST
        self.add_port(Port("value", TypeRef("Any"), is_input=True))
        self.add_port(Port("result", self.target_type or TypeRef("Any"), is_input=False))


@dataclass
class CallNode(Node):
    function: Optional[Node] = None  # FunctionNode or VariableNode
    type_args: List[TypeRef] = field(default_factory=list)
    result_type: Optional[TypeRef] = None
    effects: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.kind = NodeKind.CALL
        self.add_port(Port("function", TypeRef("Any"), is_input=True))
        self.add_port(Port("result", self.result_type or TypeRef("Any"), is_input=False))
        # Arguments added dynamically based on function signature


@dataclass
class IndexNode(Node):
    """Array/map indexing."""
    result_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.INDEX
        self.add_port(Port("collection", TypeRef("Array"), is_input=True))
        self.add_port(Port("index", TypeRef("Int"), is_input=True))
        self.add_port(Port("result", self.result_type or TypeRef("Any"), is_input=False))


@dataclass
class FieldAccessNode(Node):
    field_name: str = ""
    result_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.FIELD_ACCESS
        self.add_port(Port("object", TypeRef("Any"), is_input=True))
        self.add_port(Port("result", self.result_type or TypeRef("Any"), is_input=False))


# --- Control Flow Nodes ---

@dataclass
class IfNode(Node):
    """If-then-else with optional else branch."""
    
    def __post_init__(self):
        self.kind = NodeKind.IF
        self.add_port(Port("condition", TypeRef("Bool"), is_input=True))
        self.add_port(Port("then", TypeRef("Unit"), is_input=True))
        self.add_port(Port("else", TypeRef("Unit"), is_input=True, is_required=False))
        self.add_port(Port("result", TypeRef("Any"), is_input=False))


@dataclass
class LoopNode(Node):
    """Loop with optional iterator."""
    iterator_var: Optional[str] = None
    iterator_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.LOOP
        if self.iterator_var and self.iterator_type:
            self.add_port(Port("collection", TypeRef("Array"), is_input=True))
        self.add_port(Port("body", TypeRef("Unit"), is_input=True))
        self.add_port(Port("result", TypeRef("Unit"), is_input=False))


@dataclass
class MatchNode(Node):
    """Pattern matching."""
    
    def __post_init__(self):
        self.kind = NodeKind.MATCH
        self.add_port(Port("scrutinee", TypeRef("Any"), is_input=True))
        # Cases added dynamically
        self.add_port(Port("result", TypeRef("Any"), is_input=False))


@dataclass
class TryNode(Node):
    """Try-catch-finally."""
    
    def __post_init__(self):
        self.kind = NodeKind.TRY
        self.add_port(Port("try", TypeRef("Any"), is_input=True))
        self.add_port(Port("catch", TypeRef("Any"), is_input=True, is_required=False))
        self.add_port(Port("finally", TypeRef("Unit"), is_input=True, is_required=False))
        self.add_port(Port("result", TypeRef("Any"), is_input=False))


@dataclass
class SequenceNode(Node):
    """Sequential execution."""
    
    def __post_init__(self):
        self.kind = NodeKind.SEQUENCE
        # Statements added dynamically
        self.add_port(Port("result", TypeRef("Any"), is_input=False))


@dataclass
class ParallelNode(Node):
    """Parallel execution."""
    
    def __post_init__(self):
        self.kind = NodeKind.PARALLEL
        # Branches added dynamically
        self.add_port(Port("results", TypeRef("Array"), is_input=False))


@dataclass
class BreakNode(Node):
    def __post_init__(self):
        self.kind = NodeKind.BREAK


@dataclass
class ContinueNode(Node):
    def __post_init__(self):
        self.kind = NodeKind.CONTINUE


@dataclass
class ReturnNode(Node):
    def __post_init__(self):
        self.kind = NodeKind.RETURN
        self.add_port(Port("value", TypeRef("Any"), is_input=True))


# --- Type Nodes ---

@dataclass
class PrimitiveTypeNode(Node):
    primitive_kind: str = ""  # Int, Bool, Float, Char, String, Bytes
    bit_width: Optional[int] = None
    
    def __post_init__(self):
        self.kind = NodeKind.PRIMITIVE_TYPE


@dataclass
class CompositeTypeNode(Node):
    """Tuple, Record, Sum, Array, Map, Option, Result."""
    composite_kind: str = ""  # tuple, record, sum, array, map, option, result
    fields: List[Port] = field(default_factory=list)
    type_args: List[TypeRef] = field(default_factory=list)
    
    def __post_init__(self):
        self.kind = NodeKind.COMPOSITE_TYPE


@dataclass
class FunctionTypeNode(Node):
    params: List[Port] = field(default_factory=list)
    return_type: Optional[TypeRef] = None
    effects: List[str] = field(default_factory=list)
    is_async: bool = False
    
    def __post_init__(self):
        self.kind = NodeKind.FUNCTION_TYPE


@dataclass
class EffectTypeNode(Node):
    effect_name: str = ""
    type_args: List[TypeRef] = field(default_factory=list)
    
    def __post_init__(self):
        self.kind = NodeKind.EFFECT_TYPE


@dataclass
class GenericTypeNode(Node):
    name: str = ""
    constraints: List[str] = field(default_factory=list)
    bounds: Dict[str, TypeRef] = field(default_factory=dict)
    
    def __post_init__(self):
        self.kind = NodeKind.GENERIC_TYPE


# --- Effect Nodes ---

@dataclass
class IONode(Node):
    operation: str = ""  # read, write, print, etc.
    resource_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.IO


@dataclass
class StateNode(Node):
    location: str = ""
    state_type: Optional[TypeRef] = None
    is_read: bool = True
    
    def __post_init__(self):
        self.kind = NodeKind.STATE


@dataclass
class ExceptionNode(Node):
    exception_type: Optional[TypeRef] = None
    is_throw: bool = False
    
    def __post_init__(self):
        self.kind = NodeKind.EXCEPTION


@dataclass
class AsyncNode(Node):
    async_kind: str = ""  # spawn, await, channel_send, channel_recv
    
    def __post_init__(self):
        self.kind = NodeKind.ASYNC


@dataclass
class ResourceNode(Node):
    resource_kind: str = ""  # acquire, release, use
    resource_type: Optional[TypeRef] = None
    
    def __post_init__(self):
        self.kind = NodeKind.RESOURCE


# --- Meta Nodes ---

@dataclass
class ContractNode(Node):
    """Preconditions, postconditions, invariants."""
    contract_kind: str = ""  # pre, post, invariant
    expression: Optional[Node] = None
    
    def __post_init__(self):
        self.kind = NodeKind.CONTRACT


@dataclass
class AnnotationNode(Node):
    key: str = ""
    value: Any = None
    
    def __post_init__(self):
        self.kind = NodeKind.ANNOTATION


@dataclass
class DocumentationNode(Node):
    text: str = ""
    format: str = "markdown"  # markdown, plain
    
    def __post_init__(self):
        self.kind = NodeKind.DOCUMENTATION


@dataclass
class SourceMapNode(Node):
    """Maps graph nodes to natural language source."""
    nl_text: str = ""
    start_offset: int = 0
    end_offset: int = 0
    confidence: float = 1.0
    
    def __post_init__(self):
        self.kind = NodeKind.SOURCE_MAP


# --- Module/Scope Nodes ---

@dataclass
class ModuleNode(Node):
    module_name: str = ""
    exports: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.kind = NodeKind.MODULE


@dataclass
class FunctionNode(Node):
    """Function definition with body."""
    func_name: str = ""
    params: List[ParameterNode] = field(default_factory=list)
    return_type: Optional[TypeRef] = None
    effects: List[str] = field(default_factory=list)
    body: Optional[Node] = None
    contracts: List[ContractNode] = field(default_factory=list)
    is_async: bool = False
    is_public: bool = False
    
    def __post_init__(self):
        self.kind = NodeKind.FUNCTION
        for param in self.params:
            self.add_port(Port(param.param_name, param.param_type, is_input=True))
        if self.return_type:
            self.add_port(Port("return", self.return_type, is_input=False))


@dataclass
class ScopeNode(Node):
    """Lexical scope for variable bindings."""
    scope_name: str = ""
    bindings: Dict[str, VariableNode] = field(default_factory=dict)
    
    def __post_init__(self):
        self.kind = NodeKind.SCOPE


# --- Factory Functions ---

def create_literal(value: Any, literal_type: Optional[TypeRef] = None) -> LiteralNode:
    """Create a literal node with inferred type."""
    if literal_type is None:
        if isinstance(value, bool):
            literal_type = TypeRef("Bool")
        elif isinstance(value, int):
            literal_type = TypeRef("Int", [])
        elif isinstance(value, float):
            literal_type = TypeRef("Float", [])
        elif isinstance(value, str):
            literal_type = TypeRef("String")
        elif value is None:
            literal_type = TypeRef("Unit")
        else:
            literal_type = TypeRef("Any")
    return LiteralNode(value=value, literal_type=literal_type)


def create_variable(name: str, var_type: TypeRef, mutable: bool = False) -> VariableNode:
    return VariableNode(var_name=name, var_type=var_type, is_mutable=mutable)


def create_parameter(name: str, param_type: TypeRef, default: Any = None) -> ParameterNode:
    return ParameterNode(param_name=name, param_type=param_type, default_value=default)


def create_call(function: Node, args: List[Node], result_type: Optional[TypeRef] = None) -> CallNode:
    call = CallNode(result_type=result_type)
    call.add_port(Port("function", TypeRef("Function"), is_input=True))
    for i, arg in enumerate(args):
        call.add_port(Port(f"arg{i}", TypeRef("Any"), is_input=True))
    return call


def create_if(condition: Node, then_branch: Node, else_branch: Optional[Node] = None) -> IfNode:
    if_node = IfNode()
    # Ports will be connected via edges
    return if_node


def create_function(name: str, params: List[ParameterNode], return_type: TypeRef, body: Node) -> FunctionNode:
    return FunctionNode(
        func_name=name,
        params=params,
        return_type=return_type,
        body=body
    )


# --- Serialization ---

def node_to_dict(node: Node) -> Dict[str, Any]:
    """Serialize node to dictionary."""
    result = {
        "id": node.id,
        "kind": node.kind.value,
        "name": node.name,
        "description": node.description,
        "properties": node.properties,
        "ports": {name: {
            "name": p.name,
            "type": str(p.type) if p.type else None,
            "is_input": p.is_input,
            "is_required": p.is_required,
            "default_value": p.default_value,
            "description": p.description,
        } for name, p in node.ports.items()},
    }
    
    # Add type-specific fields
    if isinstance(node, LiteralNode):
        result["value"] = node.value
        result["literal_type"] = str(node.literal_type) if node.literal_type else None
    elif isinstance(node, VariableNode):
        result["var_name"] = node.var_name
        result["var_type"] = str(node.var_type) if node.var_type else None
        result["is_mutable"] = node.is_mutable
    elif isinstance(node, ArithmeticNode):
        result["op"] = node.op.value
    elif isinstance(node, LogicNode):
        result["op"] = node.op.value
    elif isinstance(node, ComparisonNode):
        result["op"] = node.op.value
    elif isinstance(node, FunctionNode):
        result["func_name"] = node.func_name
        result["params"] = [{"name": p.param_name, "type": str(p.param_type)} for p in node.params]
        result["return_type"] = str(node.return_type) if node.return_type else None
        result["effects"] = node.effects
        result["is_async"] = node.is_async
        result["is_public"] = node.is_public
    # ... add more as needed
    
    if node.source_location:
        result["source_location"] = node.source_location
    
    return result


def dict_to_node(data: Dict[str, Any]) -> Node:
    """Deserialize node from dictionary."""
    kind = NodeKind(data["kind"])
    
    # Create appropriate node type
    if kind == NodeKind.LITERAL:
        node = LiteralNode(
            value=data.get("value"),
            literal_type=TypeRef(data["literal_type"]) if data.get("literal_type") else None
        )
    elif kind == NodeKind.VARIABLE:
        node = VariableNode(
            var_name=data.get("var_name", ""),
            var_type=TypeRef(data["var_type"]) if data.get("var_type") else None,
            is_mutable=data.get("is_mutable", False)
        )
    elif kind == NodeKind.PARAMETER:
        node = ParameterNode(
            param_name=data.get("param_name", ""),
            param_type=TypeRef(data["param_type"]) if data.get("param_type") else None,
            default_value=data.get("default_value")
        )
    elif kind == NodeKind.FUNCTION:
        node = FunctionNode(
            func_name=data.get("func_name", ""),
            params=[],  # Will be reconstructed from ports
            return_type=TypeRef(data["return_type"]) if data.get("return_type") else None,
            effects=data.get("effects", []),
            is_async=data.get("is_async", False),
            is_public=data.get("is_public", False)
        )
    else:
        node = Node(kind=kind)
    
    # Common fields
    node.id = data.get("id", str(uuid4()))
    node.name = data.get("name", "")
    node.description = data.get("description", "")
    node.properties = data.get("properties", {})
    
    # Reconstruct ports
    for name, pdata in data.get("ports", {}).items():
        port = Port(
            name=pdata["name"],
            type=TypeRef(pdata["type"]) if pdata.get("type") else None,
            is_input=pdata.get("is_input", True),
            is_required=pdata.get("is_required", True),
            default_value=pdata.get("default_value"),
            description=pdata.get("description", "")
        )
        node.ports[name] = port
    
    if data.get("source_location"):
        node.source_location = data["source_location"]
    
    return node