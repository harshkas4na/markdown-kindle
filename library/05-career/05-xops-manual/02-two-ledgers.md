# Two Ledgers

Everything the system knows about you lives outside the repo, at `~/.x-ops/`, so none of it can be committed by accident. Two append-only files do all the work, and they're kept deliberately separate even though they'd fit in one.

## decisions.jsonl — what you chose

Every event this file records traces one of eight kinds: `candidate` (the scorer marked something and you saw it), `stash`, `dismiss`, `draft`, `sent`, `abandon`, `warned`, `override`. It's written once per event and never rewritten — `/x-taste` reads it, no skill ever edits a line in place. A record you can silently correct isn't a record.

The richest single row this file can hold is a `sent` event that still carries the `draft` it started from. That pair — what the model thought you'd say, and what you actually said — is a labelled example of exactly the gap Chapter 1 is about, and it's the raw material every voice lesson in this manual was mined from.

`override` might be worth even more. It's the moment you dismiss a guard warning before sending and type one line of why. That's you stating a rule about your own voice, in your own words, at the exact instant it applies — the one moment people can actually articulate taste, instead of a model inferring it after the fact from a pattern of edits.

```json
{"kind":"sent","statusId":"...","handle":"avrldotdev","mode":"answer",
 "draft":"for me its the skills. i have my own ones that read my repos
          and my log, cursor cant do that part. the model is not
          really the thing i am picking",
 "final":"for me its the skills. i have my own ones that read my
          repos and my log, cursor cant do that part.",
 "edited": true}
```

## pulse.jsonl — what came back

This one didn't exist until the relationship layer got built, and the reason it's a separate file rather than a wider `decisions.jsonl` is structural: decisions.jsonl is purely the record of what *you* chose. Mixing in what other people did back — a like, a reply, a follow, a follower-count snapshot — would muddy every future `/x-taste` read, because the two are different kinds of fact answering different questions.

`/x-pulse` writes this one, from a manual sweep of your own notifications page. Never scheduled — same posture as everything else in this system that touches your real account. Writes are deduplicated at the store layer before they're appended, so re-sweeping the same notification cells twice is harmless; the second pass just reports a higher skip count.

## The merge, computed fresh every time

Neither file stores a per-person summary. Instead there's one command that reads both and derives the picture on the spot:

```
node bin/xo people          # one row per handle: what you sent them,
                             #  what came back, a reciprocity ratio
node bin/xo person <handle> # the full two-way history for one person
```

A row looks like this once both logs have real entries in them: `out.sent: 2`, `in.like: 1, in.reply: 1`, `reciprocity: 1.0` — meaning this person has engaged you back exactly as much as you've engaged them. Below 1.0, you're investing more than you're getting; above 1.0, they're chasing you more than you're chasing them. Neither number is good or bad on its own — it's just no longer a feeling.

This ledger is the evidence for everything relational the rest of the system does: who's a candidate for promotion toward your circle, whether an experiment cohort is actually working, which of your own post series earns anything. Before this file existed, "is this person engaging back" was a guess made from memory. Now it's a query that takes under a second.

## Why append-only, specifically

The same reasoning that governs `~/.lifelog/events.jsonl` applies here for the same reason: a log you can rewrite isn't a record, it's a draft of one. Every append is validated on the way in rather than trusted and cleaned up later — a `stash` event without a real post URL is rejected outright at write time, because the one bad write this system ever produced was exactly that: a stash record with a profile URL instead of a post URL, which later caused a reply to land under the wrong tweet entirely. The fix wasn't a cleanup pass. It was making the bad write impossible to create in the first place.
