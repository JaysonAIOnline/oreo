"""
OREO Runtime - Graph Interpreter
Executes GIR graphs directly.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Set, Union
from collections import defaultdict
import uuid

from parser.gir import (
    Graph, Node, NodeKind, Edge, EdgeKind, DataEdge, ControlEdge, CompositionEdge,
    LiteralNode, VariableNode, ParameterNode, FunctionNode,
    IfNode, LoopNode, SequenceNode, ParallelNode, ReturnNode,
    ArithmeticNode, LogicNode, ComparisonNode, CallNode,
    ArithmeticOp, LogicOp, ComparisonOp,
    INT, BOOL, STRING, UNIT, FunctionType,
    TypeRef,
    validate_graph,
)


class Value:
    """Runtime value representation."""
    
    def __init__(self, value: Any, type_: Any = None):
        self.value = value
        self.type = type_
    
    def __repr__(self):
        return f"Value({self.value!r}, type={self.type})"
    
    def __eq__(self, other):
        if not isinstance(other, Value):
            return False
        return self.value == other.value and self.type == other.type
    
    def is_truthy(self) -> bool:
        if isinstance(self.value, bool):
            return self.value
        if self.value is None:
            return False
        if isinstance(self.value, (int, float)):
            return self.value != 0
        if isinstance(self.value, str):
            return len(self.value) > 0
        if isinstance(self.value, (list, dict)):
            return len(self.value) > 0
        return True


@dataclass
class StackFrame:
    """Call stack frame."""
    function: FunctionNode
    locals: Dict[str, Value] = field(default_factory=dict)
    pc: int = 0  # program counter - index in sequence
    return_value: Optional[Value] = None
    parent_frame: Optional['StackFrame'] = None


@dataclass
class InterpreterState:
    """Global interpreter state."""
    globals: Dict[str, Value] = field(default_factory=dict)
    call_stack: List[StackFrame] = field(default_factory=list)
    heap: Dict[str, Any] = field(default_factory=dict)  # for allocated objects
    next_heap_id: int = 0
    
    def allocate(self, value: Any) -> str:
        """Allocate object on heap, return reference."""
        ref = f"ref_{self.next_heap_id}"
        self.next_heap_id += 1
        self.heap[ref] = value
        return ref
    
    def get_global(self, name: str) -> Optional[Value]:
        return self.globals.get(name)
    
    def set_global(self, name: str, value: Value):
        self.globals[name] = value
    
    def get_local(self, name: str) -> Optional[Value]:
        for frame in reversed(self.call_stack):
            if name in frame.locals:
                return frame.locals[name]
        return None
    
    def set_local(self, name: str, value: Value):
        for frame in reversed(self.call_stack):
            if name in frame.locals:
                frame.locals[name] = value
                return
        # If not found in any frame, set in current frame
        if self.call_stack:
            self.call_stack[-1].locals[name] = value
        else:
            self.globals[name] = value


class Interpreter:
    """Graph interpreter for OREO GIR."""
    
    def __init__(self, graph: Graph, debug: bool = False):
        self.graph = graph
        self.debug = debug
        self.state = InterpreterState()
        self._node_handlers: Dict[NodeKind, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """Register node type handlers."""
        self._node_handlers = {
            NodeKind.LITERAL: self._eval_literal,
            NodeKind.VARIABLE: self._eval_variable,
            NodeKind.PARAMETER: self._eval_parameter,
            NodeKind.FUNCTION: self._eval_function_def,
            NodeKind.CALL: self._eval_call,
            NodeKind.IF: self._eval_if,
            NodeKind.LOOP: self._eval_loop,
            NodeKind.SEQUENCE: self._eval_sequence,
            NodeKind.PARALLEL: self._eval_parallel,
            NodeKind.RETURN: self._eval_return,
            NodeKind.ARITHMETIC: self._eval_arithmetic,
            NodeKind.LOGIC: self._eval_logic,
            NodeKind.COMPARISON: self._eval_comparison,
        }
    
    def run(self, entry_point: str = "main", args: List[Value] = None) -> Value:
        """Run the program starting from entry point."""
        # Validate graph first
        result = validate_graph(self.graph)
        if result.has_errors():
            raise RuntimeError(f"Graph validation failed: {result}")
        
        # Find entry function
        entry_func = None
        for node in self.graph.nodes.values():
            if node.kind == NodeKind.FUNCTION and node.name == entry_point:
                entry_func = node
                break
        
        if not entry_func:
            # Try to find any function named main or the first function
            for node in self.graph.nodes.values():
                if node.kind == NodeKind.FUNCTION:
                    entry_func = node
                    break
        
        if not entry_func:
            raise RuntimeError("No entry function found")
        
        # Call entry function
        return self._call_function(entry_func, args or [])
    
    def _call_function(self, func: FunctionNode, args: List[Value]) -> Value:
        """Call a function."""
        # Create new stack frame
        frame = StackFrame(function=func)
        
        # Bind parameters
        for i, param in enumerate(func.params):
            if i < len(args):
                frame.locals[param.param_name] = args[i]
            elif param.default_value is not None:
                frame.locals[param.param_name] = Value(param.default_value)
            else:
                frame.locals[param.param_name] = Value(None)
        
        self.state.call_stack.append(frame)
        
        try:
            # Execute function body
            if func.body:
                result = self._eval_node(func.body)
            else:
                result = Value(None, UNIT)
            
            # Check for explicit return
            if frame.return_value is not None:
                result = frame.return_value
            
            return result
        finally:
            self.state.call_stack.pop()
    
    def _eval_node(self, node: Node) -> Value:
        """Evaluate a single node."""
        if self.debug:
            print(f"EVAL: {node.kind.value} ({node.id[:8]}) {node.name}")
        
        handler = self._node_handlers.get(node.kind)
        if handler:
            return handler(node)
        else:
            if self.debug:
                print(f"  No handler for {node.kind}")
            return Value(None, UNIT)
    
    def _get_input_values(self, node: Node) -> Dict[str, Value]:
        """Get values from incoming data edges."""
        inputs = {}
        for edge in self.graph.edges:
            if edge.kind == EdgeKind.DATA and edge.target == node.id:
                source_node = self.graph.nodes.get(edge.source)
                if source_node:
                    # Evaluate source if not already
                    source_value = self._eval_node(source_node)
                    inputs[edge.target_port] = source_value
        return inputs
    
    def _set_output_value(self, node: Node, port: str, value: Value):
        """Set output value (store for downstream nodes)."""
        # In a real implementation, we'd store this on the node or in a value map
        # For now, we'll attach it to the node
        if not hasattr(node, '_outputs'):
            node._outputs = {}
        node._outputs[port] = value
    
    def _get_output_value(self, node: Node, port: str) -> Optional[Value]:
        """Get output value from node."""
        if hasattr(node, '_outputs'):
            return node._outputs.get(port)
        return None
    
    # --- Node Handlers ---
    
    def _eval_literal(self, node: Node) -> Value:
        from parser.gir import LiteralNode
        if isinstance(node, LiteralNode):
            return Value(node.value, node.literal_type)
        return Value(None)
    
    def _eval_variable(self, node: Node) -> Value:
        from parser.gir import VariableNode
        if isinstance(node, VariableNode):
            # Check local scope first
            local = self.state.get_local(node.var_name)
            if local:
                return local
            # Check globals
            global_val = self.state.get_global(node.var_name)
            if global_val:
                return global_val
            # Return default/zero value
            return Value(None)
        return Value(None)
    
    def _eval_parameter(self, node: Node) -> Value:
        # Parameters are handled in _call_function
        return Value(None)
    
    def _eval_function_def(self, node: Node) -> Value:
        # Function definitions are registered, not executed inline
        return Value(None, UNIT)
    
    def _eval_call(self, node: Node) -> Value:
        from parser.gir import CallNode
        if isinstance(node, CallNode):
            # Get function to call
            func_value = self._get_output_value(node, "function")
            if func_value and isinstance(func_value.value, FunctionNode):
                func = func_value.value
            else:
                # Look up by name in current scope
                func = None
                # Try to get from inputs
                for edge in self.graph.edges:
                    if edge.kind == EdgeKind.DATA and edge.target == node.id and edge.target_port == "function":
                        source = self.graph.nodes.get(edge.source)
                        if source and source.kind == NodeKind.FUNCTION:
                            func = source
                            break
            
            if not func:
                raise RuntimeError(f"Function not found for call")
            
            # Collect arguments
            args = []
            for edge in self.graph.edges:
                if edge.kind == EdgeKind.DATA and edge.target == node.id and edge.target_port.startswith("arg"):
                    source = self.graph.nodes.get(edge.source)
                    if source:
                        args.append(self._eval_node(source))
            
            return self._call_function(func, args)
        return Value(None)
    
    def _eval_if(self, node: Node) -> Value:
        from parser.gir import IfNode
        if isinstance(node, IfNode):
            # Evaluate condition
            condition_value = None
            for edge in self.graph.edges:
                if edge.kind == EdgeKind.DATA and edge.target == node.id and edge.target_port == "condition":
                    source = self.graph.nodes.get(edge.source)
                    if source:
                        condition_value = self._eval_node(source)
                        break
            
            if condition_value and condition_value.is_truthy():
                # Execute then branch
                for edge in self.graph.edges:
                    if edge.kind == EdgeKind.CONTROL and edge.source == node.id and edge.target_port == "then":
                        then_node = self.graph.nodes.get(edge.target)
                        if then_node:
                            return self._eval_node(then_node)
            else:
                # Execute else branch
                for edge in self.graph.edges:
                    if edge.kind == EdgeKind.CONTROL and edge.source == node.id and edge.target_port == "else":
                        else_node = self.graph.nodes.get(edge.target)
                        if else_node:
                            return self._eval_node(else_node)
            
            return Value(None, UNIT)
        return Value(None)
    
    def _eval_loop(self, node: Node) -> Value:
        from parser.gir import LoopNode
        if isinstance(node, LoopNode):
            # Get iterator if present
            collection = None
            for edge in self.graph.edges:
                if edge.kind == EdgeKind.DATA and edge.target == node.id and edge.target_port == "collection":
                    source = self.graph.nodes.get(edge.source)
                    if source:
                        collection = self._eval_node(source)
                        break
            
            # Get body
            body_node = None
            for edge in self.graph.edges:
                if edge.kind == EdgeKind.CONTROL and edge.source == node.id and edge.target_port == "body":
                    body_node = self.graph.nodes.get(edge.target)
                    break
            
            if not body_node:
                return Value(None, UNIT)
            
            if collection and isinstance(collection.value, (list, tuple)):
                # For-each loop
                for item in collection.value:
                    # Create new frame for iteration
                    old_locals = self.state.call_stack[-1].locals.copy() if self.state.call_stack else {}
                    if node.iterator_var:
                        self.state.set_local(node.iterator_var, Value(item))
                    
                    result = self._eval_node(body_node)
                    
                    # Check for break/continue
                    # Restore locals
                    if self.state.call_stack:
                        self.state.call_stack[-1].locals = old_locals
                    
                    # TODO: handle break/continue
            else:
                # While-like loop - execute once for now
                self._eval_node(body_node)
            
            return Value(None, UNIT)
        return Value(None)
    
    def _eval_sequence(self, node: Node) -> Value:
        from parser.gir import SequenceNode
        if isinstance(node, SequenceNode):
            result = Value(None, UNIT)
            # Execute children in order (composition edges)
            children = self.graph.get_children(node.id)
            for child in children:
                result = self._eval_node(child)
                # Check for return
                if self.state.call_stack and self.state.call_stack[-1].return_value is not None:
                    break
            return result
        return Value(None)
    
    def _eval_parallel(self, node: Node) -> Value:
        from parser.gir import ParallelNode
        if isinstance(node, ParallelNode):
            children = self.graph.get_children(node.id)
            results = []
            # In real implementation, would run in parallel
            for child in children:
                results.append(self._eval_node(child))
            return Value(results)
        return Value(None)
    
    def _eval_return(self, node: Node) -> Value:
        from parser.gir import ReturnNode
        if isinstance(node, ReturnNode):
            # Get return value
            ret_value = None
            for edge in self.graph.edges:
                if edge.kind == EdgeKind.DATA and edge.source == node.id and edge.source_port == "value":
                    source = self.graph.nodes.get(edge.target)
                    if source:
                        ret_value = self._eval_node(source)
                        break
            
            if self.state.call_stack:
                self.state.call_stack[-1].return_value = ret_value or Value(None, UNIT)
            
            return ret_value or Value(None, UNIT)
        return Value(None)
    
    def _eval_arithmetic(self, node: Node) -> Value:
        from parser.gir import ArithmeticNode
        if isinstance(node, ArithmeticNode):
            lhs = self._get_input(node, "lhs")
            rhs = self._get_input(node, "rhs")
            
            if lhs is None or rhs is None:
                return Value(None)
            
            if node.op == ArithmeticOp.ADD:
                result = lhs.value + rhs.value
            elif node.op == ArithmeticOp.SUB:
                result = lhs.value - rhs.value
            elif node.op == ArithmeticOp.MUL:
                result = lhs.value * rhs.value
            elif node.op == ArithmeticOp.DIV:
                result = lhs.value / rhs.value if rhs.value != 0 else 0
            elif node.op == ArithmeticOp.MOD:
                result = lhs.value % rhs.value if rhs.value != 0 else 0
            elif node.op == ArithmeticOp.NEG:
                result = -lhs.value
            else:
                result = 0
            
            return Value(result, INT)
        return Value(None)
    
    def _eval_logic(self, node: Node) -> Value:
        from parser.gir import LogicNode
        if isinstance(node, LogicNode):
            lhs = self._get_input(node, "lhs")
            rhs = self._get_input(node, "rhs") if node.op != LogicOp.NOT else None
            
            if node.op == LogicOp.AND:
                result = (lhs.value if lhs else False) and (rhs.value if rhs else False)
            elif node.op == LogicOp.OR:
                result = (lhs.value if lhs else False) or (rhs.value if rhs else False)
            elif node.op == LogicOp.NOT:
                result = not (lhs.value if lhs else False)
            else:
                result = False
            
            return Value(result, BOOL)
        return Value(None)
    
    def _eval_comparison(self, node: Node) -> Value:
        from parser.gir import ComparisonNode
        if isinstance(node, ComparisonNode):
            lhs = self._get_input(node, "lhs")
            rhs = self._get_input(node, "rhs")
            
            if lhs is None or rhs is None:
                return Value(False, BOOL)
            
            if node.op == ComparisonOp.EQ:
                result = lhs.value == rhs.value
            elif node.op == ComparisonOp.NE:
                result = lhs.value != rhs.value
            elif node.op == ComparisonOp.LT:
                result = lhs.value < rhs.value
            elif node.op == ComparisonOp.LE:
                result = lhs.value <= rhs.value
            elif node.op == ComparisonOp.GT:
                result = lhs.value > rhs.value
            elif node.op == ComparisonOp.GE:
                result = lhs.value >= rhs.value
            else:
                result = False
            
            return Value(result, BOOL)
        return Value(None)
    
    def _get_input(self, node: Node, port: str) -> Optional[Value]:
        """Get input value from a specific port."""
        for edge in self.graph.edges:
            if edge.kind == EdgeKind.DATA and edge.target == node.id and edge.target_port == port:
                source = self.graph.nodes.get(edge.source)
                if source:
                    return self._eval_node(source)
        return None


# --- Built-in Functions ---

BUILTINS = {
    "print": lambda *args: print(*[a.value if isinstance(a, Value) else a for a in args]),
    "println": lambda *args: print(*[a.value if isinstance(a, Value) else a for a in args]),
    "read_line": lambda: Value(input(), STRING),
    "int_parse": lambda s: Value(int(s.value), INT) if isinstance(s, Value) else Value(int(s), INT),
    "float_parse": lambda s: Value(float(s.value), INT) if isinstance(s, Value) else Value(float(s), INT),
    "string_concat": lambda a, b: Value(str(a.value) + str(b.value), STRING),
    "string_length": lambda s: Value(len(s.value), INT) if isinstance(s, Value) else Value(len(s), INT),
}


def create_interpreter(graph: Graph, debug: bool = False) -> Interpreter:
    """Create and configure an interpreter with builtins."""
    interp = Interpreter(graph, debug)
    
    # Register builtins as global functions
    for name, func in BUILTINS.items():
        # Create a function node for each builtin
        func_node = FunctionNode(
            func_name=name,
            params=[],
            return_type=TypeRef("Unit"),
            is_public=True
        )
        func_node._builtin = func
        interp.state.set_global(name, Value(func_node))
    
    return interp


def interpret(graph: Graph, entry: str = "main", args: List = None, debug: bool = False) -> Value:
    """Convenience function to interpret a graph."""
    interp = create_interpreter(graph, debug)
    return interp.run(entry, [Value(a) for a in (args or [])])