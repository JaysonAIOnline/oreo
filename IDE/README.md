# OREO IDE Workspace

**Visual-first, natural-language-first programming language**

---

## 🎯 Vision

Building a new programming language where:
- **Code IS a graph** — not text that gets parsed into a graph
- **Natural language is first-class** — write code in English, get executable graph
- **Visual-first** — primary interface is a node-graph editor
- **AI-native** — designed for AI to generate, verify, and reason about
- **CPU-only** — no GPU required; runs on old hardware

---

## 📁 Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for full directory layout.

```
OREO/IDE/
├── spec/                 # Language specification (+ NL/Cypher spec)
├── parser/               # NL parser + text parser + GIR + architecture
│   ├── gir/              #   computational GIR (nodes/edges/types/validation)
│   ├── nl_parser/        #   NL front-ends (semantic + architecture router)
│   └── architecture/     #   NL+visual architecture modeling (from GraphLang)
├── runtime/              # Interpreter + compiler + memory
├── visual_editor/        # Canvas, nodes, live visualization (+ architecture bridge)
├── ai_integration/       # AI codegen, verification, explanation
├── test_harness/         # Property tests, fuzzing, model checking
├── docs/                 # Documentation (+ docs/architecture/)
├── examples/             # Example programs (+ examples/architecture/)
├── Cargo.toml            # Rust workspace
├── pyproject.toml        # Python workspace
└── README.md             # This file
```

---

## 🚀 Quick Start

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
```bash
# Using the interpreter (once implemented)
cargo run --bin oreo-interpreter examples/hello_world.oreo

# Using the visual editor
cargo run --bin oreo-editor
```

### Architecture subsystem — runnable now (merged from GraphLang)
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

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [spec/OREO_LANGUAGE_SPEC.md](spec/OREO_LANGUAGE_SPEC.md) | Complete language specification |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Detailed project structure |
| [ALL AGENTS READ FIRST.md](../ALL%20AGENTS%20READ%20FIRST.md) | Agent onboarding guide |

---

## 🛣️ Roadmap

Current roadmap: **oreo_language** (8 phases)

| Phase | Status | Description |
|-------|--------|-------------|
| research | ✅ completed | Neo4j, Graph-Native Programming, Machine-Level Computing, ECC, Information Theory |
| spec | 🔄 in_progress | GIR, type system, NL syntax, visual editor defined |
| parser | 🔄 partial: architecture + compute NL | NL semantic parser + text serialization parser; **architecture NL parser merged & runnable**; **compute-NL `parse_nl` now produces valid GIR** |
| runtime | 🔄 partial | Graph interpreter, effect system, memory model, concurrency; **relationship handshake runtime merged**; bytecode compiler runs on parsed GIR |
| visual_editor | 🔄 partial | Canvas, nodes, edges, live execution visualization; **architecture talk+draw web editor merged**; computational editor modules import & run |
| ai_integration | 🔄 partial | AI codegen → GIR, contract verification (Z3), explanation engine; **LLM intent hybrid parser merged**; GIRGenerator runs NL→GIR |
| test_harness | ⏳ planned | Property-based testing, fuzzing, model checking |
| docs | 🔄 in_progress | Tutorials, API reference, language guide; **architecture docs merged** |

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

## 🤝 Contributing

See [CONTRIBUTING.md](docs/contributing.md) (to be created).

---

## 📄 License

MIT OR Apache-2.0