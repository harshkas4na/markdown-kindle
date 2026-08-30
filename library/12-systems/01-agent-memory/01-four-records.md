# Four Records, and the One That Was Missing

**Fast overview:** Before building a fifth place to write things down, it is worth being precise about what the existing four already own. They turn out to own everything except the one thing that matters here. This chapter is the boundary argument, including the strongest counter-argument against building anything new at all.

## What already exists

| Record | Owns | Audience | Leaves the machine? |
|---|---|---|---|
| git history | what changed in the files | anyone | yes, on push |
| `~/.lifelog` | what Harsh built, learned and decided | him, via five sink digests | digests do, one is a public portfolio |
| `CLAUDE.md` | the stable contract for a repo | every session | yes, committed |
| `builder-ops/findings.md` | curated judgement about what to change | him | private repo |
| **agent-memory** | **what the agent found out, and what is half-done** | **the next session** | **never** |

Read down the "owns" column and the gap is obvious once stated. Git owns the diff. lifelog owns the human narrative. `CLAUDE.md` owns the rules. `findings.md` owns the decisions about what to change. Nothing owns *experience*: the accumulated, provisional, often-wrong knowledge that a session builds up about a repo in the course of working in it and then discards.

## Why not lifelog, in detail

lifelog is the closest neighbour and the one worth arguing with properly, because it already has all the machinery. It is an append-only JSONL store with file locking, idempotent appends, a correction path that appends rather than edits, named cursors for its consumers, and a CLI already on `PATH`. Building a second one duplicates every bit of that plumbing, and the standing rule in this portfolio is that a second copy of a fact is a copy that goes stale.

That is a real argument and it deserves a real answer.

The answer is that the plumbing is duplicated but the **contract is opposed**.

lifelog's invariant is *evidence, not inference*. It captures commits deterministically, with no model in the path, specifically because a guessed summary is worse than no summary. Agent memory is model-written inference by construction: "this looked like X and behaved like Y" is exactly the kind of claim it exists to hold.

lifelog's digests reach five sinks and one of them is a public portfolio. Agent memory contains machine chatter that should never be within reach of anything published.

lifelog's bar is "a handful per session at most". Agent memory's bar is lower on purpose: an open loop is worth recording even though no human would ever want to read it.

One store would mean one admission rule serving two audiences with opposite requirements. The failure mode is a machine trap surfacing in a portfolio digest, and there is already a recorded finding on this machine about exactly the two-audience problem in that log. So: steal the internals, do not share the store.

They point in one direction only. When a memory here is genuinely about the person's own work, a decision he made or a learning that cost him time, it triggers a `me jot` into lifelog. Never the reverse, and never a copy in both.

## The graduation path

There is one more boundary, and it is the thing that stops this becoming a junk drawer that grows forever.

**A memory confirmed enough times is not a memory any more. It is a rule.**

At that point it should be promoted into the repo's `CLAUDE.md`, where it becomes part of the contract every session reads, and **deleted from the store**. The store is the waiting room for the contract, not a parallel copy of it.

Without that rule, any system like this becomes an ever-growing pile whose signal-to-noise ratio only ever gets worse. With it, the store has a natural size: it holds what is provisional, and things leave it in both directions, upward into the contract when they are proven and downward into the archive when they decay.
