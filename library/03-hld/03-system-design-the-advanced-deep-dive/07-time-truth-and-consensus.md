# Time, Truth, and Consensus

**Fast overview:** the spine of the book. Why distributed systems can't trust clocks or timeouts; what linearizability really promises and costs; what CAP actually says; and how a cluster of unreliable machines nonetheless agrees on one truth — consensus, taught through Raft (leader election, log replication, quorum overlap). Ends by cashing the IOUs from Chapters 4–6: failover, partition maps, and distributed commit all reduce to this chapter.

## The enemy: partial failure

A single machine fails honestly: it stops. A distributed system fails *ambiguously*: you sent a request and got no reply — is the remote node dead? Slow? Is the network dropping your packets, or its replies? Did it do the work and lose the ack? **You cannot distinguish these from the outside.** All you have are timeouts, and a timeout is a guess. Every hard theorem and every clever protocol in this chapter descends from this one epistemic hole.

Worse, even *your own* process lies about time: garbage-collection pauses, VM migrations, and overloaded schedulers can freeze a process for seconds mid-instruction. A node can check "I hold the lease," pause 15 seconds, and act on a lease that expired — the classic zombie-leader bug. (Defense: **fencing tokens** — every lease grant carries an increasing number; storage rejects writes bearing stale tokens. Ordering, not time, is the cure — a pattern to notice.)

## Clocks: why timestamps can't order events

Machines sync clocks via NTP, achieving tens-of-milliseconds accuracy on a good day — skew, drift, leap-second smearing, and misconfiguration are routine. So when node A stamps a write 14:02:01.005 and node B stamps a *causally later* write 14:02:00.998, last-writer-wins (Chapter 4) silently destroys the later write. **Wall clocks cannot establish order between machines.** Alternatives, cheapest first:

- **Monotonic clocks** — good for measuring *durations* on one machine, meaningless across machines.
- **Lamport / logical clocks** — counters that piggyback on messages (`local = max(local, received) + 1`), guaranteeing: if X caused Y, then stamp(X) < stamp(Y). Order without physics; the theoretical basis for "happened-before"; vector clocks extend this to *detect* concurrency (Chapter 4's version reconciliation).
- **TrueTime** (Spanner) — Google's atomic-clock-and-GPS hardware exposes time as an *interval* [earliest, latest]; Spanner **waits out the uncertainty** (~few ms) before commit, buying globally consistent timestamps with latency. The exception that proves the rule: it took dedicated hardware plus deliberate slowdown to make wall-clock time trustworthy.

## Linearizability: what "strongly consistent" actually means

**Linearizable** = the system behaves as if there were **one copy** of the data, and every operation takes effect atomically at some instant between its start and finish. Once any read returns the new value, all later reads do. It's the consistency your intuition assumes — and Chapter 4 showed how replication quietly breaks it.

What genuinely needs it: locks and leader election (a lock that two nodes can hold is not a lock), uniqueness constraints (usernames, seat 14C), cross-channel consistency (write via API, read via webhook). What doesn't: almost everything else users see — feeds, timelines, counters tolerate bounded staleness happily (Chapter 4's labeling discipline).

Its price is coordination — and here is **CAP**, said precisely for once: when a network **P**artition happens (and it will), a system must choose to remain **C**onsistent (linearizable — some nodes must refuse to answer) or **A**vailable (every node answers — answers may conflict). Not a three-way menu; a forced choice *only during partitions*. The everyday tradeoff is the sharper **PACELC** refinement: during Partition, A vs C; **E**lse, **L**atency vs **C**onsistency — you pay for linearizability in round trips *every day*, partition or not. That's the real reason defaults everywhere are weaker than you'd like.

## Consensus: manufacturing one truth

So: no trustworthy clocks, no reliable failure detection — yet Chapters 4–6 demanded a cluster agree on *exactly one* leader, *one* partition map, *one* commit verdict. **Consensus** is the primitive: nodes propose values; all deciding nodes decide the *same* value; decisions are final; progress continues as long as a **majority** is alive and talking. (FLP impossibility says even one crashy process makes deterministic consensus impossible in a fully asynchronous system — practical protocols dodge it with timeouts, accepting they may stall, never that they'll disagree.)

**Raft** (2014, designed explicitly to be teachable — the field ran on Paxos folklore before it) in one honest page:

- **Roles and terms.** Each node is follower, candidate, or leader. Time divides into numbered **terms**, each with at most one leader. Terms are Lamport clocks in disguise — stale leaders are detected by their smaller term number, not by wall time.
- **Leader election.** Followers expect heartbeats; a timeout (randomized, to avoid split votes) makes a follower a candidate: it increments the term and requests votes. **Majority votes → leader.** One vote per node per term ⇒ two leaders in one term is arithmetically impossible.
- **Log replication.** All writes go through the leader, which appends to its **log** and replicates entries; an entry acknowledged by a **majority** is *committed* and applied to the state machine. (*Connect the dot:* Chapter 3's WAL, Chapter 4's replication log — same object, now with a quorum guarding it. "Replicated state machine" = everyone applies the same log in the same order = everyone computes the same state.)
- **Safety via quorum overlap.** Any two majorities share a node. So a new leader's election quorum necessarily includes someone who saw every committed entry — and Raft's voting rule (only vote for candidates whose log is at least as up-to-date) ensures the *most complete* candidate wins. Committed entries survive any sequence of crashes and elections. That overlap argument is the entire magic of consensus; internalize it and Raft's dozens of rules become bookkeeping.

Split brain, resolved properly at last: the old leader may keep *thinking* it leads, but it cannot commit anything (no majority will follow a stale term), and fencing rejects its writes downstream. Compare Chapter 4's ad-hoc failover pain — this is what "promotion goes through consensus" buys.

## Where consensus lives in your stack

You almost never implement Raft; you *rent* it:

- **etcd** (Raft) — Kubernetes' brain: all cluster state, leases, elections.
- **ZooKeeper** (ZAB, Paxos-family) — Kafka's old controller, HBase, Hadoop-era coordination. Kafka replaced it with **KRaft** — Raft embedded in Kafka's own controllers (Chapter 9).
- **Consul**, cloud lock services, and inside every NewSQL database: **one Raft group per shard** (CockroachDB/TiDB/Spanner) — leader election, replication, *and* the 2PC coordinator (Chapter 6's escape hatch #3) all made non-blocking by replicating every role.

Usage pattern: keep consensus systems *small and boring* — a 3/5-node cluster storing kilobytes of critical coordination state (locks, leaders, maps, config), while bulk data flows through Chapter 4/5 machinery configured *by* it. Majority quorums mean: 5 nodes tolerate 2 failures; writes cost a round trip to the median follower — which is why you don't put your data plane through it.

The book's central IOUs are now paid. What remains is applying the toolkit: making reads fast (caching), making writes flow (logs and streams), reshaping data for every consumer (derived data), guarding the front door, and surviving bad days. The fun half starts now.
