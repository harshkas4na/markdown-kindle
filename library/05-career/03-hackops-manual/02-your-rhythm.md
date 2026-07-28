# Your Rhythm

The point of this system is that you stop tracking things. This chapter is the whole operating rhythm, sized honestly — and most of it is the system talking to you rather than you doing anything.

## What runs without you

`.github/workflows/scout.yml` sweeps all four sources twice a day, at roughly 07:47 and 19:47 IST, and then `gh-tools/notify.mjs` opens a GitHub Issue — a push on your phone — for exactly three things:

1. **Deadline alarms on committed events, at 3 days and 1 day.** Uncapped, never suppressed, never rate-limited. Missing a submission deadline is a total loss of everything already invested, so this one is allowed to be annoying. The 3-day alert also does the arithmetic: if the spec says six days of work and there are three left, it tells you to activate the Cut list now.
2. **Edge matches** — a newly-seen event touching a Tier-1 or Tier-2 skill from `profile/edge.md`. Worth a push even at ninety days out, because the good events are the ones you see early.
3. **Relevant unscored events closing within five days**, so nothing ages out silently.

Everything else is deliberately silent. Ninety-four events a run would train you to swipe notifications away, which defeats the entire purpose. That's also why `/hack-score` writes `radar/.graded.json` — once you've judged something, the automation stops mentioning it. If your phone ever starts feeling noisy, that file is out of date.

Twice a day is the right cadence here. Hackathon deadlines move in days, not hours, unlike the HN thread JobOps chases every six.

## Daily (10 seconds, most days zero)

Open a session in `hack-ops/` and the first thing that runs is:

```
node scripts/deadlines.mjs
```

Committed work, slippage warnings, and anything closing within fourteen days. When nothing is committed it prints "capacity is free" and you're done. When something is committed, it tells you whether you're on schedule and what today's checkpoint was.

During an active build, add `/build-log` — one short entry, blunt about slippage. Its only real job is to notice you're behind while the Cut list can still save you. A scope decision on day three is cheap. The same decision at 2am on the last day costs the submission.

## Weekly (5 minutes)

`/hack-scout` then `/hack-score`. Read the A and B rows in `radar/radar.md`. Disagree out loud when a score feels wrong — that's the calibration, and the scorer is currently a rough model of your judgment rather than a good one.

**Most weeks there is nothing worth doing, and that is the correct output.** The first full run scored the entire open field and produced no A grades, one B that was a calendar reservation rather than a build, and a recommendation to spend the week on `../job-ops/` instead.

## When something scores A or B

Two skills, in this order, and they can both kill it:

**`/hack-recon {event}`** replaces every estimate with a fact — real cash versus credits, how many places actually pay, the exact prior-work clause, eligibility, named judges, and whether the organizer has ever paid on time. Recon that finds a disqualifier is a *success*. It just saved you a week.

**`/prior-winners {event}`** mines past submissions for track economics and structural gaps. Chapter 4 covers the method.

## When you commit

Add the entry to `portfolio.md` with `est_days` recorded **at commit time**, and then never edit it. The gap between that estimate and reality is the only thing that calibrates `velocity.md`.

Then `/hack-track` puts everything on your calendar: submission deadline plus separate 72-hour and 24-hour warnings, the registration close (often much earlier and easy to miss entirely), the build days blocked as busy, and the sponsor office hours — which are worth attending, because the people running them frequently judge.

`portfolio.md` is also a hard gate. **One M+ build at a time.** The only exception is the double-entry shape: two builds sharing enough prior art that the second is a variant rather than a second start. That's exactly how November 2024 produced 1st *and* 2nd place at the same event, and it's the highest-leverage move available to you.

## Monthly and seasonally

Run `/x-intel` roughly monthly. The highest-EV events for you frequently never appear on any aggregator, because a single protocol runs them for its own developers — that shape produced the Reactive wins, the Kwala placement, and the Walrus track win. Hacker houses and curated cohorts are the thinnest fields in the space and are almost never listed anywhere; they surface on X and in Discord.

Big ecosystem events need **two passes**. ETHGlobal publishes sponsor tracks only four to six weeks out, and the track is the entire decision. Pass one reserves the calendar slot and sets a re-score date. Pass two picks the track. An event that quietly ages out unscored is the most expensive failure this system can have.

## The two habits that compound

Everything above is mechanical except two things.

**Log every outcome, including the losses and the events you abandoned.** The weakest line in your entire historical record is *"many online hackathons — no win"* with no list of which ones — a whole category of evidence lost because nobody wrote it down. `ledger.md` exists so that never happens again.

**Run `/downstream` within 48 hours, win or lose.** That's chapter 6, and it's where the money has always actually been.
