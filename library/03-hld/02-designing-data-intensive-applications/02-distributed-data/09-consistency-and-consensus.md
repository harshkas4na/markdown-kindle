# Consistency and Consensus

The previous chapter's message was bleak: networks lie by omission, clocks can't be trusted, and a paused process is indistinguishable from a dead one. This chapter is the payoff — the actual toolkit for building systems that behave predictably *anyway*, the strongest guarantees the industry knows how to build, and the fundamental limit on how strong those guarantees can be while staying fast.

## Linearizability

**Linearizability** is the strongest single-object consistency guarantee: the system behaves as if there is only one copy of the data, and every operation appears to take effect atomically at one single instant somewhere between when it was invoked and when it completed. The practical consequence: the instant a write completes, every subsequent read by anyone, anywhere, is guaranteed to see that write or something newer — never a stale value, ever.

This is easy to confuse with **serializability** (chapter 7), but they're answering different questions: serializability is about transactions not interleaving badly across potentially *many* objects; linearizability is about real-time recency on a *single* object/value. A system can have either property without the other — they're orthogonal, not points on the same scale.

Why you'd want linearizability: leader election (only one node should ever believe it's the leader), uniqueness constraints (a username can't be claimed twice), locks. Why it's expensive: providing it requires genuine coordination between nodes on every operation — you can't just answer a read from whichever nearby replica happens to be handy, because that replica might be behind. This cost is precisely what the CAP theorem is describing.

## The CAP theorem, and why the "pick 2 of 3" framing is misleading

CAP stands for **C**onsistency (specifically meaning linearizability, not the "C" in ACID — a frequent source of confusion), **A**vailability (every request to a functioning node receives a non-error response), and **P**artition tolerance (the system continues operating despite the network dropping messages between nodes).

The actual theorem is much narrower than the popular "pick two of three" slogan suggests: it says that **while a network partition is actually occurring**, you must choose between linearizable consistency and availability for the affected nodes — you cannot have both *during that partition*. Partition tolerance itself isn't really an optional choice in a real network (partitions happen whether or not you "choose" to tolerate them), and outside of an actual partition, the consistency/availability tradeoff doesn't even apply. Treating "CAP" as a general three-way system-design framework overstates what it actually claims — it's a specific statement about behavior during network partitions, not a universal taxonomy of distributed systems.

## Ordering and causality

A **total order** places every event in a single, global sequence — which is what linearizability requires. A weaker but frequently sufficient alternative is **causal order**: only events that actually causally affect one another (a reply that references a comment) need to be seen in a consistent order by everyone; two genuinely unrelated, concurrent events don't need global agreement on which "came first," because nothing depends on their relative order. Capturing causal relationships without needing full global agreement is done with tools like **Lamport timestamps** and **version vectors** — lightweight bookkeeping that can determine "did A happen-before B" without every node needing to agree on one master clock.

**Total order broadcast** is the primitive that guarantees every node delivers the exact same sequence of messages in the exact same order — and it turns out to be provably equivalent in difficulty to solving consensus itself. This isn't a footnote: total order broadcast is the actual mechanism underneath a single-leader's replication log, underneath serializable transaction ordering, and underneath distributed lock services — many seemingly different features are, underneath, the same primitive wearing different clothes.

## Consensus, formally

**Consensus** means getting a group of nodes to agree on a single value, satisfying: **validity** (the agreed value was actually proposed by someone, not invented), **agreement** (no two nodes decide differently), and **fault tolerance** (the group still reaches a decision even if some nodes fail). A landmark result (the **FLP impossibility result**) proves this is provably *unsolvable* deterministically in a fully asynchronous system if even one node might fail — which is precisely why real consensus algorithms (**Paxos**, **Raft**, **Zab**) don't try to be purely asynchronous: they lean on timeouts and leader election, accepting a small, bounded window of unavailability during an election in exchange for guaranteed correctness once one completes.

In practice, almost nobody implements consensus from scratch per system. Instead, a dedicated coordination service (**ZooKeeper**, **etcd**) implements consensus once, carefully, and everything else — leader election, distributed locking, service discovery, cluster membership — is built as a *client* of that already-solved primitive, rather than every team reinventing (and likely getting subtly wrong) consensus on their own.

## Quick reference

| Guarantee | What it promises | Typical cost | When it's actually worth it |
|---|---|---|---|
| Linearizability | Every read sees the latest write, globally, instantly | Coordination on every op; unavailable during partitions | Leadership, uniqueness constraints, locks |
| Causal consistency | Related events seen in order; unrelated events unconstrained | Cheaper — no global coordination needed | Most application data, most of the time |
| Eventual consistency | Replicas converge *eventually*, no ordering guarantee otherwise | Cheapest; highest availability | Data where transient staleness is genuinely harmless |

## Takeaways

- Linearizability and serializability solve different problems (single-value recency vs. multi-object transaction ordering) — don't reach for one when you mean the other.
- CAP is a precise, narrow statement about behavior *during* a network partition, not a general framework for classifying every distributed system's tradeoffs — treat "we're a CP system" or "we're an AP system" claims with some skepticism about what they're actually claiming.
- Strong consistency is not free anywhere in this stack — every real system is deliberately paying for it (in latency, availability, or complexity) only where it actually matters, and defaulting to weaker, cheaper guarantees (causal or eventual) for the rest.
