# OREO PROJECT — ALL AGENTS READ FIRST

**Last Updated:** 2026-08-27  
**Project Codename:** OREO  
**Type:** Neo4j-backed, visual-first, natural-language-first programming language  
**Target:** AI-friendly, CPU-only, runs on retired hardware  

---

## 🎯 PROJECT VISION

Building a **new programming language** where:
- **Code IS a graph** — not text that gets parsed into a graph
- **Natural language is first-class** — write code in English (or any NL), get executable graph
- **Visual-first** — the primary interface is a node-graph editor, not a text editor
- **AI-native** — designed for AI to generate, verify, and reason about
- **CPU-only** — no GPU required; runs on old laptops, Raspberry Pis, basement hardware
- **Understandable** — formal semantics AI can check, humans can read

---

## 📍 KEY LOCATIONS

| Purpose | Path |
|---------|------|
| **IDE Workspace** | `/home/jayson/OREO/IDE/` |
| **Data/Research** | `/home/jayson/OREO/DATA/` |
| **PostgreSQL Datastore** | Local PostgreSQL 18, database `neo4j_research` |
| **Mem20 Memory** | `/home/jayson/mem20/` (MCP server) |
| **Hermes Config** | `/root/.hermes/config.yaml` |

---

## 🗄️ POSTGRESQL DATASTORE (neo4j_research)

**Connection:**
```bash
# Local PostgreSQL 18 (port 5432)
sudo -u postgres psql -d neo4j_research
```

**Schema (11 tables):**
| Table | Purpose |
|-------|---------|
| `research_sources` | Source documents (URLs, papers, specs) |
| `research_sections` | Extracted sections from sources |
| `research_facts` | Atomic facts with categories/tags |
| `research_categories` | 12 top-level categories |
| `research_subcategories` | 30 subcategories |
| `research_source_categories` | Many-to-many source↔category |
| `research_source_subcategories` | Many-to-many source↔subcategory |
| `research_source_flags` | Quality/weak-spot flags |
| `research_depths` | Depth levels (overview → implementation) |
| `research_runs` | Ingestion run metadata |
| `research_run_sources` | Run→source mapping |

**Current Content (as of 2026-09-08 after data-integrity cleanup, refreshed by `DATA/sync_neo4j_to_oreo.py`):**
- **12 Categories:** Neo4j, Graph-Native Programming, Machine-Level Computing, Error Correcting Codes, Family & Kinship, Hardware Reverse Engineering, Information Theory, Open-Source Drivers, Programming Paradigms, Software Engineering at Machine Level, WebAssembly, Data Serialization
- **29 Sources** → **29 Sections** → **139 Facts** (deduped: duplicate source URLs were ingested twice, inflating 139 facts to 285 rows)
- **30 Subcategories** across all categories
- **Sync:** `/root/.venv/bin/python DATA/sync_neo4j_to_oreo.py` regenerates `IDE/DATA/*.json` + `index.json` + `DATA/exports/*.csv` from the `neo4j_research` Postgres DB (was `family_and_kinship.json`, now `family_&_kinship.json`).

**Key Categories for OREO Language Design:**
1. **Graph-Native Programming** — Languages where code IS a graph
2. **Machine-Level Computing** — CPU architecture, instruction sets, low-level programming
3. **Error Correcting Codes** — ECC, FEC, Reed-Solomon, Shannon theory
4. **Information Theory** — Entropy, channel capacity, noisy channel coding
5. **Programming Paradigms** — Imperative, functional, OOP, declarative, logic
6. **Software Engineering at Machine Level** — Assembly, debugging, reverse engineering

---

## 🧠 MEM20 — PERSISTENT MEMORY & COGNITIVE ENGINE

**MCP Server:** `/home/jayson/mem20/mcp/mcp_server.py` (running as systemd service `mcp-server`)

**Tools Available (14):**
| Domain | Tools |
|--------|-------|
| **Memory** | `memory_store`, `memory_recall`, `memory_probe`, `memory_reason`, `memory_status` |
| **Cognitive** | `cog_process` (analyze/synthesize/evaluate/plan), `cog_chain` |
| **Roadmap** | `roadmap_create`, `roadmap_list`, `roadmap_get`, `roadmap_update_phase` |
| **Filesystem** | `fs_read`, `fs_write`, `fs_list` |

**Usage via Hermes:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "memory_recall",
    "arguments": {"query": "graph native programming", "limit": 10}
  }
}
```

**Cognitive Engine Modes:**
- `analyze` — Break down, examine structure, identify patterns
- `synthesize` — Combine ideas, find connections, create new understanding
- `evaluate` — Assess feasibility, impact, risks, trade-offs
- `plan` — Create actionable steps, timeline, resources

---

## 🛣️ ROADMAP SYSTEM

Roadmaps stored as JSON in `/home/jayson/mem20/roadmaps/`

**Example OREO Roadmap:**
```bash
# Create via MCP tool
roadmap_create: {
  "name": "oreo_language",
  "description": "Build OREO visual-first NL-first programming language",
  "phases": ["research", "spec", "parser", "runtime", "visual_editor", "ai_integration", "test_harness", "docs"]
}
```

---

## 🔧 HERMES INTEGRATION

**Config:** `/root/.hermes/config.yaml` has `mcp_servers.mem20` enabled

**Known Issue:** `hermes mcp test mem20` fails with "Connection closed" — but direct `_connect_server` works. The server runs fine; it's a Hermes watchdog/transport layer issue.

**Workaround:** Test directly:
```python
from tools.mcp_tool import _connect_server
server = await _connect_server('mem20', config)
```

---

## 📋 CATCHUP CHECKLIST FOR NEW AGENTS

### Immediate (Do First)
- [ ] Read this entire document
- [ ] Verify PostgreSQL access: `sudo -u postgres psql -d neo4j_research -c "SELECT count(*) FROM research_facts;"`
- [ ] Test mem20 MCP: Run a `memory_recall` query for "graph native programming"
- [ ] Check OREO IDE workspace exists: `ls -la /home/jayson/OREO/IDE/`

### Context Loading (Do Second)
- [ ] Query mem20 for "OREO language design" — check cognitive engine output
- [ ] Query mem20 for "visual first programming language" — check related facts
- [ ] Review roadmap: `roadmap_get` for "oreo_language" (create if missing)
- [ ] Scan categories: Neo4j, Graph-Native Programming, Machine-Level Computing, Error Correcting Codes

### Deep Dive (Do Third)
- [ ] Extract all facts for "Graph-Native Programming" category
- [ ] Extract all facts for "Machine-Level Computing" category  
- [ ] Extract all facts for "Error Correcting Codes" category
- [ ] Run cognitive chain: ["Analyze OREO requirements", "Design graph IR", "Plan parser", "Design visual editor"]

---

## 🎯 CURRENT PRIORITIES (from latest session)

1. **OREO IDE: Architecture subsystem merged & runnable** — GraphLang checkpoint merged as `parser/architecture/` (NL→intent→Cypher/Neo4j, relationship handshake runtime, talk+draw web editor). Verified: `python3 -m parser.architecture.demo`, `examples/architecture/runtime_handshake.py`, `examples/architecture/emit_and_hit.py` all run.
2. **Computational GIR layer fully unblocked (2026-08-31)** — fixed parser/gir/types.py dataclass bug, `Node.kind`/`Edge.kind` defaults, `ANY` top-type unification, `TypeScheme` import, expression-node result ports, tokenizer symbol operators, and the semantic NL parser. `parse_nl`/`NLParser` now produce valid graphs for the documented grammar; NL→GIR→BytecodeCompiler and GIRGenerator pipelines verified.
3. **Populate OREO IDE workspace** — initial structure now present; language spec continues (in_progress).
4. **Fix Hermes MCP test connection** — debug watchdog/transport
5. **Complete mem20 production release** — verify all 6 criteria

---

## 🔑 KEY PRINCIPLES (Non-Negotiable)

| Principle | Description |
|-----------|-------------|
| **No fake code** | Real implementations only; no stubs, no placeholders |
| **CPU-only** | No GPU dependencies ever; optimize for old hardware |
| **Visual-first** | Primary interface = node graph editor |
| **NL-first** | Natural language is a first-class syntax |
| **AI-understandable** | Formal specs AI can verify; declarative semantics |
| **Graph-native** | Code IS a graph; text is a serialization format |
| **No condensing** | Preserve all research detail in datastore |

---

## 📚 REFERENCE SESSIONS

| Session | Topic | Link |
|---------|-------|------|
| `bg_3b6ce2` | OREO datastore discovery, mem20 build | `@session:default/bg_3b6ce2` |
| `20260824_092911_82babd` | Neo4j research → PostgreSQL (285 facts) | `@session:default/20260824_092911_82babd` |
| `20260825_163904_381387` | OREO project naming, neo4j focus | `@session:default/20260825_163904_381387` |

---

## 🚀 QUICK START COMMANDS

```bash
# 1. Check PostgreSQL data
sudo -u postgres psql -d neo4j_research -c "SELECT name FROM research_categories ORDER BY name;"

# 2. Test mem20 memory
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/memories/store')
from memory import recall
for r in recall(topic='Graph-Native Programming', k=5):
    print(f\"[{r['ts'][:19]}] {r['content'][:200]}\")
"

# 3. Test mem20 cognitive engine
python3 -c "
import sys; sys.path.insert(0, '/home/jayson/mem20/cog')
from cognitive_engine import process_thought
print(process_thought('How should OREO represent control flow as a graph?', 'analyze'))
"

# 4. Check roadmap
python3 -c "
import sys; sys.path.insert(0, '/home/jayson/mem20/mcp')
from mcp_server import Mem20MCPServer
import asyncio
async def test():
    s = Mem20MCPServer()
    print(await s._roadmap_list())
asyncio.run(test())
"
```

---

## ⚠️ KNOWN ISSUES

1. _(fixed 2026-08-30...31)_ Computational GIR layer — a cascade of pre-existing latent bugs was fixed once unblocked: `parser/gir/types.py` dataclass bug (`kw_only` base fields), `Node.kind`/`Edge.kind` defaults (subclasses set kind in `__post_init__`), `ANY` top-type unification in `types.py:unify`, missing `TypeScheme` import in validation.py, `create_*`/`connect_composition`/`ReturnNode`/`Port` import gaps in semantic_parser.py, literals not added to graph in `_parse_primary`, expression-node `result` ports defaulted to `Any`, tokenizer symbol operators (`+ - * / < > <= >= == !=`), if/else control-edge direction, call-node `arg{i}`/`function` ports, helper import paths (`..parser.gir` → `parser.gir`, `TokenType.FN`, missing `Set`, `TypeRef` in evaluator.py). Verified: imports OK, `parse_nl` produces valid graphs, `GIRGenerator`, `BytecodeCompiler`, `Interpreter` run.
2. **Remaining compute-NL grammar quirks (by design, not bugs)** — operator words are reserved (function named `add` tokenizes as `PLUS`); NL→`returns` keyword form not yet supported (use brace body `{ return expr }`); `runtime.interpreter` runs but is a partial evaluator (returns `None` for `return <expr>` — unimplemented value propagation, not a wiring bug).
3. **Hermes MCP test fails** — `hermes mcp test mem20` returns "Connection closed" but direct connection works
4. **mem20 systemd service** — runs but exits quickly (restart loop); MCP server works when tested directly

---

## 📞 ESCALATION

If blocked on:
- **PostgreSQL access** → Check `pg_lsclusters`, start cluster 18 main
- **mem20 MCP** → Test direct with `_connect_server` from `tools.mcp_tool`
- **Hermes config** → Check `/root/.hermes/config.yaml` mcp_servers section
- **OREO research** → Query mem20 memory system for relevant facts

---

**Remember:** This project is about pulling computing power out of attics and basements. Every design decision should ask: "Would this run on a 10-year-old laptop? Can an AI understand it? Is the graph the source of truth?"