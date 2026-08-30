# The Ninety Hours

**Fast overview:** The case for this system is one number, and the number was not known until the system was built enough to measure it. Eighty-four Claude sessions had run in `job-ops`. Ninety hours of work. Every one of them started from nothing and ended by throwing everything away. This chapter is about why that is a real cost rather than an aesthetic complaint, and why the obvious fixes had all already been tried.

## The shape of the loss

A session opens in a repo. It reads the `CLAUDE.md`, works out where things live, discovers that a particular tool behaves differently than its documentation suggests, makes a decision and has a reason for it, gets halfway through a refactor, and then ends.

The next session opens in the same repo the next day and knows none of that. Not the trap, not the reason, not the half-finished thing. It re-reads the same files, re-derives the same map, and if it is unlucky it walks into the same trap and pays for it a second time.

This is not a hypothetical. On this machine, twenty project directories under the two Claude config folders hold session transcripts. One `builder-ops` session alone is 2.1 MB across 1,150 lines. All of it is write-only. Nothing on the machine has ever read a single one of those files back.

## The measurement, which came out worse than expected

The first thing the new system did was not remember anything. It counted. It walked every transcript under both profiles, worked out which ones represented real sessions, and asked one question of each: did this session leave anything behind?

```
  repo         sessions  silent  memories  hours
  job-ops      84        84      0         90.0
  learn-ops    38        38      0         21.4
  x-ops        30        30      0         19.8
  work-ops     21        21      0         29.5
  hack-ops     19        19      0         18.9

  246 of 246 sessions left nothing behind (100%).
```

Two hundred and forty-six sessions. Not one of them produced a durable record of what it found out. Ninety of those hours were in `job-ops`, which is the biggest and most heavily machined repo in the portfolio.

That table is the entire argument. Everything after it is implementation.

## Why the obvious fixes had already failed

**"Just use the built-in memory."** Claude Code has a per-project memory directory. On this machine it sits at `~/.claude-work/projects/<slug>/memory/` and it is empty. It has been available the whole time and has never been used once. That is evidence about the mechanism, not about the need: something that requires a session to remember to be diligent, with no prompt and no feedback, does not get used.

It is also keyed by config directory and by project path. Two Claude profiles run here, `claude-work` and `claude-personal`, both of them the same person's. A memory written by one is invisible to the other. And a repo opened from a different path gets a different directory and therefore a different memory.

**"Just write it in the CLAUDE.md."** This is the right answer for a stable rule and the wrong one for an accumulating observation. A `CLAUDE.md` is a contract: it is committed, it is read by every session, and it has to stay true. A trap discovered at 11pm that might be true is not a contract. Put enough of those into a contract and it stops being read carefully, which is worse than not writing them at all.

**"Just log it."** There is already an append-only log on this machine, and the next chapter is about why it is the wrong home. Briefly: its digests reach five sinks and one of them is a public portfolio.

## The thing that makes it tractable

Here is the fact that made the whole design possible, found early and by accident.

`$CLAUDE_CODE_SESSION_ID` is exported into every Bash call a session makes. And its value is the transcript's filename: `$CLAUDE_CONFIG_DIR/projects/<slug>/<id>.jsonl`. Verified by comparing the two directly.

That single identifier does three jobs. It keys the staging area, so notes accumulate per session rather than in one shared pile. It makes confirmation counting honest, because "the same claim seen by two different sessions" is meaningfully different from "the same claim typed twice in one afternoon", and without a session identity the two are indistinguishable. And it is the join key that lets the system go back and read its own history.

Without it, most of what follows would have been guesswork.
