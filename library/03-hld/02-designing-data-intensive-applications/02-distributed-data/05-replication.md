# Replication

**Replication** means keeping the same data on multiple machines, connected over a network. Three reasons to do it: put data physically closer to users (lower latency), keep the system working even if some machines die (higher availability), and spread read traffic across more machines (higher read throughput). Copying data once is trivial — the entire chapter is about the hard part: keeping every copy correct as the data keeps *changing*.

There are three fundamental approaches to deciding who's allowed to accept writes.

## Single-leader replication

One node (the **leader**, aka primary/master) accepts all writes. It appends every write to a **replication log**, which is streamed to the other nodes (**followers**, aka replicas/slaves), each applying the same writes in the same order. Reads can be served by the leader or, for scale, by any follower.

**Synchronous vs. asynchronous replication** is the key dial: in synchronous replication, the leader waits for a follower to confirm it has the write before acknowledging success to the client — a strong durability guarantee (a confirmed write genuinely exists on ≥2 nodes), at the cost that if that follower stalls, the leader stalls too. In fully asynchronous replication, the leader acknowledges immediately and ships the write to followers in the background — fast, but if the leader fails before a follower catches up, an already-acknowledged write can simply be lost. Most real systems use **semi-synchronous** replication: one follower is synchronous (guaranteeing at least one up-to-date copy exists) and the rest are async, balancing durability against not letting one slow node stall all writes.

**Setting up a new follower** can't be done by copying files off a live leader — the data is constantly changing mid-copy. The standard approach: take a consistent snapshot of the leader at a known position in its replication log, copy that snapshot to the new follower, then have the follower replay every log entry since that position — converging it to current state without ever needing to pause the leader.

**Handling failures**: a follower that falls behind or crashes can simply reconnect and resume from its last known log position (**catch-up recovery**) — the easy case. Leader failure is the hard case, called **failover**: some other node has to notice the leader is unreachable (usually via a timeout, which is itself a tradeoff — too short causes unnecessary failovers on a merely slow leader, too long means longer real downtime), a follower has to be promoted to the new leader, and clients/other followers need to be redirected. The genuinely dangerous failure modes here: **split brain** (two nodes both believe they're the leader and both accept writes, which can silently diverge or corrupt data), and losing writes that the old leader had acknowledged but never replicated before it died.

## Multi-leader replication

Multiple nodes each accept writes, and replicate changes to each other. This is a meaningfully different shape from single-leader, used for specific situations: multi-datacenter deployments (a local leader per datacenter means writes don't cross a continent before being acknowledged, and the system tolerates an entire datacenter going down), clients that need to keep working offline (a laptop calendar app is effectively its own "leader" while disconnected, syncing changes once reconnected), and real-time collaborative editing (each participant's local edits are applied immediately and reconciled with everyone else's).

The cost of allowing more than one place to accept writes is **write conflicts** — two leaders each accept a concurrent write to the same record, and now the system has two divergent values to reconcile. Strategies for resolving this:
- **Last-write-wins (LWW)**: pick whichever write has the later timestamp and silently discard the other. Simple, but it means data loss is a *designed-in* behavior, not an edge case — dangerous for anything where losing a write matters.
- **Convergent merge logic**: custom application code (or **CRDTs** — conflict-free replicated data types, structures specifically designed so concurrent updates always merge into the same result regardless of order) that combines both writes into one sensible outcome instead of picking a winner.
- **Avoid the conflict entirely**: route all writes for a given record consistently to the same leader (e.g. "this user's writes always go to their home region"), which sidesteps concurrent-write conflicts for that record at the cost of losing multi-leader's full flexibility.

## Leaderless replication

Any replica can accept a write (the Dynamo-style model — Cassandra, Riak, Voldemort). A client (or a coordinating node) sends a write to several replicas in parallel and considers it successful once enough of them acknowledge; reads similarly query several replicas in parallel and use per-value version information to determine which response is current.

**Quorums** formalize "enough": with `n` total replicas, require `w` replicas to acknowledge a write and `r` replicas to respond to a read. If `w + r > n`, every read is guaranteed to overlap with at least one replica that saw the latest write — a useful guarantee, but only probabilistically safe in practice, because real systems still have edge cases around concurrent writes, replicas that silently fell behind, and the exact timing of when a "stale" replica gets corrected.

Two mechanisms keep leaderless replicas from drifting apart permanently: **read repair** (when a read notices one replica returned a stale value, it writes the correct value back to that replica on the spot) and **anti-entropy** (a background process that continuously compares replicas and propagates any differences, independent of read traffic). To stay *available* even during a network partition, some systems use **sloppy quorums**: if the "correct" home replicas for a key aren't reachable, the write is accepted by whichever `w` nodes *are* reachable instead, and later handed off to the correct nodes once reachable again (**hinted handoff**) — trading strict quorum guarantees for availability during a partition.

## Consistency guarantees that actually matter day to day

Replication lag creates real, visible bugs unless you deliberately guard against them:

- **Read-your-writes consistency**: a user should always see their own just-made write, even if it hasn't reached every replica yet — typically fixed by routing a user's reads for their own data to the leader (or a replica known to be caught up).
- **Monotonic reads**: a user should never see data go *backwards in time* — e.g. seeing a new comment, refreshing, and having it disappear because the refresh happened to hit a more-lagged replica. Fixed by consistently routing a given user's reads to the same replica.
- **Consistent prefix reads**: if writes happened in a particular causal order, every reader should see them in that same order — this becomes a real problem specifically in partitioned systems, where causally related writes can land on different partitions with independently varying lag, so nothing guarantees they're observed in the "sent" order without extra work.

## Quick reference

| Approach | Write availability during a partition | Conflict handling | Typical use |
|---|---|---|---|
| Single-leader | Writes unavailable if leader unreachable | None needed (single writer) | Default choice for most OLTP systems |
| Multi-leader | Each region keeps accepting writes independently | Required — LWW, CRDTs, or app merge logic | Multi-datacenter, offline-capable, collaborative apps |
| Leaderless | Degrades gracefully via sloppy quorums | Required — version vectors, read repair | High-availability key-value stores (Dynamo-style) |

## Takeaways

- Replication trades off in one consistent direction: the more nodes that are allowed to accept writes independently, the more availability you get during failures/partitions, and the more conflict-handling machinery you now owe the system.
- "My database replicates" says nothing about whether it's sync or async — and that single detail is exactly what determines whether an acknowledged write can be silently lost during a failover.
- Replication-lag bugs (stale reads, time appearing to go backwards) are not exotic — they're the default behavior of any asynchronously replicated system, and need to be explicitly designed against per use case.
