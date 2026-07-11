# Case Studies and the Back-of-Envelope Toolkit

**Fast overview:** the graduation chapter. First the estimation toolkit (the arithmetic that turns "100M users" into hardware), then three classic designs solved end-to-end with the book's vocabulary — URL shortener, Twitter-scale feed, chat — each chosen because it exercises a different spine: caching, fan-out, and ordering respectively. Ends with the interview method and the reading list.

## The back-of-envelope toolkit

Constants worth knowing cold: ~100k seconds/day (use 86,400 when showing work); 1M requests/day ≈ **12/sec** (magic conversion); peak ≈ 2–5× average; Chapter 1's latency table; a modern server: tens of thousands of simple RPS, hundreds of GB RAM, TBs of NVMe.

The drill, on a Twitter-alike: 200M DAU, 2 posts/day, 100 timeline views/day.
- Writes: 400M posts/day ≈ **4,600/sec**, peak ~15k/sec. Trivial for a partitioned write path.
- Reads: 20B timeline loads/day ≈ **230k/sec** — read:write is 50:1. *The architecture will be read-dominated: cache and precompute* (Chapter 2 stage 4 instincts, quantified).
- Storage: a post ≈ 1KB → 400GB/day of posts, ~150TB/year — one partitioned cluster's problem, not a hard one. Media is separate (object storage + CDN) by two orders of magnitude.
- Feed cache: 200M users × 800 post-IDs × 8B ≈ **1.3TB of RAM** — a Redis cluster of ~15–30 nodes. Feasible, so precomputation is on the table.

That's the whole skill: three multiplications that *choose the architecture* before any boxes get drawn.

## Case study 1: URL shortener (the caching spine)

Requirements: shorten (write, rare), redirect (read, brutal ratio ~1000:1, latency-critical), 100M new URLs/month (~40 writes/sec — tiny), maybe 100k redirects/sec peak.

- **Key generation:** base62 of a counter (7 chars = 62⁷ ≈ 3.5 trillion). A global counter is a SPOF/hot spot (Chapter 5) → allocate counter *ranges* to app servers (coordination via the Chapter 7 store, amortized), or pre-generate a key pool. Hash-of-URL alternative: idempotent (same URL → same code — Chapter 11 thinking!) but needs collision handling.
- **Storage:** key→URL is a pure KV workload; any replicated store works at these sizes; partition by short-code hash when needed.
- **The read path is a cache problem:** redirects follow a hard power law → Redis cache-aside with ~1-day TTLs gets 95%+ hit rate; negative-cache unknown codes and/or Bloom filter to kill penetration attacks (Chapter 8's kit, deployed verbatim); CDN/edge caching of hot redirects moves the p50 to ~10ms globally (Chapter 1's distance rule).
- **301 vs 302:** permanent redirects get cached by browsers (fastest, but kills analytics); 302 keeps clicks visible — a *product* decision surfaced by an HTTP detail. Click analytics: fire-and-forget events to a log → stream aggregation (Chapters 9–10), never a synchronous DB write on the redirect path.

## Case study 2: the feed (the fan-out spine)

The famous decision: when a user posts, is the work done at **write time** or **read time**?

- **Fan-out on write (push):** on post, look up followers, insert the post ID into each follower's precomputed feed list (Redis sorted sets). Reads are O(1) — fetch a list (230k reads/sec becomes trivial). Cost: a post by a user with F followers = F writes. Average user (F≈200): fine, done async via the log (Chapter 9 — post event → fan-out workers; a delay of seconds is invisible).
- **The celebrity problem:** F = 100M ⇒ one post = 100M writes — hours of queue time, terabytes of churn (Chapter 5's hot key, in write form). Fan-out on read for them: don't push; at read time, *merge* the precomputed feed with fresh posts pulled from followed celebrities (each user follows few celebrities; the merge is small).
- **The hybrid** (what Twitter/X actually converged on): push for normal users, pull for the >~100k-follower tail, merge at read. Plus ranking: candidate posts flow through a scoring service at read time — which needs features from a feature store — *derived data* (Chapter 10) making its product appearance.
- Supporting cast: posts in a partitioned store keyed by user; follow graph partitioned by follower (fan-out reads it by "who follows X" — a *global* secondary index question, Chapter 5); Snowflake IDs for time-sortable, coordination-free post IDs; everything behind Chapter 11's gateway and Chapter 12's budgets.

The transferable lesson: **read/write ratio + skew decides where work happens.** Feeds are the canonical instance of a universal pattern (notification systems, activity streams, materialized timelines of any kind).

## Case study 3: chat (the ordering spine)

Requirements: 1:1 and group messages, delivery states, online presence, history, typing indicators. What's new versus the feed: **persistent connections** and **per-conversation ordering**.

- **Connections:** clients hold WebSockets to a stateful gateway fleet (statelessness — Chapter 2 — bends here; the *session* is state). Users ↔ gateway mapping lives in Redis; gateways are found by consistent hashing (Chapter 5/11). Sending a message: persist first, then route to recipients' gateways for push; offline users get it on reconnect + mobile push.
- **Ordering:** global order is neither possible (Chapter 7: no trustworthy timestamps) nor needed. Order *per conversation*: partition messages by conversation_id (Chapter 5's maxim: dominant query = one shard) and assign per-conversation sequence numbers (single writer per conversation — the partition's leader — makes this cheap; Chapter 4/7). Kafka-style per-partition ordering (Chapter 9) is the same trick if a log carries the messages.
- **Delivery states** (sent/delivered/read): at-least-once delivery + client-side dedup by message ID — Chapter 9's ladder and Chapter 11's idempotency, on the client. Receipts are just tiny reverse-messages.
- **Storage:** write-heavy, time-ordered, ranged-scanned by conversation — LSM territory (Chapter 3; Cassandra/Scylla with (conversation_id, seq) as (partition, clustering) key is the textbook schema — Chapter 5's hybrid partitioning, verbatim).
- **Presence:** heartbeats into TTL'd Redis keys; broadcast presence changes only to *interested* parties (a subscription fan-out — small feed problem inside the chat problem). Typing indicators: fire-and-forget pub/sub, deliberately unreliable (shed first under load — Chapter 12's priority shedding, as product design).

## The interview method (and the design method — same method)

1. **Requirements, 5 minutes.** Functional (what does it do) + non-functional as *numbers* (scale, latency, availability, consistency needs per path — Chapter 4's labeling).
2. **Envelope math, 3 minutes.** QPS, storage, read:write, skew. Let the numbers pick the architecture family (they did, in all three cases above).
3. **High-level boxes, 10 minutes.** Client → edge → services → data. Name the system of record, the derived stores, the async paths. Draw the *write path* and *read path* separately.
4. **Deep dives, 15+ minutes.** Wherever the numbers said the pain lives (fan-out, ordering, hot keys...). This is where the book's chapters are your parts bin.
5. **Failure pass, 5 minutes.** Kill each box; say what users see; invoke Chapter 12's kit and the consistency anomalies you accepted. Mentioning what you *deliberately degraded* is senior-signal number one.

## Reading list

- **Kleppmann & Riccomini, *Designing Data-Intensive Applications*, 2nd ed. (2026)** — the book behind Chapters 3–10; the new edition adds cloud-native, local-first/CRDTs, and reworked consensus chapters. Read it slowly; it's the field's one indispensable text (your shelf already carries notes on the 1st ed. — the deep dives here complement them).
- **Raft**: the "In Search of an Understandable Consensus Algorithm" paper + thesecretlivesofdata.com visualization — Chapter 7 from the source.
- **Jepsen analyses** (jepsen.io) — real databases failing consistency claims under partition; the most educational schadenfreude in the field. Kyle Kingsbury's "consistency map" pairs with Chapters 4/6/7.
- **Google SRE book** (free online) — SLOs, error budgets, and the operational culture of Chapter 12.
- **Kafka: The Definitive Guide** + Kleppmann's "Turning the Database Inside Out" talk — Chapters 9–10's worldview.
- **System Design Primer** (GitHub) for breadth; **ByteByteGo / Alex Xu volumes** for interview-shaped case studies beyond the three here.
- Engineering blogs that are actually good: Cloudflare (networking), Discord (chat at scale — their Cassandra→Scylla messages saga is Case Study 3 in production), Netflix (resilience), Stripe (idempotency, APIs), Uber (storage evolution).

## Closing the loop

The book opened with a request leaving a phone and a promise: every component exists because a previous one hit a wall. You can now recite the whole causal chain — one box → stateless fleet → replicas and their lies → shards and their maxims → transactions → consensus holding the coordination weight → caches, logs, and derived stores moving the work around → a hardened front door → systems that fail on purpose instead of by surprise. That chain, plus three multiplications on an envelope, is the entire discipline. The rest is practice — and the practice is just this story, retold with your product's nouns.
