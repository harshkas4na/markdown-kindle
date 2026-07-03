# Storage and Retrieval

Chapter 2 was about the data model you *talk to*. This chapter is about what actually happens underneath when the database stores and finds your data — and it matters because the storage engine's internal design directly determines what your database is fast and slow at, regardless of which query language sits on top of it.

Databases split broadly into two families, optimized for opposite access patterns:

- **OLTP** (online transactional processing): lots of small, frequent reads/writes, usually keyed by some ID (fetch this user, update this order) — the day-to-day operational database behind an application.
- **OLAP** (online analytical processing): far fewer queries, but each one scans a huge portion of the data to compute an aggregate (total revenue by region and month, over years of history) — the data-warehouse side.

These two access patterns are different enough that the storage engines built for them look almost nothing alike internally.

## Log-structured storage: the append-only idea

The simplest possible database is an append-only file: every write is just appended to the end. This is about as fast as writing to disk can be, because **sequential writes** are dramatically faster than random writes on both spinning disks and (to a lesser degree) SSDs — no seeking, no interleaving with other data. The problem: finding a specific record means scanning the whole file, which is unacceptably slow once the file is large. The solution is always the same shape: keep the fast append-only log, and build a separate **index** that tells you where to look, without ever needing to scan.

**Hash indexes** (the Bitcask model): keep an in-memory hash map of `key → byte offset in the log file`. A write appends to the log and updates the hash map; a read looks up the offset and seeks straight to it. Extremely fast for point lookups, but two real constraints: the whole index has to fit in memory (or fail), and the log grows forever unless you periodically **compact** it — merging segment files, keeping only the most recent value for each key, and using **tombstones** (a special marker) to represent deletions so a delete doesn't just silently disappear the moment old segments are discarded.

**SSTables and LSM-trees**: the more general and more widely used design (LevelDB, RocksDB, Cassandra, HBase). The key idea: instead of an arbitrarily-ordered log, keep each segment file sorted by key (a **Sorted String Table**, or SSTable). Sorted segments unlock two big wins over plain hash indexes: merging multiple segments during compaction becomes a simple, efficient mergesort-style pass (even when the data is far bigger than memory), and the in-memory index no longer needs an entry for *every* key — a sparse index (one entry every few KB) is enough, because once you're near the right spot, a short sequential scan finds the exact key.

The write path that makes this work: incoming writes go first into an in-memory sorted structure (a **memtable**, typically a balanced tree). Once it hits a size threshold, it's flushed to disk as a new SSTable, and a background process periodically merges older SSTables together, discarding overwritten and tombstoned keys — the same log-and-compact shape as the hash-index approach, just organized around sorted order instead of raw offsets. This overall family of design is called a **Log-Structured Merge-tree (LSM-tree)**. To avoid disk I/O on reads for keys that don't exist at all, LSM engines commonly keep a **Bloom filter** per segment — a compact, probabilistic structure that can say "definitely not present" cheaply, avoiding an unnecessary disk read.

**B-trees**: the long-standing default in most relational databases (and most filesystems). Instead of an ever-growing sequence of immutable log segments, a B-tree is one large structure of fixed-size **pages** (traditionally 4 KB) arranged as a tree, where each write finds the correct page and **updates it in place**. In-place updates aren't naturally crash-safe (a crash mid-write to a page can corrupt it), so B-tree engines pair the tree with a **write-ahead log (WAL)** — every change is appended to the WAL before being applied to the tree, so a crash can always be recovered by replaying the WAL.

| | LSM-trees | B-trees |
|---|---|---|
| Writes | Sequential only — much higher sustained write throughput | In-place — more random I/O per write |
| Compaction/maintenance overhead | Background compaction can compete with foreground I/O ("write amplification") | None needed; overhead is WAL instead |
| Read latency | Can be less predictable (may need to check several segments) | Very predictable — fixed tree depth |
| Compression | Generally better (larger sequential blocks compress well) | Comparatively worse (fixed pages, in-place fragmentation) |
| Maturity/tooling | Newer, still catching up in some areas (e.g. transactional locking) | Decades of production hardening |

Neither is strictly better — LSM-trees win on write-heavy workloads and storage efficiency; B-trees win on predictable read latency and are the safer, more battle-tested default for general-purpose transactional workloads.

## OLAP storage: column-oriented databases

Analytical queries have a completely different shape: they touch a huge number of rows, but usually only a handful of columns out of a wide table (e.g. "average order value by region" doesn't need the customer's shipping address or notes field). Row-oriented storage (the OLTP default — one row's fields stored contiguously) is wasteful here, because reading "just three columns" still means reading every row's full width off disk.

**Column-oriented storage** flips this: store each column's values contiguously across all rows, instead of each row's values contiguously across all columns. An analytical query then only reads the columns it actually needs — often a fraction of the total data. This layout also unlocks much better **compression**: a single column tends to have far fewer distinct values than a whole row (e.g. a "country" column repeats the same handful of strings millions of times), which compresses extremely well with techniques like bitmap encoding and run-length encoding, and also enables **vectorized processing** (operating on a compressed column in tight, CPU-cache-friendly batches).

Data warehouses commonly organize their tables around a **star schema**: a large central **fact table** (one row per event — a sale, a page view) with foreign keys out to smaller **dimension tables** (who, what, where, when) — denormalized on purpose, because the analytical workload cares about scanning the facts fast, not normalizing away duplication.

## Takeaways

- The right storage engine follows directly from the access pattern, not from "which database is popular": write-heavy and point-lookup-heavy favors LSM-trees; predictable low-latency reads with a mature ecosystem favors B-trees; wide-table aggregate scans favor column-oriented storage.
- The append-only-log-plus-index shape shows up everywhere in this space (hash indexes, SSTables, WALs) because sequential I/O is the one lever that's always faster, and every design here is some variation of "get the append-only speed, then bolt on a way to find things without scanning."
- OLTP and OLAP aren't just "different queries on the same data" — they usually end up as physically different storage systems for a reason, connected by a pipeline (covered later in batch/stream processing) rather than one engine serving both well.
