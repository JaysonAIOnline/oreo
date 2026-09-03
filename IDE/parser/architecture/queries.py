"""Same GraphLang questions in several graph query languages.

Intent stays the source of truth. These strings are projections.
"""

from __future__ import annotations

from typing import Any


NEIGHBORS_CYPHER = """
MATCH (n)-[r:CONNECTS_TO]->(d:Database)
WHERE d.id = $db_id OR toLower(d.name) = toLower($db_name)
OPTIONAL MATCH (n)-[:AUTHENTICATES_WITH]->(auth:Auth)
OPTIONAL MATCH (n)-[:INCLUDES]->(inc:Include)
RETURN n, r, d, auth, collect(inc.name) AS includes
""".strip()

# ISO GQL (ISO/IEC 39075:2024) is close to Cypher; FILTER replaces WHERE
# in some dialects, MATCH/RETURN is valid in both.
NEIGHBORS_GQL = """
MATCH (n)-[r:CONNECTS_TO]->(d:Database)
FILTER d.name = $db_name
OPTIONAL MATCH (n)-[:AUTHENTICATES_WITH]->(auth:Auth)
OPTIONAL MATCH (n)-[:INCLUDES]->(inc:Include)
RETURN n, r, d, auth, inc
""".strip()

NEIGHBORS_GREMLIN = """
g.V().hasLabel('Database').has('name', dbName)
  .inE('CONNECTS_TO').as('r')
  .outV().as('n')
  .project('node', 'secure', 'auth', 'includes')
    .by(select('n').values('name'))
    .by(select('r').values('secure'))
    .by(out('AUTHENTICATES_WITH').values('name').fold())
    .by(out('INCLUDES').values('name').fold())
""".strip()

# SPARQL is RDF/triple oriented. Property graphs map to triples.
NEIGHBORS_SPARQL = """
PREFIX gl: <https://graphlang.dev/vocab#>
SELECT ?page ?secure ?auth ?include
WHERE {
  ?page gl:CONNECTS_TO ?db .
  ?db gl:name ?dbName .
  OPTIONAL { ?page gl:secure ?secure }
  OPTIONAL { ?page gl:AUTHENTICATES_WITH ?auth }
  OPTIONAL { ?page gl:INCLUDES ?include }
  FILTER (LCASE(STR(?dbName)) = LCASE(?wanted))
}
""".strip()

OPEN_PAGE_CYPHER = """
MATCH (p:Page)
WHERE p.name = $page
OPTIONAL MATCH (p)-[c:CONNECTS_TO]->(d:Database)
OPTIONAL MATCH (p)-[:AUTHENTICATES_WITH]->(a:Auth)
OPTIONAL MATCH (p)-[i:INCLUDES]->(inc:Include)
RETURN p.name AS page, d.name AS database, c.secure AS secure,
       a.name AS auth, collect(inc.name) AS includes
""".strip()

IMPACT_CYPHER = """
MATCH (target)
WHERE target.name = $name
OPTIONAL MATCH (src)-[r]->(target)
RETURN target.name AS target,
       collect({from: src.name, rel: type(r)}) AS inbound
""".strip()

IMPACT_GREMLIN = """
g.V().has('name', name)
  .inE().as('e')
  .outV().as('src')
  .select('src','e')
    .by('name')
    .by(label)
""".strip()

LINT_CYPHER = """
MATCH (p:Page)
WHERE NOT (p)-[:CONNECTS_TO]->(:Database)
RETURN p.name AS page
""".strip()

LINT_GQL = """
MATCH (p:Page)
FILTER NOT EXISTS { MATCH (p)-[:CONNECTS_TO]->(:Database) }
RETURN p.name AS page
""".strip()


EXAMPLES: dict[str, dict[str, str]] = {
    "neighbors": {
        "cypher": NEIGHBORS_CYPHER,
        "gql": NEIGHBORS_GQL,
        "gremlin": NEIGHBORS_GREMLIN,
        "sparql": NEIGHBORS_SPARQL,
    },
    "open_page": {"cypher": OPEN_PAGE_CYPHER},
    "impact": {"cypher": IMPACT_CYPHER, "gremlin": IMPACT_GREMLIN},
    "lint": {"cypher": LINT_CYPHER, "gql": LINT_GQL},
}


def catalog() -> dict[str, Any]:
    return {
        "intent_is_source_of_truth": True,
        "default_projection": "cypher",
        "languages": EXAMPLES,
        "notes": {
            "cypher": "Property-graph default. openCypher + Neo4j. Closest to GraphLang intents.",
            "gql": "ISO/IEC 39075:2024. Cypher-like patterns, official standard.",
            "gremlin": "Apache TinkerPop. Imperative traversal steps.",
            "sparql": "W3C RDF. Use only if the store is triples, not a property graph.",
            "sql_pgq": "SQL:2023 graph patterns inside SELECT. Good when data stays in tables.",
        },
    }
