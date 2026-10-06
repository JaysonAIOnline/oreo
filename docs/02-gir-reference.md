# OREO GIR (Graph Intermediate Representation) Reference

> Complete reference for the Graph Intermediate Representation — the core data structure of the OREO language.

---

## 1. Overview

The GIR is a **directed, hierarchical, typed graph** where:
- **Nodes** represent operations, values, types, effects, and metadata
- **Edges** represent data flow, control flow, dependencies, and composition
- **Ports** are typed connection points on nodes
- The graph IS the program — text is merely a serialization format

---

## 2. Node Definitions

### 2.1 Base Node Class

```python
@dataclass
class Node:
    kind: NodeKind
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    ports: Dict[str, Port] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    source_location: Optional[Dict[str, Any]] = None  # file, line, col, nl_text
    parent: Optional["Node"] = None  # for hierarchical graphs
```

### 2.2 Port Definition

```python
@dataclass
class Port:
    name: str
    type: Optional[TypeRef] = None
    is_input: bool = True
    is_required: bool = True
    default_value: Optional[Any] = None
    description: str = ""
```

### 2.3 Type Reference

```python
@dataclass
class TypeRef:
    name: str
    type_args: List["TypeRef"] = field(default_factory=list)
    is_mutable: bool = False
    effects: List[str] = field(default_factory=list)
```

---

## 3. Complete NodeKind Enum

### 3.1 Value Nodes
| Kind | Class | Description | Key Properties |
|------|-------|-------------|----------------|
| `LITERAL` | `LiteralNode` | Constant value | `value`, `literal_type` |
| `VARIABLE` | `VariableNode` | Mutable/immutable variable | `var_name`, `var_type`, `is_mutable` |
| `PARAMETER` | `ParameterNode` | Function parameter | `param_name`, `param_type`, `default_value` |
| `CONSTANT` | `ConstantNode` | Named constant | `const_name`, `const_type`, `value` |

### 3.2 Operation Nodes
| Kind | Class | Description | Key Properties |
|------|-------|-------------|----------------|
| `ARITHMETIC` | `ArithmeticNode` | +, -, *, /, %, ^, unary - | `op: ArithmeticOp` |
| `LOGIC` | `LogicNode` | and, or, not, xor | `op: LogicOp` |
| `COMPARISON` | `ComparisonNode` | ==, !=, <, <=, >, >= | `op: ComparisonOp` |
| `CAST` | `CastNode` | Type conversion | `target_type: TypeRef` |
| `CALL` | `CallNode` | Function call | `callee` (via DATA edge) |
| `INDEX` | `IndexNode` | Array/sequence indexing | — |
| `FIELD_ACCESS` | `FieldAccessNode` | Record field access | `field_name: str` |

### 3.3 Control Flow Nodes
| Kind | Class | Description | Key Properties |
|------|-------|-------------|----------------|
| `IF` | `IfNode` | Conditional branch | `condition`, `then_branch`, `else_branch` |
| `LOOP` | `LoopNode` | Iteration (for/while) | `iterator`, `body`, `kind: LoopKind` |
| `MATCH` | `MatchNode` | Pattern matching | `subject`, `cases: List[MatchCase]` |
| `TRY` | `TryNode` | Exception handling | `body`, `catch_clauses`, `finally` |
| `SEQUENCE` | `SequenceNode` | Sequential execution | `steps: List[Node]` |
| `PARALLEL` | `ParallelNode` | Parallel execution | `branches: List[Node]` |
| `BREAK` | `BreakNode` | Loop break | — |
| `CONTINUE` | `ContinueNode` | Loop continue | — |
| `RETURN` | `ReturnNode` | Function return | `value` (via DATA edge) |

### 3.4 Type Nodes
| Kind | Class | Description |
|------|-------|-------------|
| `PRIMITIVE_TYPE` | `PrimitiveTypeNode` | Int, UInt, Float, Bool, Char, String, Bytes |
| `COMPOSITE_TYPE` | `CompositeTypeNode` | Tuple, Record, Sum, Array, Map, Option, Result |
| `FUNCTION_TYPE` | `FunctionTypeNode` | Fn(Params) -> Return [Effects] |
| `EFFECT_TYPE` | `EffectTypeNode` | IO, State, Exception, Async, Resource, Custom |
| `GENERIC_TYPE` | `GenericTypeNode` | Type parameter with constraints |

### 3.5 Effect Nodes
| Kind | Description |
|------|-------------|
| `IO` | Input/output operations |
| `STATE` | Mutable state (with location) |
| `EXCEPTION` | Exception throwing/catching |
| `ASYNC` | Asynchronous computation |
| `RESOURCE` | Resource acquisition/release |

### 3.6 Meta Nodes
| Kind | Description |
|------|-------------|
| `CONTRACT` | Pre/post conditions, invariants |
| `ANNOTATION` | Arbitrary metadata |
| `DOCUMENTATION` | Human-readable docs |
| `SOURCE_MAP` | Maps to original NL/text source |

### 3.7 Scope Nodes
| Kind | Class | Description |
|------|-------|-------------|
| `MODULE` | `ModuleNode` | Top-level module |
| `FUNCTION` | `FunctionNode` | Function definition with params, return type, effects, body |
| `SCOPE` | `ScopeNode` | Lexical scope block |

---

## 4. Complete EdgeKind Enum

| EdgeKind | Source Port | Target Port | Description |
|----------|-------------|-------------|-------------|
| `DATA` | output | input | Typed value flow |
| `CONTROL` | control_out | control_in | Execution order |
| `DEPENDENCY` | — | — | Compile-time dependency |
| `COMPOSITION` | — | — | Parent-child hierarchy |
| `ANNOTATION` | — | — | Metadata attachment |

---

## 5. Edge Definition

```python
@dataclass
class Edge:
    kind: EdgeKind
    id: str = field(default_factory=lambda: str(uuid4()))
    source: str  # node id
    target: str  # node id
    source_port: str = ""
    target_port: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
```

**Port naming conventions for DATA edges:**
- Function call: `arg0`, `arg1`, ..., `function` (for callee)
- Arithmetic: `lhs`, `rhs`
- Comparison: `lhs`, `rhs`
- If: `condition`, `then`, `else`
- Return: `value`
- Index: `collection`, `index`

---

## 6. Graph Container

```python
@dataclass
class Graph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_node(self, node: Node) -> Node:
        self.nodes[node.id] = node
        if node.parent:
            node.parent_id = node.parent.id
        return node
    
    def add_edge(self, edge: Edge) -> Edge:
        self.edges.append(edge)
        return edge
    
    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)
    
    def remove_node(self, node_id: str) -> bool:
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
            return True
        return False
```

---

## 7. Validation Rules

**File:** `/home/jayson/OREO/IDE/parser/gir/validation.py`

### 7.1 Graph Well-Formedness
- All edge source/target node IDs exist in graph
- No duplicate edge IDs
- No self-loops on DATA edges
- Composition edges form a valid tree (no cycles)

### 7.2 Port Compatibility
- DATA edges: source port type ⊆ target port type (subtyping)
- Required input ports must be connected
- Port arity matches (no extra connections on single-input ports)

### 7.3 Type Checking
- All nodes have valid type assignments
- Function calls: argument types match parameter types
- Control flow: condition is Bool, branches have compatible types
- Effect rows: callee effects ⊆ caller effects (subsumption)

### 7.4 Effect Checking
- Pure functions cannot call effectful functions without handling
- Effect polymorphism: row subsumption verified
- State effects: locations tracked, no aliasing violations

---

## 8. Serialization

### 8.1 JSON Format (.oreo.json)

```json
{
  "version": "0.1.0",
  "metadata": { "name": "my_program", "created": "2026-01-15T10:30:00Z" },
  "nodes": [
    {
      "id": "n1",
      "kind": "function",
      "name": "add",
      "description": "Add two integers",
      "ports": {
        "a": { "name": "a", "type": "Int(32)", "is_input": true },
        "b": { "name": "b", "type": "Int(32)", "is_input": true },
        "result": { "name": "result", "type": "Int(32)", "is_input": false }
      },
      "properties": { "params": ["a", "b"], "return_type": "Int(32)", "effects": [] }
    }
  ],
  "edges": [
    {
      "id": "e1",
      "kind": "DATA",
      "source": "n1",
      "target": "n2",
      "source_port": "result",
      "target_port": "arg0"
    }
  ]
}
```

### 8.2 Binary Format (.oreo)
- Compact binary encoding (MessagePack-based)
- Includes: nodes, edges, type table, string pool, source maps
- Versioned with magic bytes `OREO\x01`

---

## 9. Rust Implementation

### 9.1 Core Crates
```
oreo-gir/
├── src/
│   ├── nodes.rs       # NodeKind, Node, Port, LiteralNode, etc.
│   ├── edges.rs       # EdgeKind, Edge
│   ├── types.rs       # TypeRef, PrimitiveKind, CompositeKind, etc.
│   ├── graph.rs       # Graph container
│   ├── validation.rs  # GraphValidator, TypeChecker
│   └── mod.rs
```

### 9.2 Key Traits
```rust
// Node type identification
trait NodeKind {
    fn kind(&self) -> NodeKind;
    fn ports(&self) -> &HashMap<String, Port>;
}

// Type checking
trait TypeCheck {
    fn check(&self, ctx: &TypeContext) -> Result<TypeRef, TypeError>;
}

// Effect checking
trait EffectCheck {
    fn check_effects(&self, ctx: &EffectContext) -> Result<EffectRow, EffectError>;
}
```

---

## 10. Usage Examples

### 10.1 Building a Simple Function Graph

```python
from parser.gir import Graph, FunctionNode, ParameterNode, ArithmeticNode, ArithmeticOp, TypeRef, NodeKind, Edge, EdgeKind, Port

graph = Graph()

# Create function node
add_fn = FunctionNode(
    name="add",
    params=[
        ParameterNode(param_name="a", param_type=TypeRef("Int(32)")),
        ParameterNode(param_name="b", param_type=TypeRef("Int(32)")),
    ],
    return_type=TypeRef("Int(32)"),
    effects=[],
)
graph.add_node(add_fn)

# Create arithmetic node
add_op = ArithmeticNode(op=ArithmeticOp.ADD)
graph.add_node(add_op)

# Connect: a -> lhs, b -> rhs
graph.add_edge(Edge(kind=EdgeKind.DATA, source=add_fn.params[0].id, target=add_op.id, source_port="output", target_port="lhs"))
graph.add_edge(Edge(kind=EdgeKind.DATA, source=add_fn.params[1].id, target=add_op.id, source_port="output", target_port="rhs"))

# Connect result -> function output
graph.add_edge(Edge(kind=EdgeKind.DATA, source=add_op.id, target=add_fn.id, source_port="result", target_port="return"))
```

### 10.2 Architecture Graph (GraphLang)

```python
from parser.architecture import Graph as ArchGraph, Page, Database, Auth, Include

g = ArchGraph()
g.merge_page("page_landing", "Landing", "/")
g.merge_database("db_main", "MainDB", "postgres")
g.merge_auth("auth_secure_jwt", "SecureJWT", "jwt", "secure", requires_https=True)

g.connect_with_auth("page_landing", "db_main", "auth_secure_jwt")
g.include("page_landing", "inc_header", order=0)
g.include("page_landing", "inc_footer", order=1)

# Runtime enforces: pages without CONNECTS_TO + AUTHENTICATES_WITH are refused
runtime = GraphRuntime(g)
response = runtime.handle_request("page_landing")  # Returns 403 if no handshake
```

---

## 11. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `/home/jayson/OREO/IDE/parser/gir/nodes.py` | 719 | All node definitions |
| `/home/jayson/OREO/IDE/parser/gir/edges.py` | ~500 | Edge definitions |
| `/home/jayson/OREO/IDE/parser/gir/types.py` | ~500 | Type system |
| `/home/jayson/OREO/IDE/parser/gir/validation.py` | ~500 | Graph validation, type checking |
| `/home/jayson/OREO/IDE/src/gir/nodes.rs` | ~1400 | Rust node definitions |
| `/home/jayson/OREO/IDE/src/gir/edges.rs` | ~800 | Rust edge definitions |
| `/home/jayson/OREO/IDE/src/gir/type_checker.rs` | ~1600 | Bidirectional type checker |

---

## 12. Visual Editor Node Palette

The visual editor organizes nodes by category (from `node_registry.py`):

| Category | Nodes | Color |
|----------|-------|-------|
| **Module** | MODULE, FUNCTION, SCOPE | Dark blue/purple |
| **Value** | LITERAL, VARIABLE, PARAMETER, CONSTANT | Blue/cyan/teal |
| **Operation** | ARITHMETIC, LOGIC, COMPARISON, CAST, CALL, INDEX, FIELD_ACCESS | Orange/red/purple |
| **Control** | IF, LOOP, MATCH, TRY, SEQUENCE, PARALLEL, BREAK, CONTINUE, RETURN | Yellow/gold |
| **Type** | PRIMITIVE_TYPE, COMPOSITE_TYPE, FUNCTION_TYPE, EFFECT_TYPE, GENERIC_TYPE | Dark gray |
| **Effect** | IO, STATE, EXCEPTION, ASYNC, RESOURCE | Orange |
| **Meta** | CONTRACT, ANNOTATION, DOCUMENTATION, SOURCE_MAP | Gray |

---

## 13. Quick Reference: Common Patterns

### Function Definition
```
FUNCTION Node
├── PARAMETER (port: "a") ──DATA──► ARITHMETIC (port: "lhs")
├── PARAMETER (port: "b") ──DATA──► ARITHMETIC (port: "rhs")
ARITHMETIC (port: "result") ──DATA──► FUNCTION (port: "return")
```

### If-Else
```
IF Node
├── condition ──DATA──► COMPARISON
├── then ──CONTROL──► SEQUENCE (then branch)
└── else ──CONTROL──► SEQUENCE (else branch)
```

### Loop
```
LOOP Node (kind: FOR_EACH)
├── iterator ──DATA──► VARIABLE (collection)
└── body ──CONTROL──► SEQUENCE (loop body)
```

---

*Generated from OREO source code — see `/home/jayson/OREO/IDE/parser/gir/` for implementation.*