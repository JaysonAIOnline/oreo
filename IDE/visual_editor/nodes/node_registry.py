"""
Visual Editor - Node Registry
Registry of node types available in the visual editor palette.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from parser.gir import (
    Node, NodeKind, Port, TypeRef,
    LiteralNode, VariableNode, ParameterNode, FunctionNode,
    IfNode, CallNode, ArithmeticNode, LogicNode, ComparisonNode,
    SequenceNode, ParallelNode, ReturnNode,
    INT, BOOL, STRING, UNIT, make_function,
    create_literal, create_variable, create_parameter, create_call,
    create_if, create_function,
    ArithmeticOp, LogicOp, ComparisonOp,
)


class NodeCategory(Enum):
    """Categories for organizing nodes in the palette."""
    VALUES = "Values"
    OPERATIONS = "Operations"
    CONTROL_FLOW = "Control Flow"
    FUNCTIONS = "Functions"
    TYPES = "Types"
    EFFECTS = "Effects"
    META = "Meta"
    MODULES = "Modules"


@dataclass
class NodeTemplate:
    """Template for creating nodes from the palette."""
    kind: NodeKind
    category: NodeCategory
    name: str
    description: str
    default_ports: List[Port] = field(default_factory=list)
    default_properties: Dict[str, Any] = field(default_factory=dict)
    factory: Optional[Callable[..., Node]] = None
    icon: str = ""  # Icon identifier
    color: str = ""  # Override color
    tags: List[str] = field(default_factory=list)


class NodeRegistry:
    """Registry of all node types available in the visual editor."""
    
    def __init__(self):
        self._templates: Dict[NodeKind, NodeTemplate] = {}
        self._categories: Dict[NodeCategory, List[NodeKind]] = {}
        self._register_builtins()
    
    def _register_builtins(self):
        """Register all built-in node types."""
        
        # ===== VALUES =====
        
        self.register(NodeTemplate(
            kind=NodeKind.LITERAL,
            category=NodeCategory.VALUES,
            name="Literal",
            description="Constant value (number, string, boolean)",
            default_ports=[
                Port("value", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_literal_node,
            icon="literal",
            tags=["constant", "value"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.VARIABLE,
            category=NodeCategory.VALUES,
            name="Variable",
            description="Named variable reference",
            default_ports=[
                Port("value", TypeRef("Any"), is_input=True),
                Port("value", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_variable_node,
            icon="variable",
            tags=["reference", "mutable"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.PARAMETER,
            category=NodeCategory.VALUES,
            name="Parameter",
            description="Function parameter",
            default_ports=[
                Port("value", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_parameter_node,
            icon="parameter",
            tags=["function", "input"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.CONSTANT,
            category=NodeCategory.VALUES,
            name="Constant",
            description="Named constant value",
            default_ports=[
                Port("value", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_constant_node,
            icon="constant",
            tags=["constant", "immutable"],
        ))
        
        # ===== OPERATIONS =====
        
        self.register(NodeTemplate(
            kind=NodeKind.ARITHMETIC,
            category=NodeCategory.OPERATIONS,
            name="Arithmetic",
            description="Arithmetic operation (+, -, *, /, %, ^)",
            default_ports=[
                Port("lhs", TypeRef("Int"), is_input=True),
                Port("rhs", TypeRef("Int"), is_input=True),
                Port("result", TypeRef("Int"), is_input=False),
            ],
            default_properties={"op": "add"},
            factory=self._create_arithmetic_node,
            icon="arithmetic",
            tags=["math", "numeric"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.LOGIC,
            category=NodeCategory.OPERATIONS,
            name="Logic",
            description="Logical operation (and, or, not, xor)",
            default_ports=[
                Port("lhs", TypeRef("Bool"), is_input=True),
                Port("rhs", TypeRef("Bool"), is_input=True),
                Port("result", TypeRef("Bool"), is_input=False),
            ],
            default_properties={"op": "and"},
            factory=self._create_logic_node,
            icon="logic",
            tags=["boolean", "logical"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.COMPARISON,
            category=NodeCategory.OPERATIONS,
            name="Comparison",
            description="Comparison operation (==, !=, <, <=, >, >=)",
            default_ports=[
                Port("lhs", TypeRef("Int"), is_input=True),
                Port("rhs", TypeRef("Int"), is_input=True),
                Port("result", TypeRef("Bool"), is_input=False),
            ],
            default_properties={"op": "eq"},
            factory=self._create_comparison_node,
            icon="comparison",
            tags=["compare", "relational"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.CAST,
            category=NodeCategory.OPERATIONS,
            name="Cast",
            description="Type cast/conversion",
            default_ports=[
                Port("value", TypeRef("Any"), is_input=True),
                Port("result", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_cast_node,
            icon="cast",
            tags=["convert", "type"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.CALL,
            category=NodeCategory.OPERATIONS,
            name="Call",
            description="Function call",
            default_ports=[
                Port("function", TypeRef("Function"), is_input=True),
                Port("arg0", TypeRef("Any"), is_input=True),
            ],
            factory=self._create_call_node,
            icon="call",
            tags=["invoke", "function"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.INDEX,
            category=NodeCategory.OPERATIONS,
            name="Index",
            description="Array/map indexing",
            default_ports=[
                Port("collection", TypeRef("Array"), is_input=True),
                Port("index", TypeRef("Int"), is_input=True),
                Port("result", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_index_node,
            icon="index",
            tags=["array", "access"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.FIELD_ACCESS,
            category=NodeCategory.OPERATIONS,
            name="Field Access",
            description="Record/object field access",
            default_ports=[
                Port("object", TypeRef("Record"), is_input=True),
                Port("result", TypeRef("Any"), is_input=False),
            ],
            default_properties={"field_name": ""},
            factory=self._create_field_access_node,
            icon="field",
            tags=["record", "access"],
        ))
        
        # ===== CONTROL FLOW =====
        
        self.register(NodeTemplate(
            kind=NodeKind.IF,
            category=NodeCategory.CONTROL_FLOW,
            name="If",
            description="Conditional branch (if-then-else)",
            default_ports=[
                Port("condition", TypeRef("Bool"), is_input=True),
                Port("then", TypeRef("Unit"), is_input=True),
                Port("else", TypeRef("Unit"), is_input=True, is_required=False),
                Port("result", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_if_node,
            icon="if",
            tags=["branch", "conditional"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.LOOP,
            category=NodeCategory.CONTROL_FLOW,
            name="Loop",
            description="Loop with optional iterator",
            default_ports=[
                Port("collection", TypeRef("Array"), is_input=True),
                Port("body", TypeRef("Unit"), is_input=True),
                Port("result", TypeRef("Unit"), is_input=False),
            ],
            default_properties={"iterator_var": "", "iterator_type": None},
            factory=self._create_loop_node,
            icon="loop",
            tags=["iterate", "repeat"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.MATCH,
            category=NodeCategory.CONTROL_FLOW,
            name="Match",
            description="Pattern matching",
            default_ports=[
                Port("scrutinee", TypeRef("Any"), is_input=True),
                Port("result", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_match_node,
            icon="match",
            tags=["pattern", "switch"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.TRY,
            category=NodeCategory.CONTROL_FLOW,
            name="Try",
            description="Try-catch-finally error handling",
            default_ports=[
                Port("try", TypeRef("Unit"), is_input=True),
                Port("catch", TypeRef("Unit"), is_input=True, is_required=False),
                Port("finally", TypeRef("Unit"), is_input=True, is_required=False),
                Port("result", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_try_node,
            icon="try",
            tags=["error", "exception"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.SEQUENCE,
            category=NodeCategory.CONTROL_FLOW,
            name="Sequence",
            description="Sequential execution of statements",
            default_ports=[
                Port("result", TypeRef("Any"), is_input=False),
            ],
            factory=self._create_sequence_node,
            icon="sequence",
            tags=["block", "statements"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.PARALLEL,
            category=NodeCategory.CONTROL_FLOW,
            name="Parallel",
            description="Parallel execution of branches",
            default_ports=[
                Port("results", TypeRef("Array"), is_input=False),
            ],
            factory=self._create_parallel_node,
            icon="parallel",
            tags=["concurrent", "async"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.RETURN,
            category=NodeCategory.CONTROL_FLOW,
            name="Return",
            description="Return from function",
            default_ports=[
                Port("value", TypeRef("Any"), is_input=True),
            ],
            factory=self._create_return_node,
            icon="return",
            tags=["exit", "function"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.BREAK,
            category=NodeCategory.CONTROL_FLOW,
            name="Break",
            description="Break out of loop",
            default_ports=[],
            factory=lambda: Node(kind=NodeKind.BREAK),
            icon="break",
            tags=["loop", "exit"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.CONTINUE,
            category=NodeCategory.CONTROL_FLOW,
            name="Continue",
            description="Continue to next loop iteration",
            default_ports=[],
            factory=lambda: Node(kind=NodeKind.CONTINUE),
            icon="continue",
            tags=["loop", "skip"],
        ))
        
        # ===== FUNCTIONS =====
        
        self.register(NodeTemplate(
            kind=NodeKind.FUNCTION,
            category=NodeCategory.FUNCTIONS,
            name="Function",
            description="Function definition",
            default_ports=[],
            factory=self._create_function_node,
            icon="function",
            tags=["define", "callable"],
        ))
        
        # ===== TYPES =====
        
        self.register(NodeTemplate(
            kind=NodeKind.PRIMITIVE_TYPE,
            category=NodeCategory.TYPES,
            name="Primitive Type",
            description="Primitive type (Int, Bool, Float, String, etc.)",
            default_ports=[],
            default_properties={"primitive_kind": "Int", "bit_width": None},
            factory=self._create_primitive_type_node,
            icon="type",
            tags=["primitive", "builtin"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.COMPOSITE_TYPE,
            category=NodeCategory.TYPES,
            name="Composite Type",
            description="Composite type (Tuple, Record, Sum, Array, Map, Option, Result)",
            default_ports=[],
            default_properties={"composite_kind": "Record"},
            factory=self._create_composite_type_node,
            icon="composite",
            tags=["compound", "structure"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.FUNCTION_TYPE,
            category=NodeCategory.TYPES,
            name="Function Type",
            description="Function type signature",
            default_ports=[],
            factory=self._create_function_type_node,
            icon="fn_type",
            tags=["signature", "callable"],
        ))
        
        # ===== EFFECTS =====
        
        self.register(NodeTemplate(
            kind=NodeKind.IO,
            category=NodeCategory.EFFECTS,
            name="IO Effect",
            description="Input/output operation",
            default_ports=[
                Port("input", TypeRef("Any"), is_input=True),
                Port("output", TypeRef("Any"), is_input=False),
            ],
            default_properties={"operation": "print"},
            factory=self._create_io_node,
            icon="io",
            tags=["effect", "side-effect"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.STATE,
            category=NodeCategory.EFFECTS,
            name="State Effect",
            description="Mutable state access",
            default_ports=[
                Port("location", TypeRef("Ref"), is_input=True),
                Port("value", TypeRef("Any"), is_input=True),
                Port("result", TypeRef("Any"), is_input=False),
            ],
            default_properties={"is_read": True},
            factory=self._create_state_node,
            icon="state",
            tags=["effect", "mutation"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.EXCEPTION,
            category=NodeCategory.EFFECTS,
            name="Exception Effect",
            description="Throw or catch exception",
            default_ports=[
                Port("exception", TypeRef("Any"), is_input=True),
                Port("result", TypeRef("Never"), is_input=False),
            ],
            default_properties={"is_throw": True},
            factory=self._create_exception_node,
            icon="exception",
            tags=["effect", "error"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.ASYNC,
            category=NodeCategory.EFFECTS,
            name="Async Effect",
            description="Asynchronous operation (spawn, await, channel)",
            default_ports=[
                Port("input", TypeRef("Any"), is_input=True),
                Port("output", TypeRef("Any"), is_input=False),
            ],
            default_properties={"async_kind": "spawn"},
            factory=self._create_async_node,
            icon="async",
            tags=["effect", "concurrency"],
        ))
        
        # ===== META =====
        
        self.register(NodeTemplate(
            kind=NodeKind.CONTRACT,
            category=NodeCategory.META,
            name="Contract",
            description="Precondition, postcondition, or invariant",
            default_ports=[
                Port("expression", TypeRef("Bool"), is_input=True),
            ],
            default_properties={"contract_kind": "pre"},
            factory=self._create_contract_node,
            icon="contract",
            tags=["verify", "specification"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.ANNOTATION,
            category=NodeCategory.META,
            name="Annotation",
            description="Metadata annotation",
            default_ports=[],
            default_properties={"key": "", "value": None},
            factory=self._create_annotation_node,
            icon="annotation",
            tags=["metadata", "tag"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.DOCUMENTATION,
            category=NodeCategory.META,
            name="Documentation",
            description="Documentation comment",
            default_ports=[],
            default_properties={"text": "", "format": "markdown"},
            factory=self._create_documentation_node,
            icon="doc",
            tags=["comment", "docs"],
        ))
        
        # ===== MODULES =====
        
        self.register(NodeTemplate(
            kind=NodeKind.MODULE,
            category=NodeCategory.MODULES,
            name="Module",
            description="Top-level module",
            default_ports=[],
            default_properties={"module_name": "", "exports": [], "imports": []},
            factory=self._create_module_node,
            icon="module",
            tags=["package", "namespace"],
        ))
        
        self.register(NodeTemplate(
            kind=NodeKind.SCOPE,
            category=NodeCategory.MODULES,
            name="Scope",
            description="Lexical scope",
            default_ports=[],
            default_properties={"scope_name": ""},
            factory=self._create_scope_node,
            icon="scope",
            tags=["block", "local"],
        ))
    
    def register(self, template: NodeTemplate):
        """Register a node template."""
        self._templates[template.kind] = template
        if template.category not in self._categories:
            self._categories[template.category] = []
        if template.kind not in self._categories[template.category]:
            self._categories[template.category].append(template.kind)
    
    def get(self, kind: NodeKind) -> Optional[NodeTemplate]:
        """Get template by node kind."""
        return self._templates.get(kind)
    
    def get_by_category(self, category: NodeCategory) -> List[NodeTemplate]:
        """Get all templates in a category."""
        kinds = self._categories.get(category, [])
        return [self._templates[k] for k in kinds if k in self._templates]
    
    def all_categories(self) -> List[NodeCategory]:
        """Get all categories with registered nodes."""
        return list(self._categories.keys())
    
    def all_templates(self) -> List[NodeTemplate]:
        """Get all registered templates."""
        return list(self._templates.values())
    
    def create_node(self, kind: NodeKind, **kwargs) -> Node:
        """Create a node from template."""
        template = self._templates.get(kind)
        if not template:
            raise ValueError(f"No template for node kind: {kind}")
        
        if template.factory:
            return template.factory(**kwargs)
        
        # Default creation
        node = Node(kind=kind, name=template.name)
        for port in template.default_ports:
            node.add_port(port)
        node.properties.update(template.default_properties)
        node.properties.update(kwargs)
        return node
    
    def search(self, query: str) -> List[NodeTemplate]:
        """Search templates by name, description, or tags."""
        query = query.lower()
        results = []
        for template in self._templates.values():
            if (query in template.name.lower() or
                query in template.description.lower() or
                any(query in tag.lower() for tag in template.tags)):
                results.append(template)
        return results
    
    # --- Factory Methods ---
    
    def _create_literal_node(self, value: Any = 0, literal_type: TypeRef = None) -> Node:
        if literal_type is None:
            if isinstance(value, bool):
                literal_type = TypeRef("Bool")
            elif isinstance(value, int):
                literal_type = TypeRef("Int")
            elif isinstance(value, float):
                literal_type = TypeRef("Float")
            elif isinstance(value, str):
                literal_type = TypeRef("String")
            else:
                literal_type = TypeRef("Any")
        return create_literal(value, literal_type)
    
    def _create_variable_node(self, name: str = "x", var_type: TypeRef = None, mutable: bool = False) -> Node:
        if var_type is None:
            var_type = TypeRef("Any")
        return create_variable(name, var_type, mutable)
    
    def _create_parameter_node(self, name: str = "param", param_type: TypeRef = None, default: Any = None) -> Node:
        if param_type is None:
            param_type = TypeRef("Any")
        return create_parameter(name, param_type, default)
    
    def _create_constant_node(self, name: str = "CONST", const_type: TypeRef = None, value: Any = None) -> Node:
        if const_type is None:
            const_type = TypeRef("Any")
        from parser.gir import ConstantNode
        return ConstantNode(const_name=name, const_type=const_type, value=value)
    
    def _create_arithmetic_node(self, op: str = "add") -> Node:
        op_map = {
            "add": ArithmeticOp.ADD,
            "sub": ArithmeticOp.SUB,
            "mul": ArithmeticOp.MUL,
            "div": ArithmeticOp.DIV,
            "mod": ArithmeticOp.MOD,
            "pow": ArithmeticOp.POW,
            "neg": ArithmeticOp.NEG,
        }
        return ArithmeticNode(op=op_map.get(op, ArithmeticOp.ADD))
    
    def _create_logic_node(self, op: str = "and") -> Node:
        op_map = {
            "and": LogicOp.AND,
            "or": LogicOp.OR,
            "not": LogicOp.NOT,
            "xor": LogicOp.XOR,
        }
        return LogicNode(op=op_map.get(op, LogicOp.AND))
    
    def _create_comparison_node(self, op: str = "eq") -> Node:
        op_map = {
            "eq": ComparisonOp.EQ,
            "ne": ComparisonOp.NE,
            "lt": ComparisonOp.LT,
            "le": ComparisonOp.LE,
            "gt": ComparisonOp.GT,
            "ge": ComparisonOp.GE,
        }
        return ComparisonNode(op=op_map.get(op, ComparisonOp.EQ))
    
    def _create_cast_node(self, target_type: TypeRef = None) -> Node:
        from parser.gir import CastNode
        return CastNode(target_type=target_type or TypeRef("Any"))
    
    def _create_call_node(self, function: Node = None) -> Node:
        return create_call(function, [])
    
    def _create_index_node(self) -> Node:
        from parser.gir import IndexNode
        return IndexNode()
    
    def _create_field_access_node(self, field_name: str = "") -> Node:
        from parser.gir import FieldAccessNode
        return FieldAccessNode(field_name=field_name)
    
    def _create_if_node(self) -> Node:
        return IfNode()
    
    def _create_loop_node(self, iterator_var: str = "", iterator_type: TypeRef = None) -> Node:
        return LoopNode(iterator_var=iterator_var, iterator_type=iterator_type)
    
    def _create_match_node(self) -> Node:
        return MatchNode()
    
    def _create_try_node(self) -> Node:
        return TryNode()
    
    def _create_sequence_node(self) -> Node:
        return SequenceNode()
    
    def _create_parallel_node(self) -> Node:
        return ParallelNode()
    
    def _create_return_node(self) -> Node:
        return ReturnNode()
    
    def _create_function_node(self, name: str = "func", params: List = None, 
                              return_type: TypeRef = None, body: Node = None) -> Node:
        return create_function(name, params or [], return_type or TypeRef("Unit"), body or SequenceNode())
    
    def _create_primitive_type_node(self, primitive_kind: str = "Int", bit_width: int = None) -> Node:
        from parser.gir import PrimitiveTypeNode
        return PrimitiveTypeNode(primitive_kind=primitive_kind, bit_width=bit_width)
    
    def _create_composite_type_node(self, composite_kind: str = "Record") -> Node:
        from parser.gir import CompositeTypeNode
        return CompositeTypeNode(composite_kind=composite_kind)
    
    def _create_function_type_node(self) -> Node:
        from parser.gir import FunctionTypeNode
        return FunctionTypeNode()
    
    def _create_io_node(self, operation: str = "print") -> Node:
        from parser.gir import IONode
        return IONode(operation=operation)
    
    def _create_state_node(self, location: str = "", state_type: TypeRef = None, is_read: bool = True) -> Node:
        from parser.gir import StateNode
        return StateNode(location=location, state_type=state_type, is_read=is_read)
    
    def _create_exception_node(self, exception_type: TypeRef = None, is_throw: bool = True) -> Node:
        from parser.gir import ExceptionNode
        return ExceptionNode(exception_type=exception_type, is_throw=is_throw)
    
    def _create_async_node(self, async_kind: str = "spawn") -> Node:
        from parser.gir import AsyncNode
        return AsyncNode(async_kind=async_kind)
    
    def _create_contract_node(self, contract_kind: str = "pre", expression: Node = None) -> Node:
        from parser.gir import ContractNode
        return ContractNode(contract_kind=contract_kind, expression=expression)
    
    def _create_annotation_node(self, key: str = "", value: Any = None) -> Node:
        from parser.gir import AnnotationNode
        return AnnotationNode(key=key, value=value)
    
    def _create_documentation_node(self, text: str = "", format: str = "markdown") -> Node:
        from parser.gir import DocumentationNode
        return DocumentationNode(text=text, format=format)
    
    def _create_module_node(self, name: str = "main", exports: List = None, imports: List = None) -> Node:
        from parser.gir import ModuleNode
        return ModuleNode(module_name=name, exports=exports or [], imports=imports or [])
    
    def _create_scope_node(self, name: str = "scope") -> Node:
        from parser.gir import ScopeNode
        return ScopeNode(scope_name=name)


# Global registry instance
_REGISTRY: Optional[NodeRegistry] = None


def get_node_registry() -> NodeRegistry:
    """Get global node registry."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = NodeRegistry()
    return _REGISTRY


def register_node_template(template: NodeTemplate):
    """Register a custom node template."""
    get_node_registry().register(template)


def create_node(kind: NodeKind, **kwargs) -> Node:
    """Create a node from the global registry."""
    return get_node_registry().create_node(kind, **kwargs)


def get_palette_categories() -> List[Dict[str, Any]]:
    """Get palette structure for UI."""
    registry = get_node_registry()
    categories = []
    for category in registry.all_categories():
        templates = registry.get_by_category(category)
        categories.append({
            "category": category.value,
            "nodes": [
                {
                    "kind": t.kind.value,
                    "name": t.name,
                    "description": t.description,
                    "icon": t.icon,
                    "tags": t.tags,
                }
                for t in templates
            ],
        })
    return categories