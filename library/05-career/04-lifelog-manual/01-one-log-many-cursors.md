# One Log, Many Cursors

This is the chapter that explains why the system can't corrupt itself, and it's worth reading properly because every other decision follows from it.

## The log

`~/.lifelog/events.jsonl`, mode 0700. One JSON object per line, appended, never rewritten. An event looks like this:

```json
{"id":"20260728T072334-1b3e33","ts":"2026-07-28T12:53:34+05:30","type":"commit",
 "source":"git","project":"HackOps","title":"Init","meta":{...}}
```

The `id` is a UTC timestamp plus six random hex characters, which makes it **lexicographically sortable**. That's not decoration — sorting by id is sorting by time, so "everything after this point" is a string comparison rather than a date query. Cursors are built on it.

Appends take an exclusive `flock` first. Two repos committing at the same instant would otherwise interleave halfway through a line and corrupt both.

## Why a cursor, not a timestamp

The obvious design is "last synced at 3pm, show me everything since 3pm." It's wrong, and the failure is silent.

Clocks drift. A backfill inserts events dated last year *today*. A commit written while your laptop was asleep lands out of order. Every one of those is an event that a timestamp query steps straight over, and you never find out, because a sync that misses something looks exactly like a sync with nothing to do.

A cursor is a position in a stream, not a moment in time. `AfterID` means *literally every line after this one*, regardless of what date it claims. An event inserted below your cursor is still below it and still gets read.

## Why nothing is applied twice

**Applying is what moves the cursor.** That's the whole guarantee, and it's structural rather than a rule anyone has to follow.

Run `me digest --sink jobops`, apply the edits, run `me ack jobops --id <last>`. The cursor is now past those events. They can never appear in a jobops digest again — not because something remembers having applied them, but because they're behind the mark.

This is what makes the CLAUDE.md wiring in each sink repo safe. Four different sessions, in four different repos, can all try to sync the same sink. Whichever gets there first does the work and moves the cursor; the rest run `me sinks`, see `0 pending`, and skip. No coordination, no locks, no schedule.

It also means **re-reading a digest before acking is always free**. The digest is a pure function of the log and the cursor. Read it ten times, get the same thing.

## The one way to actually lose data

Ack before the edits are written.

That's it. That's the only destructive operation in the system. The cursor moves past events whose changes were never applied, and those events will never appear in that sink's digest again. The log still has them — nothing is deleted, ever — but the routine way of finding them is gone, and you'd need `--all` or `--days` to dig them back out.

Which is why the rule is stated in the skill, in every sink's CLAUDE.md, and at the bottom of every digest: **write the edits, then ack.** Never the other way around, never "I'll ack now and fix it after."

## Idempotency: why backfill is re-runnable

Some events carry a `key` — a commit SHA, a GitHub event id, an RSS guid. Before appending, the store checks `keys.idx` and silently no-ops if that key has been seen.

This is what makes `me backfill ~ --days 3650` safe to run whenever you like. It walked 407 commits back to JEUWEI on day one. Run it again tomorrow and it adds only what's new, because every commit it re-encounters is keyed by a SHA already in the index. Same for the nightly collectors: re-polling Medium doesn't duplicate ten articles.

## Corrections are events too

Append-only sounds like "mistakes are permanent." It isn't, because a correction is itself an event:

```sh
me retract <id> --reason "duplicate"     # hide it from every digest
me amend <id> "what it should say"       # replace its text
```

Neither one edits a line. Both append a new event pointing at the original, and `Read` resolves them on the way out. The consequence is the useful part: **a correction written months later still applies to the original, in every window.** Pull up last March and the retraction from July is already honoured, because resolution happens at read time, not write time.

The alternative — editing the line in place — would mean a digest generated before the fix and one generated after disagree about history, and neither knows it.

## What this buys you in practice

You can add a consumer at any time and it starts from zero with full history. You can fall six weeks behind on a sink and lose nothing. You can correct an entry from March in July. You can run the same sync from four different repos without thinking about it. You can re-run backfill on a whim.

None of that is a feature anyone implemented. It all falls out of *one ordered log, cursors instead of copies, append-only with resolution on read*.
