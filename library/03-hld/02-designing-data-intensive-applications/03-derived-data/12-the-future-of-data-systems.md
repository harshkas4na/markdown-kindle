# The Future of Data Systems

This closing chapter pulls batch (chapter 10) and stream (chapter 11) processing together into one mental model, then zooms out past pure engineering to what building *trustworthy* data systems actually requires.

## Unbundling the database

The book's synthesis idea: stop thinking of a database as one monolithic black box, and instead think of its internal pieces — storage, indexing, caching, materialized views — as things that could be built yourself out of **streams**. A derived view (a search index, a cache, a recommendation table) is nothing more than the output of a stream processor continuously folding new events over an evolving state — and a batch job, in this frame, is simply the special case of running that same processing logic once over a *bounded* stream (a fixed snapshot instead of an ongoing feed).

This reframing has a real practical payoff: "keep this cache/index in sync with the source database" stops being an ad hoc, bolt-on synchronization problem solved with cron jobs and dual-write bugs, and becomes the exact same well-understood dataflow-and-derived-view pattern used consistently everywhere else in the book — with change data capture as the mechanism that keeps the underlying stream live.

## The Lambda architecture (an interim, imperfect answer)

One real-world compromise for needing both speed and accuracy: run the *same* logic through two separate paths — a batch path (slow, but eventually fully accurate over the complete dataset) and a stream path (fast, but only approximately correct on recent data) — and merge their outputs for querying. Kleppmann treats this as a genuine, working pattern but a deliberately awkward one: the same business logic has to be implemented and kept in sync across two different systems, and reconciling their outputs is its own ongoing source of bugs. The more satisfying direction — stream processors (like Flink) capable of handling both the low-latency and eventually-fully-correct case within one unified system — is presented as where the ecosystem was actually headed, rather than the Lambda architecture being an end-state worth committing to long-term.

## Correctness beyond "did the write commit"

As systems decompose into more services and more partitions, a single ACID transaction increasingly can't be the thing enforcing your invariants anymore — a uniqueness constraint, an ordering guarantee, or a real business rule ("don't ship an order until payment clears") frequently needs to hold *across* multiple partitions or services that no single database transaction spans. Correctness in that world has to be actively designed into the flow of events themselves — idempotent operations, fencing (chapter 8), exactly-once processing (chapter 11) — rather than assumed for free from ACID guarantees that no longer cover the whole picture.

## The responsibility that comes with these systems

The book's closing argument is deliberately non-technical: the exact same techniques that make data systems reliable and scalable — collecting detailed behavioral data, building predictive models from it, automating decisions at scale — are equally capable of being used to profile, discriminate against, or manipulate the people that data describes. An engineer who builds the pipeline carries some real responsibility for what that pipeline enables downstream, not just for its uptime and correctness. "I only built the infrastructure" is not, on its own, a complete answer when that infrastructure is what makes large-scale surveillance or unfair automated decision-making practically possible.

## Takeaways

- Every earlier chapter's tradeoff (replication lag, partition skew, isolation-level gaps, consensus cost) is an instance of one repeating shape: distributing work and data across machines and a network that can't be fully trusted — the "unbundled database via streams" idea is the cleanest tool this book offers for reasoning about that shape consistently, instead of solving it differently in every corner of a system.
- Treat the Lambda architecture as a known, working stopgap, not a target — duplicated logic across a batch and a stream path is a real, ongoing maintenance cost, and unified stream processing is the better long-term direction where it's available.
- Technical correctness (the transaction committed, the replica converged) and *responsible* correctness (what the system is actually being used to do to real people) are separate questions — this book is thorough on the first and is explicit that engineers shouldn't outsource the second to "someone else's job."
