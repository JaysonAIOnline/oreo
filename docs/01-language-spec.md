# OREO Language Specification

> Complete language specification for OREO — a visual-first, natural-language-first programming language where **code IS a graph**, not text parsed into a graph.

---

## 1. Core Philosophy

### 1.1 Graph-Native Semantics
- **Code is a graph** — not text that gets parsed into a graph
- Nodes = operations, values, types, effects
- Edges = data flow, control flow, dependency, composition
- The graph IS the source of truth; text is a serialization format

### 1.2 Natural Language First
- Write programs in English (or any NL)
- NL maps to graph structures via semantic parsing
- Round-trip: NL → Graph → NL (lossless)
- AI generates graph directly; NL is human interface

### 1.3 Visual-First Interface
- Primary editor = node-graph canvas
- Drag nodes, connect ports, see data flow
- Text view = alternative serialization
- Live execution visualization on the graph

### 1.4 AI-Understandable Design
- Formal operational semantics (small-step, big-step)
- Type system with decidable inference
- Effect system for side effects (IO, state, exceptions)
- Contracts/preconditions/postconditions as first-class

---

## 2. Graph Intermediate Representation (GIR)

The GIR is the heart of OREO — a graph-native representation where every program is a directed acyclic graph of nodes connected by typed edges.

### 2.1 Node Categories (NodeKind)

| Category | Kinds | Purpose |
|----------|-------|---------|
| **Value** | `LITERAL`, `VARIABLE`, `PARAMETER`, `CONSTANT` | Data representation |
| **Operation** | `ARITHMETIC`, `LOGIC`, `COMPARISON`, `CAST`, `CALL`, `INDEX`, `FIELD_ACCESS` | Compute values |
| **Control** | `IF`, `LOOP`, `MATCH`, `TRY`, `SEQUENCE`, `PARALLEL`, `BREAK`, `CONTINUE`, `RETURN` | Control flow |
| **Type** | `PRIMITIVE_TYPE`, `COMPOSITE_TYPE`, `FUNCTION_TYPE`, `EFFECT_TYPE`, `GENERIC_TYPE` | Type definitions |
| **Effect** | `IO`, `STATE`, `EXCEPTION`, `ASYNC`, `RESOURCE` | Side effects |
| **Meta** | `CONTRACT`, `ANNOTATION`, `DOCUMENTATION`, `SOURCE_MAP` | Metadata |
| **Scope** | `MODULE`, `FUNCTION`, `SCOPE` | Hierarchy |

### 2.2 Edge Types (EdgeKind)

| Edge | Purpose |
|------|---------|
| `DATA` | Typed value flow between ports |
| `CONTROL` | Execution order |
| `DEPENDENCY` | Compile-time dependency |
| `COMPOSITION` | Structural containment (parent/child) |
| `ANNOTATION` | Metadata attachment |

### 2.3 Graph Properties
- **Directed** — edges have source → target
- **Acyclic for data flow** — no value cycles (feedback via explicit loop nodes)
- **Hierarchical** — subgraphs for modules, functions, scopes
- **Typed ports** — each port has a type; connections validated

### 2.4 Core Data Structures

```python
# Port - typed connection point
@dataclass
class Port:
    name: str
    type: Optional[TypeRef] = None
    is_input: bool = True
    is_required: bool = True
    default_value: Optional[Any] = None
    description: str = ""

# TypeRef - reference to a type (supports forward refs, generics, mutability, effects)
@dataclass
class TypeRef:
    name: str
    type_args: List["TypeRef"] = field(default_factory=list)
    is_mutable: bool = False
    effects: List[str] = field(default_factory=list)

# Base Node
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

---

## 3. Type System

### 3.1 Primitive Types
```
Int(n)         ::= signed integer, n bits (8, 16, 32, 64, 128)
UInt(n)        ::= unsigned integer
Float(n)       ::= IEEE 754 (16, 32, 64, 80)
Bool           ::= true | false
Char           ::= Unicode code point
String         ::= UTF-8 sequence
Bytes          ::= raw byte sequence
```

### 3.2 Composite Types
```
Tuple(T1, ..., Tn)     ::= fixed-size product
Record{name: T, ...}   ::= named product
Sum(variant: T, ...)   ::= tagged union (ADT)
Array(T, n?)           ::= sequence (fixed or dynamic)
Map(K, V)              ::= associative
Option(T)              ::= Some(T) | None
Result(T, E)           ::= Ok(T) | Err(E)
```

### 3.3 Function Types
```
Fn(Params) -> Return [Effects]
Params ::= (name: Type, ...) [default values]
Return ::= Type
Effects ::= {IO, State, Exception, Async, ...}
```

### 3.4 Effect System
```
Effect ::= IO | State(Loc) | Exception(E) | Async | Resource(R) | Custom(name)
EffectRow ::= {Effect, ...} | <empty> (pure)
Polymorphic over effects: fn[T](x: T) -> T [e] where e ⊆ {IO, State}
```

### 3.5 Generic Types & Constraints
```
forall<T: Trait>. Type
Trait ::= { method: Fn(...) -> ... [Effects] }
Where clauses: where T: Clone + Send + Sync
```

### 3.6 Rust Implementation (bidirectional type checker)
The type checker lives in `/home/jayson/OREO/IDE/src/gir/type_checker.rs` and implements:
- Bidirectional type checking (synthesis + checking)
- Effect inference and subsumption
- Constraint solving for generics
- Trait resolution
- Error reporting with source locations

---

## 4. Natural Language Syntax

### 4.1 Design Principles
- **Declarative** — describe *what*, not *how*
- **Composable** — small phrases combine into larger programs
- **Context-aware** — pronouns, references resolve to graph nodes
- **Incremental** — partial NL parses to partial graph

### 4.2 Example Mappings

| Natural Language | Graph Structure |
|------------------|-----------------|
| "define function add taking two integers returning their sum" | `Fn(a: Int, b: Int) -> Int [pure]` with `OpNode(Add)` |
| "if user is admin then grant access else deny" | `IfNode(cond=UserIsAdmin, then=GrantAccess, else=Deny)` |
| "read file config.json and parse as JSON" | `Sequence(Call(readFile, "config.json"), Call(parseJSON, _))` |
| "for each item in list, process it in parallel" | `Parallel(Loop(items, ProcessItem))` |

### 4.3 Ambiguity Resolution
- Type-directed disambiguation
- Context from surrounding graph
- Interactive clarification (ask user/AI)
- Default to most general interpretation

### 4.4 Architecture NL Layer (GraphLang)
The architecture subsystem (merged from GraphLang) provides a separate NL layer for **application architecture modeling** (pages, databases, auth handshakes, includes).

**Key files:**
- `/home/jayson/OREO/IDE/parser/architecture/lines.py` — NL intent inference
- `/home/jayson/OREO/IDE/parser/architecture/runtime.py` — Relationship runtime (handshake enforcement)
- `/home/jayson/OREO/IDE/parser/architecture/emit.py` — Emit runnable web apps from graph
- `/home/jayson/OREO/IDE/parser/architecture/visual.py` — Talk+draw web editor with voice

**NL → Cypher patterns (from NL_CYPHER_SPEC.md):**

| NL Command | Intent | Graph Operation |
|------------|--------|-----------------|
| "Create a landing page at /" | Create page | MERGE `page_landing` with `path:"/"` |
| "Add a postgres database called MainDB" | Create db | MERGE `db_main` engine postgres |
| "Create a secure JWT auth named SecureJWT" | Create auth | MERGE Auth method jwt, level secure |
| "Connect the db to the landing page with a secure auth" | Connect + auth | Pattern: CONNECTS_TO + AUTHENTICATES_WITH |
| "Make every page include Header and Footer" | Fan-out includes | INCLUDES from all Pages |

**Structured Intent JSON (what the parser emits):**
```json
{
  "action": "connect_with_auth",
  "source": { "label": "Page", "ref": "Landing" },
  "target": { "label": "Database", "ref": "MainDB" },
  "auth": { "method": "jwt", "level": "secure", "requires_https": true },
  "roles": [],
  "create_missing": true
}
```

---

## 5. Visual Editor Specification

### 5.1 Canvas
- Infinite 2D canvas with zoom/pan
- Grid snap, alignment guides
- Mini-map for navigation
- Layers: data flow, control flow, metadata

### 5.2 Node Rendering
- **Shape** = node category (circle=value, diamond=control, rectangle=op)
- **Color** = type category (blue=primitive, green=composite, orange=effect)
- **Ports** = typed connection points on node boundary
- **Labels** = NL description + type signature

### 5.3 Interaction
- **Create** — palette search, drag from library, NL input box
- **Connect** — drag port-to-port; type-check on drop
- **Inspect** — click node → properties panel (type, effects, contracts, source NL)
- **Execute** — "Run from here", "Step", "Visualize data flow"

### 5.4 Live Visualization
- **Token highlighting** — values flowing through edges in real-time
- **Heat map** — execution frequency, hot paths
- **Time travel** — scrub through execution history
- **Diff view** — compare two graph versions

### 5.5 Implementation
**Python canvas renderer** (`/home/jayson/OREO/IDE/visual_editor/canvas/renderer.py`):
- `Viewport` — zoom/pan, coordinate transforms, fit-to-content
- `NodeRenderer` — typed node colors, port rendering, labels
- `EdgeRenderer` — Bezier curves, data/control edge styling
- `RenderContext` — selection, hover, drag state, minimap

**Node Registry** (`/home/jayson/OREO/IDE/visual_editor/nodes/node_registry.py`):
- Registry of node types available in the visual editor palette
- Category organization (Value, Operation, Control, Type, Effect, Meta, Scope)
- Search/filter by category, name, description

**Architecture Bridge** (`/home/jayson/OREO/IDE/visual_editor/architecture.py`):
- Bridges the Architecture subsystem's self-contained web editor
- Imports `parser.architecture.visual` (GraphLang talk+draw editor)

**Web Frontend** (`/home/jayson/OREO/IDE/visual_editor/web/`):
- Node.js/React frontend for the canvas
- WebSocket connection to Python backend for live execution

---

## 6. Runtime Semantics

### 6.1 Evaluation Model
- **Graph reduction** — nodes fire when all inputs ready
- **Parallel by default** — independent nodes execute concurrently
- **Deterministic** — same graph + same inputs = same outputs
- **Incremental** — only re-evaluate changed subgraph

### 6.2 Memory Model
- **Value semantics** — immutable by default
- **Explicit mutability** — `mut` keyword, tracked in effect system
- **Ownership** — single owner, borrow checker (Rust-style)
- **GC for cycles** — reference counting + cycle detector

### 6.3 Concurrency
- **Structured concurrency** — scopes, cancellation propagation
- **Async/await** — effect-polymorphic
- **Channels** — typed, bounded/unbounded
- **Actors** — optional, for distributed

### 6.4 Graph Interpreter (Reference Implementation)
**File:** `/home/jayson/OREO/IDE/runtime/interpreter/evaluator.py`

```python
class GraphInterpreter:
    """Executes GIR graphs directly."""
    
    def __init__(self):
        self.call_stack: List[Frame] = []
        self.heap: Dict[str, Value] = {}
        self.effect_handlers: Dict[Effect, Handler] = {}
    
    def execute(self, graph: Graph, entry: str, args: List[Value]) -> Value:
        # 1. Find entry function
        # 2. Create initial frame
        # 3. Reduction loop: fire ready nodes
        # 4. Handle effects (IO, State, Exception, Async)
        # 5. Return result
```

**Key features:**
- Worklist algorithm for parallel node execution
- Effect handler dispatch (IO, State, Exception, Async)
- Structured concurrency with cancellation scopes
- Value memoization for incremental re-execution

---

## 7. Compiler Backends

### 7.1 Target Backends
| Backend | Output | Status |
|---------|--------|--------|
| `BYTECODE` | Custom `.oreobc` bytecode for OREO VM | ✅ Implemented |
| `LLVM_IR` | LLVM Intermediate Representation | 🔄 Planned |
| `WASM` | WebAssembly | 🔄 Planned |
| `C` | C source code | 🔄 Planned |
| `RUST` | Rust source code | 🔄 Planned |
| `PYTHON` | Python source code | 🔄 Planned |
| `JAVASCRIPT` | JavaScript/TypeScript | 🔄 Planned |

### 7.2 Bytecode Compiler (Implemented)
**File:** `/home/jayson/OREO/IDE/runtime/compiler/backends.py`

```python
class BytecodeCompiler(CompilerBackend):
    """Compiles GIR to custom bytecode for OREO VM."""
    
    def compile(self, unit: CompilationUnit) -> CompilationResult:
        # 1. Collect all functions in graph
        # 2. Build function table + string pool
        # 3. Compile each function body to stack-based bytecode
        # 4. Emit: .strings, .functions, .function name: <instructions>
```

**Instruction set (subset):**
- `ldint`, `ldfloat`, `ldbool`, `ldstr`, `ldnull` — load constants
- `ldloc`, `stloc` — local variable access
- `ldglob`, `stglob` — global variable access
- `call`, `call_dyn` — function calls
- `add`, `sub`, `mul`, `div`, `mod` — arithmetic
- `eq`, `ne`, `lt`, `le`, `gt`, `ge` — comparison
- `and`, `or`, `not`, `xor` — logic
- `ret`, `br`, `brfalse` — control flow

---

## 8. AI Integration

### 8.1 Code Generation
**File:** `/home/jayson/OREO/IDE/ai_integration/codegen/gir_generator.py`

- AI outputs GIR directly (not text)
- Type-checks as it generates
- Verifies contracts via SMT (Z3)
- Explains decisions in NL

**Key class:** `GIRGenerator` — generates GIR graphs from natural language using LLM

### 8.2 Verification
- **Type checking** — decidable, fast (bidirectional)
- **Contract checking** — SMT-backed pre/post conditions (Z3)
- **Model checking** — for finite-state subgraphs
- **Fuzzing** — property-based test generation

### 8.3 Explanation
- "Why this node?" → trace to NL source
- "What if?" → counterfactual execution
- "Show me" → visual subgraph extraction

### 8.4 LLM Intent Hybrid Parser
**File:** `/home/jayson/OREO/IDE/ai_integration/parser.py`

Merges LLM-based intent parsing with deterministic rule-based parser for:
- Architecture NL commands (pages, databases, auth)
- Computational NL (functions, control flow)

---

## 9. Test Harness

### 9.1 Property-Based Testing
**File:** `/home/jayson/OREO/IDE/test_harness/property_tests.py`

- Generates random GIR graphs
- Verifies type safety, effect safety
- Checks round-trip serialization (NL → Graph → NL)
- Validates interpreter vs. compiler equivalence

### 9.2 Fuzzing
**File:** `/home/jayson/OREO/IDE/test_harness/fuzzing.py`

- Mutation-based fuzzing of GIR graphs
- Targets: parser, type checker, interpreter, compiler
- Coverage-guided (instrumented bytecode)

### 9.3 Model Checking
**File:** `/home/jayson/OREO/IDE/test_harness/model_checking.py`

- Finite-state subgraph exploration
- Verifies safety/liveness properties
- Counterexample generation

### 9.4 Integration Tests
**File:** `/home/jayson/OREO/IDE/test_harness/integration.py`

- End-to-end: NL → Parse → Type-check → Interpret → Compile → Execute
- Architecture subsystem: NL → Graph → Runtime handshake → Emit → Hit routes

---

## 10. Serialization Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Binary | `.oreo` | Compact, fast, versioned. Includes: GIR, types, effects, contracts, source maps, NL annotations |
| JSON | `.oreo.json` | Human-readable, diffable, schema-validated |
| Text | `.oreo.txt` | NL representation (round-trippable), Markdown-embeddable |
| GraphViz | `.dot` | For documentation, export |
| Mermaid | `.mmd` | For documentation, export |

---

## 11. Toolchain

### 11.1 Parser
- NL → GIR (semantic parsing)
- Text serialization → GIR
- Incremental, error-tolerant
- Architecture NL router (separate pipeline for app architecture)

### 11.2 Type Checker
- Bidirectional type inference
- Effect inference
- Constraint solving (traits, generics)
- Z3-backed contract verification

### 11.3 Compiler
- GIR → bytecode (custom VM) or LLVM IR
- JIT for hot paths
- AOT for distribution

### 11.4 Runtime
- Graph interpreter (reference)
- Compiled executor (optimized)
- Debugger, profiler, visualizer

---

## 12. Project Structure

```
OREO/IDE/
├── spec/                      # Language specification
│   ├── OREO_LANGUAGE_SPEC.md  # Complete language spec (this doc source)
│   └── NL_CYPHER_SPEC.md      # Architecture NL + Cypher patterns
├── parser/                    # NL parser + text parser + GIR + architecture
│   ├── gir/                   # Computational GIR
│   │   ├── nodes.py           # Node definitions (719 lines)
│   │   ├── edges.py           # Edge definitions
│   │   ├── types.py           # Type system
│   │   └── validation.py      # Graph validation, type checking
│   ├── nl_parser/             # NL front-ends
│   │   ├── semantic_parser.py # NL → computational GIR
│   │   └── architecture_router.py # NL → Architecture package
│   └── architecture/          # NL+visual architecture modeling (GraphLang)
│       ├── lines.py           # Speech → intent → Cypher
│       ├── runtime.py         # Handshake enforcement
│       ├── emit.py            # Emit runnable web app
│       └── visual.py          # Talk+draw web editor (ears + voice)
├── runtime/                   # Interpreter + compiler + memory
│   ├── interpreter/
│   │   └── evaluator.py       # Graph interpreter
│   └── compiler/
│       └── backends.py        # Compiler backends (bytecode, LLVM, WASM, etc.)
├── visual_editor/             # Canvas, nodes, live visualization
│   ├── canvas/renderer.py     # Canvas rendering (721 lines)
│   ├── interaction/tools.py   # User interaction handling
│   ├── nodes/node_registry.py # Node palette registry
│   └── architecture.py        # Bridge to Architecture web editor
├── ai_integration/            # AI codegen, verification, explanation
│   ├── codegen/gir_generator.py
│   └── parser.py              # LLM intent hybrid parser
├── test_harness/              # Property tests, fuzzing, model checking
│   ├── property_tests.py
│   ├── fuzzing.py
│   ├── model_checking.py
│   └── integration.py
├── docs/                      # Documentation
├── examples/                  # Example programs
│   ├── hello_world.oreo
│   ├── factorial.oreo
│   └── architecture/          # Architecture subsystem examples
├── Cargo.toml                 # Rust workspace (core GIR, type checker)
├── pyproject.toml             # Python workspace (parser, runtime, editor, AI)
└── README.md                  # This file
```

---

## 13. Quick Start

### Prerequisites
- Rust 1.75+ (for core implementation)
- Python 3.11+ (for AI integration, tooling)
- Node.js 18+ (for visual editor web frontend)

### Build
```bash
# Rust workspace
cargo build --workspace

# Python workspace
pip install -e .[dev,ai]

# Visual editor (if using web frontend)
cd visual_editor/web && npm install && npm run dev
```

### Run Examples

**Architecture subsystem (runnable now — merged from GraphLang):**
```bash
# NL -> architecture graph (pages, databases, auth handshakes, includes)
python3 -m parser.architecture.demo

# Relationship runtime: pages are refused until a handshake line exists
python3 examples/architecture/runtime_handshake.py

# Emit a runnable web app from the graph and hit its routes
python3 examples/architecture/emit_and_hit.py

# Live talk + draw web editor (ears + voice)
python3 -m parser.architecture.visual
```

**Computational (when interpreter is ready):**
```bash
# Using the interpreter
cargo run --bin oreo-interpreter examples/hello_world.oreo

# Using the visual editor
cargo run --bin oreo-editor
```

### Example Programs

**hello_world.oreo:**
```
define function main
 call print "Hello, World!"
```

**factorial.oreo:**
```
define function factorial(n: Int) -> Int
 if n <= 1 then
  return 1
 else
  return n * factorial(n - 1)

define function main
 var result = factorial(5)
 call print result
```

---

## 14. Roadmap Status

| Phase | Status | Description |
|-------|--------|-------------|
| research | ✅ completed | Neo4j, Graph-Native Programming, Machine-Level Computing, ECC, Information Theory |
| spec | 🔄 in_progress | GIR, type system, NL syntax, visual editor defined |
| parser | 🔄 partial | Architecture NL parser merged & runnable; compute-NL `parse_nl` produces valid GIR |
| runtime | 🔄 partial | Graph interpreter, effect system, memory model; bytecode compiler runs on parsed GIR |
| visual_editor | 🔄 partial | Canvas, nodes, edges, live viz; architecture talk+draw web editor merged |
| ai_integration | 🔄 partial | AI codegen → GIR, contract verification (Z3), explanation engine; GIRGenerator runs NL→GIR |
| test_harness | ⏳ planned | Property-based testing, fuzzing, model checking |
| docs | 🔄 in_progress | Tutorials, API reference, language guide; architecture docs merged |

---

## 15. Research Foundation

Built on **neo4j_research** PostgreSQL datastore with 285 facts across 12 categories:

- **Graph-Native Programming** — Languages where code IS a graph
- **Machine-Level Computing** — CPU architecture, instruction sets, low-level programming
- **Error Correcting Codes** — ECC, FEC, Reed-Solomon, Shannon theory
- **Information Theory** — Entropy, channel capacity, noisy channel coding
- **Programming Paradigms** — Imperative, functional, OOP, declarative, logic
- **Software Engineering at Machine Level** — Assembly, debugging, reverse engineering
- **WebAssembly** — Portable low-level runtime, virtual ISA
- **Neo4j** — Graph database patterns, Cypher query language
- **Data Serialization** — JSON, YAML, Protobuf, MessagePack, CBOR, Avro
- **Hardware Reverse Engineering** — PCB/IC reverse engineering, decapping
- **Open-Source Drivers** — Linux kernel drivers, GPU drivers
- **Family & Kinship** — Genealogy, family tree data models

Access via mem20 MCP server:
```python
memory_recall(query="graph native programming", category="Graph-Native Programming", limit=10)
```

---

## 16. License

MIT OR Apache-2.0