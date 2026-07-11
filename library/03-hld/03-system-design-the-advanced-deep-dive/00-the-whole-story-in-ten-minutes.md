# The Whole Story in Ten Minutes

Same method as the Uniswap deep dive on your shelf: the entire plot at high speed first, so every later chapter lands on scaffolding instead of sand. Read fast; don't stop to master anything. Every paragraph below becomes a full chapter.

## Act 1 — One machine, and why it's not enough (Chapters 1–2)

Every system design conversation is secretly about one thing: **a request arrives; what has to happen before the answer leaves?** Chapter 1 walks that path end to end — DNS, load balancer, TLS, application server, database, and back — with the latency price tag of each step. This gives us the shared map every later chapter modifies.

Then the arc begins. Your app runs on one server. It succeeds; the server melts. You scale *up* (bigger machine) until money or physics objects, then you must scale *out* (more machines) — and scaling out forces the first great design rule: **make the application servers stateless**, push all state down into databases and caches, so any server can answer any request and machines become interchangeable cattle. The load balancer becomes the front door; the database becomes the bottleneck; and the rest of the book is, honestly, a series of increasingly clever answers to "the database is the bottleneck."

## Act 2 — The database, opened up (Chapters 3–6)

**Chapter 3 — storage engines.** Underneath every database sits one of two data structures. **B-trees** keep data sorted in fixed-size pages updated in place — read-optimized, the engine of Postgres and MySQL. **LSM-trees** batch writes in memory and flush sorted immutable files, merging them in the background — write-optimized, the engine of Cassandra, RocksDB, LevelDB. Reads vs writes, space vs amplification: knowing which engine you're standing on explains half of every database's personality.

**Chapter 4 — replication.** Copy the data to survive machine death and to serve more reads. Leader-follower is the workhorse; the poison is **replication lag** — followers serve stale data, and suddenly a user can post a comment and not see it. We name the anomalies (read-your-writes, monotonic reads) and the exotic modes (multi-leader, and leaderless quorums à la Dynamo/Cassandra, where `W + R > N` gives you overlap instead of certainty).

**Chapter 5 — partitioning.** When data outgrows any one machine, shard it — by key range (sortable, hot-spot-prone) or by hash (balanced, range-scan-hostile), with **consistent hashing** so adding a node doesn't reshuffle the world. Then the sequels: rebalancing, hot keys, and the awkward fact that secondary indexes and cross-shard queries stop being free.

**Chapter 6 — transactions.** The anomaly zoo (dirty reads, lost updates, write skew), the isolation levels that fence different subsets of it, and the two great implementations — locking (2PL) and multi-version concurrency (MVCC/snapshot isolation). Then transactions try to span shards, and we meet two-phase commit and its blocking heart.

## Act 3 — The uncomfortable truths (Chapter 7)

Distributed systems run on machines with unsynchronized clocks, networks that lose messages, and processes that pause mid-sentence. Chapter 7 stares at this: why you can't trust timestamps to order events, what **linearizability** actually promises, what CAP actually says (during a partition, choose consistency or availability — and the interesting tradeoff is really latency vs consistency), and how a cluster nonetheless agrees on anything: **consensus**, via Raft — leader election, log replication, quorum overlap — the algorithm inside etcd, and the reason a "simple" three-node control plane works. This chapter is the book's spine; everything before it secretly depended on it, and everything after builds on it.

## Act 4 — Moving the work around (Chapters 8–10)

**Chapter 8 — caching.** The only true performance shortcut: answer from memory what you already computed. Patterns (cache-aside, write-through), the two hard problems (invalidation, and the thundering-herd stampede when a hot key expires), and the full hierarchy from browser cache to CDN to Redis.

**Chapter 9 — logs and streams.** The quiet superstar of modern architecture: the **append-only log**. Kafka turns "database replication internals" into a public building block — producers append, consumer groups read at their own pace, partitions give parallelism and per-key ordering. On top of it: change-data-capture (the database's own changelog as an event stream), event sourcing, and the honest version of "exactly-once."

**Chapter 10 — derived data.** Stop asking one database to do everything. Keep one **system of record**, then *derive* everything else from its change stream: search indexes (Elasticsearch), analytics warehouses, feature stores, caches. Batch used to own this (MapReduce); streams took over; the pattern — state as something you can always rebuild from the log — is the closest thing this field has to a unifying theory.

## Act 5 — The front door and the failure modes (Chapters 11–12)

**Chapter 11 — the traffic layer.** Load balancing algorithms and L4 vs L7, API gateways, **rate limiting** (token bucket and friends, and the subtlety of doing it across a fleet), and **idempotency** — the unglamorous discipline that makes retries safe, without which every network hiccup double-charges a credit card.

**Chapter 12 — failure and observability.** Systems fail sideways: retries amplify load, queues hide overload until latency explodes, one slow dependency cascades. The defenses — timeouts, exponential backoff with jitter, circuit breakers, backpressure, load shedding, bulkheads — and the instruments: metrics, logs, traces, SLOs and error budgets, percentiles (p99, not averages — your best customers live in the tail).

## Act 6 — Putting it together (Chapter 13)

Full worked designs — the URL shortener, a Twitter-scale feed (the fan-out-on-write vs fan-out-on-read decision, and the celebrity hybrid), and a chat system — each solved with the book's vocabulary and real numbers. Plus the **back-of-envelope toolkit** (the latency table, powers of two, the arithmetic that turns "100M DAU" into "~1,200 writes/sec, plan for 12,000 peak") and the interview method: requirements → estimates → high level → deep dives → failure modes.

## How to read

- Chapters strictly build: replication lag (4) haunts caching (8); the log (9) re-explains replication (4) and resolves derived data (10); consensus (7) underlies everything with the word "leader" in it.
- "*Connect the dot*" flags a deliberate callback. The dots are the curriculum.
- Numbers are 2026-current and rounded for memory, not precision.

Turn the page. A request has just left a phone.
