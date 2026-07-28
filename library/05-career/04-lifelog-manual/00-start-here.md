# Start Here

Every file that describes you was true on the day you wrote it and slightly wrong every day after. `facts.yaml` doesn't know about the thing you shipped last Tuesday. `skills.md` still calls a project active that you haven't touched since April. The vault has a note for a project you abandoned and none for the one you're actually building. Not because you're careless — because keeping them current means *remembering to*, and nobody does that for fourteen months straight.

Lifelog is the fix, and the fix is not discipline. It's evidence. One append-only log at `~/.lifelog/events.jsonl`, fed automatically by every commit on this machine and manually by ⇧⌘J when something happens that a commit can't prove. Everything else reads from it.

It lives at `PROJECTS/Me/lifelog`, the binary is `me`, and this manual is about operating it.

## The one idea underneath everything

JobOps and HackOps are pipelines — things go in one end and come out the other. Lifelog isn't. It's a **stream with readers**, and that difference is the whole design.

There is exactly one ordered log. Every consumer of it — the Second Brain vault, `job-ops/profile`, `portfolio/public/skills.md`, `hack-ops/profile` — holds nothing but a **cursor**: a mark saying *how far through the log have I read*. That's it. No consumer has a copy, a cache, or a schedule.

That single choice buys you three things that look unrelated and aren't:

- **Nothing is ever applied twice**, because applying is what moves the cursor.
- **Nothing is ever lost**, because the log is append-only and a reader that falls behind just has more to read.
- **A consumer added a year from now replays all of history into itself for free.** This is not theoretical — `hackops` became the fourth sink two days after the log was built, cost one line of config, and immediately received all 427 events back to 2025.

Chapter 1 is that idea in full. Read it first; everything else descends from it.

## The part that makes it honest

A log of what you did is only useful if it's also willing to say what you *stopped* doing. So status decays on its own: 14 days to stop being active, 45 to go warm, 120 to go cold. There is deliberately **no way to pin a project active by hand**. If you haven't touched it, it stops claiming you have, and the file that says otherwise gets corrected on the next sync.

That's the mechanism. Not the log — the decay. The log makes updates possible; decay makes them *honest*.

## What the system owns vs what you own

The system owns everything mechanical: capturing every commit on the machine through one global git hook, extracting a structured summary from each one with no model involved, polling GitHub and Medium nightly, computing decayed status, ranking events by how much they actually matter, and producing a digest an AI can apply to a sink.

You own two things:

1. **The half that leaves no git trace.** Decisions and why you made them, opinions, things you learned the hard way, what blocked you, the post you wrote, the video you're planning. Commits prove you wrote code. Nothing but you can record why. Chapter 2 is about capturing that well, and about what *not* to bother capturing.
2. **The sync, and specifically the ack.** The digest tells an AI what changed; a human decides what that means for a file written in your voice. Chapter 5 covers the loop and the one rule that can actually lose data.

## How to read this

Chapter 1 is the model — one log, many cursors, and why corrections are events too. Chapter 2 is capture: what only you can record, and what's a waste of a keystroke. Chapter 3 is everything that records itself while you do nothing.

**Chapter 4 is the one to read if you only read one.** It's an ordinary Tuesday walked end to end — what you do, what lands in the log, and which system downstream ends up changed by it — plus a table of every event type and where it goes. Everything before it is the theory of that chapter.

Chapter 5 is reading your own record, which is more useful than it sounds: it's where posts, articles and interview answers come from. Chapter 6 is the sync loop that updates the vault, `facts.yaml` and `skills.md`. Chapter 7 is what breaks, why, and how to tell.
