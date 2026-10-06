# OREO Documentation

> Visual-first, natural-language-first programming language where **code IS a graph**, not text parsed into a graph.

---

## 📚 Documentation Index

| Document | Description |
|----------|-------------|
| [01-language-spec.md](01-language-spec.md) | Complete language specification — philosophy, GIR, type system, NL syntax, visual editor, runtime, AI integration, serialization, toolchain, roadmap |
| [02-gir-reference.md](02-gir-reference.md) | Graph Intermediate Representation reference — all node kinds, edge kinds, validation rules, serialization formats, Rust implementation |
| [03-nl-syntax-parser.md](03-nl-syntax-parser.md) | Natural language syntax & parser architecture — computational NL, architecture NL (GraphLang), two-pipeline design, ambiguity resolution |
| [04-runtime-compiler.md](04-runtime-compiler.md) | Runtime & compiler — graph interpreter, effect system, memory model, concurrency, bytecode compiler, VM spec, Rust core |
| [05-visual-editor.md](05-visual-editor.md) | Visual editor — canvas renderer, interaction system, node registry, GraphLang bridge, web frontend, live visualization |
| [06-ai-testing.md](06-ai-testing.md) | AI integration & test harness — GIR generation, hybrid parser, explanation engine, property tests, fuzzing, model checking, integration tests |

---

## 🚀 Quick Start

### Prerequisites
- Rust 1.75+ (core implementation)
- Python 3.11+ (AI integration, tooling, architecture subsystem)
- Node.js 18+ (visual editor web frontend)

### Build
```bash
# Rust workspace
cargo build --workspace

# Python workspace
pip install -e .[dev,ai]

# Visual editor (web frontend)
cd visual_editor/web && npm install && npm run dev
```

### Run Architecture Subsystem (Runnable Now — Merged from GraphLang)
```bash
# NL → architecture graph (pages, databases, auth handshakes, includes)
python3 -m parser.architecture.demo

# Relationship runtime: pages refused until handshake line exists
python3 examples/architecture/runtime_handshake.py

# Emit runnable web app from graph and hit its routes
python3 examples/architecture/emit_and_hit.py

# Live talk + draw web editor (ears + voice)
python3 -m parser.architecture.visual
```

### Run Computational Examples (When Interpreter Ready)
```bash
# Using the interpreter
cargo run --bin oreo-interpreter examples/hello_world.oreo

# Using the visual editor
cargo run --bin oreo-editor
```

---

## 🏗️ Project Structure

```
OREO/IDE/
├── spec/                      # Language specification
│   ├── OREO_LANGUAGE_SPEC.md  # Complete language spec
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
│       ├── lines.py           # Speech → Intent → Cypher
│       ├── runtime.py         # Handshake enforcement
│       ├── emit.py            # Emit runnable web app
│       ├── visual.py          # Talk+draw web editor (ears + voice)
│       ├── optimize.py        # Cypher optimizer
│       ├── store.py           # In-memory graph store
│       └── voice.py           # TTS narration
├── runtime/                   # Interpreter + compiler + memory
│   ├── interpreter/
│   │   └── evaluator.py       # Graph interpreter (~1700 lines)
│   └── compiler/
│       └── backends.py        # Compiler backends (bytecode + stubs)
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
├── docs/                      # This documentation
├── examples/                  # Example programs
│   ├── hello_world.oreo
│   ├── factorial.oreo
│   └── architecture/          # Architecture subsystem examples
├── Cargo.toml                 # Rust workspace (core GIR, type checker)
├── pyproject.toml             # Python workspace (parser, runtime, editor, AI)
└── README.md                  # Project overview
```

---

## 🎯 Vision

Building a new programming language where:
- **Code IS a graph** — not text that gets parsed into a graph
- **Natural language is first-class** — write code in English, get executable graph
- **Visual-first** — primary interface is a node-graph editor
- **AI-native** — designed for AI to generate, verify, and reason about
- **CPU-only** — no GPU required; runs on old hardware

---

## 🛣️ Roadmap Status

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

## 🔬 Research Foundation

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

## 📄 License

MIT OR Apache-2.0

---

## 🔗 Related Projects

- **GraphLang** — Merged architecture NL+visual subsystem (`parser/architecture/`)
- **neo4j_research** — Research datastore (285 facts, 12 categories)
- **mem20** — Memory + cognition substrate for AI agents (MCP server)