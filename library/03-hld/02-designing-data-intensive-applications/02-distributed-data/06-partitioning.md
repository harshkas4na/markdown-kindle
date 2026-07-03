# Partitioning

Replication (previous chapter) is about keeping *copies* of the same data. Partitioning (aka **sharding**) is the opposite move: splitting *different* data across multiple nodes, so that a dataset — and the write load against it — can grow past what any single machine can hold or handle. The two are almost always combined in practice: each partition is itself replicated, so you get both horizontal scale and fault tolerance at once. Replication alone only ever scales reads; partitioning is what scales writes and total data volume.

## How to split the keyspace

**Key range partitioning**: each partition owns a contiguous range of keys, like a paper phone book split into "A–C," "D–F," and so on. The advantage: range queries (fetch everything between key X and key Y) stay within one partition and are efficient. The danger: if access isn't uniform across the key space, you get **hot spots** — the classic mistake is partitioning by timestamp, which sounds reasonable but puts every write for "right now" on a single partition while all the older partitions sit idle.

**Hash partitioning**: hash each key and assign partitions by ranges of the hash output. This scrambles keys that were adjacent in the original space, so range queries lose their efficiency (a scan now has to hit every partition), but in exchange, load is spread far more evenly since the hash function destroys any structure in the original keys that might have caused skew. A specific technique, **consistent hashing**, is worth knowing by name because of what it avoids: naive `hash(key) % N` reshuffles almost *every* key the moment `N` changes (adding or removing one node), which triggers a massive, unnecessary wave of data movement. Consistent hashing instead assigns only a *proportional slice* of keys to move when nodes are added or removed — the rest stay put.

**Skew that hashing can't fix**: hashing solves *general* unevenness, but it cannot save you from a single extremely popular individual key — a celebrity account, a viral post — all of whose reads/writes land on one partition regardless of how well-distributed the hash function is. That specific problem needs an application-level fix: split a known-hot key across a handful of sub-keys (e.g. append a random suffix) and merge results back together on read.

## Partitioning secondary indexes

This is where partitioning gets genuinely tricky, because an index entry for "all items where color = red" doesn't have one obvious home the way a primary key does.

- **Document-partitioned (local) indexes**: each partition maintains its own index covering only the documents stored on it. Writes stay fast and local (only the partition holding that document needs updating). The cost lands on reads: a query needs to hit *every* partition and merge results (**scatter-gather**) — which means the read's tail latency is bounded by the *slowest* partition, not the average.
- **Term-partitioned (global) indexes**: the index itself is partitioned by the term being indexed (e.g. all "color = red" entries live together, on whichever partition owns that term), regardless of where the underlying documents live. Reads become fast and single-partition. The cost lands on writes: a single write to one document may now need to update index entries that live on several different partitions — which is usually done **asynchronously**, meaning the index can lag slightly behind the underlying data.

Neither option is free — it's the same fast-write/fast-read tension that shows up throughout this book, just relocated to index maintenance specifically.

## Rebalancing partitions

Data volume and load grow, which means nodes need to be added — and existing partitions need to move to make room, without breaking anything mid-move.

The trap to avoid: `hash(key) % N`. It looks like an obvious approach, but changing `N` (adding one node) changes almost every key's target partition simultaneously, meaning nearly the entire dataset gets reshuffled for the sake of adding one machine — an unnecessary, expensive stampede.

The approach real systems actually use: pick a **fixed, generous number of partitions up front** (deliberately many more than the current node count — e.g. 1,000 partitions across 10 nodes), and handle growth by moving whole, already-existing partitions between nodes rather than recomputing keys at all. No key is ever individually rehashed; only entire partition-sized chunks are reassigned. This is how Cassandra, Elasticsearch, and most other production sharded systems actually rebalance — the fixed-partition-count decision made at setup time is precisely what avoids the `% N` trap later.

## Request routing

Given a partitioned dataset, a client request still needs to find the *right* node. Three common patterns:
1. Contact any node; if it doesn't own the requested key, it forwards the request internally.
2. Route everything through a dedicated routing tier that knows the current partition-to-node mapping.
3. Make clients themselves partition-aware, so they contact the correct node directly.

All three need a shared, up-to-date source of truth for "which node owns which partition right now," especially as rebalancing happens — commonly delegated to an external coordination service (a ZooKeeper/etcd-style system, itself built on the consensus mechanisms covered later) that nodes and routers subscribe to for live updates.

## Takeaways

- Partitioning is the only lever that scales *write* throughput and total dataset size — replication alone never does that, it only scales reads and adds fault tolerance.
- Range partitioning keeps queries efficient but risks skew from non-uniform access; hash partitioning fixes general skew but kills range queries — the choice is a direct tradeoff on your actual query patterns.
- The single biggest rebalancing mistake is any scheme where adding one node reshuffles most of the dataset — fixed partition counts assigned to nodes (not derived from `% N`) are what avoids it.
