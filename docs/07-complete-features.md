# 7. Complete Feature-by-Feature Reference — OREO Language

> Comprehensive reference for every feature, component, and interaction in the OREO visual-first NL-first programming language. Treats the reader as if they've never seen the code.

---

## Table of Contents

1. [Language Specification](#1-language-specification)
2. [Graph Intermediate Representation (GIR)](#2-graph-intermediate-representation-gir)
3. [NL Syntax & Parser](#3-nl-syntax--parser)
4. [Runtime & Compiler](#4-runtime--compiler)
5. [Visual Editor](#5-visual-editor)
6. [AI Testing](#6-ai-testing)
7. [Retroactive Completion Audit](#7-retroactive-completion-audit)

---

## 1. Language Specification

### Core Philosophy

| Principle | Description |
|-----------|-------------|
| Graph-Native Semantics | Code IS a graph, not text parsed into a graph |
| Natural Language First | Write programs in English, NL maps to graph structures |
| Visual-First Interface | Primary editor = node-graph canvas |
| AI-Understandable Design | Formal semantics, type system, effect system, contracts |

### Node Categories (NodeKind)

| Category | Kinds | Purpose |
|----------|-------|---------|
| Value | LITERAL, VARIABLE, PARAMETER, CONSTANT | Data representation |
| Operation | ARITHMETIC, LOGIC, COMPARISON, CAST, CALL, INDEX, FIELD_ACCESS | Compute values |
| Control | IF, LOOP, MATCH, TRY, SEQUENCE, PARALLEL, BREAK, CONTINUE, RETURN | Control flow |
| Type | PRIMITIVE_TYPE, COMPOSITE_TYPE, FUNCTION_TYPE, EFFECT_TYPE, GENERIC_TYPE | Type definitions |
| Effect | IO, STATE, EXCEPTION, ASYNC, RESOURCE | Side effects |
| Meta | CONTRACT, ANNOTATION, DOCUMENTATION, SOURCE_MAP | Metadata |
| Scope | MODULE, FUNCTION, SCOPE | Hierarchy |

### Edge Types (EdgeKind)

| Edge | Purpose |
|------|---------|
| DATA | Typed value flow between ports |
| CONTROL | Execution order |
| DEPENDENCY | Compile-time dependency |
| COMPOSITION | Structural containment (parent/child) |
| ANNOTATION | Metadata attachment |

### Core Data Structures

```python
@dataclass
class Port:
    name: str
    type: Optional[TypeRef] = None
    is_input: bool = True
    is_required: bool = True
    default_value: Optional[Any] = None
    description: str = ""

@dataclass
class TypeRef:
    name: str
    type_args: List["TypeRef"] = field(default_factory=list)
    is_mutable: bool = False
    effects: List[str] = field(default_factory=list)

@dataclass
class Node:
    kind: NodeKind
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    ports: Dict[str, Port] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    source_location: Optional[Dict[str, Any]] = None
    parent: Optional["Node"] = None
```

---

## 2. Graph Intermediate Representation (GIR)

### GIR Properties

- **Directed** — edges have source → target
- **Acyclic for data flow** — no value cycles (feedback via explicit loop nodes)
- **Hierarchical** — subgraphs for modules, functions, scopes
- **Typed ports** — each port has a type; connections validated

### GIR Node Types (60+ NodeKinds)

| Category | Count | Examples |
|----------|-------|---------|
| Value | 4 | LITERAL, VARIABLE, PARAMETER, CONSTANT |
| Operation | 7 | ARITHMETIC, LOGIC, COMPARISON, CAST, CALL, INDEX, FIELD_ACCESS |
| Control | 9 | IF, LOOP, MATCH, TRY, SEQUENCE, PARALLEL, BREAK, CONTINUE, RETURN |
| Type | 5 | PRIMITIVE_TYPE, COMPOSITE_TYPE, FUNCTION_TYPE, EFFECT_TYPE, GENERIC_TYPE |
| Effect | 5 | IO, STATE, EXCEPTION, ASYNC, RESOURCE |
| Meta | 4 | CONTRACT, ANNOTATION, DOCUMENTATION, SOURCE_MAP |
| Scope | 3 | MODULE, FUNCTION, SCOPE |

### GIR Edge Types (5 EdgeKinds)

| Edge | Source → Target | Purpose |
|------|-----------------|---------|
| DATA | Operation → Operation | Typed value flow |
| CONTROL | Control → Any | Execution order |
| DEPENDENCY | Any → Any | Compile-time dependency |
| COMPOSITION | Parent → Child | Structural containment |
| ANNOTATION | Meta → Any | Metadata attachment |

### GIR Validation

- Port type checking on all DATA edges
- Acyclicity enforcement for data flow
- Hierarchical scope resolution
- Effect tracking through call graph

---

## 3. NL Syntax & Parser

### Two-Pipeline Design

| Pipeline | Input | Output | Use Case |
|----------|-------|--------|----------|
| Computational NL | English instructions | GIR graph | Writing code in natural language |
| Architecture NL (GraphLang) | Graph specification | GIR graph | Defining system architecture |

### Parser Architecture

```
NL Input
    │
    ▼
Architecture Router (nl_parser/architecture_router.py)
    │
    ├── Computational NL → Semantic Parser (nl_parser/semantic_parser.py)
    │                           │
    │                           ▼
    │                       GIR Generation (parser/gir/types.py)
    │
    └── Architecture NL → GraphLang Parser (parser/architecture/)
                                │
                                ▼
                            GIR Generation
```

### Key Parser Modules

| Module | Path | Purpose |
|--------|------|---------|
| Architecture Parser | `parser/architecture/parser.py` | Parses GraphLang architecture specs |
| Architecture Engine | `parser/architecture/engine.py` | Executes architecture definitions |
| NL Architecture Router | `nl_parser/architecture_router.py` | Routes NL to correct parser |
| NL Semantic Parser | `nl_parser/semantic_parser.py` | Parses computational NL |
| GIR Types | `parser/gir/types.py` | Core GIR data structures |

### NL Syntax Examples

**Computational NL:**
```
Create a function called "calculate_total" that takes a list of numbers
and returns the sum of all even numbers multiplied by 2.
```

**Architecture NL (GraphLang):**
```
APPLICATION: ECommerce
  CONTAINS:
    MODULE: UserAuth
      CONTAINS:
        FUNCTION: login
        FUNCTION: logout
    MODULE: ProductCatalog
      CONTAINS:
        FUNCTION: search
        FUNCTION: filter
```

### Hybrid Parser

Uses rules-first with LLM fallback:
1. Try rule-based parsing first (fast, deterministic)
2. If confidence < threshold, fall back to LLM (OpenAICompat/xAI)
3. LLM output validated against GIR schema before acceptance

---

## 4. Runtime & Compiler

### Runtime Architecture

```
GIR Graph
    │
    ▼
Compiler (runtime/compiler.py)
    │
    ├── Interpreter Path → Graph Interpreter (runtime/interpreter.py)
    │                          │
    │                          ▼
    │                      Execution (node-by-node evaluation)
    │
    └── Bytecode Path → Bytecode Compiler (runtime/bytecode.py)
                            │
                            ▼
                        VM Execution (runtime/vm.py)
```

### Key Runtime Components

| Component | Path | Purpose |
|-----------|------|---------|
| Graph Interpreter | `runtime/interpreter.py` | Direct graph execution |
| Bytecode Compiler | `runtime/bytecode.py` | Compiles GIR to bytecode |
| VM | `runtime/vm.py` | Executes compiled bytecode |
| Memory Model | `runtime/memory.py` | Memory management |
| Effect System | `runtime/effects.py` | Side effect tracking |

### Function Runtime

- Implements handshake protocol (pages refuse until CONNECTS_TO line)
- Function emission operational
- Full graph interpreter still pending

### Effect System

| Effect | Description | Tracking |
|--------|-------------|----------|
| IO | Input/Output operations | Tracked per function |
| State | Mutable state access | Tracked per variable |
| Exception | Error propagation | Tracked per try/catch |
| ASYNC | Asynchronous operations | Tracked per async block |
| RESOURCE | Resource acquisition/release | Tracked per scope |

---

## 5. Visual Editor

### Architecture

```
Visual Editor (visual_editor/)
├── Canvas Renderer — Renders GIR graph as node diagram
├── Interaction Layer — Drag, connect, select, delete
├── Node Registry — All available node types
├── GraphLang Bridge — Syncs with GraphLang parser
└── Web Frontend — Talk+draw web editor
```

### Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| Architecture | `visual_editor/architecture.py` | Editor architecture definition |
| Canvas | `visual_editor/canvas.py` | Node-graph canvas rendering |
| Interaction | `visual_editor/interaction.py` | Mouse/keyboard interaction |
| Nodes | `visual_editor/nodes.py` | Node type definitions |
| GraphLang Editor | `parser/architecture/graphlang_editor.html` | Web-based GraphLang editor |

### Features

- Drag nodes from palette to canvas
- Connect ports with typed edges
- Live execution visualization
- Talk+draw web editor with ears+voice
- Round-trip: visual ↔ text ↔ GIR

### Known Issues

- Computational GIR editor blocked by GIR import bug
- Full visual editor still in development

---

## 6. AI Testing

### Test Harness Architecture

```
Test Harness (test_harness/)
├── Property Tests — Generate and verify properties
├── Fuzzing — Random input generation
├── Integration — End-to-end testing
└── Model Checking — Formal verification
```

### Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| GIR Generator | `ai_integration/gir_generator.py` | Generates GIR from NL |
| Hybrid Parser | `ai_integration/hybrid_parser.py` | Rules-first with LLM fallback |
| Explanation Engine | `ai_integration/explanation.py` | Explains GIR in NL |
| Property Tests | `test_harness/property_tests/` | Property-based testing |
| Fuzzing | `test_harness/fuzzing/` | Fuzz testing |
| Integration | `test_harness/integration/` | Integration tests |
| Model Checking | `test_harness/model_checking/` | Formal verification |

### AI Integration

| Feature | Status | Description |
|---------|--------|-------------|
| GIR Generator | In Progress | Generates GIR from NL descriptions |
| Hybrid Parser | Operational | Rules-first with LLM fallback |
| Explanation Engine | In Progress | Explains GIR in natural language |
| CypherOptimizer | Merged | Optimizes Cypher queries |
| Advise/Scene Packs | Merged | AI-powered advice system |
| Computational AI Codegen | Pending | AI code generation for computational graphs |

### Test Coverage

| Test Type | Status | Coverage |
|-----------|--------|----------|
| Property Tests | Framework in place | Needs expansion |
| Fuzzing | Framework in place | Needs expansion |
| Integration | Framework in place | Needs expansion |
| Model Checking | Framework in place | Needs expansion |

---

## 7. Retroactive Completion Audit

### Phase 1: Research — COMPLETED

- **Date:** August 2026
- **Deliverables:** Research materials in `/home/jayson/OREO/IDE/docs/`
- **Sources:** Neo4j, Graph-Native Programming, Machine-Level Computing, ECC, Information Theory

### Phase 2: Spec — COMPLETED

- **Date:** August 2026
- **Deliverables:** `spec/OREO_LANGUAGE_SPEC.md`, `spec/NL_CYPHER_SPEC.md`
- **Coverage:** GIR, type system, NL syntax, visual editor architecture

### Phase 3: Parser — COMPLETED

- **Date:** August 2026
- **Deliverables:** 20+ parser modules
- **Coverage:** Parsing, emission, optimization, import/export, voice, visual, audit, advise, bolt protocol, queries, LLM integration, shape analysis, lines/drawing

### Phase 4: Runtime — IN PROGRESS

- **Status:** FunctionRuntime and app emission operational
- **Pending:** Full graph interpreter, bytecode compiler, VM

### Phase 5: Visual Editor — IN PROGRESS

- **Status:** Talk+draw web editor with ears+voice
- **Pending:** Computational GIR editor (blocked by GIR import bug)

### Phase 6: AI Integration — IN PROGRESS

- **Status:** HybridParser operational, CypherOptimizer merged
- **Pending:** Computational AI codegen

### Phase 7: Test Harness — IN PROGRESS

- **Status:** Framework in place
- **Pending:** Test expansion

### Phase 8: Docs — IN PROGRESS

- **Status:** Spec docs, README, PROJECT_STRUCTURE written
- **Pending:** Full language guides, user-facing docs

### Documentation Status

| File | Size | Coverage |
|------|------|----------|
| `01-language-spec.md` | 22KB | Complete language spec |
| `02-gir-reference.md` | 13KB | All 60+ NodeKinds, 5 EdgeKinds |
| `03-nl-syntax-parser.md` | 15KB | Computational NL + Architecture NL |
| `04-runtime-compiler.md` | 15KB | Graph interpreter, bytecode, VM |
| `05-visual-editor.md` | 14KB | Canvas, interaction, nodes |
| `06-ai-testing.md` | 17KB | GIRGenerator, hybrid parser, tests |
| `README.md` | 8KB | Documentation index |

---

Last updated: 2026-09-06
