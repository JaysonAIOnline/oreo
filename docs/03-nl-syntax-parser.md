# OREO Natural Language Syntax & Parser Architecture

> Documentation for the NL syntax, semantic parser, and architecture NL router.

---

## 1. Natural Language Syntax

### 1.1 Design Principles

- **Declarative** — describe *what*, not *how*
- **Composable** — small phrases combine into larger programs
- **Context-aware** — pronouns, references resolve to graph nodes
- **Incremental** — partial NL parses to partial graph

### 1.2 Core NL Constructs

#### Function Definition
```
"define function <name> taking <params> returning <type>"
"define async function <name> taking <params> returning <type> with effects <effects>"
```

**Examples:**
- `"define function add taking two integers returning their sum"`
- `"define function factorial taking integer n returning integer with effects none"`
- `"define async function fetch taking url string returning json with effects IO"`

#### Control Flow
```
"if <condition> then <then-branch> else <else-branch>"
"for each <item> in <collection> do <body>"
"while <condition> do <body>"
"match <subject> with <cases>"
"try <body> catch <handler> finally <cleanup>"
```

**Examples:**
- `"if user is admin then grant access else deny"`
- `"for each item in list, process it in parallel"`
- `"while queue not empty, process next item"`

#### Data Operations
```
"read <source> and parse as <format>"
"call <function> with <arguments>"
"create <type> with <fields>"
"get <field> from <object>"
```

**Examples:**
- `"read file config.json and parse as JSON"`
- `"call database query with select * from users"`
- `"create record with name, email, age"`

#### Effects & Contracts
```
"with effect <effect>"
"require <precondition>"
"ensure <postcondition>"
```

**Examples:**
- `"with effect IO"`
- `"require n > 0"`
- `"ensure result >= 0"`

---

## 2. Example Mappings (NL → GIR)

| Natural Language | GIR Structure |
|------------------|---------------|
| `"define function add taking two integers returning their sum"` | `FunctionNode(name="add", params=[a:Int, b:Int], return=Int, effects=[])` with `ArithmeticNode(ADD)` |
| `"if user is admin then grant access else deny"` | `IfNode(cond=Call(UserIsAdmin), then=Call(GrantAccess), else=Call(Deny))` |
| `"read file config.json and parse as JSON"` | `Sequence(Call(readFile, "config.json"), Call(parseJSON, _))` |
| `"for each item in list, process it in parallel"` | `Parallel(Loop(items, Call(ProcessItem)))` |
| `"define function factorial taking integer n returning integer"` | `FunctionNode(name="factorial", params=[n:Int], return=Int, body=If(n<=1, 1, n*factorial(n-1)))` |

---

## 3. Semantic Parser Architecture

### 3.1 File Structure
```
/home/jayson/OREO/IDE/parser/nl_parser/
├── semantic_parser.py      # NL → computational GIR
├── architecture_router.py  # NL → Architecture package (GraphLang)
└── __init__.py
```

### 3.2 Semantic Parser (`semantic_parser.py`)

**Class:** `SemanticParser`

```python
class SemanticParser:
    """Converts natural language descriptions into GIR graphs."""
    
    def __init__(self):
        self.context = ParseContext()  # tracks variables, functions, types in scope
    
    def parse(self, nl_text: str, context: Optional[ParseContext] = None) -> Graph:
        """Parse NL text into a GIR graph."""
        # 1. Tokenize and segment
        # 2. Identify intent (function_def, control_flow, data_op, etc.)
        # 3. Extract entities (names, types, values)
        # 4. Build GIR nodes and edges
        # 5. Type-check as we go
        # 6. Return graph
    
    def parse_incremental(self, nl_fragment: str) -> GraphDelta:
        """Parse a fragment, return delta for live editing."""
```

**Key Methods:**
- `parse_function_def(text)` → FunctionNode
- `parse_control_flow(text)` → IfNode/LoopNode/MatchNode/TryNode
- `parse_data_operation(text)` → CallNode/SequenceNode
- `parse_type_annotation(text)` → TypeRef
- `parse_effect_row(text)` → EffectRow

### 3.3 Architecture Router (`architecture_router.py`)

Routes architecture-related NL (pages, databases, auth, includes) to the GraphLang subsystem:

```python
class ArchitectureNLRouter:
    """Routes natural-language that is about *application architecture* 
    (pages, databases, auth handshakes, includes) to the OREO Architecture
    package (parser/architecture)."""
    
    def route(self, nl_text: str) -> Optional[ArchIntent]:
        # Detects: "page", "database", "db", "auth", "include", "connect", "handshake"
        # Returns: ArchIntent or None (for computational NL)
```

**Supported Architecture Intents:**
| Intent | NL Patterns | GraphLang Action |
|--------|-------------|------------------|
| `create_page` | "create page", "landing page", "page at /" | `merge_page()` |
| `create_database` | "create database", "add a db", "postgres database" | `merge_database()` |
| `create_auth` | "create auth", "secure auth", "JWT auth" | `merge_auth()` |
| `create_include` | "create include", "shared module", "header", "footer" | `merge_include()` |
| `connect_with_auth` | "connect ... with auth", "secure connection" | `connect_with_auth()` |
| `include` | "include", "add header", "add footer" | `include()` |
| `query_neighbors` | "show me what connects to", "what uses" | `query_neighbors()` |
| `impact` | "what would break if", "impact of deleting" | `impact_analysis()` |

---

## 4. Architecture NL Layer (GraphLang)

Merged from the GraphLang project — a self-contained NL+visual architecture modeling system.

### 4.1 Files
```
/home/jayson/OREO/IDE/parser/architecture/
├── lines.py        # Speech → Intent → Cypher
├── runtime.py      # Handshake enforcement (CONNECTS_TO + AUTHENTICATES_WITH)
├── emit.py         # Emit runnable web app from graph
├── visual.py       # Talk+draw web editor (ears + voice)
├── optimize.py     # Cypher optimizer
├── store.py        # In-memory graph store
├── voice.py        # TTS narration
└── __init__.py
```

### 4.2 NL → Intent → Cypher Pipeline

**File:** `lines.py`

```python
# 1. Speech → Intent (deterministic rules + light NLP)
def infer_intent(speech: str) -> Intent:
    # Pattern matching on speech
    # Returns structured Intent object

# 2. Intent → Cypher (template-based)
def intent_to_cypher(intent: Intent) -> str:
    # Uses predefined Cypher templates (from NL_CYPHER_SPEC.md)
    # Returns parameterized Cypher query

# 3. Cypher → Graph (execution)
def execute_cypher(cypher: str, params: Dict) -> Graph:
    # Runs on in-memory graph store
```

### 4.3 Intent Types

```python
@dataclass
class Intent:
    action: str  # create_node, connect, connect_with_auth, include, disconnect, update_props, query_neighbors, impact, lint
    source: Optional[NodeRef] = None
    target: Optional[NodeRef] = None
    auth: Optional[AuthSpec] = None
    roles: List[str] = field(default_factory=list)
    create_missing: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)
```

### 4.4 Cypher Templates (from NL_CYPHER_SPEC.md)

**Key Patterns:**
1. **Upsert Page** — `MERGE (p:Page {id: $id}) ...`
2. **Upsert Database** — `MERGE (d:Database {id: $id}) ...`
3. **Upsert Auth** — `MERGE (a:Auth {id: $id}) ...`
4. **Upsert Include** — `MERGE (i:Include {id: $id}) ...`
5. **Connect with Handshake** — `MERGE (src)-[r:CONNECTS_TO]->(db) ...`
6. **Attach Auth** — `MERGE (src)-[r:AUTHENTICATES_WITH]->(a) ...`
7. **Include Module** — `MERGE (src)-[r:INCLUDES]->(i) ...`
8. **Combined: Connect + Secure Auth** — Pattern 1.8 (full handshake)
9. **Query: Neighborhood** — `MATCH (n)-[r:CONNECTS_TO]->(d:Database) ...`
10. **Query: Impact Analysis** — `MATCH (target {id: $id}) OPTIONAL MATCH ...`

### 4.5 Runtime Enforcement

**File:** `runtime.py`

```python
class GraphRuntime:
    """Relationship runtime: edges are the program.
    
    - CONNECTS_TO opens a store handle
    - AUTHENTICATES_WITH is the handshake
    - INCLUDES are composed into the response
    - No line means the request is refused
    """
    
    def handle_request(self, page_id: str) -> Response:
        # 1. Check page exists
        # 2. Check CONNECTS_TO to a Database
        # 3. Check AUTHENTICATES_WITH to an Auth
        # 4. If any missing → 403 Forbidden
        # 5. Compose INCLUDES in order
        # 6. Execute handler, return response
```

---

## 5. Parser Integration

### 5.1 Two-Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input (NL)                          │
└─────────────────────────────┬───────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌─────────────────────┐           ┌─────────────────────┐
    │ Architecture NL     │           │ Computational NL    │
    │ (pages, dbs, auth,  │           │ (functions, logic,  │
    │  includes, connect) │           │  data, control)     │
    └────────────┬────────┘           └──────────┬──────────┘
                 │                               │
                 ▼                               ▼
        ┌─────────────────┐             ┌─────────────────┐
        │ GraphLang       │             │ Semantic Parser │
        │ (parser/arch)   │             │ (parser/nl)     │
        └────────┬────────┘             └────────┬────────┘
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │   Unified GIR Graph    │
                    └────────────────────────┘
```

### 5.2 Entry Points

**Computational NL:**
```python
from parser.nl_parser import SemanticParser

parser = SemanticParser()
graph = parser.parse("define function add taking two integers returning their sum")
```

**Architecture NL:**
```python
from parser.architecture import Graph, GraphRuntime

g = Graph()
g.merge_page("page_landing", "Landing", "/")
g.merge_database("db_main", "MainDB", "postgres")
g.merge_auth("auth_secure_jwt", "SecureJWT", "jwt", "secure", requires_https=True)
g.connect_with_auth("page_landing", "db_main", "auth_secure_jwt")

runtime = GraphRuntime(g)
response = runtime.handle_request("page_landing")
```

**Unified (via Architecture Router):**
```python
from parser.nl_parser import ArchitectureNLRouter

router = ArchitectureNLRouter()
intent = router.route("connect the db to the landing page with a secure auth")
if intent:
    # Execute via GraphLang
    pass
else:
    # Route to computational parser
    pass
```

---

## 6. Ambiguity Resolution

### 6.1 Strategies (in priority order)

1. **Type-directed** — Use expected type from context to disambiguate
2. **Graph context** — References resolve to nearby nodes in graph
3. **Interactive clarification** — Ask user/AI: "Did you mean X or Y?"
4. **Most general** — Default to most general interpretation

### 6.2 Common Ambiguities

| Ambiguity | Resolution |
|-----------|------------|
| "the function" | Most recently defined, or only one in scope |
| "it" / "that" | Last mentioned value node |
| "the database" | Most recent Database node, or only one |
| "secure auth" | Auth with `level="secure"`, create JWT+HTTPS if none |
| "all pages" | Every `:Page` node in architecture graph |

---

## 7. Running the Parsers

### 7.1 Architecture NL Demo
```bash
# Interactive demo
python3 -m parser.architecture.demo

# Direct NL input
python3 -c "
from parser.architecture import Graph, GraphRuntime
g = Graph()
# ... build graph via NL ...
"
```

### 7.2 Computational NL (when ready)
```bash
# Via semantic parser (Python)
python3 -c "
from parser.nl_parser import SemanticParser
p = SemanticParser()
g = p.parse('define function add taking a:int b:int returning int')
print(g)
"
```

### 7.3 Visual Editor Integration

The visual editor accepts NL input via:
- **NL Input Box** — type NL, see graph appear on canvas
- **Voice Input** — speech-to-text → NL → graph (via `voice.py`)
- **AI Generation** — LLM → Intent → Graph (via `ai_integration/codegen/gir_generator.py`)

---

## 8. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `/home/jayson/OREO/IDE/parser/nl_parser/semantic_parser.py` | ~1600 | Computational NL → GIR |
| `/home/jayson/OREO/IDE/parser/nl_parser/architecture_router.py` | ~250 | Architecture NL router |
| `/home/jayson/OREO/IDE/parser/architecture/lines.py` | ~1900 | Speech → Intent → Cypher |
| `/home/jayson/OREO/IDE/parser/architecture/runtime.py` | ~600 | Handshake runtime |
| `/home/jayson/OREO/IDE/parser/architecture/emit.py` | ~500 | Emit web app |
| `/home/jayson/OREO/IDE/parser/architecture/visual.py` | ~1900 | Talk+draw web editor |
| `/home/jayson/OREO/IDE/spec/NL_CYPHER_SPEC.md` | 328 | Cypher templates reference |

---

## 9. Example: Complete Architecture Flow

**Speech:**
> "I need a db, three pages and a couple of includes. Connect the db to the landing page with a secure auth. Make all pages include Header and Footer."

**Resulting Graph:**
```
(:Database {id:"db_main", name:"MainDB"})
(:Page {id:"page_landing", name:"Landing", path:"/"})
(:Page {id:"page_dashboard", name:"Dashboard"})
(:Page {id:"page_settings", name:"Settings"})
(:Include {id:"inc_header", name:"Header"})
(:Include {id:"inc_footer", name:"Footer"})
(:Auth {id:"auth_secure_jwt", method:"jwt", level:"secure", requires_https:true})

(page_landing)-[:CONNECTS_TO {secure:true, auth_method:"jwt"}]->(db_main)
(page_landing)-[:AUTHENTICATES_WITH {required:true}]->(auth_secure_jwt)
(page_landing)-[:INCLUDES {order:0}]->(inc_header)
(page_landing)-[:INCLUDES {order:1}]->(inc_footer)
(page_dashboard)-[:INCLUDES {order:0}]->(inc_header)
(page_dashboard)-[:INCLUDES {order:1}]->(inc_footer)
(page_settings)-[:INCLUDES {order:0}]->(inc_header)
(page_settings)-[:INCLUDES {order:1}]->(inc_footer)
```

**Note:** Only Landing received the handshake. Dashboard and Settings still have includes but no `CONNECTS_TO` until explicitly connected — the line is the contract.

---

*Generated from OREO source code — see `/home/jayson/OREO/IDE/parser/nl_parser/` and `/home/jayson/OREO/IDE/parser/architecture/` for implementation.*