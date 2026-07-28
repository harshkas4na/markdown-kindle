# The Sync Loop

This is where the log stops being a diary and starts changing the files that represent you.

## Say the sentence

> "sync it with current me"

The `sync-me` skill takes over: read the pending events for a sink, apply them to that sink's files, advance the cursor. By hand it's three steps:

```sh
me digest --sink secondbrain     # markdown: project state, new tech, new events
# ...apply the edits...
me ack secondbrain --id <id printed at the bottom of the digest>
```

## The four sinks and what they own

| Sink | Owns |
| --- | --- |
| `secondbrain` | `01 Projects/*.md`, `00 Me/Skill Stack.md`, `00 Me/Timeline.md`, `02 Areas/*`, `05 Writing/Article Ideas.md` |
| `jobops` | `profile/facts.yaml`, `profile/learnings.md`, `profile/stories.md` |
| `portfolio` | `public/skills.md`, `app/data.ts` |
| `hackops` | `profile/prior-art.md`, `profile/velocity.md`, `profile/edge.md` |

Each of those repos carries a CLAUDE.md section telling its sessions to run `me sinks` at start and drain anything behind — its own sink first, then any sibling that's fallen behind. Nothing coordinates them, because nothing has to: applying moves the cursor, so the first session there does the work and the rest see zero.

## The digest ranks, it doesn't dump

This is the part that makes a 400-event window usable.

Commits that added dependencies, created new files, or broke something are shown in full — those are the ones carrying information. Typo-and-tweak commits collapse into one honest line per project:

```
Also: 12 smaller commits, +340/-120 — chore×7, fix×5.
```

Treat that line as **evidence of activity, never as something to describe feature by feature**. It says the week was busy. It does not say what shipped.

Commits are also grouped by conventional-commit scope, which is the closest the log gets to answering "which features exist and how far along are they" — `feat(panel)` appearing six times over four days is a feature being built, and it reads that way.

## The rules that keep a sync honest

These are in the skill, and they're the difference between a profile that's current and one that's inflated:

- **Never claim what the digest doesn't support.** No inferred skill level, no "mastered", no invented metrics.
- **`deps added` is evidence. `initial stack (scaffolded)` is not.** One is something you reached for; the other is what a template generated.
- **Commit activity says nothing about whether a deployed thing is live.** "No commits in 184 days" means exactly that.
- **A `cold` or `dormant` project stops being described as "currently building".** Demote the wording; never delete the history.
- **Reconcile, don't rewrite.** Preserve your voice, structure, and anything the digest doesn't contradict. `skills.md` is first-person and direct; `facts.yaml` is structured truth; the vault uses `[[wikilinks]]` and new notes get linked into the graph.
- **Dates stay absolute.** `2026-07-28`, never "recently" — "recently" is how a file starts lying again.
- **If the digest is empty, say so and stop.** Do not invent an update.

## The ack rule

**Only ack after the edits are written.**

Acking early is the one operation that loses data — those events drop out of that sink's next digest permanently. Re-reading a digest before acking is always safe and always returns the same thing, so there is never a reason to ack "to be safe."

## Correcting the record

The log is append-only, but wrong entries aren't permanent:

```sh
me retract <id> --reason "duplicate"
me amend <id> "what it should say"
```

Event ids are printed under every digest entry. A correction applies to the original in every window, including ones generated before you wrote it — resolution happens at read time.

Use `retract` when a capture was noise or a duplicate. Use `amend` when the substance was right and the wording wasn't. Both are cheap; neither destroys anything.

## When a sink drifts a long way

Nothing breaks. A sink 400 events behind produces a long digest, and the ranking is what makes it survivable — you get the significant commits in full and the rest collapsed.

If it's genuinely enormous, narrow it:

```sh
me digest --sink jobops --days 30      # ignore the cursor, last 30 days
me digest --sink jobops --all          # everything, ignore the cursor
```

Both leave the cursor alone. When you ack, you ack to a specific id, so you stay in control of what "caught up" means.

## What a good sync actually changes

Usually less than you'd expect, and that's correct. A month of work might move three lines in `facts.yaml`, add one project note, and demote two projects from active to warm.

The demotions are the valuable part. Adding new work is the easy half — any of these files would have grown on its own. What no one does by hand is go back and quietly downgrade the thing they've stopped working on, and that's exactly the drift that makes a profile stop being true.
