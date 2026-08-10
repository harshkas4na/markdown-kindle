# How It Learns

`/x-taste` is the pass that reads everything the other skills wrote down and rewrites the files that shape every future draft. It's the reason this system is supposed to get better instead of just accumulating drafts — and it's built with a real guardrail against the failure mode that would make it actively harmful.

## Don't run it too early

Below roughly 30 real decisions, a taste pass is fitting noise, and a taste file rewritten from six data points is worse than the hand-seeded prior it replaced — because it now claims to be evidence. The check exists in the skill itself. Patience here isn't a suggestion, it's the difference between the system converging on you and the system converging on whatever happened to be in the log that week.

## What it reads

```
node bin/xo stats        # counts by kind, edit rate, mode accuracy
node bin/xo pairs        # every draft/final pair, diffed
node bin/xo people       # both directions per handle — reciprocity
node bin/xo overrides    # guard warnings you dismissed, with your reason
```

`xo overrides` deserves its own sentence: it's the closest thing this system has to you filling out a survey about your own voice, except you didn't fill out a survey, you just typed one honest line the moment a warning felt wrong. Every one of those gets read on every pass.

## What it rewrites

`state/weights.json` holds your circle, warm, and broadcast lists plus the scorer's feature weights, and it moves in small, deliberate steps — three to five points per weight, never more than three weights touched in one pass, because a scorer that swings on every session has no memory at all. `profile/taste.md` gets its strong-yes and strong-no tables rebuilt from what actually happened, and rows the evidence stopped supporting get deleted, not softened. `profile/voice-x.md` and `profile/voice-post.md` absorb whatever the latest pairs taught — Chapter 1's four lessons and the either/or question pattern all entered the system exactly this way, one real edit at a time.

## What it already learned, worth knowing before you read a fresh draft

Four lessons came out of the earliest sessions, and they're covered properly in Chapter 1: you write in broken lines, not paragraphs; you answer the literal question before adding a belief on top of it; the tool is never named, under any circumstance; and you're blunter about things than a draft tends to make you, but warm with people, which means the right move on an unclear read is the milder draft, since you can always sharpen it and an over-blunt reply to the wrong person costs more than a soft one ever would.

A fifth arrived only once real sends accumulated: the either/or question. Not "curious how this works," but "was it move ordering or the eval fn." Chapter 3 covers the mechanics; the point here is where it came from — three separate people, three separate sends, the same shape, never explicitly stated by you and never guessable from the corpus alone, because the corpus was six months old and this pattern only showed up in the newest week of sends. That's the entire argument for why this pass has to keep running. A voice file frozen at the first harvest would never have found it.

## Promotion is a taste decision now, with evidence behind it

Circle and warm lists used to move on instinct — two good exchanges, promote; a run of dismissals, demote. Now `xo people` supplies the other half of the picture: a real exchange means the other person came back, not just that you sent something. High reciprocity from an unlisted or warm handle is a real promotion case. Zero inbound from a long-standing circle member is a question the pass raises, not a demotion it executes on its own — some real relationships simply don't run through public replies. And nobody mid-experiment gets touched in either direction, because changing a cohort member's scoring while the window is open would be exactly the contamination Chapter 4's harness exists to prevent.

## The failure this pass is built to avoid

A single edit is not automatically a style lesson. One draft got cut because it stated a belief you don't hold — a factual correction, not a rhythm preference — and reading it as the latter would have written a permanent, wrong rule from one data point. Before any edit becomes a rule, the pass has to ask which of four things actually happened: a fact was wrong, a stance was wrong, a rewording changed nothing about meaning, or something true and in-voice got cut. Only the last two are style signals, and even a clean deletion waits for a second instance before it becomes a written rule. When it's genuinely ambiguous, the honest move is to ask you directly. One question is cheaper than a wrong rule quietly distorting every draft after it.
