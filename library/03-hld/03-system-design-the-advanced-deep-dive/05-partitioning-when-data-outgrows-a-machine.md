# Partitioning — When Data Outgrows a Machine

**Fast overview:** partitioning (sharding) splits data across machines so no single node holds or serves everything — the write-wall answer from Chapter 2, stage 5. Decisions that define your fate: *how* to split (range vs hash), how to *rebalance* when nodes come and go (consistent hashing and its rivals), what to do about *hot keys*, and how to live without cheap cross-shard queries, indexes, and transactions. Every partition is itself replicated (Chapter 4) — the two compose, they don't compete.

## Range vs hash: the first fork

**Range partitioning:** sort by key, cut into contiguous ranges (A–F here, G–M there). HBase, Spanner, CockroachDB, and most "NewSQL." Gift: **range scans work** — "all events for March" touches one or two shards. Curse: **skew**. Monotonic keys (timestamps, auto-increment IDs) aim *every insert at the last shard* — the classic time-series hot spot. Mitigation: prefix the key with something spreading (tenant ID, sensor ID) so recency spreads across many ranges.

**Hash partitioning:** `shard = hash(key) mod-ish N`. Uniform by construction; adjacent keys scatter — **range scans die** (must fan out to all shards). Cassandra/Dynamo default. Hybrid worth knowing (Cassandra's model): **hash by partition key, then sort by clustering key within the partition** — "hash by user_id, range-scan that user's timeline" — the best of both for entity-centric workloads, and quietly the schema-design idiom of most large-scale apps.

## Rebalancing: the mod-N trap and consistent hashing

Naive `hash(key) mod N` is a time bomb: change N and *nearly every key moves*. Rebalancing must move as little as possible while staying balanced.

**Consistent hashing** (the interview classic): imagine the hash space as a ring; nodes sit at hashed positions; each key belongs to the next node clockwise. Add/remove a node and only the adjacent arc moves — 1/N of the data. Real implementations add **virtual nodes** (each physical node appears ~100–256 times on the ring) to smooth the load and let heterogeneous machines take proportional shares. Where you've already met it without the name: Cassandra's token ring, DynamoDB's partitioning, Memcached client sharding, load balancers pinning sessions (*connect the dot:* Chapter 4's monotonic-reads fix was consistent-hashing users to replicas).

The grown-up alternative most real databases use: **explicit partition assignment** — many fixed partitions (say 1024) mapped to nodes by a lookup table in a coordination service; rebalancing = *reassign partitions*, moving whole partitions, not keys. Simpler to reason about, supports manual placement, and the mapping table needs a consistent, watchable home — which is literally why ZooKeeper/etcd exist (Chapter 7's consensus, already earning its keep). Kafka (Chapter 9) works exactly this way.

**Request routing** (how a query finds its shard) is the same choice re-cast: routing tier consults the mapping (needs the coordination service), smart clients cache it, or any-node-forwards (Cassandra gossip). All three exist in production; all three must handle "my map is stale" mid-rebalance.

## Hot keys: when one key is the whole problem

Partitioning spreads *keys*; it cannot spread *one* key. The celebrity problem: Justin Bieber's row takes a million reads/sec; his shard melts while others idle. Escalating toolkit:

1. **Cache it** — a hot key is by definition cacheable (Chapter 8); this solves reads 95% of the time.
2. **Split the key** — append a random suffix (`bieber#1..#16`) spreading load over 16 shards; readers fan in. Works for counters/append streams; complicates reads.
3. **Special-case it** — detect hot entities and handle them on a dedicated path (Chapter 13's feed design does exactly this: celebrities get fan-out-on-read while normal users get fan-out-on-write).

Write-hot keys (a viral post's like-counter) add: batch increments in memory and flush (trade freshness), or CRDT counters across replicas (Chapter 4's toolkit).

## What sharding breaks (the fine print from Chapter 2)

- **Secondary indexes.** "Find users by email" when sharded by user_id: either each shard indexes its own data and queries **scatter-gather** every shard (read amplification, tail latency — Chapter 1's amplification is back), or you keep a **global index, itself sharded by the indexed value** (email-sharded index) — reads go to one place, but now *every write touches two shards* and the index is async → briefly stale. Local vs global index is a real design decision with no free option; DynamoDB literally sells both (LSI/GSI).
- **Transactions across shards** stop being free — Chapter 6 ends with 2PC and why everyone avoids it.
- **Joins** across shards become application-side or ETL jobs — one more reason derived data (Chapter 10) exists.
- **Unique constraints, auto-increment IDs** need global coordination — hence Snowflake-style ID schemes (timestamp + worker + sequence: k-ordered, coordination-free; Chapter 13 uses one).

Design maxim that falls out: **choose the partition key so your dominant queries are single-shard.** Shard a chat app by conversation_id, not message_id; a multi-tenant SaaS by tenant_id; a social graph… painfully (the graph has no clean cut — one reason dedicated graph infra exists).

## Buy vs build, 2026 edition

Nobody hand-rolls sharding in application code anymore without duress. The market: **Vitess** (YouTube-lineage MySQL sharding, now the boring-good default), **Citus** (sharded Postgres), **CockroachDB/Spanner/TiDB** (range-sharded, consensus-replicated, auto-rebalancing — Chapter 7's machinery productized), **Cassandra/Scylla** (hash-ring, leaderless — Chapter 4's third family), **DynamoDB/Aurora-limitless** (rent the problem). The skills this chapter taught — partition-key choice, skew diagnosis, rebalance behavior — are exactly the knobs those systems still leave in your hands. The vendor moves the machinery; the *modeling* remains yours.

Two dangling threads got louder here: partitions + replicas per partition + failover per partition = a lot of "who is the leader of shard 47 right now?" — a question only **consensus** answers safely (Chapter 7). And updating "two places on a write" (global indexes) begged for reliable multi-step updates — **transactions**, next chapter.
