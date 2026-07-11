# Replication — Copies and Their Lies

**Fast overview:** replication keeps the same data on multiple machines — for durability, for failover, and for read scale (Chapter 2, stage 4). The mechanics are simple: ship the log. The pain is what copies do when you're not looking: lag, staleness anomalies, failover data loss, and split brain. This chapter covers the three architectures — single-leader, multi-leader, leaderless — and the consistency vocabulary you need to reason about all of them.

## Single-leader: the workhorse

One node is the **leader**: all writes go to it. It appends each change to its replication log (*connect the dot:* Chapter 3's WAL, now with an audience) and **followers** replay it in order, byte-for-byte arriving at the same state. Reads can go anywhere.

The first big dial: **synchronous or asynchronous** followers?

- **Sync:** leader confirms the write only after follower(s) have it. Zero-loss failover; but every write waits on the network, and one slow follower stalls everything. Nobody runs all-sync; common compromise is **semi-sync** — *one* sync follower (a guaranteed up-to-date heir), rest async.
- **Async:** leader confirms immediately, followers catch up whenever. Fast, and the default — at the price written in blood below.

**Failover** is where replication earns its complexity budget. Leader dies; the system must: detect it (timeouts — but is it dead, or slow, or partitioned? Chapter 7's opening question), promote the most-caught-up follower, and repoint everyone. Two demons:

- **Lost writes:** with async replication, the dead leader had writes nobody else received. GitHub's classic 2012 incident made this famous. You either accept small loss windows or pay sync latency — pick per system, on purpose.
- **Split brain:** the "dead" leader was merely partitioned, and now two leaders accept conflicting writes. Proper cure: promotion must go through **quorum/consensus** (Chapter 7 — Raft exists almost exactly for this), plus fencing tokens so a zombie leader's writes are rejected.

## The lag anomalies: what stale reads feel like

Async followers run seconds (or, under load, minutes) behind. Three named anomalies — learn them as *user stories*, because that's how they'll be reported to you:

- **Read-your-own-writes violation:** user posts a comment (→ leader), refreshes (→ stale follower), comment is *gone*. Panic, duplicate post. Fix: **read-your-writes consistency** — route a user's reads to the leader briefly after they write (track "wrote at T; use leader until followers pass T"), or session-pin.
- **Non-monotonic reads:** two refreshes hit differently-lagged followers; a comment appears, then *disappears*. Time ran backward. Fix: **monotonic reads** — pin each session to one replica (consistent hashing of user→replica, Chapter 5's tool).
- **Causality inversion:** question replicates slower than its answer; readers see the reply before the question. Fix: **consistent-prefix reads** / causal ordering — hard in general (Chapter 7's ordering problem in miniature).

These are the **weak/eventual-consistency** anomalies. The strong end of the spectrum — **linearizability**, "the system behaves as if there's one copy" — costs coordination on every operation (Chapter 7 prices it exactly). The engineering skill is not choosing "strong everywhere" (slow) or "eventual everywhere" (buggy) but *labeling each read path* with the weakest consistency its user story tolerates.

## Multi-leader: write anywhere, merge later

Leaders in several regions, each accepting local writes, replicating to each other async. Wins: local write latency worldwide, region-outage survivability (Chapter 2, stage 6), offline-first clients (your phone's calendar is a leader!). The bill: **write conflicts** — two regions edit the same record concurrently, and *there is no ground truth about which came first* (clocks can't be trusted to order events across machines — Chapter 7 will prove this, not just assert it).

Conflict handling, worst to best:

- **Last-writer-wins (LWW):** compare timestamps, drop the loser *silently*. Simple; loses data by design; Cassandra's default and the cause of a thousand quiet bugs.
- **Application merge:** surface both versions (like git); the app or user resolves.
- **CRDTs** — data structures (counters, sets, sequences) whose concurrent updates merge deterministically by construction; the mathematically honest option where it fits (collaborative editors, carts, counters; the tech behind Figma-style local-first sync, which DDIA's 2026 second edition now covers as a first-class topic).

Rule of thumb: avoid multi-leader on the same records; use it where writes naturally partition by geography/user and conflicts are rare or mergeable.

## Leaderless: quorums instead of a boss

The Dynamo family (Cassandra, Riak, and DynamoDB's ancestry): no leader; a client (or coordinator) writes to **N** replicas, considers success at **W** acks; reads query **R** replicas and take the newest version. If

```
W + R > N        (e.g. N=3, W=2, R=2)
```

read and write sets *overlap*, so a read touches at least one node with the latest value. Behind the scenes: **read repair** (fix stale replicas noticed during reads) and **anti-entropy** (background sync via Merkle trees); **hinted handoff** takes writes for a down node and delivers later.

Tunable per query: W=1 for fast fire-and-forget telemetry; W=quorum for things that matter. But be precise about what quorums do **not** give you: overlap is not linearizability (concurrent writes can interleave so different readers disagree on the winner; sloppy quorums weaken it further; version reconciliation needs vector clocks or LWW with all its sins). Quorums give you *high availability with bounded staleness*, not one-copy behavior. When interviewers ask "is R+W>N strongly consistent?" the accurate answer is "no — it's overlap, not consensus" (Chapter 7 supplies the real thing).

## Choosing, and the map forward

| Need | Choose |
|---|---|
| default OLTP, clear semantics | single-leader (+ semi-sync heir, consensus-backed failover) |
| multi-region local writes, mergeable data | multi-leader + CRDTs/app merge |
| always-writeable, per-query tunable, AP-leaning | leaderless quorums |

And notice what every architecture in this chapter kept doing: *shipping an ordered log of changes and replaying it*. The log ordered by **one** leader was what made single-leader simple; the lack of a single order is exactly what made multi-leader and leaderless messy. So two threads now dangle: **who decides the order when machines disagree?** — consensus, Chapter 7 — and **what if the ordered log itself were the product?** — Kafka, Chapter 9. First, though: the data got too big for any one leader at all. Sharding.
