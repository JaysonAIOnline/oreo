# Graph query languages (for GraphLang)

GraphLang intents stay the source of truth.
Cypher / GQL / Gremlin / SPARQL are projections of those intents.

## Landscape

| Language | Model | Style | Best fit |
|---|---|---|---|
| **Cypher / openCypher** | Property graph | Declarative `MATCH` patterns | GraphLang default. Neo4j, Memgraph, FalkorDB, Neptune |
| **GQL** (ISO/IEC 39075:2024) | Property graph | Cypher-like standard | Portability across vendors adopting the ISO spec |
| **Gremlin** (TinkerPop) | Property graph | Imperative traversal `g.V()...` | JanusGraph, Neptune, Cosmos DB |
| **SPARQL** | RDF triples | Triple patterns | Semantic web / ontology stores |
| **SQL/PGQ** | Tables + graph view | Graph pattern inside SQL | Oracle 23ai, some Postgres work |
| **GSQL / nGQL** | Property graph | Vendor languages | TigerGraph / Nebula — avoid unless locked in |

GQL published April 2024. It formalised most of Cypher’s pattern syntax.
If you already write Cypher you are most of the way to GQL.

Sources: ISO GQL overview, Neo4j GQL conformance notes, language comparison writeups.

## What GraphLang should emit

1. **Intents** first (`connect_with_auth`, `include_all`, `query_neighbors`).
2. **Cypher** as the default executable projection (optimizer already does this).
3. **GQL twin** when targeting ISO-only engines (Spanner Graph, Fabric Graph).
4. **Gremlin** only if the store is TinkerPop-only.
5. Do not use SPARQL unless the data is actually RDF.

## Same GraphLang question

Speech: “Show me everything that connects to MainDB.”

**Cypher**
```cypher
MATCH (n)-[r:CONNECTS_TO]->(d:Database {name: $db_name})
OPTIONAL MATCH (n)-[:AUTHENTICATES_WITH]->(auth)
RETURN n, r.secure AS secure, auth.name
```

**GQL**
```gql
MATCH (n)-[r:CONNECTS_TO]->(d:Database)
FILTER d.name = $db_name
OPTIONAL MATCH (n)-[:AUTHENTICATES_WITH]->(auth)
RETURN n, r, auth
```

**Gremlin**
```
g.V().has('Database','name', dbName).inE('CONNECTS_TO').outV()
```

**SPARQL**
```sparql
SELECT ?page WHERE { ?page gl:CONNECTS_TO ?db . ?db gl:name "MainDB" }
```

The runtime does not wait on these strings.
It walks `CONNECTS_TO` / `AUTHENTICATES_WITH` / `INCLUDES` directly.
The query languages are for export, inspection, and Neo4j.
