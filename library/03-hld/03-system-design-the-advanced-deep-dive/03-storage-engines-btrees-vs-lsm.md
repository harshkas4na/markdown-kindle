# Storage Engines — B-trees vs LSM

**Fast overview:** peel any database and you find one of two engines. **B-trees** update data in place inside fixed-size pages — steady reads, the relational default. **LSM-trees** never update in place: writes land in memory, flush as sorted immutable files, and background *compaction* merges them — write-optimized, the NoSQL default. This chapter builds both from scratch, introduces the three "amplifications" that let you compare any engine quantitatively, and explains the write-ahead log — which will return in Chapter 9 wearing a Kafka costume.

## Start from zero: the dumbest database

Append every write to a file; to read, scan backward for the key's last value. Writes are *optimal* — pure sequential append (Chapter 1's physics: sequential I/O is the fastest thing disks do). Reads are O(n) — hopeless. Every real engine is a strategy for adding *read structure* to that append-only speed, and the two families differ in *where* they pay for it.

## B-trees: sorted pages, updated in place

The 1970s answer, still running Postgres, MySQL/InnoDB, SQL Server, Oracle:

- Data lives in **fixed-size pages** (typically 4–16KB) forming a wide, shallow tree: each internal page holds hundreds of key-separated child pointers; leaves hold rows (or row pointers), sorted.
- **Read:** walk root → internal → leaf. A branching factor of ~500 means a *four-level* tree addresses hundreds of gigabytes — 3–4 page reads per lookup, and the top levels live permanently in RAM cache, so often just one real disk read. Range scans are lovely: find the start leaf, walk siblings.
- **Write:** read the leaf page, modify, write it back *in place*. A full page **splits** into two (and the split can propagate upward — how the tree stays balanced).

The in-place update has a dark corner: a crash mid-split corrupts the tree. So every serious B-tree engine writes intentions first to a **write-ahead log (WAL)** — an append-only file of "I am about to change X." Crash recovery replays the WAL. Savor the irony: *the read-optimized in-place engine keeps an append-only log under the hood anyway* — durability always ends up being a log. (*Connect the dot:* replication (Chapter 4) works by shipping this same log to followers; Chapter 9 makes the log a first-class public citizen.)

## LSM-trees: immutable sorted runs, merged later

The write-optimized answer (Google's Bigtable lineage: LevelDB, RocksDB; Cassandra, HBase, ScyllaDB; and inside many "NewSQL" stores):

- **Write:** append to a WAL (durability), then insert into the **memtable** — an in-RAM sorted structure (skip list, red-black tree). This is why LSM writes are fast: one sequential append + one memory insert; the disk's random-write problem is simply not on the path.
- **Flush:** a full memtable is written out as an **SSTable** — an immutable, sorted file with an index. Sequential write, done.
- **Read:** check memtable, then SSTables *newest to oldest* (the key might be in any of them). To avoid touching files that can't contain the key, each SSTable carries a **Bloom filter** — a tiny probabilistic set that answers "definitely not here" (no false negatives, small false-positive rate). Bloom filters are what make LSM reads livable; know them.
- **Compaction:** background threads merge SSTables (a k-way merge of sorted files — cheap and sequential), dropping overwritten versions and deleted keys (deletes are written as **tombstone** markers until compaction physically removes them — yes, deletes initially *add* data). Two strategies with real operational consequences: **size-tiered** (merge similar-sized files — write-cheap, space-hungry, read-scattered) vs **leveled** (strict per-level sorted runs — read-tight, write-heavier). RocksDB tuning is 80% choosing where on this dial to sit.

## The three amplifications: how to compare engines like an adult

For any engine, ask what one logical operation costs in physical I/O:

- **Write amplification** — bytes physically written per byte logically written. B-tree: rewrite a whole page per row touched, plus WAL. LSM: each byte is rewritten every time compaction touches its file — total WA of 10–30× is normal. (On SSDs, WA also burns device lifetime.)
- **Read amplification** — physical reads per logical read. B-tree: tree depth, mostly cached ≈ 1. LSM: potentially one probe per SSTable level, tamed by Bloom filters.
- **Space amplification** — disk used vs live data. B-tree: fragmented half-empty pages. LSM: not-yet-compacted duplicates and tombstones.

**RUM conjecture:** you cannot minimize Read, Update (write), and Memory/space overheads simultaneously — pick two-ish. This one line explains why the storage world has *families* instead of a winner.

Rules of thumb that follow:

| Workload | Lean |
|---|---|
| read-heavy, point + range queries, transactional | B-tree |
| write-heavy ingest (events, logs, time series, metrics) | LSM |
| strict latency predictability | B-tree (compaction bursts are LSM's classic p99 spike) |
| cheap disks, huge datasets, sequential-friendly | LSM |

## The row/column footnote that matters

Everything above is **row-oriented, OLTP**: fetch/update whole records by key. Analytics (**OLAP**) inverts the access pattern — scan *one column* across billions of rows — so warehouses (ClickHouse, BigQuery, Snowflake, Parquet files) store data **by column**: each column contiguous, compressed 10–100× (similar values compress absurdly well), scanned at memory bandwidth. Same logical data, opposite physical layout, orders-of-magnitude difference per workload. This is why Chapter 10 will insist on *copying* data out of your OLTP store into differently-shaped derived stores rather than making one database do both jobs.

## What the engine explains upstairs

- Postgres's write behavior under heavy update load (page churn, WAL volume, autovacuum) vs Cassandra swallowing firehose ingest — Chapter 3 in one sentence.
- Why Cassandra reads can degrade until compaction catches up, and why ops dashboards track "pending compactions."
- Why "just add an index" is not free: every index is another B-tree (or another sorted structure) that *every write must also update* — write amplification you chose voluntarily. Index for the queries you have, resist the rest.
- Why *every* durable system — SQL, NoSQL, message broker — has an append-only log at its core. Hold that thought hard: in Chapter 4 the log gets shipped between machines and called replication; in Chapter 9 it gets a public API and is called Kafka.

Next: the data survives a disk. Now make it survive a *machine* — replication, and the first real taste of distributed disagreement.
