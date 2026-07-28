# One Hackathon, End to End

Watching the machine move once is worth more than any amount of description. This is the full path, with the real example from the first live run where it exists.

## 0. It finds you

Twice a day the scout sweeps Devpost (open *and* upcoming — upcoming is the bigger and more useful set, since an event already accepting submissions is one you're late to), Devfolio, Superteam Earn, and ETHGlobal. Ninety-odd live events land in `radar/raw-YYYY-MM-DD.json`, deduped and normalized. Finished events accumulate separately in `radar/archive-events.json` — eighty-plus of them with showcase URLs, which is the corpus chapter 4 mines.

If something matches your edge, your phone buzzes. Otherwise it waits for you.

## 1. `/hack-score` — the filter

Five axes, weighted: win probability 35%, compounding return 25%, cost 20%, trust 10%, learning value 10%. Every A and B row names a **specific track**, because an event without a track recommendation isn't scored at all.

The capacity gate applies last: if an M+ build is already committed, a new event must beat it outright and name what it would displace.

What the first real run looked like: 96 events in, **zero A grades**, one B, six C's, and about fifty-four F's clustered into Indian college hackathons paying in domain names and n8n licences, generic AI wrappers, and domain challenges needing expertise you don't have. The $2,000,000 Gemini XPRIZE was an automatic skip — 22,493 registrants, the exact undifferentiated-mega-pool shape that produced the Delhi zero.

## 2. `/hack-recon` — the disqualifier hunt

Three things get checked before anything else, because they kill events fastest:

**Eligibility.** Four of six Superteam bounties turned out to be country-locked. The one that looked best on the board — $5,000 with only four submissions — was **Vietnam-only**.

**The live field size.** Zeroclaw looked like the best cash-per-day play available. Recon found **62 submissions already in**, against seven paid places. $81 per submission.

**Places paid versus headline pool.** A $2,000 bounty paying exactly one winner against 81 submissions is a completely different bet from $2,000 across ten places.

Then the rest: cash versus credits, the exact prior-work clause quoted rather than paraphrased, team-size rules, required artifacts, named judges, organizer payout history, every date converted to IST.

The Zeroclaw dossier is worth reading in the repo as a model. It surfaced the published rubric — Use case 30%, Safety and custody 25%, Craft 20%, Reproducibility 15%, Showcase 10% — which is 70% finish quality, exactly your Tier-3 edge. It also flagged two unresolved eligibility questions to settle in Discord *before* investing build time.

## 3. `/prior-winners` — what actually wins here

Chapter 4. Output is a map of structural gaps, not a summary of past winners.

## 4. Commit

Yours alone. `portfolio.md`, `est_days` frozen, calendar populated by `/hack-track`. You register yourself — the system never signs you up for anything.

## 5. `/idea-forge` — what to build

Five to eight candidates, cut to three, each rated **Novelty / Pull / Feasibility** on the same one-to-three-star scale you used for the UHI hooks. Every candidate must attack a named gap; no gap, no idea.

Ranking rule: Pull and Feasibility are hard constraints, Novelty is the differentiator. An idea the sponsor doesn't care about loses even if it's brilliant, and an idea that can't ship in time is worth exactly zero. It also flags the double-entry play when two ideas share enough prior art to make the second one cheap.

## 6. `/build-spec` — the plan that survives the deadline

Written in a deliberate order:

**The demo script first**, before any architecture. Ninety seconds, stating what a judge sees. Everything not on the path to that script is optional *by definition*, which is what makes the later scope cuts obvious instead of agonizing.

**Then three scope tiers, committed now.** Core is what makes a submission exist. Strong is what makes it competitive. **Cut is written down explicitly as not building** — and that list is the single most valuable line in the file. It's the same judgment as removing ReacDEFI's conversational deploy, just applied early instead of late.

**Then the schedule, backwards from the deadline in IST**, with one demoable checkpoint per day, Core complete by the midpoint, and **the final day reserved entirely for the finish**. Deploy, live URL, README, demo video, submission form. Never borrowed against. If the plan needs that day, the plan is wrong and scope comes out instead.

If the stack is unfamiliar, there's a ramp day with a concrete hello-world-deployed target and a pre-decided **abort condition**: not deployed by end of ramp day, fall back to the familiar-stack idea. Decided now, while it's cheap.

## 7. `/build-log` — daily, blunt

One entry: the checkpoint, the actual, on-track or slipping or behind. Behind at the midpoint triggers the Cut list you already agreed to. It names the candidate and the consequence; you choose.

It also watches dependencies, because the most common overrun isn't the code. A dry faucet, a rate-limited RPC, an unapproved API key — or a deployed interface that doesn't match its own docs, which cost you days on the Uniswap V3 range manager. When the code is provably right, stop debugging the code and verify the assumption about the dependency.

## 8. `/submit-pack` and `/demo-day`

`/submit-pack` walks the dossier's required-artifact list **first** — missing a required tag or a video length limit is the cheapest possible way to lose after doing all the work — then produces the judge-facing README with the live URL and video at the top, the tightened demo script, every form answer, and the X thread. You submit and post.

`/demo-day` runs only for in-person judging, and it's a different skill from making artifacts. The 30-second version is the one that matters, because judges walk up mid-sentence and leave when they've decided. Working thing on screen immediately, one number that makes it real. Plus openers tuned per judge type, the eight likely questions with honest answers, and a **downloaded offline fallback video**, because live demos fail.

## 9. `/downstream`, then `/outcome`

Chapter 6, then chapter 5. In that order, because the 48-hour window on sponsor follow-up decays faster than your memory of what happened.
