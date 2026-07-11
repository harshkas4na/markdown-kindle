# Logs, Queues, and Streams — Kafka and Friends

**Fast overview:** the append-only log has been hiding inside every chapter — the WAL (3), the replication stream (4), Raft's replicated log (7). This chapter makes it a public, first-class piece of architecture: message queues vs event logs, Kafka's mechanics (partitions, consumer groups, offsets, KRaft), the delivery-guarantee ladder ending at the truth about "exactly-once," and the patterns built on top — CDC, the outbox, event sourcing. This is the chapter that ties the book together; Chapter 10 then builds the full derived-data worldview on it.

## Two species: queues and logs

**Message queues** (RabbitMQ, SQS, ActiveMQ): a *task distribution* tool. Producer enqueues jobs; competing workers each grab one; on ack it's **deleted**. Semantics: each message consumed once (by someone), redelivered on worker failure, per-message routing/priority/delay. The natural home of Chapter 2's stage-5½ background work.

**Event logs** (Kafka, Pulsar, Kinesis, Redpanda): a *record of what happened*. Producers append; the log **retains** entries (days, or forever) regardless of who read them; each consumer tracks its own **offset** — its bookmark in the log. Consequences that queues can't offer: many independent consumers reading the *same* events at their own pace; **replay** (reset your offset, reprocess history — the killer feature: new services bootstrap from the past, bugs get fixed by reprocessing); and ordering within a partition.

Choose by verb: "do this job" → queue; "this happened" → log. Modern default has drifted heavily toward logs, because "this happened" turns out to be the more fundamental statement (Chapter 10 completes that argument).

## Kafka mechanics, the load-bearing parts

A **topic** is split into **partitions**; each partition is — literally — an append-only file (Chapter 3's dumbest-database, now a product; sequential I/O + zero-copy sends is why Kafka casually moves GB/s per broker).

- **Ordering:** guaranteed *within a partition only*. Producers choose partitions by key (`hash(user_id)` → all of that user's events in order — Chapter 5's hash partitioning verbatim). No key → round-robin, no order.
- **Consumer groups:** consumers sharing a group-id split the partitions among themselves (a partition has exactly one consumer per group) — parallelism up to the partition count, so *partition count is a capacity decision you make early*. Different group-ids see everything independently — that's the fan-out to N systems.
- **Offsets:** each group periodically commits "processed through offset X per partition" back to Kafka. Crash → rebalance → new assignee resumes from the last commit. The gap between "processed" and "committed" is exactly where delivery guarantees live (below).
- **Replication:** each partition has a leader broker + followers; producers can require `acks=all` (in-sync replicas have it) before success — Chapter 4's semi-sync replication, verbatim.
- **KRaft:** cluster metadata (partition→broker maps, controller election) historically lived in ZooKeeper; modern Kafka runs **Raft among its own controllers** (Chapter 7, cashing in again). One less system to operate.

## The delivery-guarantee ladder

Where can a message be lost or doubled? Producer→broker (retry on unacked send ⇒ possible duplicate append; fix: **idempotent producer** — sequence numbers per producer/partition, broker dedups). Broker (replication + acks). Consumer: the eternal two-step — process the message and commit the offset, *in which order?*

- Commit **then** process → crash between ⇒ message skipped: **at-most-once**.
- Process **then** commit → crash between ⇒ message reprocessed: **at-least-once**. The sane default.
- **"Exactly-once"** — the honest version: delivery cannot be exactly-once (Chapter 7's ambiguous failures guarantee redelivery somewhere), but **exactly-once *processing effects*** are achievable two ways: (1) *transactionally couple* the side effect with the offset commit (Kafka transactions do this when the effect is "write to another Kafka topic" — the Streams model; or store offsets in the same DB transaction as your state update); (2) make the effect **idempotent**, so duplicates are harmless — dedup keys, upserts, "set state to X" rather than "increment" (Chapter 11 gives idempotency its full treatment; it is the cheaper and more robust half).

Say it the way practitioners do: *at-least-once delivery + idempotent handling = effectively exactly once.* Interviewers who hear that sentence relax visibly.

## Patterns on top of the log

**CDC — change data capture.** Tail the database's own WAL (Chapter 3!) and publish every committed row-change as an event (Debezium is the standard tool). Now anything — cache invalidators (Chapter 8's event-driven option), search indexers, warehouses, other services — follows *the database's actual truth*, in commit order, without the DB knowing or caring. This is Chapter 4's replication stream, generalized from "keeps followers in sync" to "keeps the *whole company* in sync."

**The outbox pattern.** The dual-write bug: service updates its DB *and* publishes an event — one succeeds, the other fails, and downstream diverges forever. Fix: within the *single* DB transaction, also insert the event into an `outbox` table; a relay (or CDC on the outbox) publishes it. Atomicity borrowed from the local transaction (Chapter 6), reliability from at-least-once relay + consumer idempotency. Memorize this one; it's asked about constantly *because production keeps re-learning it*.

**Event sourcing.** Radical version: don't store current state at all — store the *events* (`AccountOpened`, `MoneyDeposited`), derive state by folding over them, snapshot for speed. Perfect audit history, temporal queries, natural fit for domains that *are* ledgers. Costs: schema evolution of eternal events, unfamiliar queries — usually paired with **CQRS** (write side = event log; read side = projections built from it, which is Chapter 10's whole worldview in miniature). Apply within bounded domains (payments, orders), not as a religion.

**Stream processing** — the standing-query layer over logs (Kafka Streams, Flink): windowed aggregations (5-minute counts — with **watermarks** to decide when late events stop counting), stream joins, materialized views kept continuously fresh. State lives in local RocksDB (Chapter 3!) checkpointed for recovery. Flink is 2026's heavyweight default; Streams the embedded lightweight.

## When *not* to Kafka

A cron job, a Postgres table used as a work queue (`SELECT ... FOR UPDATE SKIP LOCKED` — genuinely fine to ~1k jobs/sec), Redis streams, or SQS carry a startup's async needs with a tenth of the operational mass. The log-as-spine architecture earns its keep at *many-consumers, many-producers, replay-matters* scale. Before that, it's résumé-driven design — the same disease as Chapter 2's stage-6-at-stage-0.

The log now connects storage (3), replication (4), partitioning (5), and consensus (7) into one picture, and it's carrying every copy the earlier chapters created. One question remains: if everything downstream is rebuilt from the log anyway… what *is* a database, really? Chapter 10 turns the database inside out.
