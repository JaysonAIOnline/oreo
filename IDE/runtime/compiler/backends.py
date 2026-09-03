"""
OREO Runtime - Compiler Backends
Compiles GIR graphs to various target formats.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from enum import Enum

from parser.gir import (
    Graph, Node, NodeKind, Edge, EdgeKind,
    FunctionNode, TypeRef,
    INT, BOOL, STRING, UNIT, FunctionType,
)


class TargetBackend(Enum):
    """Compilation target backends."""
    BYTECODE = "bytecode"      # Custom bytecode for VM
    LLVM_IR = "llvm_ir"        # LLVM Intermediate Representation
    WASM = "wasm"              # WebAssembly
    C = "c"                    # C source code
    RUST = "rust"              # Rust source code
    PYTHON = "python"          # Python source code
    JAVASCRIPT = "javascript"  # JavaScript/TypeScript


@dataclass
class CompilationUnit:
    """A unit of compilation (function or module)."""
    name: str
    graph: Graph
    entry_function: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompilationResult:
    """Result of compilation."""
    success: bool
    output: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)  # backend-specific


class CompilerBackend(ABC):
    """Abstract compiler backend."""
    
    def __init__(self, target: TargetBackend):
        self.target = target
    
    @abstractmethod
    def compile(self, unit: CompilationUnit) -> CompilationResult:
        """Compile a compilation unit."""
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """Get output file extension."""
        pass


class BytecodeCompiler(CompilerBackend):
    """Compiles GIR to custom bytecode for OREO VM."""
    
    def __init__(self):
        super().__init__(TargetBackend.BYTECODE)
        self.instruction_counter = 0
        self.string_pool: List[str] = []
        self.function_table: Dict[str, int] = {}
    
    def get_file_extension(self) -> str:
        return ".oreobc"
    
    def compile(self, unit: CompilationUnit) -> CompilationResult:
        self.instruction_counter = 0
        self.string_pool = []
        self.function_table = {}
        
        bytecode = []
        bytecode.append("; OREO Bytecode v1")
        bytecode.append(f"; Module: {unit.name}")
        bytecode.append("")
        
        # Collect all functions
        functions = [n for n in unit.graph.nodes.values() if n.kind == NodeKind.FUNCTION]
        
        # Build function table
        for i, func in enumerate(functions):
            self.function_table[func.name] = i
        
        # String pool
        if self.string_pool:
            bytecode.append(".strings:")
            for i, s in enumerate(self.string_pool):
                bytecode.append(f'  {i}: "{self._escape_string(s)}"')
            bytecode.append("")
        
        # Function table
        bytecode.append(".functions:")
        for name, idx in self.function_table.items():
            bytecode.append(f"  {idx}: {name}")
        bytecode.append("")
        
        # Compile each function
        for func in functions:
            if func.name == unit.entry_function or unit.entry_function is None:
                func_bytecode = self._compile_function(func, unit.graph)
                bytecode.extend(func_bytecode)
                bytecode.append("")
        
        return CompilationResult(
            success=True,
            output="\n".join(bytecode),
            artifacts={"functions": self.function_table, "strings": self.string_pool}
        )
    
    def _compile_function(self, func: FunctionNode, graph: Graph) -> List[str]:
        lines = []
        lines.append(f".function {func.name}:")
        lines.append(f"  ; params: {len(func.params)}")
        lines.append(f"  ; returns: {func.return_type}")
        lines.append(f"  ; effects: {func.effects}")
        
        # Allocate locals for parameters
        for i, param in enumerate(func.params):
            lines.append(f"  param {i} -> local {i}  ; {param.param_name}: {param.param_type}")
        
        # Compile body
        if func.body:
            body_code = self._compile_node(func.body, graph, local_offset=len(func.params))
            lines.extend(body_code)
        else:
            lines.append("  ret  ; implicit return")
        
        lines.append("  end")
        return lines
    
    def _compile_node(self, node: Node, graph: Graph, local_offset: int = 0, indent: str = "  ") -> List[str]:
        lines = []
        
        if node.kind == NodeKind.LITERAL:
            from parser.gir import LiteralNode
            if isinstance(node, LiteralNode):
                val = node.value
                if isinstance(val, str):
                    str_idx = self._get_string_index(val)
                    lines.append(f"{indent}ldstr {str_idx}")
                elif isinstance(val, bool):
                    lines.append(f"{indent}ldbool {1 if val else 0}")
                elif isinstance(val, int):
                    lines.append(f"{indent}ldint {val}")
                elif isinstance(val, float):
                    lines.append(f"{indent}ldfloat {val}")
                else:
                    lines.append(f"{indent}ldnull")
        
        elif node.kind == NodeKind.VARIABLE:
            from parser.gir import VariableNode
            if isinstance(node, VariableNode):
                # Find local index
                local_idx = self._find_local(node.var_name, graph)
                if local_idx >= 0:
                    lines.append(f"{indent}ldloc {local_offset + local_idx}")
                else:
                    lines.append(f"{indent}ldglob {node.var_name}")
        
        elif node.kind == NodeKind.CALL:
            from parser.gir import CallNode
            if isinstance(node, CallNode):
                # Compile arguments in reverse order (stack-based)
                arg_edges = [e for e in graph.edges 
                            if e.kind == EdgeKind.DATA and e.target == node.id and e.target_port.startswith("arg")]
                arg_edges.sort(key=lambda e: e.target_port)  # arg0, arg1, ...
                
                for edge in arg_edges:
                    source = graph.nodes.get(edge.source)
                    if source:
                        lines.extend(self._compile_node(source, graph, local_offset, indent))
                
                # Function reference
                func_edge = next((e for e in graph.edges 
                                 if e.kind == EdgeKind.DATA and e.target == node.id and e.target_port == "function"), None)
                if func_edge:
                    func_node = graph.nodes.get(func_edge.source)
                    if func_node and func_node.kind == NodeKind.FUNCTION:
                        func_idx = self.function_table.get(func_node.name, -1)
                        if func_idx >= 0:
                            lines.append(f"{indent}call {func_idx}")
                        else:
                            lines.append(f"{indent}call_dyn  ; {func_node.name}")
        
        elif node.kind == NodeKind.ARITHMETIC:
            from parser.gir import ArithmeticNode, ArithmeticOp
            if isinstance(node, ArithmeticNode):
                # Get operands
                lhs_edge = next((e for e in graph.edges 
                                if e.kind == EdgeKind.DATA and e.target == node.id and e.target_port == "lhs"), None)
                rhs_edge = next((e for e in graph.edges 
                                if e.kind == EdgeKind.DATA and e.target == node.id and e.target_port == "rhs"), None)
                
                if lhs_edge:
                    source = graph.nodes.get(lhs_edge.source)
                    if source:
                        lines.extend(self._compile_node(source, graph, local_offset, indent))
                
                if rhs_edge:
                    source = graph.nodes.get(rhs_edge.source)
                    if source:
                        lines.extend(self._compile_node(source, graph, local_offset, indent))
                
                op_map = {
                    ArithmeticOp.ADD: "add",
                    ArithmeticOp.SUB: "sub",
                    ArithmeticOp.MUL: "mul",
                    ArithmeticOp.DIV: "div",
                    ArithmeticOp.MOD: "mod",
                }
                lines.append(f"{indent}{op_map.get(node.op, 'add')}")
        
        elif node.kind == NodeKind.RETURN:
            from parser.gir import ReturnNode
            if isinstance(node, ReturnNode):
                # Get return value
                val_edge = next((e for e in graph.edges 
                                if e.kind == EdgeKind.DATA and e.source == node.id and e.source_port == "value"), None)
                if val_edge:
                    source = graph.nodes.get(val_edge.target)
                    if source:
                        lines.extend(self._compile_node(source, graph, local_offset, indent))
                lines.append(f"{indent}ret")
        
        elif node.kind == NodeKind.SEQUENCE:
            children = graph.get_children(node.id)
            for child in children:
                lines.extend(self._compile_node(child, graph, local_offset, indent))
        
        elif node.kind == NodeKind.IF:
            from parser.gir import IfNode
            if isinstance(node, IfNode):
                # Condition
                cond_edge = next((e for e in graph.edges 
                                 if e.kind == EdgeKind.DATA and e.target == node.id and e.target_port == "condition"), None)
                if cond_edge:
                    source = graph.nodes.get(cond_edge.source)
                    if source:
                        lines.extend(self._compile_node(source, graph, local_offset, indent))
                
                lines.append(f"{indent}brfalse ELSE_{node.id[:8]}")
                
                # Then branch
                then_edge = next((e for e in graph.edges 
                                 if e.kind == EdgeKind.CONTROL and e.source == node.id and e.target_port == "then"), None)
                if then_edge:
                    then_node = graph.nodes.get(then_edge.target)
                    if then_node:
                        lines.extend(self._compile_node(then_node, graph, local_offset, indent))
                
                lines.append(f"{indent}br END_{node.id[:8]}")
                lines.append(f"{indent}ELSE_{node.id[:8]}:")
                
                # Else branch
                else_edge = next((e for e in graph.edges 
                                 if e.kind == EdgeKind.CONTROL and e.source == node.id and e.target_port == "else"), None)
                if else_edge:
                    else_node = graph.nodes.get(else_edge.target)
                    if else_node:
                        lines.extend(self._compile_node(else_node, graph, local_offset, indent))
                
                lines.append(f"{indent}END_{node.id[:8]}:")
        
        return lines
    
    def _get_string_index(self, s: str) -> int:
        if s in self.string_pool:
            return self.string_pool.index(s)
        self.string_pool.append(s)
        return len(self.string_pool) - 1
    
    def _find_local(self, name: str, graph: Graph) -> int:
        # Simplified - would need proper scope analysis
        return -1
    
    def _escape_string(self, s: str) -> str:
        return s.replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')


class LLVMIRCompiler(CompilerBackend):
    """Compiles GIR to LLVM IR."""
    
    def __init__(self):
        super().__init__(TargetBackend.LLVM_IR)
    
    def get_file_extension(self) -> str:
        return ".ll"
    
    def compile(self, unit: CompilationUnit) -> CompilationResult:
        lines = []
        lines.append("; ModuleID = 'oreo_module'")
        lines.append(f'source_filename = "{unit.name}.oreo"')
        lines.append("")
        
        # Declare external functions
        lines.append("declare i32 @printf(i8*, ...)")
        lines.append("declare i32 @scanf(i8*, ...)")
        lines.append("")
        
        # Compile functions
        functions = [n for n in unit.graph.nodes.values() if n.kind == NodeKind.FUNCTION]
        for func in functions:
            if func.name == unit.entry_function or unit.entry_function is None:
                func_ir = self._compile_function(func, unit.graph)
                lines.extend(func_ir)
                lines.append("")
        
        return CompilationResult(
            success=True,
            output="\n".join(lines)
        )
    
    def _compile_function(self, func: FunctionNode, graph: Graph) -> List[str]:
        lines = []
        
        # Function signature
        ret_type = self._type_to_llvm(func.return_type) if func.return_type else "void"
        param_types = [self._type_to_llvm(p.param_type) for p in func.params]
        params_str = ", ".join(f"{t} %{p.param_name}" for p, t in zip(func.params, param_types))
        
        lines.append(f"define {ret_type} @{func.name}({params_str}) {{")
        lines.append("entry:")
        
        # Allocate stack slots for parameters
        for param in func.params:
            llvm_type = self._type_to_llvm(param.param_type)
            lines.append(f"  %{{param.param_name}}.addr = alloca {llvm_type}")
            lines.append(f"  store {llvm_type} %{param.param_name}, {llvm_type}* %{param.param_name}.addr")
        
        # Compile body
        if func.body:
            body_code = self._compile_node(func.body, graph)
            lines.extend(f"  {line}" for line in body_code)
        else:
            if ret_type != "void":
                lines.append(f"  ret {ret_type} 0")
            else:
                lines.append("  ret void")
        
        lines.append("}")
        return lines
    
    def _compile_node(self, node: Node, graph: Graph) -> List[str]:
        lines = []
        
        if node.kind == NodeKind.LITERAL:
            from parser.gir import LiteralNode
            if isinstance(node, LiteralNode):
                val = node.value
                if isinstance(val, int):
                    lines.append(f"; literal: {val}")
                elif isinstance(val, bool):
                    lines.append(f"; literal: {1 if val else 0}")
                elif isinstance(val, str):
                    lines.append(f"; literal: \"{val}\"")
        
        elif node.kind == NodeKind.RETURN:
            from parser.gir import ReturnNode
            if isinstance(node, ReturnNode):
                val_edge = next((e for e in graph.edges 
                                if e.kind == EdgeKind.DATA and e.source == node.id and e.source_port == "value"), None)
                if val_edge:
                    # Simplified
                    lines.append("ret i32 0")
                else:
                    lines.append("ret void")
        
        return lines
    
    def _type_to_llvm(self, type_ref: TypeRef) -> str:
        if not type_ref:
            return "i32"
        
        name = type_ref.name.lower()
        if name in ("int", "integer"):
            return "i32"
        elif name in ("bool", "boolean"):
            return "i1"
        elif name in ("float", "double"):
            return "double"
        elif name in ("string", "str"):
            return "i8*"
        elif name in ("unit", "void"):
            return "void"
        else:
            return "i32"  # Default


class PythonCompiler(CompilerBackend):
    """Compiles GIR to Python source code."""
    
    def __init__(self):
        super().__init__(TargetBackend.PYTHON)
    
    def get_file_extension(self) -> str:
        return ".py"
    
    def compile(self, unit: CompilationUnit) -> CompilationResult:
        lines = []
        lines.append("# Generated by OREO Python Compiler")
        lines.append(f"# Module: {unit.name}")
        lines.append("")
        
        # Imports
        lines.append("from typing import Any, List, Dict, Optional")
        lines.append("")
        
        # Compile functions
        functions = [n for n in unit.graph.nodes.values() if n.kind == NodeKind.FUNCTION]
        for func in functions:
            if func.name == unit.entry_function or unit.entry_function is None:
                func_code = self._compile_function(func, unit.graph)
                lines.extend(func_code)
                lines.append("")
        
        # Main entry point
        if unit.entry_function:
            lines.append("if __name__ == '__main__':")
            lines.append(f"    {unit.entry_function}()")
        
        return CompilationResult(
            success=True,
            output="\n".join(lines)
        )
    
    def _compile_function(self, func: FunctionNode, graph: Graph) -> List[str]:
        lines = []
        
        # Function signature
        params = [p.param_name for p in func.params]
        params_str = ", ".join(params)
        
        lines.append(f"def {func.name}({params_str}):")
        
        if func.body:
            body_code = self._compile_node(func.body, graph, indent="    ")
            lines.extend(body_code)
        else:
            lines.append("    pass")
        
        return lines
    
    def _compile_node(self, node: Node, graph: Graph, indent: str = "    ") -> List[str]:
        lines = []
        
        if node.kind == NodeKind.LITERAL:
            from parser.gir import LiteralNode
            if isinstance(node, LiteralNode):
                val = node.value
                if isinstance(val, str):
                    lines.append(f'{indent}# literal: "{val}"')
                else:
                    lines.append(f'{indent}# literal: {val}')
        
        elif node.kind == NodeKind.CALL:
            from parser.gir import CallNode
            if isinstance(node, CallNode):
                # Get function name
                func_edge = next((e for e in graph.edges 
                                 if e.kind == EdgeKind.DATA and e.target == node.id and e.target_port == "function"), None)
                if func_edge:
                    func_node = graph.nodes.get(func_edge.source)
                    if func_node and func_node.kind == NodeKind.FUNCTION:
                        func_name = func_node.name
                        
                        # Get arguments
                        arg_edges = [e for e in graph.edges 
                                    if e.kind == EdgeKind.DATA and e.target == node.id and e.target_port.startswith("arg")]
                        arg_edges.sort(key=lambda e: e.target_port)
                        
                        args = []
                        for edge in arg_edges:
                            source = graph.nodes.get(edge.source)
                            if source and source.kind == NodeKind.LITERAL:
                                from parser.gir import LiteralNode
                                if isinstance(source, LiteralNode):
                                    val = source.value
                                    if isinstance(val, str):
                                        args.append(f'"{val}"')
                                    else:
                                        args.append(str(val))
                        
                        args_str = ", ".join(args)
                        lines.append(f'{indent}{func_name}({args_str})')
        
        elif node.kind == NodeKind.RETURN:
            from parser.gir import ReturnNode
            if isinstance(node, ReturnNode):
                lines.append(f"{indent}return")
        
        elif node.kind == NodeKind.SEQUENCE:
            children = graph.get_children(node.id)
            for child in children:
                lines.extend(self._compile_node(child, graph, indent))
        
        elif node.kind == NodeKind.IF:
            from parser.gir import IfNode
            if isinstance(node, IfNode):
                lines.append(f"{indent}if True:  # condition")
                
                then_edge = next((e for e in graph.edges 
                                 if e.kind == EdgeKind.CONTROL and e.source == node.id and e.target_port == "then"), None)
                if then_edge:
                    then_node = graph.nodes.get(then_edge.target)
                    if then_node:
                        lines.extend(self._compile_node(then_node, graph, indent + "    "))
                
                else_edge = next((e for e in graph.edges 
                                 if e.kind == EdgeKind.CONTROL and e.source == node.id and e.target_port == "else"), None)
                if else_edge:
                    lines.append(f"{indent}else:")
                    else_node = graph.nodes.get(else_edge.target)
                    if else_node:
                        lines.extend(self._compile_node(else_node, graph, indent + "    "))
        
        return lines


class Compiler:
    """Main compiler coordinating multiple backends."""
    
    def __init__(self):
        self.backends: Dict[TargetBackend, CompilerBackend] = {
            TargetBackend.BYTECODE: BytecodeCompiler(),
            TargetBackend.LLVM_IR: LLVMIRCompiler(),
            TargetBackend.PYTHON: PythonCompiler(),
        }
    
    def register_backend(self, backend: CompilerBackend):
        self.backends[backend.target] = backend
    
    def compile(self, graph: Graph, target: TargetBackend, 
                entry_function: str = None, module_name: str = "main") -> CompilationResult:
        """Compile graph to target backend."""
        if target not in self.backends:
            return CompilationResult(
                success=False,
                errors=[f"Unknown target backend: {target}"]
            )
        
        unit = CompilationUnit(
            name=module_name,
            graph=graph,
            entry_function=entry_function
        )
        
        backend = self.backends[target]
        return backend.compile(unit)
    
    def get_available_targets(self) -> List[TargetBackend]:
        return list(self.backends.keys())


def create_compiler() -> Compiler:
    """Factory function to create compiler with default backends."""
    return Compiler()