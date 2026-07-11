# Transactions and the Anomaly Zoo

**Fast overview:** transactions let you make several reads and writes behave as one atomic, isolated unit — the abstraction that hides concurrency and crashes from application code. This chapter builds the anomaly zoo (the concrete bugs concurrency causes), maps isolation levels to which animals they cage, opens the two implementation engines (locking vs multi-version), and ends where Chapter 5 left us hanging: transactions that span shards, and why two-phase commit is everyone's least favorite answer.

## ACID, decoded honestly

- **Atomicity** — all-or-nothing *on crash/abort*: half-finished transactions roll back (implemented with the WAL — Chapter 3's log again: undo/redo records). Nothing to do with concurrency, despite the name.
- **Consistency** — your invariants ("balances sum to zero") hold if each transaction preserves them; really a property of *your* code. The C is marketing filler and everyone in the field admits it.
- **Isolation** — concurrent transactions don't step on each other; the meaty one, and the rest of this chapter.
- **Durability** — committed means fsync'd to the WAL (and, in 2026 practice, replicated — Chapter 4; a single machine's fsync is table stakes, not durability).

## The anomaly zoo

Learn these as concrete bugs, not definitions — each has emptied a real bank account somewhere:

- **Dirty read:** you read data from a transaction that later aborts — you acted on data that *never existed*.
- **Dirty write:** you overwrite uncommitted data — two interleaved transactions braid their writes.
- **Read skew (non-repeatable read):** you read account A, someone's transfer commits, you read account B — your two reads straddle the change and the books look unbalanced. Deadly for backups and analytics scans.
- **Lost update:** two counters do read-modify-write concurrently; both read 41, both write 42. One increment vanishes. The most common real-world concurrency bug.
- **Write skew:** the shape-shifter. Two doctors both check "≥2 doctors on call," both go off call — the *premise* each validated was invalidated by the *other's* write, though they touched different rows. Generalization: any check-then-act on a predicate ("no meeting overlaps," "username free") where concurrent transactions insert rows the other's check would have caught — the insert case is called a **phantom**.

## Isolation levels: which animals each level cages

Standard levels, in the modern (implementation-aware) reading:

| Level | Blocks | Still bites you |
|---|---|---|
| Read uncommitted | ~nothing | everything |
| Read committed | dirty read/write | read skew, lost update, write skew |
| Snapshot / repeatable read | + read skew (you see one consistent point in time) | lost update (in some impls), write skew, phantoms |
| Serializable | everything — result equals *some* serial order | your latency budget, occasionally |

Field notes that matter more than the table: **read committed is the default** in Postgres/Oracle (MySQL's default, repeatable read, ≈ snapshot) — so *the default setting of the world's databases permits lost updates and write skew*. Most teams discover their isolation level from an incident. Also, names lie across vendors — Oracle's "serializable" is actually snapshot isolation; test, don't trust.

## The two engines under isolation

**Pessimistic — two-phase locking (2PL):** readers take shared locks, writers exclusive; hold everything until commit. Truly serializable, and how it was done for decades. Costs: readers block writers and vice versa; deadlocks (detector kills a victim); throughput cliff under contention. (No relation to two-phase *commit* below — cursed naming.)

**Optimistic — MVCC (multi-version concurrency control):** never update in place; keep multiple versions of each row stamped with transaction IDs; each transaction reads *the snapshot as of its start*. **Readers never block writers, writers never block readers** — the property that made Postgres/MySQL/Oracle feel fast and made snapshot isolation the world's real default. Writes still conflict on the same row ("first committer wins" or locks). Garbage: old versions must be vacuumed — Postgres's autovacuum and its bloat dramas are MVCC's rent. (*Connect the dot:* "immutable versions + background cleanup" is Chapter 3's LSM philosophy applied to concurrency — the field keeps rediscovering append-and-compact.)

**Modern serializable = SSI:** run MVCC optimistically, *track* read/write dependencies, and abort transactions whose overlap could create a cycle (a non-serializable outcome). Serializable Snapshot Isolation is how Postgres's `SERIALIZABLE` works — write-skew-proof at ~10–30% throughput cost plus retry logic (aborted transactions must be retried — your framework needs a retry loop, which needs idempotency thinking, Chapter 11). The pragmatic 2026 posture: **snapshot isolation by default; explicit weapons for the known animals** — `SELECT ... FOR UPDATE` or atomic `UPDATE x = x + 1` for lost updates; unique constraints for phantoms; SSI or materialized locks for genuine write-skew invariants.

An honorable oddball: **actual serial execution** — if transactions are short and the dataset fits in RAM, just run them one at a time on one core (Redis; VoltDB). Serializability by not having concurrency at all. Works precisely until it doesn't.

## Distributed transactions: the part everyone avoids

Chapter 5 sharded your data; now a transfer debits shard A and credits shard B. Two independent commits can half-happen (A commits, B's node crashes) — atomicity across machines needs a protocol.

**Two-phase commit (2PC):** a coordinator asks all participants to **prepare** (each writes redo/undo to its WAL and promises "I *can* commit"), then, if all say yes, tells everyone to **commit**. Correct — and operationally hated for one property: **it blocks**. Between a participant's "prepared" and the coordinator's verdict, that participant holds locks and *cannot decide alone* — if the coordinator dies, prepared transactions sit locked ("in doubt") until it returns. The coordinator is a SPOF whose failure freezes unrelated traffic; throughput pays two round trips + fsyncs per commit. XA (the cross-vendor 2PC standard) earned its dismal reputation here.

How 2026 systems actually cope, in order of preference:

1. **Don't distribute the transaction.** Choose partition keys so hot transactions are single-shard (Chapter 5's maxim, now with teeth). Model money as per-account append-only ledgers, not cross-account row updates.
2. **Sagas:** a multi-step business flow = sequence of *local* transactions + **compensating actions** for rollback (book flight → book hotel → hotel fails → *cancel flight*). Eventual atomicity, explicit failure choreography; the standard microservices answer — often driven through a log (Chapter 9) so steps retry reliably. Requires designing every step to be compensatable and idempotent (Chapter 11).
3. **Consensus-integrated commit:** NewSQL (Spanner, CockroachDB, TiDB) runs 2PC *where coordinator and participants are themselves Raft/Paxos groups* — no single machine's death blocks anything, because every role is replicated. 2PC's logic survives; its SPOF doesn't. The price is quorum latency per cross-shard commit (physics from Chapter 2, stage 6).

That trick — "make the fragile role a replicated state machine" — is the single most load-bearing idea in modern infrastructure, and we've now promised it three chapters in a row: leader election (4), partition maps (5), transaction coordination (6). Time to pay up. Next: time, clocks, and consensus — the chapter where distributed systems stop being folklore and become theorems.
