# OREO Research Data Exports

**Source:** `neo4j_research` PostgreSQL database  
**Export Date:** 2026-08-27  
**Total Facts:** 285 across 12 categories, 30 subcategories

---

## Files

| File | Rows | Description |
|------|------|-------------|
| `facts_by_category.csv` | 278 | All facts with category, content, confidence, fact_type, key_term |
| `sources_categories.csv` | 59 | Sources mapped to categories and subcategories |
| `oreo_research_complete.csv` | 1 | Header only (query needs adjustment) |

---

## Categories (12)

1. **Data Serialization** — JSON, YAML, Protobuf, MessagePack, CBOR, Avro
2. **Error Correcting Codes** — ECC, FEC, Reed-Solomon, Hamming, LDPC, Shannon theory
3. **Family & Kinship** — Genealogy, family tree data models, extended family structures
4. **Graph-Native Programming** — Languages where code IS a graph
5. **Hardware Reverse Engineering** — PCB/IC reverse engineering, decapping, chip analysis
6. **Information Theory** — Claude Shannon, entropy, channel capacity, noisy channel coding theorem
7. **Machine-Level Computing** — CPU architecture, instruction sets, low-level programming
8. **Neo4j** — Graph database platform and technology
9. **Open-Source Drivers** — Linux kernel drivers, GPU drivers, free software hardware support
10. **Programming Paradigms** — Imperative, functional, OOP, declarative, logic — evolution and classification
11. **Software Engineering at Machine Level** — Assembly, debugging, reverse engineering, systems programming
12. **WebAssembly** — Portable low-level runtime, virtual ISA, sandboxed execution

---

## Key Categories for OREO Language Design

### Graph-Native Programming
- Control-flow graphs, graph rewriting, AST as graph
- Languages where code IS a graph (not text → graph)
- Visual programming, node-based editors

### Machine-Level Computing
- CPU architecture, instruction sets (x86, ARM, RISC-V)
- Assembly, debugging, reverse engineering
- Memory models, cache hierarchies, branch prediction

### Error Correcting Codes
- Reed-Solomon, Hamming, LDPC, Turbo codes
- Shannon theory, channel capacity
- Fault tolerance, reliability engineering

### Information Theory
- Entropy, mutual information
- Noisy channel coding theorem
- Compression bounds, data density

### Programming Paradigms
- Imperative, functional, OOP, declarative, logic
- Effect systems, algebraic effects
- Language evolution and classification

---

## Usage

```python
import pandas as pd

# Load facts by category
facts = pd.read_csv('facts_by_category.csv')

# Filter for OREO-relevant categories
oreo_cats = [
    'Graph-Native Programming',
    'Machine-Level Computing', 
    'Error Correcting Codes',
    'Information Theory',
    'Programming Paradigms',
    'Software Engineering at Machine Level',
    'WebAssembly',
    'Data Serialization'
]

oreo_facts = facts[facts['category'].isin(oreo_cats)]
print(f"OREO-relevant facts: {len(oreo_facts)}")
```

---

## Next Steps

1. **Process into AI-readable format** — convert to structured knowledge base
2. **Build category-specific guides** — one per OREO-relevant category
3. **Create fact embeddings** — for semantic search in mem20
4. **Link to mem20 memory system** — import key facts for AI reasoning
