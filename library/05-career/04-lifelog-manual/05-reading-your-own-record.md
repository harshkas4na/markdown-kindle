# Reading Your Own Record

The log is not just an input to other systems. Reading it directly is the fastest way to answer questions you currently answer from memory, badly.

## me status

```
PROJECT                  STATUS   LAST       COMMITS EVENTS  STACK
hack-ops                 active   1h ago           1      1  md mjs json yaml
Metro Diaries            active   6d ago         131    131  tsx ts md json
mygit (Git rebuilt in Go) warm    27d ago          1      1  go md mod txt
Hashtro                  cold     108d ago       169    169  tsx js py ts
JEUWEI                   dormant  354d ago         5      5  tsx ts json js
```

Four states, on thresholds you can change in `config.json`: **active** under 14 days, **warm** under 45, **cold** under 120, **dormant** beyond. Every one is computed from the last real event.

There is deliberately no way to pin a project active. That's not an oversight — it's the entire honesty mechanism. The moment you can override decay by hand, the file starts describing the projects you *feel* attached to rather than the ones you're working on, and you're back to a `skills.md` that lies.

Read this before writing any profile copy. It routinely contradicts what you were about to claim.

## me week

```sh
me week            # last 7 days
me week --days 30
```

Events, commits, net lines, projects touched, grouped by project. This is the input for posts and articles — not because it writes them, but because it removes the "what did I even do this week" stall that kills the habit. You get a factual list and pick the one worth a thread.

It's also the honest answer to *"why does this week feel like nothing happened?"* Sometimes it genuinely was nothing. Sometimes it was 30,000 lines and you'd forgotten by Friday.

## me events

```sh
me events --type idea --days 30       # every idea this month
me events --type learning --days 90   # what you actually learned this quarter
me events --project JobOps --limit 20 # one project's whole history
me events --type post,ship --days 60  # your own output
me events --json | jq ...             # when you want to compute something
```

Filters compose. `--json` emits one object per line, so anything you'd normally do with `grep`/`jq` works.

## Three questions it answers well

**"What have I actually been building?"** — `me status` plus `me week`. Not the projects you talk about, the ones with commits.

**"What do I have for this interview?"** — `me events --type decision,learning --days 180`. Decisions with reasons are the raw material for design questions, and they're the ones you'd otherwise reconstruct on the spot and get wrong.

**"What should I write about?"** — `me events --type idea,opinion,learning`. An idea you wrote down in March that still looks good in July is worth an article; an idea you can't remember having had probably wasn't.

## What it's specifically bad at

- **Judging importance.** `me events` is chronological, not ranked. The digest ranks; the reading commands don't. A 400-file scaffolding commit and a 3-line fix that took a day look similar.
- **Anything not in the log.** It only knows commits and captures. A week of interviews looks empty.
- **Being a task list.** It's a record of what happened, with no notion of what should. Don't try to make it one; that's what `job-ops` and `hack-ops` are for.

## me sinks

```
SINK             LAST SYNC       PENDING  SYNCED THROUGH
hackops          23m ago               0  20260728T085118-ab64ca
jobops           27m ago               0  20260728T084917-eec00c
```

How far behind each consumer is and when it last synced — the last-sync column comes from `sync` events the log writes on every ack, so the log can answer *"when did skills.md last reflect reality?"* without anyone having to remember.

Run it at the start of any session in a sink repo. Chapter 6 is what to do when the number isn't zero.
