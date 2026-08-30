# Why Git-Shaped, Specifically

**Fast overview:** "Git for X" is usually a bad idea wearing a good idea's clothes. Here it is a real answer, but only because five specific mechanics each solve a specific, named failure of the naive version. Just as important is the list of git features deliberately left out, and the reason they are all the same reason.

## The naive version and how it dies

The obvious implementation of agent memory is a markdown file per repo that sessions append to. It fails in a completely predictable way and it fails fast.

Six sessions independently discover that a page-text read straight after a navigation returns the previous page. Six sessions each append a line saying so. Now the file has six near-identical lines, worded differently. There is no way to tell that these are one fact observed six times rather than six facts, so there is no way to rank them, so the file has to be read in full or not at all. Within a month it is long enough that it is not read at all.

Everything below is a fix for a failure of that shape.

## The five mechanics

| git concept | here | the failure it prevents |
|---|---|---|
| **blob**, content-addressed | **entry**, id = sha256 of its canonical payload | The six-lines problem. The same claim from six sessions collapses to one entry seen six times, and that count becomes the ranking signal. Without this the whole thing is unreadable within a month. |
| **tree** | **scope state**, folded from the log | "What do I know about job-ops" in one read, not a replay of history. This is what makes a session-start digest affordable at all. |
| **commit** | **checkpoint** with a parent | Ordering and provenance, and it makes "what changed since yesterday" a *diff* rather than a search. The day-window view falls out for free. |
| **ref** | **scope head**, one per repo | Session start costs one read regardless of how much history has accumulated. |
| **revert / notes** | **correction**: refute and amend append, never edit | A memory that turns out wrong keeps its place with the correction attached, which is worth more than a gap. |

The first row is the load-bearing one. Content addressing is what turns a pile into a ranked list, and the ranking is what makes a budget possible, and the budget is what makes the whole thing readable. Take out content addressing and the rest collapses.

## What "content-addressed" means in practice

An entry's id is the sha256 of a canonical payload containing exactly four things: kind, scope, the normalised claim, and the sorted anchors. Not the reasoning, not the confidence, not the timestamp, not the session. Those are *observations about* the claim and are allowed to differ between sightings.

The normalisation is deliberately timid: lowercase, collapse whitespace, strip trailing punctuation. Nothing cleverer. Stemming or stopword removal would start collapsing claims that are genuinely different, and a false merge is worse than a duplicate, because it silently attaches one claim's confirmations to another's.

The result is that a session in x-ops writing *"The stale read looks completely plausible"* and a session in hack-ops writing *"the stale read looks completely plausible."* produce the same key. Two sightings, one memory.

## Counting confirmations honestly

Sightings are counted **by distinct session, never by record.**

This sounds like a detail and it is not. The digest ranks on confirmation count. If confirmations were counted per record, an entry could climb to the top of every future session's context by being mentioned twice in one enthusiastic afternoon. Sessions are the only unit of independent observation available, so sessions are the unit.

This is also why the session identifier from the previous chapter is load-bearing rather than convenient. Without it there is no way to distinguish "two sessions agree" from "one session repeated itself", and the ranking signal would lie in exactly the direction that inflates it.

## What was deliberately not built

Merge. Three-way diff. Packfiles. Remotes. Branching topology.

Every one of those exists so that **many humans can edit the same source file concurrently**. That is not what is happening here. There is one machine, writes are append-only, and the resolution rule is last-writer-wins with history preserved. Concurrency needs exactly one lock and a re-read of the head inside it.

The concurrency is real, incidentally, not theoretical. Six Claude sessions were live on this machine while this was being written. Ten concurrent writers were tested: one linear chain, no forks, no orphaned parents, no corrupt lines. That is the whole concurrency story, and building for merges would have doubled the code for nothing.

This paragraph exists in the system's own `CLAUDE.md` for a specific reason. Someone will eventually notice the missing pieces and try to "complete" the git model. The reason they are missing needs to be written down where that person will find it.
