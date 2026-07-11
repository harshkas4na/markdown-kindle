# The Life of a Request

**Fast overview:** before designing systems, watch one work. This chapter follows a single tap — "load my feed" — from a phone to a data center and back, naming every component and its latency budget. Every later chapter is a renovation of some room in this house, so we build the house first.

## The cast, in order of appearance

**1. DNS (~1–50ms, usually cached).** The phone must turn `api.example.com` into an IP address. Resolvers cache aggressively (per the record's TTL), so most requests skip this. Two design notes that matter later: DNS is *the* coarsest load-balancing and failover tool (GeoDNS returns a nearby region's IP; changing records shifts traffic in minutes, not milliseconds — TTLs make DNS failover slow); and because it's cached everywhere, it fails *gracefully but staleley*.

**2. TCP + TLS handshake (~1–3 round trips).** Before a byte of HTTP, the phone and server perform the TCP handshake and TLS negotiation. Round trips are the currency here: a transatlantic round trip is ~80ms, so three of them is a quarter second — which is why persistent connections, connection pooling, TLS session resumption, and HTTP/2–3 multiplexing exist (QUIC/HTTP-3 folds transport + TLS into one round trip). Rule you'll reuse constantly: **latency is dominated by round trips × distance, not bandwidth.** Put things near users (CDN, Chapter 8) or make fewer trips (batching, Chapter 11).

**3. The load balancer (~sub-ms).** The IP the phone dialed isn't a server — it's a **load balancer** (or a fleet behind one virtual IP). It terminates TLS (often), health-checks backends, and spreads requests across application servers. L4 vs L7, algorithms, and sticky sessions are Chapter 11's domain; for now: the LB is what makes a *group* of servers look like one, which is the enabling trick of Chapter 2's whole scaling story.

**4. The application server (~1–50ms of its own work).** Your code: authenticate the token, validate input, decide what data the response needs. Modern shape: either a monolith (one deployable doing all of this) or a set of services this "edge" service fans out to. The critical property established in Chapter 2: this tier should hold **no user state in memory between requests** — session data lives in a shared store, so *any* server can serve *anyone*, and killing a server loses nothing.

**5. The cache (~0.2–1ms in-datacenter).** Before touching the database, check Redis/Memcached: "feed for user 4132, computed 20 seconds ago?" A hit ends the story here — this is why cache hit rate is the single highest-leverage performance number in most systems (Chapter 8). A miss continues down.

**6. The database (~1–20ms per query, if healthy).** The system of record. The query planner turns SQL into index lookups (Chapter 3 opens this box); reads maybe go to replicas (Chapter 4); big datasets shard across machines (Chapter 5); multi-step updates need transactions (Chapter 6). The database is where scaling hurts first and most, which is why Act 2 of this book is four chapters long.

**7. Downstream fan-out (in parallel, ideally).** A real feed request might also call a follow-graph service, a ranking service, and an ads service. Fan-out introduces the **tail-latency amplification** problem: if each of 5 parallel calls is slow 1% of the time, the *request* is slow ~5% of the time — your p99 becomes your users' p95. Percentiles, hedged requests, and timeouts live in Chapter 12, but the phenomenon is born here.

**8. The response, assembled and returned** — serialized (JSON/protobuf), compressed, back through LB and network. Static/heavy assets (images, video) don't take this path at all: they're served from a **CDN** — caches at the network edge, ~10–50ms from nearly everyone on earth (Chapter 8).

## The numbers to carry in your head

The classic "latency numbers" table, 2026-adjusted and rounded to be memorable:

| Operation | Cost |
|---|---|
| L1 cache reference | ~1 ns |
| Main-memory reference | ~100 ns |
| Read 1MB sequentially from RAM | ~10 µs |
| SSD random read | ~20–100 µs |
| Read 1MB sequentially from SSD | ~200 µs–1 ms |
| Same-datacenter round trip | ~0.5 ms |
| HDD seek | ~5–10 ms |
| Cross-continent round trip (e.g. CA↔NL) | ~150 ms |

Three morals fall straight out:

- **Memory beats disk by ~100–1000×** → caching (Chapter 8) isn't an optimization, it's a different physics regime.
- **Sequential beats random** on every medium → the append-only log (Chapters 3 and 9) is fast *because* it never seeks.
- **The network inside a datacenter is fast; between datacenters it isn't** → replication across regions is fundamentally asynchronous (Chapter 4), and geo-distribution is a latency decision before it's a reliability one.

## The two currencies: latency and throughput

Vocabulary the whole book prices things in:

- **Latency** — time for one request (measure in percentiles: p50 median, p99 the experience of your heaviest users — averages lie, Chapter 12).
- **Throughput** — requests per second the system sustains.

They're linked by queueing, not identical: a system at 90%+ utilization develops explosive queue-wait latency even though throughput looks fine (the hockey-stick curve — Chapter 12's overload story). Design targets are stated as **SLOs**: "p99 < 300ms while serving 50k RPS."

## Where the story goes

Look back over the path and notice: every component exists to solve a problem a *previous* component created. The LB exists because one server wasn't enough (Chapter 2). Replicas exist because the database drowned in reads (Chapter 4) — and they create staleness. The cache exists because even replicas are too slow (Chapter 8) — and it creates invalidation. The log (Chapter 9) exists to keep all these copies honest. System design is not choosing components from a catalog; it's this chain of consequences, managed deliberately. Next chapter: the chain's first link — the day one server stops being enough.
