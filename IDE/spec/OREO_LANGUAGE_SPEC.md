# OREO Language Specification

**Version:** 0.1.0 (Draft)  
**Status:** Initial Design  
**Last Updated:** 2026-08-27  

---

## 1. CORE PHILOSOPHY

### 1.1 Graph-Native Semantics
- **Code is a graph** — not text parsed into a graph
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

## 2. GRAPH INTERMEDIATE REPRESENTATION (GIR)

### 2.1 Node Types
```
ValueNode      ::= Literal | Variable | Parameter | Constant
OpNode         ::= Arithmetic | Logic | Comparison | Cast | Call
ControlNode    ::= If | Loop | Match | Try | Sequence | Parallel
TypeNode       ::= Primitive | Composite | Function | Effect | Generic
EffectNode     ::= IO | State | Exception | Async | Resource
MetaNode       ::= Contract | Annotation | Documentation | SourceMap
```

### 2.2 Edge Types
```
DataEdge       ::= value flow (typed)
ControlEdge    ::= execution order
DependencyEdge ::= compile-time dependency
CompositionEdge ::= structural containment
AnnotationEdge ::= metadata attachment
```

### 2.3 Graph Properties
- **Directed** — edges have source → target
- **Acyclic for data flow** — no value cycles (feedback via explicit loop nodes)
- **Hierarchical** — subgraphs for modules, functions, scopes
- **Typed ports** — each port has a type; connections validated

---

## 3. TYPE SYSTEM

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

---

## 4. NATURAL LANGUAGE SYNTAX

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

---

## 5. VISUAL EDITOR SPEC

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

---

## 6. RUNTIME SEMANTICS

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

---

## 7. AI INTEGRATION

### 7.1 Code Generation
- AI outputs GIR directly (not text)
- Type-checks as it generates
- Verifies contracts via SMT (Z3)
- Explains decisions in NL

### 7.2 Verification
- **Type checking** — decidable, fast
- **Contract checking** — SMT-backed pre/post conditions
- **Model checking** — for finite-state subgraphs
- **Fuzzing** — property-based test generation

### 7.3 Explanation
- "Why this node?" → trace to NL source
- "What if?" → counterfactual execution
- "Show me" → visual subgraph extraction

---

## 8. SERIALIZATION FORMATS

### 8.1 Binary (.oreo)
- Compact, fast, versioned
- Includes: GIR, types, effects, contracts, source maps, NL annotations

### 8.2 JSON (.oreo.json)
- Human-readable, diffable
- Schema-validated

### 8.3 Text (.oreo.txt)
- NL representation (round-trippable)
- Markdown-embeddable

### 8.4 GraphViz / Mermaid
- For documentation, export

---

## 9. TOOLCHAIN

### 9.1 Parser
- NL → GIR (semantic parsing)
- Text serialization → GIR
- Incremental, error-tolerant

### 9.2 Type Checker
- Bidirectional type inference
- Effect inference
- Constraint solving (traits, generics)

### 9.3 Compiler
- GIR → bytecode (custom VM) or LLVM IR
- JIT for hot paths
- AOT for distribution

### 9.4 Runtime
- Graph interpreter (reference)
- Compiled executor (optimized)
- Debugger, profiler, visualizer

---

## 10. ROADMAP

### Phase 1: Core (Months 1-3)
- [ ] GIR definition + Rust implementation
- [ ] Type checker (primitives, composites, functions)
- [ ] Effect system (IO, State, Exception)
- [ ] Binary serialization

### Phase 2: NL + Visual (Months 3-6)
- [ ] NL semantic parser (subset)
- [ ] Visual editor (canvas, nodes, edges)
- [ ] Live execution visualization
- [ ] Round-trip NL ↔ Graph

### Phase 3: AI Integration (Months 6-9)
- [ ] AI code generation → GIR
- [ ] Contract verification (Z3)
- [ ] Explanation engine

### Phase 4: Production (Months 9-12)
- [ ] Compiler (LLVM backend)
- [ ] Package manager
- [ ] Standard library
- [ ] Documentation, tutorials

---

## 11. OPEN QUESTIONS

1. **Effect polymorphism syntax** — row polymorphism vs. effect handlers?
2. **NL ambiguity threshold** — when to ask vs. guess?
3. **Graph versioning** — how to diff/merge graphs?
3. **Incremental compilation granularity** — node-level? subgraph-level?
4. **Distribution model** — single binary? WASM? container?
5. **Bootstrapping** — write OREO compiler in OREO?

---

## APPENDIX: RELATED RESEARCH (from neo4j_research)

Key categories to mine:
- **Graph-Native Programming** — existing graph-based languages
- **Machine-Level Computing** — instruction sets, CPU architecture
- **Error Correcting Codes** — reliability, fault tolerance
- **Information Theory** — entropy bounds, compression
- **Programming Paradigms** — classification, evolution
- **Software Engineering at Machine Level** — debugging, reverse engineering
- **WebAssembly** — portable runtime, sandboxing
- **Neo4j** — graph DB patterns, Cypher query language