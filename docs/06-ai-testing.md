# OREO AI Integration & Test Harness

> Documentation for AI code generation, verification, explanation, and the test harness (property tests, fuzzing, model checking).

---

## 1. AI Integration Overview

OREO is designed **AI-first** — the graph (GIR) is the native representation for AI generation, verification, and reasoning. AI doesn't generate text code; it generates graphs directly.

### 1.1 Three Pillars

| Pillar | Purpose | Implementation |
|--------|---------|----------------|
| **Code Generation** | AI → GIR | `ai_integration/codegen/gir_generator.py` |
| **Verification** | Type-check, contracts, model-check | `ai_integration/verification/` (planned) |
| **Explanation** | Graph → NL, counterfactuals, subgraph extraction | `ai_integration/explanation/` (planned) |

---

## 2. AI Code Generation

### 2.1 File
`/home/jayson/OREO/IDE/ai_integration/codegen/gir_generator.py`

### 2.2 GIRGenerator Class

```python
class GIRGenerator:
    """Generates GIR graphs from natural language using AI."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.type_checker = TypeChecker()
        self.contract_verifier = ContractVerifier()  # Z3-backed
    
    def generate(self, nl_prompt: str, context: Optional[Graph] = None) -> GenerationResult:
        """Generate GIR from NL prompt."""
        # 1. Build prompt with context (existing graph, type info, patterns)
        # 2. Call LLM with structured output schema (GIR JSON)
        # 3. Parse LLM output into GIR nodes/edges
        # 4. Type-check generated graph
        # 5. Verify contracts with Z3
        # 6. Return result (graph + any errors/warnings)
    
    def generate_incremental(self, nl_fragment: str, existing_graph: Graph) -> GraphDelta:
        """Generate a graph delta for live editing."""
```

### 2.3 Generation Pipeline

```
NL Prompt
    │
    ▼
┌─────────────────────────────────────┐
│  Prompt Builder                     │
│  - System prompt (GIR schema)       │
│  - Context (existing graph, types)  │
│  - Few-shot examples                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  LLM (structured output)            │
│  Output: GIR JSON + reasoning       │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Parser & Validator                 │
│  - JSON → GIR nodes/edges           │
│  - Type check (bidirectional)       │
│  - Effect check                     │
│  - Contract verify (Z3)             │
└────────────┬────────────────────────┘
             │
             ▼
      Generated Graph
```

### 2.4 LLM Output Schema

The LLM emits structured JSON matching the GIR schema:

```json
{
  "nodes": [
    {
      "id": "n1",
      "kind": "function",
      "name": "add",
      "properties": {
        "params": ["a", "b"],
        "return_type": "Int(32)",
        "effects": []
      },
      "ports": {
        "a": { "name": "a", "type": "Int(32)", "is_input": true },
        "b": { "name": "b", "type": "Int(32)", "is_input": true },
        "result": { "name": "result", "type": "Int(32)", "is_input": false }
      }
    },
    {
      "id": "n2",
      "kind": "arithmetic",
      "properties": { "op": "add" },
      "ports": {
        "lhs": { "name": "lhs", "type": "Int(32)", "is_input": true },
        "rhs": { "name": "rhs", "type": "Int(32)", "is_input": true },
        "result": { "name": "result", "type": "Int(32)", "is_input": false }
      }
    }
  ],
  "edges": [
    { "id": "e1", "kind": "DATA", "source": "n1", "target": "n2", "source_port": "a", "target_port": "lhs" },
    { "id": "e2", "kind": "DATA", "source": "n1", "target": "n2", "source_port": "b", "target_port": "rhs" },
    { "id": "e3", "kind": "DATA", "source": "n2", "target": "n1", "source_port": "result", "target_port": "return" }
  ],
  "reasoning": "Created add function with two Int params. Used ArithmeticNode(ADD) for the body. Connected params to lhs/rhs, result to return port."
}
```

### 2.5 Type Checking During Generation

- **Bidirectional type inference** — synthesizes types for expressions, checks against expected
- **Effect inference** — infers effect row from operations
- **Constraint solving** — resolves generics, traits
- **Error feedback to LLM** — if type check fails, error fed back for retry

### 2.6 Contract Verification (Z3)

```python
class ContractVerifier:
    """Verifies pre/post conditions using Z3 SMT solver."""
    
    def verify(self, graph: Graph) -> VerificationResult:
        # 1. Extract all CONTRACT nodes
        # 2. Translate to Z3 formulas
        # 3. Check satisfiability
        # 4. Check implication: pre ∧ body → post
        # 5. Return: verified / counterexample / unknown
```

**Contract types:**
- `requires` — precondition
- `ensures` — postcondition
- `invariant` — loop invariant
- `decreases` — termination metric

---

## 3. LLM Intent Hybrid Parser

### 3.1 File
`/home/jayson/OREO/IDE/ai_integration/parser.py`

### 3.2 Purpose
Merges LLM-based intent parsing with deterministic rule-based parser for:
- Architecture NL commands (pages, databases, auth, includes)
- Computational NL (functions, control flow, data operations)

### 3.3 Architecture

```python
class HybridParser:
    """Combines deterministic parser + LLM for robust NL understanding."""
    
    def __init__(self, llm_client: LLMClient):
        self.deterministic = SemanticParser()  # Rule-based
        self.llm = llm_client
    
    def parse(self, nl_text: str, context: ParseContext) -> ParseResult:
        # 1. Try deterministic parser first (fast, reliable for known patterns)
        det_result = self.deterministic.parse(nl_text, context)
        if det_result.confidence > 0.9:
            return det_result
        
        # 2. Fall back to LLM for ambiguous/novel input
        llm_result = self._llm_parse(nl_text, context)
        
        # 3. Validate LLM output with deterministic checks
        validated = self._validate(llm_result)
        return validated
```

### 3.4 Supported Intent Types (Architecture)

| Intent | Example NL | Deterministic | LLM Fallback |
|--------|------------|---------------|--------------|
| `create_page` | "landing page at /" | ✅ | — |
| `create_database` | "postgres db" | ✅ | — |
| `create_auth` | "secure JWT auth" | ✅ | — |
| `connect_with_auth` | "connect with auth" | ✅ | — |
| `complex_composition` | "build a dashboard with auth, db, and real-time updates" | ❌ | ✅ |

---

## 4. Explanation Engine (Planned)

### 4.1 Capabilities

| Query | Response |
|-------|----------|
| "Why this node?" | Trace to NL source, show contributing constraints |
| "What if I change X?" | Counterfactual execution — simulate graph with modification |
| "Show me the data flow for Y" | Extract visual subgraph from source to sink |
| "Explain this type error" | Natural language explanation of type mismatch |
| "What are the effects here?" | List all effects, their handlers, propagation |

### 4.2 Implementation Approach

```python
class ExplanationEngine:
    def explain_node(self, graph: Graph, node_id: str) -> Explanation:
        # 1. Find SOURCE_MAP edge to original NL
        # 2. Trace type derivation path
        # 3. Generate NL explanation
    
    def counterfactual(self, graph: Graph, modification: GraphDelta) -> SimulationResult:
        # 1. Apply modification to graph copy
        # 2. Re-type-check
        # 3. Simulate execution
        # 4. Compare outputs
    
    def extract_subgraph(self, graph: Graph, from_node: str, to_node: str) -> Graph:
        # 1. Find all paths from→to
        # 2. Return induced subgraph
        # 3. Layout for visualization
```

---

## 5. Test Harness

### 5.1 File Structure
```
/home/jayson/OREO/IDE/test_harness/
├── property_tests.py      # Property-based testing
├── fuzzing.py             # Mutation-based fuzzing
├── model_checking.py      # Finite-state model checking
└── integration.py         # End-to-end integration tests
```

---

## 6. Property-Based Testing

### 6.1 File
`/home/jayson/OREO/IDE/test_harness/property_tests.py`

### 6.2 Properties Tested

| Property | Description |
|----------|-------------|
| **Type Safety** | Well-typed graphs never get stuck (progress + preservation) |
| **Effect Safety** | Effect rows correctly tracked, no unhandled effects |
| **Round-trip** | NL → Graph → NL preserves semantics |
| **Serialization** | Graph → JSON → Graph = original |
| **Interpreter = Compiler** | Interpreted result = compiled bytecode result |
| **Determinism** | Same graph + same inputs = same outputs |
| **Incrementality** | Incremental re-execution = full re-execution |
| **Parallelism** | Parallel execution = sequential (for pure graphs) |

### 6.3 Generator Functions

```python
# Hypothesis-style generators for GIR graphs

@composite
def random_type(draw) -> TypeRef:
    """Generate random well-formed type."""
    kind = draw(sampled_from(["Int", "Bool", "String", "Array", "Function"]))
    # ... build type with constraints

@composite
def random_graph(draw) -> Graph:
    """Generate random well-typed GIR graph."""
    # 1. Generate random function signatures
    # 2. Generate bodies using typed operations
    # 3. Ensure all ports connected correctly
    # 4. Type-check before returning

@composite
def random_nl_program(draw) -> str:
    """Generate random NL program description."""
    # Template-based generation
    templates = [
        "define function {name} taking {params} returning {type}",
        "if {cond} then {then} else {else}",
        "for each {item} in {collection} do {body}",
    ]
    # ...
```

### 6.4 Running Property Tests

```bash
# Run all property tests
python3 -m pytest test_harness/property_tests.py -v

# Run with more examples
python3 -m pytest test_harness/property_tests.py -v --hypothesis-max-examples=1000

# Specific property
python3 -m pytest test_harness/property_tests.py::test_type_safety -v
```

---

## 7. Fuzzing

### 7.1 File
`/home/jayson/OREO/IDE/test_harness/fuzzing.py`

### 7.2 Targets

| Target | Fuzzing Strategy |
|--------|------------------|
| **Parser** | Random NL strings, malformed syntax, unicode edge cases |
| **Type Checker** | Random well-formed graphs, type edge cases (recursive, higher-kinded) |
| **Interpreter** | Random graphs with effects, deep recursion, large values |
| **Compiler** | Random graphs → bytecode → VM execution |
| **Serialization** | Random graphs → JSON/binary → round-trip |

### 7.3 Mutation Strategies

```python
class GIRMutator:
    """Mutates GIR graphs for fuzzing."""
    
    def mutate(self, graph: Graph) -> Graph:
        mutations = [
            self._add_node,
            self._remove_node,
            self._change_node_kind,
            self._add_edge,
            self._remove_edge,
            self._change_edge_kind,
            self._mutate_port_type,
            self._mutate_property,
            self._swap_subgraphs,
        ]
        # Apply random mutations
        for _ in range(random.randint(1, 5)):
            graph = random.choice(mutations)(graph)
        return graph
```

### 7.4 Coverage-Guided Fuzzing

- Instrument bytecode interpreter with coverage counters
- Use `afl` or `libfuzzer` style feedback
- Prioritize mutations that increase coverage

```bash
# Run fuzzer
python3 -m test_harness.fuzzing --target parser --iterations 10000
python3 -m test_harness.fuzzing --target type_checker --iterations 5000
python3 -m test_harness.fuzzing --target interpreter --iterations 2000
```

---

## 8. Model Checking

### 8.1 File
`/home/jayson/OREO/IDE/test_harness/model_checking.py`

### 8.2 Approach

For **finite-state subgraphs** (no unbounded loops, bounded data domains):
1. Extract finite-state subgraph
2. Build transition system
3. Model check with temporal logic (LTL/CTL)
4. Generate counterexamples for violations

### 8.3 Properties Verified

| Property | Logic | Example |
|----------|-------|---------|
| **Safety** | `G !error` | "Never reach error state" |
| **Liveness** | `F done` | "Eventually complete" |
| **Deadlock Freedom** | `G (enabled → F executed)` | "No stuck nodes" |
| **Resource Safety** | `G (acquire → F release)` | "Resources released" |
| **Termination** | `F return` | "Function returns" |

### 8.4 Counterexample Generation

When property fails:
- Minimal counterexample trace
- Visualizable as graph execution sequence
- Maps back to source NL for debugging

---

## 9. Integration Tests

### 9.1 File
`/home/jayson/OREO/IDE/test_harness/integration.py`

### 9.2 Test Scenarios

| Scenario | Pipeline |
|----------|----------|
| **Computational NL** | NL → Parse → Type-check → Interpret |
| **Architecture NL** | NL → GraphLang → Runtime handshake → Emit → Hit routes |
| **Round-trip** | Graph → NL → Graph (semantic equivalence) |
| **Compile + Run** | Graph → Bytecode → VM → Result = Interpreter |
| **AI Generation** | NL → AI → Graph → Type-check → Verify contracts |
| **Visual Edit** | Canvas action → Graph delta → Type-check → Re-render |

### 9.3 Architecture Integration Test (Runnable Now)

```python
# test_harness/integration.py::test_architecture_handshake

def test_architecture_handshake():
    """Full GraphLang pipeline: NL → Graph → Runtime → Emit → Hit."""
    from parser.architecture import Graph, GraphRuntime
    from parser.architecture.emit import emit_app
    import requests
    
    # 1. Build graph via NL (simulated)
    g = Graph()
    g.merge_page("page_landing", "Landing", "/")
    g.merge_database("db_main", "MainDB", "sqlite")
    g.merge_auth("auth_test", "TestAuth", "none", "open", requires_https=False)
    g.connect_with_auth("page_landing", "db_main", "auth_test")
    
    # 2. Runtime enforces handshake
    runtime = GraphRuntime(g)
    response = runtime.handle_request("page_landing")
    assert response.status == 200  # Handshake satisfied
    
    # 3. Emit runnable app
    app_code = emit_app(g, "test_app")
    
    # 4. Run app and hit routes (subprocess)
    # ... verify HTTP responses ...
```

### 9.4 Running Integration Tests

```bash
# All integration tests
python3 -m pytest test_harness/integration.py -v

# Architecture only (runnable now)
python3 -m pytest test_harness/integration.py::test_architecture_handshake -v

# With coverage
python3 -m pytest test_harness/integration.py --cov=parser --cov=runtime
```

---

## 10. Test Infrastructure

### 10.1 Configuration
`/home/jayson/OREO/IDE/pyproject.toml` includes:
```toml
[tool.pytest.ini_options]
testpaths = ["test_harness"]
python_files = ["test_*.py"]
python_functions = ["test_*"]

[tool.hypothesis]
max_examples = 100
deadline = 5000  # ms

[tool.coverage.run]
source = ["parser", "runtime", "visual_editor", "ai_integration"]
```

### 10.2 CI Pipeline (Planned)

```yaml
# .github/workflows/test.yml
jobs:
  property-tests:
    runs-on: ubuntu-latest
    steps:
      - run: python3 -m pytest test_harness/property_tests.py --hypothesis-max-examples=500
  
  fuzzing:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - run: python3 -m test_harness.fuzzing --all-targets --time 1800
  
  model-checking:
    runs-on: ubuntu-latest
    steps:
      - run: python3 -m pytest test_harness/model_checking.py -v
  
  integration:
    runs-on: ubuntu-latest
    steps:
      - run: python3 -m pytest test_harness/integration.py -v
```

---

## 11. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `/home/jayson/OREO/IDE/ai_integration/codegen/gir_generator.py` | ~700 | AI → GIR generation |
| `/home/jayson/OREO/IDE/ai_integration/parser.py` | ~1800 | Hybrid NL parser |
| `/home/jayson/OREO/IDE/test_harness/property_tests.py` | ~1300 | Property-based tests |
| `/home/jayson/OREO/IDE/test_harness/fuzzing.py` | ~1100 | Mutation fuzzing |
| `/home/jayson/OREO/IDE/test_harness/model_checking.py` | ~900 | Finite-state model checking |
| `/home/jayson/OREO/IDE/test_harness/integration.py` | ~1200 | End-to-end integration |

---

## 12. Running All Tests

```bash
# Quick test suite (property + integration)
python3 -m pytest test_harness/property_tests.py test_harness/integration.py -v

# Full test suite (includes fuzzing - slow)
python3 -m pytest test_harness/ -v --hypothesis-max-examples=50

# Architecture subsystem only (fast, runnable now)
python3 -m pytest test_harness/integration.py -k architecture -v
```

---

*Generated from OREO source code — see `/home/jayson/OREO/IDE/ai_integration/` and `/home/jayson/OREO/IDE/test_harness/` for implementation.*