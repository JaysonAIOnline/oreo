# Neo4j vs Memgraph, and GQL syntax

GraphLang emits intents first, then Cypher (and a GQL twin).
Either database can run the Cypher projection.

## Neo4j vs Memgraph

| | Neo4j | Memgraph |
|---|---|---|
| Engine | Disk-native property graph, JVM | In-memory first, C++ |
| Language | Cypher, converging on ISO GQL | openCypher; MemGQL translates ISO GQL |
| Protocol | Bolt | Bolt (same family of drivers) |
| Sweet spot | Large durable graphs, enterprise Graph Data Science, Aura | Low-latency traversals that fit in RAM, streaming, GraphRAG hot path |
| Persistence | Page cache + on-disk store | RAM + WAL/snapshots |
| Scale story | Stronger when the graph outgrows memory / deep multi-hop at large size | Fast when the working set stays in RAM |
| Extras | Bloom, GDS (65+ algos), Aura Agent, Document Intelligence | MAGE modules, native streaming (Kafka), MemGQL federation |
| Constraints | `CREATE CONSTRAINT ... FOR ... REQUIRE` | Accepts Neo4j-style constraint syntax plus native `ON` / `ASSERT` |
| Paths | `shortestPath`, quantified paths in newer Cypher | Built-in BFS/DFS/K-shortest; syntax differs |

Treat vendor latency claims as marketing. Independent-ish pictures:

- In-memory Memgraph is often quicker on small/hot graphs and simple reads.
- Neo4j tends to hold up better as data and hop-depth grow past RAM.
- Cypher dialects are close but not identical (indexes, shortest path, some functions).

**For GraphLang:** keep emitting portable openCypher. Use Neo4j when you want the managed AI/graph platform. Use Memgraph when the handshake path must stay in microseconds and the graph fits memory.

## GQL syntax (ISO/IEC 39075:2024)

GQL is the ISO standard for property graphs. Most `MATCH ... RETURN` Cypher is already valid GQL. Differences that matter:

| Job | Cypher | GQL |
|---|---|---|
| Filter after match | `WHERE` | `FILTER` (also `WHERE` inside a pattern) |
| Create | `CREATE` | `INSERT` |
| Unwind a list | `UNWIND` | `FOR x IN list` |
| Bind a value | `WITH` (drops unlisted vars) | `LET x = expr` (keeps prior vars) |
| No result, side effects only | (omit RETURN) | `FINISH` |
| Variable-length | `-[*1..3]->` | `-[e]->{1,3}` or `->+` `->*` `->?` |
| Distinct edges on a path | manual | `MATCH TRAIL p = ...` |
| Merge upsert | `MERGE` | not in GQL v1 (vendor extension) |

### Same GraphLang question in both

Speech: *Show pages connected to MainDB with secure auth.*

**Cypher**
```cypher
MATCH (p:Page)-[c:CONNECTS_TO]->(d:Database)
WHERE d.name = $db AND c.secure = true
OPTIONAL MATCH (p)-[:AUTHENTICATES_WITH]->(a:Auth)
RETURN p.name, a.name
```

**GQL**
```gql
MATCH (p:Page)-[c:CONNECTS_TO]->(d:Database)
FILTER d.name = $db AND c.secure = true
OPTIONAL MATCH (p)-[:AUTHENTICATES_WITH]->(a:Auth)
RETURN p.name, a.name
```

**GQL insert of the handshake** (no MERGE in the standard)
```gql
INSERT (p:Page {id: 'page_landing', name: 'Landing'})
       -[:CONNECTS_TO {secure: true}]->
       (d:Database {id: 'db_main', name: 'MainDB'})
INSERT (p)-[:AUTHENTICATES_WITH {required: true}]->
       (:Auth {name: 'SecureJWT', method: 'jwt', level: 'secure'})
```

**GQL list unnest**
```gql
FOR name IN ['Header', 'Footer']
MATCH (p:Page)
INSERT (p)-[:INCLUDES]->(:Include {name: name})
FINISH
```

GraphLang still uses `MERGE` in the Cypher backend because that is how Neo4j/Memgraph upsert safely. The GQL twin in `graphlang/queries.py` is for ISO-only engines (Spanner Graph, Fabric Graph, MemGQL).
