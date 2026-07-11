# Derived Data — Search, Analytics, and the Inside-Out Database

**Fast overview:** stop asking one database to serve transactions, search, analytics, recommendations, and caching — no single engine's physics (Chapter 3) can win at all of them. Instead: one **system of record**, and a family of **derived stores** — search indexes, warehouses, caches, feature stores — each shaped for its consumer and each rebuildable from the change stream (Chapter 9). This chapter covers search engines (the flagship derived store), the analytics stack, batch vs streaming pipelines, and the "unbundled database" worldview that names what you've actually been building all book.

## The principle: systems of record vs derived data

Divide every byte in your company into two classes. **Systems of record** hold facts first — writes land here; correctness lives here (your OLTP Postgres, the orders topic). **Derived data** is *any* transformation of those facts: indexes, caches (Chapter 8 admitted this), materialized views, ML features, the warehouse. Derived data is redundant *on purpose* — lose it, rebuild it from the source.

Why the division is liberating: derived stores can be **denormalized, duplicated, and specialized** without guilt (consistency worries apply to records, not projections); and each consumer gets the physics it needs — the same order row lives simultaneously as a B-tree row (point lookups), an inverted-index posting (search), a column segment (analytics), and a Redis hash (checkout page). Four copies, four shapes, one truth — kept honest by CDC (Chapter 9) rather than by heroic dual-writes (the outbox lesson).

## Search: the inverted index

Why not `WHERE description LIKE '%wireless headphones%'`? Because a B-tree (Chapter 3) indexes *whole values from the left*: a contains-query scans every row. Search needs the inversion: map each **term → list of documents containing it** (the *postings list*).

A query tokenizes ("wireless", "headphones"), intersects postings lists, then **ranks** — classically BM25 (roughly: rarer terms weigh more; more occurrences in a shorter document weigh more), in 2026 typically *hybridized* with **vector similarity** (embedding-based semantic match, ANN indexes like HNSW) — lexical for precision, vectors for meaning.

**Elasticsearch/OpenSearch** (Lucene inside) operationalize this: documents flow in (from CDC!); each index shard is a Lucene instance; text passes analyzers (tokenize, lowercase, stem — the analyzer config *is* half of search quality). Two properties to respect: **near-real-time** — documents become searchable after a refresh interval (~1s), a deliberate throughput tradeoff, and another instance of Chapter 4's staleness; and **segments are immutable** — Lucene writes append-only segment files, merges them in the background… Chapter 3's LSM design, rediscovered by the search world independently. (The pattern count for "append + compact" is now: storage engines, MVCC, Kafka, Lucene.)

Design stance: search is a *projection*, not a record. Never write to Elasticsearch first; feed it from the stream, size its lag SLO explicitly, plan to rebuild indexes wholesale (reindex-then-swap-alias) as mappings evolve.

## Analytics: the column stack

The OLTP/OLAP split (Chapter 3's footnote, expanded). Analysts scan billions of rows, few columns, heavy aggregation — columnar engines (Snowflake, BigQuery, ClickHouse, DuckDB; Parquet as the file lingua franca) compress those columns 10–100× and scan them at memory bandwidth. Running analyst queries on the OLTP primary is a classic outage recipe (one table scan evicts the buffer pool that was serving your p99 — Chapters 3 + 8 colliding).

The 2026-shaped pipeline: OLTP → CDC/events → object storage in **open table formats** (Iceberg/Delta — Parquet plus transactions, schema evolution, and time travel; the "lakehouse") → SQL engines over it, plus **real-time OLAP** (ClickHouse, Pinot, Druid) where dashboards need seconds-fresh aggregates. ELT replaced ETL (land raw, transform in-warehouse with dbt-style tooling) because storage got cheap and rebuildability (that word again) beats pre-cooking.

## Batch and stream: the two pipeline engines

**Batch** (MapReduce's descendants: Spark): bounded input → deterministic output. Its superpower is a *fault-tolerance and correctness* model, not speed: inputs are immutable, outputs are pure functions of inputs, so failed tasks re-run and — crucially — **buggy jobs re-run too**. Code has bugs; a pipeline whose outputs can be regenerated from retained inputs turns "we corrupted the features table" from an incident into a re-run. This property is called **human fault tolerance** and it is the most underrated argument for keeping raw immutable inputs (the log, retained).

**Streaming** (Flink, Kafka Streams — Chapter 9): the same transformations over unbounded input, continuously, with windows/watermarks for time and checkpointed state for recovery. The old **Lambda architecture** (run both batch and stream, reconcile) has largely given way to **Kappa** — one streaming pipeline, with *replay* (Chapter 9's killer feature) serving the "recompute history" role batch used to own; engines like Flink treat batch as the finite special case of streaming.

Decision rule: freshness SLO. Humans reading a weekly report → batch. Fraud checks, feeds, dashboards under a minute → streaming. Both: Kappa with replay, or lakehouse tables fed by streams.

## The inside-out database

Step back and look at what this book has assembled. A classical database contains: a WAL, indexes, materialized views, a replication stream, a cache (buffer pool). Your architecture now contains: **Kafka** (the WAL, made public), **Elasticsearch** (the index, as a service), **warehouse/lakehouse** (materialized views), **Redis** (the buffer pool), **CDC** (the replication stream) — *the database, unbundled*, its internal organs replaced by products connected by logs. Kleppmann's framing: it's databases turned inside out, with the log as the spine and every store a subscriber.

The worldview in three design rules:

1. **Facts flow in one direction.** Writes hit the record system; everything downstream *derives*. No derived store is ever written directly; no dual writes (outbox, Chapter 9).
2. **Every derived store is disposable.** If you can't rebuild it from retained inputs, it's secretly a system of record — either promote it honestly or fix the pipeline.
3. **Staleness is a per-edge SLO.** Each derivation lags (search ~seconds, warehouse ~minutes); state the number, monitor it (Chapter 12), and design UX for it (Chapter 4's read-your-writes tricks where users notice).

The data architecture is complete: records, streams, projections. What's left is the *operational* half of the discipline — the front door that shapes incoming traffic, and the failure modes that emerge when all these pieces meet a bad day. Two chapters to go before the case studies cash everything in.
