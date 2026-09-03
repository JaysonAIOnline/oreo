"""
GIR (Graph Intermediate Representation) Package
Core graph representation for the OREO language.
"""

from .nodes import (
    Node, NodeKind, Port, TypeRef,
    LiteralNode, VariableNode, ParameterNode, ConstantNode,
    ArithmeticNode, LogicNode, ComparisonNode, CastNode, CallNode,
    IndexNode, FieldAccessNode,
    IfNode, LoopNode, MatchNode, TryNode, SequenceNode, ParallelNode,
    BreakNode, ContinueNode, ReturnNode,
    PrimitiveTypeNode, CompositeTypeNode, FunctionTypeNode, EffectTypeNode, GenericTypeNode,
    IONode, StateNode, ExceptionNode, AsyncNode, ResourceNode,
    ContractNode, AnnotationNode, DocumentationNode, SourceMapNode,
    ModuleNode, FunctionNode, ScopeNode,
    create_literal, create_variable, create_parameter, create_call,
    create_if, create_function,
    node_to_dict, dict_to_node,
    ArithmeticOp, LogicOp, ComparisonOp,
)

from .edges import (
    Graph, Edge, EdgeKind,
    DataEdge, ControlEdge, DependencyEdge, CompositionEdge,
    AnnotationEdge, TypeEdge, ScopeEdge, EffectEdge, ContractEdge,
    connect_data, connect_control, connect_composition, annotate,
    set_type, add_effect, add_contract,
    edge_to_dict, dict_to_edge,
)

from .types import (
    Type, PrimitiveType, CompositeType, FunctionType, Effect, TypeVar,
    TypeVarType, ForAllType, AliasType, TypeEnvironment,
    TypeScheme, Trait, TraitMethod, WhereClause,
    RecordField, Variant,
    PrimitiveKind, CompositeKind, EffectKind,
    unify, apply_subst, check_type, UnificationError, TypeError,
    resolve_trait, check_trait_bounds,
    UNIT, BOOL, INT, UINT, FLOAT, CHAR, STRING, BYTES, NEVER, ANY,
    INT8, INT16, INT32, INT64, INT128,
    UINT8, UINT16, UINT32, UINT64, UINT128,
    FLOAT16, FLOAT32, FLOAT64, FLOAT80,
    make_tuple, make_record, make_sum, make_array, make_map,
    make_option, make_result, make_function,
    EFFECT_IO, EFFECT_STATE, EFFECT_EXCEPTION, EFFECT_ASYNC,
    EFFECT_RESOURCE, EFFECT_PANIC, EFFECT_NONDET,
    make_effect, make_effect_row,
)

from .validation import (
    ValidationSeverity, ValidationIssue, ValidationResult,
    GraphValidator, validate_graph, validate_node,
)

__all__ = [
    # Nodes
    "Node", "NodeKind", "Port", "TypeRef",
    "LiteralNode", "VariableNode", "ParameterNode", "ConstantNode",
    "ArithmeticNode", "LogicNode", "ComparisonNode", "CastNode", "CallNode",
    "IndexNode", "FieldAccessNode",
    "IfNode", "LoopNode", "MatchNode", "TryNode", "SequenceNode", "ParallelNode",
    "BreakNode", "ContinueNode", "ReturnNode",
    "PrimitiveTypeNode", "CompositeTypeNode", "FunctionTypeNode", "EffectTypeNode", "GenericTypeNode",
    "IONode", "StateNode", "ExceptionNode", "AsyncNode", "ResourceNode",
    "ContractNode", "AnnotationNode", "DocumentationNode", "SourceMapNode",
    "ModuleNode", "FunctionNode", "ScopeNode",
    "create_literal", "create_variable", "create_parameter", "create_call",
    "create_if", "create_function",
    "node_to_dict", "dict_to_node",
    "ArithmeticOp", "LogicOp", "ComparisonOp",
    
    # Edges
    "Graph", "Edge", "EdgeKind",
    "DataEdge", "ControlEdge", "DependencyEdge", "CompositionEdge",
    "AnnotationEdge", "TypeEdge", "ScopeEdge", "EffectEdge", "ContractEdge",
    "connect_data", "connect_control", "connect_composition", "annotate",
    "set_type", "add_effect", "add_contract",
    "edge_to_dict", "dict_to_edge",
    
    # Types
    "Type", "PrimitiveType", "CompositeType", "FunctionType", "Effect", "TypeVar",
    "TypeVarType", "ForAllType", "AliasType", "TypeEnvironment",
    "TypeScheme", "Trait", "TraitMethod", "WhereClause",
    "RecordField", "Variant",
    "PrimitiveKind", "CompositeKind", "EffectKind",
    "unify", "apply_subst", "check_type", "UnificationError", "TypeError",
    "resolve_trait", "check_trait_bounds",
    "UNIT", "BOOL", "INT", "UINT", "FLOAT", "CHAR", "STRING", "BYTES", "NEVER", "ANY",
    "INT8", "INT16", "INT32", "INT64", "INT128",
    "UINT8", "UINT16", "UINT32", "UINT64", "UINT128",
    "FLOAT16", "FLOAT32", "FLOAT64", "FLOAT80",
    "make_tuple", "make_record", "make_sum", "make_array", "make_map",
    "make_option", "make_result", "make_function",
    "EFFECT_IO", "EFFECT_STATE", "EFFECT_EXCEPTION", "EFFECT_ASYNC",
    "EFFECT_RESOURCE", "EFFECT_PANIC", "EFFECT_NONDET",
    "make_effect", "make_effect_row",
    
    # Validation
    "ValidationSeverity", "ValidationIssue", "ValidationResult",
    "GraphValidator", "validate_graph", "validate_node",
]