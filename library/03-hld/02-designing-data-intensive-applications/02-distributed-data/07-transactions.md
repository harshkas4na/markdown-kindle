# Transactions

Real systems fail in a lot of specific, unglamorous ways: a process crashes halfway through a multi-step write, a network connection drops mid-request, two clients modify the same record at the same time and step on each other, a machine loses power before a write finishes hitting disk. A **transaction** exists to hide this entire list of failure modes behind one simple promise to the application: either the whole group of operations happened, or none of it did, and from any other observer's point of view it looks instantaneous. That promise is usually summarized as **ACID** — but Kleppmann is deliberately skeptical of the term, because in practice it means noticeably different things across different databases.

## ACID, precisely

- **Atomicity**: not fundamentally about concurrency — it's about **abortability**. If a multi-step write fails partway through, the database guarantees none of the partial changes are visible, so the client can safely retry the whole thing without needing to reason about what state it left things in.
- **Consistency**: arguably shouldn't be a database-level guarantee at all — it's really an *application-level* property (your invariants — e.g. "account balances must sum to zero across a transfer" — stay true). The database can't know your invariants; the most it can do is provide atomicity and isolation reliably enough that the application can *enforce* consistency itself.
- **Isolation**: concurrently running transactions shouldn't see each other's half-finished work. How strictly this is actually enforced is a spectrum, not a boolean — see below, because this is where most of the real complexity and most of the real bugs live.
- **Durability**: once a transaction commits, it survives a crash. In practice this almost always means "written to a write-ahead log on disk before acknowledging," with the usual caveat that a single disk can itself fail — full durability in production really means replicated durability, not just "touched a disk once."

## Weak isolation levels, and the specific bugs each one still allows

This is the part that actually matters day to day, because most production databases do *not* default to full isolation — they default to something weaker for performance, and the specific gap between "weaker" and "full" is exactly where subtle bugs live.

- **Read committed**: the baseline most databases guarantee by default. It prevents **dirty reads** (seeing another transaction's uncommitted writes) and **dirty writes** (overwriting another transaction's not-yet-committed writes). It does *not* prevent **non-repeatable reads** — reading the same row twice within one transaction can give two different answers if someone else committed a change in between.
- **Snapshot isolation** (often labeled "repeatable read"): each transaction reads from a consistent snapshot of the database taken at the moment it started, so it never observes any concurrent commits at all — fixing non-repeatable reads outright. Implemented via **MVCC** (multi-version concurrency control): the database keeps multiple versions of each row, each tagged with the ID of the transaction that created or deleted it, and every transaction is shown exactly the versions that were visible as of its own start time. This still does not prevent **write skew**.
- **Write skew** is the genuinely sneaky anomaly, because neither transaction directly overwrites the other's write, so naive conflict detection misses it entirely. Classic example: two doctors are both on call; each independently checks "is at least one other doctor still on call before I go off," both see the other still listed, both commit "I'm off call" — and now nobody's on call, an invariant neither transaction could see was being violated, because each only read the *other's* state, not their own write's effect on the *combined* result. Snapshot isolation cannot catch this because there's no direct write-write conflict to detect.
- **Serializable isolation** is the only level that guarantees transactions behave *as if* they ran one at a time, in some order, with no anomalies at all — including write skew. Three real ways to achieve it:
  - **Actual serial execution**: run transactions strictly one at a time on a single thread. Sounds naively slow, but if transactions are short and the working set fits in memory, this can outperform locking-based approaches — the actual justification behind single-threaded engines like early Redis and VoltDB.
  - **Two-phase locking (2PL)**: readers block writers and writers block both readers and writers, via shared/exclusive locks held until commit. Correct, but kills concurrency badly under contention and is prone to deadlocks.
  - **Serializable snapshot isolation (SSI)**: an optimistic approach — transactions run concurrently under ordinary snapshot isolation (fast, no blocking), while the database tracks read/write dependencies in the background; if a transaction's snapshot turns out to have been invalidated by a conflicting concurrent commit, it's aborted and the client retries. This gets serializability's full correctness with much better throughput than 2PL under most real workloads, which is why it's the modern preferred approach where available.

## Quick reference: which anomalies survive at each level

| Isolation level | Dirty reads | Dirty writes | Non-repeatable reads | Write skew |
|---|---|---|---|---|
| Read committed | Prevented | Prevented | Possible | Possible |
| Snapshot isolation | Prevented | Prevented | Prevented | Possible |
| Serializable | Prevented | Prevented | Prevented | Prevented |

## Takeaways

- "This database supports transactions" tells you almost nothing on its own — the actual guarantee ranges from "barely stronger than nothing" to "fully serializable," and the difference is a specific, named isolation level, not a marketing checkbox.
- Most production databases default to something weaker than serializable, on purpose, for throughput — which means write skew is a live risk in ordinary application code unless you either explicitly request serializable isolation or design around it (e.g. `SELECT ... FOR UPDATE`-style explicit locking).
- Atomicity is really about safe retries after partial failure, not about concurrency — don't confuse it with isolation, which is the concurrency guarantee.
