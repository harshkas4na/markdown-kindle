# Stream Processing

Batch processing (previous chapter) treats input as a bounded file that's already fully present before the job starts. **Stream processing** reframes the same core operations — filter, join, aggregate — as continuous, low-latency computation over an **unbounded** input: events that keep arriving indefinitely, processed incrementally as they show up rather than all at once after the fact.

## Event streams and message brokers

The simplest way to move an event from a producer to a consumer is directly — but that requires both ends to be online simultaneously and couples their availability together. A **message broker** sits in between as a durable middleman: producers publish without needing a consumer ready right now, consumers can be slow or temporarily offline without losing messages, and multiple independent consumers can subscribe to the same stream.

Two meaningfully different broker designs:
- **Traditional message queues** (AMQP/JMS-style): a message is removed once it's been acknowledged by a consumer. Good for distributing discrete tasks across a worker pool, but awkward for replaying history or supporting multiple independent consumer groups without duplicating every message per group.
- **Log-based brokers** (Kafka-style): messages form an append-only, durable, replayable log, partitioned by key. Consumers simply track their own read offset into the log, which makes replaying history — or adding an entirely new consumer months later that wants to process everything from the beginning — trivial rather than a special case. The tradeoff: to preserve per-key ordering, related messages generally need to land in the same partition, which reintroduces the same key-choice/skew considerations covered under partitioning.

## Change Data Capture (CDC)

**CDC** treats a database's own internal write-ahead/replication log as an event stream that other systems can subscribe to. Instead of periodically polling or bulk-exporting the database (slow, all-or-nothing, and always somewhat stale by the time it finishes), downstream systems — a search index, a cache, an analytics store — subscribe to a live stream of every insert/update/delete as it actually happens, staying continuously synchronized instead of catching up in batches. This is the batch chapter's "derived data as a reproducible view of the input" idea, just applied continuously rather than on a periodic schedule.

## Event sourcing

Rather than storing only the current state of a record and overwriting it in place, **event sourcing** stores the full, append-only log of state-*changing events* as the actual source of truth — current state (and any other useful view) is derived by replaying and folding over that event log. This gives a complete audit trail essentially for free, and it means an entirely new view of the data can be built later just by replaying history against new logic — the tradeoff is that the application has to model logical corrections and deletions as *new events* layered on top of history, rather than simply erasing or overwriting data.

## What you actually do to events as they arrive

- **Simple per-event transformations** — no memory of prior events needed (enrich a record, filter out ones that don't match a condition).
- **Windowed aggregations** — genuine state is needed (e.g. "requests per minute"), and the surprisingly hard part is defining what "per minute" even means once events can arrive late or out of order. Three common window shapes: **tumbling windows** (fixed-length, non-overlapping), **hopping/sliding windows** (fixed-length but overlapping), and **session windows** (grouped by gaps of inactivity rather than fixed clock boundaries). Underneath all three sits a sharper distinction: **processing time** (when the stream processor happened to see the event) versus **event time** (when the event actually occurred). Using processing time is simpler to implement, but it's wrong the moment there's any delay between an event happening and it arriving — network delay, retries, buffering — which in real systems is essentially always true to some degree.
- **Stream-stream and stream-table joins** — joining two live, unbounded streams requires buffering and waiting for a plausible match within some bounded time window, since there's no way to know for certain whether a matching event is still coming. Joining a stream against a mostly-static table (e.g. enriching a click event with the clicking user's current profile) instead requires keeping that table itself continuously up to date — commonly via CDC, tying this section back to the earlier one.

## Fault tolerance for streams

Batch processing's fault-tolerance trick — "just rerun the whole job on failure" — doesn't translate cleanly to a stream that never ends. What's needed instead is **exactly-once semantics**: a guarantee that a processed event affects downstream state exactly once, even across a crash-and-retry. Two ways this is actually achieved: designing operations to be **idempotent** (applying the same operation twice produces the same result as applying it once, so an accidental retry is harmless), or committing "the offset just processed" and "the resulting output" **atomically together** — so a crash before that atomic commit simply means the event gets reprocessed from scratch next time (safe, because nothing partial was ever visible), and a crash after it means the event is never touched again.

## Takeaways

- Stream processing isn't "batch processing but faster" — the unbounded nature of the input forces genuinely different handling of state, windowing, and fault tolerance, not just a smaller latency budget.
- Event time vs. processing time is not a pedantic distinction — using processing time when correctness actually requires event time is one of the most common, hard-to-notice bugs in real stream processing systems, because it looks correct under low load and quietly drifts wrong the moment there's any lag.
- CDC and event sourcing are the same underlying idea (a log of changes as the real source of truth) applied at two different layers — one treats an existing database's internals as the log, the other makes the log the primary data model from the start.
