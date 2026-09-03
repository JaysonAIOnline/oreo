# Microservices architecture and state management

GraphLang already treats **lines as contracts**. That is the same idea these patterns encode in prose.

## Microservices (what actually matters)

A service is not “a small app.” It is a **capability that owns its data** and talks through explicit paths.

### Structure

| Pattern | Meaning | GraphLang |
|---|---|---|
| Database per service | No shared tables across capabilities | Each `Service` has its own `Database`. No two services share one db line unless you meant that. |
| API gateway | One front door | `APIGateway` → services. Pages never talk to every backend. |
| Sidecar / mesh | Policy next to the process (auth, retries, observe) | `AUTHENTICATES_WITH` + a `Service` named Mesh/Sidecar on the same node |
| Anti-corruption | Translate another team’s model | A `Function` on the line between two services |

### Talk

| Pattern | When | Line |
|---|---|---|
| Sync request/response | Need an answer now | `CONNECTS_TO` with purpose “request/response” |
| Async events | Announce a fact, don’t wait | `PUBLISHES` / `SUBSCRIBES` (event bus in the middle) |
| Choreography saga | Each service reacts to events | Chain of event lines, no boss node |
| Orchestration saga | One coordinator drives steps + compensations | `Saga` service with `ORCHESTRATES` lines |
| Outbox | Don’t lose the event after the db write | Function on the db→bus line |
| CQRS | Writes and reads are different models | `CommandAPI` writes, `QueryAPI` reads a projection db |
| Circuit breaker | Fail fast when the other side is sick | Property on the line: `break_after`, `purpose` |

Distributed transactions across services are the trap. Sagas replace them: do a step, on failure run a compensating step. Orchestrator if the flow is long and you need to see it. Choreography if the flow is short and teams want no center. 

### State that lives in the fleet

- **Source of truth** stays in the service that owns it.
- **Replicas / projections** are other databases fed by events (CQRS).
- **Never** let Checkout and Forum share MainDB “for convenience.” Completeness audit should call that out.

## State management (client + whole system)

The useful split is not Redux vs Zustand. It is **where the truth lives** and **how it moves**.

| Kind of state | Best home | Pattern |
|---|---|---|
| Widget-only (open/closed) | Local | Colocate. Do not put in a global store. |
| Session / auth / theme | App store | Small global store |
| Server records | Query cache / sync engine | Treat as cache of the graph, not a second truth |
| Long-lived domain | Event log + fold | Event sourcing / reducer |
| Multi-device / multi-agent | Sync engine | Local write, then sync; conflicts are events |

Redux, Raft, and event sourcing share one shape: **append an event, fold a deterministic function over the log.** Frontend actions ≈ backend events ≈ GraphLang intents.

Local-first / sync engines (Electric, Convex, Ditto, Instant) invert fetch: the UI binds to data; the network is a side effect. That matches GraphLang’s “page talks to db through a line” better than “component calls axios.”

### How the layers meet

```
UI local state     →  not in the graph
UI session store   →  Auth + tiny Resource
Client cache       →  projection of Database
Service memory     →  ephemeral, not source of truth
Service database   →  Database node the service owns
Events between     →  lines through EventBus
Saga               →  Service that only exists to sequence lines
```

## What GraphLang should offer when it sees “microservices” or “state”

- Services + one database each
- API gateway
- Event bus
- Optional Saga orchestrator
- Token auth on the gateway
- Completeness: two services sharing one db is a warning
- Completeness: gateway with no auth line is a warning
- For “app state”: SessionStore, EventLog, Projection — not another Page
