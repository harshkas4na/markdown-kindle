# How It Learns

"Self-improving" is usually a slide. Here's the actual mechanism, so you know what to feed it and what it does with the food.

## Everything else is a prediction

The scorer predicts. The spec predicts. `velocity.md` predicts. `/outcome` is the only step that checks any of it against reality, which makes it the only step that can make the system less wrong.

The contract is blunt: **the more honestly you log, including the losses, the better every future decision gets.**

## Four files, four jobs

`profile/edge.md` — your skills ranked by **rarity in a hackathon field**, not by how good you are at them. Includes an explicit non-edges list, because knowing what not to enter protects more weeks than knowing what to enter.

`profile/prior-art.md` — the reuse inventory, mapped to what each asset *re-aims at*. This is the speed multiplier: a build that scores M from scratch is often S when a Tier-1 asset transfers. It's also why an event producing nothing reusable was more expensive than it looked.

`profile/velocity.md` — build-days per stack, honestly, plus the unfamiliar-stack multiplier. Corrected only after **three misses in the same direction**. One miss is noise.

`profile/record.yaml` — the causal ledger. Not what happened, but *why*, with a confidence flag on every entry: `confirmed`, `inferred`, or `unknown`.

## Why the confidence flags matter

That file was seeded from your vault, which meant most readings started as `inferred` — my reconstruction, not your words. Then you corrected one, and it cascaded.

The original inference was "wins come from sponsor tracks." You said: **ETHGlobal Delhi was Uniswap and 1inch tracks.** That single sentence:

- rewrote the central pattern to `thin-not-just-sponsor`
- added `edge-is-relative-to-the-room`
- corrected `depth-beats-breadth`, which had wrongly claimed both zero-result events were generic fields
- inverted a live recommendation in `radar.md`, where a Uniswap sponsor at ETHGlobal Mumbai had been listed as the thing that would turn it into an A grade, and is now the thing to discount
- changed the rubric in `hack-score` and the non-edges list in `edge.md`

One answer, five files. That's what the `inferred` flags are for — they mark exactly where your correction is worth the most, and they're still sitting there in the remaining entries.

## Promote and prune

The rule that keeps these files short and true instead of growing into noise:

**Promotion needs three confirmations. Deletion needs one contradiction.**

A pattern confirmed three times gets promoted into `record.yaml`'s `patterns:` block, which *is* the scoring rubric. A pattern contradicted once gets deleted. `ledger.md` carries a calibration table tracking where each scoring axis has been wrong and in which direction.

## Propagating, which is the part that gets skipped

A post-mortem nobody acts on is a diary. `/outcome` pushes each finding to where it changes behaviour: new artifacts into `prior-art.md`, wrong estimates into `velocity.md`, causal lessons into `record.yaml`, bad axes into the `hack-score` skill file itself, late-paying organizers into the trust axis, and missed events back into the scout.

It also asks before editing anything — it proposes the diff and you confirm.

## The periodic review

Ask for a review rather than a single outcome and you get the analysis your historical record could never support: hit rate by **event shape**. Sponsor track versus main pool. Thin versus marquee. Online versus in-person. Hacker house versus open. Familiar versus unfamiliar stack. Plus estimate accuracy by stack, and total days spent against cash and downstream value.

That last one is allowed to conclude the pipeline isn't earning its time. It's a real possible answer and the review will say it out loud.

## The system corrects itself too

Two of the sharpest rules in `hack-score` exist because the first live run embarrassed the first version of it. Missing data is not zero — Devfolio publishes prize amounts for about one event in ten. Read the event name skeptically — "Hacker House" meant 10,869 registrations. Both are now written into the skill.

The same loop runs on the plumbing. Devpost was silently pulling only `status[]=open`, which is the set of events you're already late to; adding `upcoming` doubled coverage. Unstop was probed, found to have a working API, and **deliberately declined** — its inventory is almost entirely college hackathons, and adding forty F-grade rows per run to a radar whose whole value is filtering makes the tool worse. That decision is written down in `hack-scout` so it doesn't get rediscovered and re-litigated in six months.

When a source breaks, the scout says which one and what broke, rather than quietly returning fewer events. Silent coverage loss is the main failure mode of the entire system.
