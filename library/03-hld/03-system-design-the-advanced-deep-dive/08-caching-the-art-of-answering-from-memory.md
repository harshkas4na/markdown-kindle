# Caching — The Art of Answering From Memory

**Fast overview:** caching exploits Chapter 1's physics (memory is 100–1000× closer than disk, edges are 100ms closer than origins) to answer repeated questions without redoing the work. This chapter covers the full hierarchy (browser → CDN → gateway → Redis → DB internals), the access patterns (cache-aside and friends), and the two famous hard problems: invalidation, and the stampede family of self-inflicted outages. Caches are Chapter 4's "copies that lie" pushed to the extreme — fastest copy, weakest promise.

## The hierarchy: cache at every distance

- **Client/browser** — HTTP `Cache-Control`, ETags; zero-network hits; you control it only via headers, so *get the headers right* (immutable fingerprinted assets: cache forever; APIs: usually `no-store` unless deliberate).
- **CDN / edge** (CloudFront, Cloudflare, Fastly) — static assets by default; increasingly *dynamic* API caching and edge compute. Solves distance (Chapter 1: RTTs dominate), absorbs traffic spikes and DDoS before they touch you.
- **Gateway/reverse-proxy** (nginx, Varnish) — whole-response caching in your datacenter.
- **Application cache** (Redis, Memcached) — *the* workhorse tier: sub-millisecond, shared across the stateless fleet (Chapter 2's contract: state lives in shared stores — this is that store's fast half). Redis in practice: not just a cache — sorted sets (leaderboards), streams, pub/sub, locks (with Chapter 7's fencing caveats!), rate-limit counters (Chapter 11).
- **Database-internal** — buffer pools (Chapter 3's B-tree top levels living in RAM), query caches. Free; already working; the reason "the DB is fast in staging."

Sizing intuition: hit rate is everything. At 95% hit rate, the DB sees 1/20th of reads; going 95→99% cuts its load *another* 5× — small hit-rate gains at the top are massive load changes at the bottom. Conversely (the flip side that bites): **a cold or flushed cache multiplies DB load 20×instantly** — see stampedes below.

## Patterns: who fills the cache, who writes the DB

- **Cache-aside (lazy)** — the default 90% answer. App reads cache; on miss reads DB and populates; on *write*, update DB then **delete** (don't update) the cache key. Deleting is safer than setting: computing the new value in-app races concurrent writers (you can set a stale value with no TTL to save you); a delete just forces the next reader to fetch truth.
- **Read-through / write-through** — the cache library/service itself loads on miss / writes DB synchronously on write. Same semantics, tidier code, cache always consistent-ish; write latency now includes the cache.
- **Write-behind (write-back)** — buffer writes in cache, flush to DB async. Absorbs write bursts (RAM-speed writes!) at the price of *losing acknowledged writes* if the cache dies pre-flush. Use only where loss is tolerable (view counters) or the "cache" is durable (which is a queue — Chapter 9 does this properly).
- **Refresh-ahead / precompute** — for known-hot keys, refresh before expiry or compute proactively (the feed caches of Chapter 13 are precomputed products, not caches of queries).

## Hard problem #1: invalidation

("There are only two hard things in computer science…") The core issue is Chapter 4's in miniature: a copy exists; the original changed; who tells the copy? Strategies, weakest to strongest:

- **TTL** — every entry expires. The universal backstop: bounded staleness, zero plumbing. Short TTLs = fresher + more DB load; long = cheaper + staler. *Always set a TTL even when you also invalidate explicitly* — it caps the blast radius of every bug below.
- **Explicit invalidation** — writers delete affected keys. Precise but fragile: every write path must know every cache key shape derived from that data (the "who else caches this?" problem grows with the codebase).
- **Event-driven invalidation** — subscribe cache-maintainers to the database's change stream (CDC — Chapter 9/10) so *the data itself* announces changes; writers can't forget. The architecturally honest solution, and another vote for the log as spine.
- **Versioned keys** — key includes a version/updated_at (`user:42:v17`); writers bump the version pointer; old entries die by TTL. Sidesteps racy deletes elegantly where an authoritative version exists.

Related decision: **what to cache** — raw rows (reusable, cheap to invalidate precisely) vs computed responses (max latency win, invalidates broadly). Mature systems cache both layers deliberately.

## Hard problem #2: stampedes and their family

The self-inflicted outages, all sharing one shape — *the cache's absence is correlated*:

- **Thundering herd / cache stampede:** a hot key expires; 10,000 concurrent requests all miss, all hit the DB with the *same* query. Fixes: **request coalescing / single-flight** (one loader per key, everyone else waits — build or use a library), **stale-while-revalidate** (serve the expired value while one worker refreshes), **jittered TTLs** (never let a class of keys expire in sync), and **probabilistic early refresh** (hot keys refresh slightly before expiry with randomness).
- **Cold-start herd:** cache restarts empty → DB gets 20× load → DB dies → cache can't fill. Fixes: cache warming before taking traffic, replicated caches (Redis replicas + persistence), gradual traffic ramp.
- **Cache penetration:** queries for keys that *don't exist* (or an attacker inventing them) always miss and always hit the DB. Fixes: cache negative results (short TTL), or a Bloom filter of valid keys in front (*connect the dot:* Chapter 3's LSM trick, same job — cheap "definitely not here").
- **Hot-key overload:** one key exceeds even one *cache node's* capacity (Chapter 5's celebrity, now melting Redis). Fixes: replicate the key across nodes, client-local micro-caches (a 1-second in-process TTL on the top-100 keys absorbs astonishing load).

## The honest summary

A cache is a bet that the recent past predicts the immediate future, paid for in staleness and operational sharp edges. Rules that survive contact with production: every entry has a TTL; every hot path has a coalesced loader; hit rate, eviction rate, and *DB load with cache disabled* are dashboards you look at before the incident; and the cache is *not* the system of record — anything you can't recompute from the source of truth doesn't belong there. That "recompute from the source of truth" instinct — state as a derived, rebuildable artifact — is about to become the organizing principle of the next two chapters, where the source of truth grows an API of its own: the log.
