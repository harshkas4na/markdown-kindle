# The Front Door — Load Balancing, Rate Limiting, and Idempotency

**Fast overview:** the traffic layer — everything between the internet and your services. Load balancing (L4 vs L7, algorithms, health checks), API gateways, rate limiting (the algorithms and the awkwardness of enforcing them across a fleet), and idempotency — the discipline that makes retries safe and quietly underwrites every "reliable" claim made anywhere else in this book.

## Load balancing: L4 vs L7, and the algorithms

**L4 (transport-level)** balancers route by IP/port, forwarding packets without reading them: brutal throughput, TLS stays end-to-end, no HTTP awareness. **L7 (application-level)** balancers terminate TLS and read requests: route by path/header (`/api/video` → video fleet), retry failed requests, compress, cache, observe. Standard shape: an L4 tier (or anycast) in front of an L7 tier (Envoy, nginx, ALB) in front of services. Kubernetes ingress and service meshes are this same machinery, containerized.

Algorithms, and when each earns its keep:

- **Round robin** — default; fine for uniform, fast requests.
- **Least connections / least request** — better when request costs vary (long-poll + quick REST mixed): routes around busy backends automatically.
- **Power of two choices** — pick two random backends, send to the less loaded. Nearly optimal load spread, trivially cheap, no global state — the quiet star of the family and a great interview aside.
- **Consistent hashing** (Chapter 5's ring, third appearance) — when backend locality matters: cache-affinity (same user → same node's warm cache), or stateful backends (websocket servers). This is "sticky sessions" done with math instead of cookies.

**Health checks** decide the *set* being balanced over: active probes (`/healthz`) plus passive signals (error/timeout rates) eject bad backends. Two footguns worth naming: a health endpoint that checks *dependencies* (DB reachable?) can eject the *entire fleet* when one shared dependency blips — health checks should verify "this instance works," not "the world works"; and slow ejection + aggressive retries is how one bad node poisons p99 for minutes (Chapter 12 picks this up).

## Gateways and the API edge

The **API gateway** is L7 routing plus cross-cutting policy: authentication (verify JWT once at the edge, pass claims inward), request validation, response shaping, per-client quotas, canary routing (1% of traffic → new version), and observability tagging (trace IDs are born here — Chapter 12). Internally, service meshes (sidecar or sidecarless Envoy) apply the same policies service-to-service — mTLS, retries, circuit breaking as *platform*, not per-app code. Design instinct: policy that must be uniform (authn, limits, TLS) belongs at the edge/mesh; logic that varies per domain belongs in services. Gateways that accumulate business logic become the new monolith, with YAML.

## Rate limiting: the algorithms

Protects against abuse, bugs (a retry loop is indistinguishable from an attack), and *your own* marketing emails. The algorithms:

- **Fixed window** — counter per minute. Trivial; bursts 2× at boundaries (100 at 11:59:59 + 100 at 12:00:00).
- **Sliding window log** — timestamped entries; exact but memory-heavy per key.
- **Sliding window counter** — weighted blend of adjacent fixed windows; the practical compromise most gateways use.
- **Token bucket** — bucket of capacity B refilling at rate R; each request takes a token. Steady rate R with bursts up to B — *two independent knobs*, which is why it's the industry default (AWS, Stripe). Implement in Redis with atomic Lua: state is just (tokens, last_refill).
- **Leaky bucket** — the inverse framing: a queue drained at constant rate; smooths output rather than admitting bursts.

Distributed reality: a per-instance limiter multiplies limits by fleet size; the *centralized* limiter (Redis) adds a hop and a hot key (Chapter 8's hot-key toolkit applies — including the honest fix: shard the counter and accept approximation). Most fleets converge on *approximately correct, cheap* — local pre-filters with async global sync — because exact global limits at high QPS cost more than they protect. Return `429` with `Retry-After`, and distinguish **throttling** (per-client fairness) from **load shedding** (Chapter 12: dropping work to survive — different trigger, different audience).

## Idempotency: making retries safe

The deepest idea in the chapter, and the one that stitches the whole book's promises together. Chapter 7 established that a timeout is ambiguous — the request may have *succeeded* invisibly. Chapter 9's delivery guarantees bottomed out in "at-least-once + idempotent handling." So: **every reliable system retries, and every retry is a potential duplicate.** If `POST /payments` isn't idempotent, your reliability machinery is a double-charging machine.

The pattern (Stripe-shaped, now universal):

1. Client generates an **idempotency key** (UUID) per logical operation and sends it as a header; *the same key on every retry of that operation*.
2. Server, atomically with the operation's own transaction, records the key → result (Chapter 6's atomicity doing the heavy lifting: the "have I seen this?" check and the side effect must commit together, or the crash window between them re-creates the bug).
3. Replays return the stored result — success answered twice, executed once. TTL the keys (24h typical); handle the concurrent-retry race (second request while first in flight: block on or reject with the key's in-progress state).

Cheaper forms when you control the semantics: natural idempotency (`PUT` full state, upserts, "set status = shipped"), conditional writes (`If-Match` ETags, compare-and-swap versions — which also cures Chapter 6's lost update), and dedup tables keyed by natural business keys (order_id) instead of client UUIDs. The design habit: for every mutation in your API, be able to answer *"what happens if this arrives twice?"* — an answer of "…bad things" is a bug you've merely not met yet.

## The front door, assembled

Trace Chapter 1's request once more with grown-up eyes: anycast/L4 → L7 gateway (TLS, authn, rate limit by token bucket in Redis, trace ID minted) → consistent-hash or least-request to a stateless service (Chapter 2) → which calls other services through a mesh with budgets and retries — every retry carrying an idempotency key so the whole nervous system can be aggressive about reliability without corrupting state. One chapter remains before the case studies: what happens when, despite all of it, things go wrong anyway — and how to build systems (and dashboards) that bend instead of shatter.
