# OREO IDE Workspace - Project Structure

```
/home/jayson/OREO/IDE/
├── spec/
│   └── OREO_LANGUAGE_SPEC.md          # Language specification (this file)
├── parser/
│   ├── README.md                       # Parser module documentation
│   ├── nl_parser/                      # Natural language semantic parser
│   │   ├── semantic_parser.py          # NL -> computational GIR
│   │   ├── architecture_router.py      # NL -> Architecture subsystem (runnable)
│   │   └── __init__.py
│   ├── architecture/                   # NL+visual architecture modeling (merged from GraphLang)
│   │   ├── parser.py                   # Speech -> Intent (deterministic rules)
│   │   ├── llm.py                      # HybridParser: rules-first + LLM fallback
│   │   ├── store.py                    # InMemoryGraph + Neo4jGraph/BoltStore
│   │   ├── engine.py                   # RelationshipEngine (handshake runtime)
│   │   ├── runtime.py                  # GraphRuntime facade
│   │   ├── emit.py                     # emit a runnable web app from graph lines
│   │   ├── optimize.py                 # Cypher optimizer (batching, schema prelude)
│   │   ├── queries.py                  # same intent in Cypher/GQL/Gremlin/SPARQL
│   │   ├── audit.py                    # syntax + completeness audits
│   │   ├── advise.py                   # scene/line suggestions (collaborator)
│   │   ├── shape.py                    # graph -> geometric solid/strut model
│   │   ├── lines.py                    # purpose -> line intent (draw semantics)
│   │   ├── functions.py                # executable Function nodes
│   │   ├── voice.py                    # spoken replies
│   │   ├── importer.py                 # import existing Python/Ruby into graph
│   │   ├── bolt.py                     # Neo4j/Memgraph Bolt adapter
│   │   ├── cli.py, demo.py, visual.py  # editor server (talk + draw web UI)
│   │   └── graphlang_editor.html       # live editor with ears + voice
│   ├── text_parser/                    # Text serialization parser
│   │   ├── lexer.py
│   │   ├── parser.py
│   │   └── ast.py
│   └── gir/                            # Graph IR definitions
│       ├── nodes.py
│       ├── edges.py
│       ├── types.py
│       └── validation.py
├── runtime/
│   ├── README.md                       # Runtime module documentation
│   ├── interpreter/                    # Graph interpreter
│   │   ├── evaluator.py
│   │   ├── scheduler.py
│   │   ├── memory_model.py
│   │   └── effects.py
│   ├── compiler/                       # Compiler backends
│   │   ├── llvm_backend.py
│   │   ├── bytecode_backend.py
│   │   └── jit.py
│   └── memory/
│       ├── allocator.py
│       ├── gc.py
│       └── ownership.py
├── visual_editor/
│   ├── README.md                       # Visual editor documentation
│   ├── canvas/                         # Canvas rendering
│   │   ├── renderer.py
│   │   ├── viewport.py
│   │   └── layers.py
│   ├── nodes/                          # Node rendering
│   │   ├── node_registry.py
│   │   ├── shapes.py
│   │   └── ports.py
│   ├── interaction/                    # User interaction
│   │   ├── create_tool.py
│   │   ├── connect_tool.py
│   │   ├── inspect_panel.py
│   │   └── nl_input.py
│   └── visualization/                  # Live execution viz
│       ├── token_flow.py
│       ├── heatmap.py
│       └── time_travel.py
├── ai_integration/
│   ├── README.md                       # AI integration documentation
│   ├── codegen/                        # AI code generation
│   │   ├── gir_generator.py
│   │   ├── type_checker.py
│   │   └── contract_verifier.py
│   ├── verification/                   # Formal verification
│   │   ├── z3_wrapper.py
│   │   ├── model_checker.py
│   │   └── property_tester.py
│   └── explanation/                    # Explanation engine
│       ├── trace_explainer.py
│       ├── counterfactual.py
│       └── subgraph_extractor.py
├── test_harness/
│   ├── README.md                       # Testing documentation
│   ├── property_tests/                 # Property-based testing
│   │   ├── generators.py
│   │   └── runners.py
│   ├── fuzzing/                        # Fuzzing infrastructure
│   │   ├── mutators.py
│   │   └── coverage.py
│   ├── model_checking/                 # Model checking
│   │   └── finite_state.py
│   └── integration/                    # Integration tests
│       ├── test_specs.py
│       └── test_examples.py
├── docs/
│   ├── README.md                       # Documentation index
│   ├── language_guide.md               # Language tutorial
│   ├── api_reference.md                # API documentation
│   ├── visual_editor_guide.md          # Editor user guide
│   ├── ai_integration_guide.md         # AI integration guide
│   └── contributing.md                 # Contribution guide
├── examples/
│   ├── hello_world.oreo
│   ├── factorial.oreo
│   ├── fibonacci.oreo
│   ├── file_io.oreo
│   ├── http_server.oreo
│   └── concurrent.oreo
├── Cargo.toml                          # Rust project manifest
├── pyproject.toml                      # Python project manifest
├── Makefile                            # Build automation
└── README.md                           # Project root README
```