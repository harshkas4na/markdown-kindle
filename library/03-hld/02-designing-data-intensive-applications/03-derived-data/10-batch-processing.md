# Batch Processing

Everything from replication through consensus was about **online systems**: respond to one request at a time, as it arrives, with low latency the whole point. This chapter is about a very different job done on the same underlying data — **offline/batch processing**: take a large, bounded dataset that already fully exists, run some computation over the whole thing, and produce a derived output. Same data, opposite engineering priorities: throughput over latency, minutes-to-hours runtimes are fine, and the entire input is available up front rather than trickling in.

## The Unix philosophy, scaled to a cluster

Batch frameworks are the conceptual descendants of the Unix command line: small, composable tools (`sort`, `uniq`, `grep`, `awk`) connected via pipes, each one reading and writing a uniform interface (a stream of bytes on stdin/stdout). That uniformity — not needing to know or care what produced your input or what will consume your output — is what makes wildly different tools reusable together, and it's exactly the idea batch frameworks scale from one machine's pipeline up to thousands of machines cooperating on one job.

## MapReduce, the model

**MapReduce** describes a specific shape of distributed computation, independent of any one implementation:

- **Map**: takes one input record and emits zero, one, or several key-value pairs. Mappers run in parallel across many machines, each handling one chunk of the input, with *no communication between mappers* — this isolation is deliberate and is what makes the next property possible.
- **Shuffle**: the framework groups every emitted value by key and routes each group to the reducer responsible for that key. This phase is genuinely expensive — real network transfer and disk I/O across the whole cluster — and it's the part people most often forget when reasoning about a MapReduce job's actual cost; the map and reduce steps themselves are frequently cheap by comparison.
- **Reduce**: takes all the values collected for one key and produces the final output for that key. Also parallelized, typically one worker per key-range/partition of the shuffle output.

The reason for this specific, somewhat rigid shape: because mappers and reducers are pure functions of their own local input (no shared mutable state, no side effects on other tasks), the framework can freely **retry a failed task** by simply rerunning it on a different machine, without needing to coordinate with or roll back anything else currently in flight. Fault tolerance here comes from task-level idempotent retry, not from any heroic, stateful recovery logic — a direct consequence of the map/reduce isolation constraint, not an accident.

## Joins in batch processing

Batch joins are worth understanding specifically because there's no live index to consult mid-query — everything has to be arranged in advance.

- **Sort-merge join**: both datasets are partitioned and sorted by the join key ahead of time, then matched with a single sequential scan through both — the same mechanical idea as merging two sorted lists in mergesort. No random lookups are needed anywhere, because the sort order itself guarantees matching keys arrive at the same time.
- **Broadcast hash join**: if one side of the join is small enough to fit comfortably in memory, ship a full copy of it to *every* mapper, and each mapper does an ordinary in-memory hash join locally against its chunk of the larger dataset — this entirely avoids shuffling the large side across the network.
- **Skewed joins**: a small number of keys (a viral post, a dominant product) can have wildly more matching records than everything else, which overwhelms whichever single reducer is assigned that key. The fix mirrors the hot-key fix from partitioning: split the hot key's records across several reducers and recombine the partial results afterward.

## Beyond MapReduce: dataflow engines

Later systems (**Spark**, **Tez**, **Flink**'s batch mode) generalize past MapReduce's rigid map-shuffle-reduce shape by modeling a job as an arbitrary graph of operators instead of forcing every computation through exactly one map phase and one reduce phase. Two practical wins from this: intermediate results between stages can be kept **in memory** rather than always round-tripping to disk between every map and reduce step (MapReduce's biggest real-world performance weakness on multi-stage jobs), and joins/filters/aggregations can be expressed as native operators directly, instead of being hand-built out of the map/reduce primitives the way earlier systems required.

## What a batch job's output actually represents

The typical output of a batch job is a **full, fresh replacement** of some derived dataset — a rebuilt search index, a recomputed set of recommendations, a regenerated report — written out cleanly each run rather than patched incrementally. This reflects a specific, useful mental model: derived data is treated as a **reproducible function of its input**. If a bug produced wrong output, the fix is to fix the code and simply *rerun the job* — not to hunt down and hand-patch corrupted state that's already spread across a live system. This "input is immutable, output is a pure, always-recomputable function of it" idea is the thread that connects directly into stream processing next: a stream processor is really the same idea, just run continuously instead of once.

## Takeaways

- Batch and online systems aren't different implementations of the same problem — they're solving genuinely different problems (bounded throughput-optimized computation vs. unbounded latency-optimized response), and conflating them leads to picking the wrong tool.
- The shuffle phase, not map or reduce individually, is usually where a batch job's real cost lives — reason about job cost with that in mind.
- Treating derived output as a reproducible function of immutable input (rather than mutable state to patch) is what makes batch pipelines safe to fix and rerun with confidence — worth carrying forward as a design principle even outside batch processing specifically.
