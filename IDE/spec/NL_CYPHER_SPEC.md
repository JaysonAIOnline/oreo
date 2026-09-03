# Graph Language — NL Layer + Cypher Spec (v0.1)

Source of truth is the property graph.
Natural language mutates or queries that graph.
Relationships carry behavior.

## Conventions

- Always `MERGE` nodes by `id` when possible; fall back to `name` for human commands.
- Always `MERGE` relationships so repeated speech does not duplicate edges.
- Generate stable ids: `{label}_{slug}` e.g. `page_landing`, `db_main`, `auth_secure_jwt`.
- Timestamps: `datetime()` on create; do not overwrite `created_at` on merge.
- Prefer reuse of existing `Auth` nodes with the same `method` + `level`.

---

## 1. Exact Cypher patterns

### 1.1 Upsert a Page

```cypher
MERGE (p:Page {id: $id})
ON CREATE SET
  p.name = $name,
  p.path = $path,
  p.type = $type,
  p.created_at = datetime()
ON MATCH SET
  p.name = coalesce($name, p.name),
  p.path = coalesce($path, p.path),
  p.type = coalesce($type, p.type)
RETURN p
```

### 1.2 Upsert a Database

```cypher
MERGE (d:Database {id: $id})
ON CREATE SET
  d.name = $name,
  d.engine = $engine,
  d.host = $host,
  d.port = $port,
  d.created_at = datetime()
ON MATCH SET
  d.name = coalesce($name, d.name),
  d.engine = coalesce($engine, d.engine),
  d.host = coalesce($host, d.host),
  d.port = coalesce($port, d.port)
RETURN d
```

### 1.3 Upsert an Auth provider

```cypher
MERGE (a:Auth {id: $id})
ON CREATE SET
  a.name = $name,
  a.method = $method,
  a.level = $level,
  a.token_expiry = $token_expiry,
  a.requires_https = $requires_https,
  a.created_at = datetime()
ON MATCH SET
  a.name = coalesce($name, a.name),
  a.method = coalesce($method, a.method),
  a.level = coalesce($level, a.level),
  a.token_expiry = coalesce($token_expiry, a.token_expiry),
  a.requires_https = coalesce($requires_https, a.requires_https)
RETURN a
```

### 1.4 Upsert an Include

```cypher
MERGE (i:Include {id: $id})
ON CREATE SET
  i.name = $name,
  i.path = $path,
  i.created_at = datetime()
ON MATCH SET
  i.name = coalesce($name, i.name),
  i.path = coalesce($path, i.path)
RETURN i
```

### 1.5 Connect a resource to a database (the handshake line)

```cypher
MATCH (src {id: $src_id})
MATCH (db:Database {id: $db_id})
MERGE (src)-[r:CONNECTS_TO]->(db)
ON CREATE SET
  r.secure = $secure,
  r.auth_method = $auth_method,
  r.pool_size = $pool_size,
  r.timeout = $timeout,
  r.created_at = datetime()
ON MATCH SET
  r.secure = coalesce($secure, r.secure),
  r.auth_method = coalesce($auth_method, r.auth_method),
  r.pool_size = coalesce($pool_size, r.pool_size),
  r.timeout = coalesce($timeout, r.timeout)
RETURN src, r, db
```

### 1.6 Attach auth to a resource

```cypher
MATCH (src {id: $src_id})
MATCH (a:Auth {id: $auth_id})
MERGE (src)-[r:AUTHENTICATES_WITH]->(a)
ON CREATE SET
  r.required = $required,
  r.roles = $roles,
  r.created_at = datetime()
ON MATCH SET
  r.required = coalesce($required, r.required),
  r.roles = coalesce($roles, r.roles)
RETURN src, r, a
```

### 1.7 Include a shared module

```cypher
MATCH (src {id: $src_id})
MATCH (i:Include {id: $include_id})
MERGE (src)-[r:INCLUDES]->(i)
ON CREATE SET
  r.order = $order,
  r.created_at = datetime()
ON MATCH SET
  r.order = coalesce($order, r.order)
RETURN src, r, i
```

### 1.8 Combined intent: connect + secure auth

This is the pattern for:
“Connect the db to the landing page with a secure auth”

```cypher
MERGE (p:Page {id: $page_id})
ON CREATE SET p.name = $page_name, p.path = $page_path, p.created_at = datetime()

MERGE (d:Database {id: $db_id})
ON CREATE SET d.name = $db_name, d.engine = $engine, d.created_at = datetime()

MERGE (a:Auth {id: $auth_id})
ON CREATE SET
  a.name = $auth_name,
  a.method = $auth_method,
  a.level = $auth_level,
  a.requires_https = true,
  a.created_at = datetime()

MERGE (p)-[c:CONNECTS_TO]->(d)
ON CREATE SET
  c.secure = true,
  c.auth_method = $auth_method,
  c.created_at = datetime()
ON MATCH SET
  c.secure = true,
  c.auth_method = $auth_method

MERGE (p)-[authRel:AUTHENTICATES_WITH]->(a)
ON CREATE SET
  authRel.required = true,
  authRel.roles = $roles,
  authRel.created_at = datetime()

RETURN p, d, a, c, authRel
```

### 1.9 Query: everything connected to a database

```cypher
MATCH (n)-[r:CONNECTS_TO]->(d:Database)
WHERE d.id = $db_id OR toLower(d.name) = toLower($db_name)
OPTIONAL MATCH (n)-[a:AUTHENTICATES_WITH]->(auth:Auth)
OPTIONAL MATCH (n)-[i:INCLUDES]->(inc:Include)
RETURN n, r, d, a, auth, i, inc
```

### 1.10 Query: impact analysis (“what would break if I delete X?”)

```cypher
MATCH (target {id: $id})
OPTIONAL MATCH (src)-[r]->(target)
OPTIONAL MATCH (target)-[r2]->(dst)
RETURN target,
       collect(DISTINCT {from: src, rel: type(r)}) AS inbound,
       collect(DISTINCT {to: dst, rel: type(r2)}) AS outbound
```

### 1.11 Disconnect / delete a relationship only

```cypher
MATCH (src {id: $src_id})-[r:CONNECTS_TO]->(dst {id: $dst_id})
DELETE r
```

### 1.12 Apply one include to many pages

```cypher
MATCH (p:Page)
WHERE p.id IN $page_ids
MATCH (i:Include {id: $include_id})
MERGE (p)-[r:INCLUDES]->(i)
ON CREATE SET r.order = $order, r.created_at = datetime()
RETURN p, r, i
```

---

## 2. NL command cookbook

Default resolution rules for names:
- “the db” / “the database” → most recently mentioned Database, else the only Database, else ask.
- “landing page” / “home” → Page whose `name` or `path` matches.
- “secure auth” → Auth with `level = "secure"`. Create JWT + HTTPS if none exists.
- “all pages” → every `:Page` node.

### Create structure

| You say | Intent | Graph operation |
|---|---|---|
| I need a db, three pages and a couple of includes | Bulk create | MERGE MainDB + Home/Dashboard/Settings + Header/Footer |
| Create a landing page at / | Create page | MERGE `page_landing` with `path:"/"` |
| Add a postgres database called MainDB | Create db | MERGE `db_main` engine postgres |
| Create a secure JWT auth named SecureJWT | Create auth | MERGE Auth method jwt, level secure, requires_https true |

### Draw the handshake line

| You say | Intent | Graph operation |
|---|---|---|
| Connect the db to the landing page with a secure auth | Connect + auth | Pattern 1.8 |
| Connect all pages to MainDB with the same secure auth | Fan-out connect | For each Page: CONNECTS_TO + AUTHENTICATES_WITH |
| Make Dashboard connect to MainDB with session-based secure auth | Connect + specific auth | MERGE Auth method session, level secure; link Dashboard |
| Draw a line from Home to MainDB | Bare handshake | CONNECTS_TO only (`secure:false` unless said) |
| Use JWT on that connection | Enrich existing edge | SET CONNECTS_TO.auth_method = "jwt", secure = true + ensure AUTHENTICATES_WITH |

### Includes

| You say | Intent | Graph operation |
|---|---|---|
| Make every page include Header and Footer | Fan-out includes | INCLUDES from all Pages |
| Dashboard should also include Sidebar | Add include | INCLUDES Dashboard → Sidebar |
| Load Header before Footer on Home | Ordered includes | INCLUDES.order = 0 then 1 |

### Inspect

| You say | Intent | Graph operation |
|---|---|---|
| Show me everything that connects to MainDB | Neighborhood | Pattern 1.9 |
| What auth does the landing page use? | Read auth path | MATCH (p:Page {name:"Landing"})-[:AUTHENTICATES_WITH]->(a) |
| What would break if I delete Header? | Impact | Pattern 1.10 |
| List pages with no database connection | Lint | MATCH (p:Page) WHERE NOT (p)-[:CONNECTS_TO]->(:Database) RETURN p |

### Change / undo

| You say | Intent | Graph operation |
|---|---|---|
| Remove the connection between Settings and MainDB | Delete edge only | Pattern 1.11 |
| Disconnect landing from auth but keep the db line | Partial undo | DELETE AUTHENTICATES_WITH only |
| Rename Landing to Home | Property update | SET p.name = "Home" (keep id) |
| Make that connection require HTTPS | Tighten auth | SET Auth.requires_https = true, CONNECTS_TO.secure = true |

---

## 3. NL parser contract (what the model must emit)

The NL layer should not emit free-form Cypher when possible.
It should emit a structured intent, then a template fills Cypher.

```json
{
  "action": "connect_with_auth",
  "source": { "label": "Page", "ref": "Landing" },
  "target": { "label": "Database", "ref": "MainDB" },
  "auth": { "method": "jwt", "level": "secure", "requires_https": true },
  "roles": [],
  "create_missing": true
}
```

Supported actions:
- `create_node`
- `connect`
- `connect_with_auth`
- `include`
- `disconnect`
- `update_props`
- `query_neighbors`
- `impact`
- `lint`

---

## 4. Worked example

Speech:
> “I need a db, three pages and a couple of includes. Connect the db to the landing page with a secure auth. Make all pages include Header and Footer.”

Resulting graph:

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

Note: only Landing received the handshake in this speech.
Dashboard and Settings still have includes, but no `CONNECTS_TO` until you say so.
That is intentional — the line is the contract.
