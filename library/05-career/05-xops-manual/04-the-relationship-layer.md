# The Relationship Layer

You had a theory, described roughly like this: people engage back if you engage with them — but not everyone, especially not the big accounts. So take ten or fifteen of your ~740 active followers, engage with them genuinely and consistently, and see who actually reciprocates. That idea needed three things it didn't have: a way to name the cohort without it drifting, a way to visit them without it becoming a script, and a way to measure whether it worked that wasn't just a feeling six weeks later.

## The experiment harness

`state/cohorts.json` exists so a growth idea has to declare itself honestly before it starts. Every experiment carries a hypothesis, a cohort, a duration, and a metric, written down before day one — because an experiment defined after the fact always looks like it worked, and that's not evidence, it's a story.

```json
{
  "name": "probe-1",
  "status": "planned",
  "hypothesis": "Engaging genuinely with 10-15 active followers'
                 posts over two weeks gets at least a third of them
                 engaging back on my posts.",
  "cohort": [],
  "durationDays": 14,
  "metric": "per-handle inbound events (xo people) during the
             window, vs the same handles' inbound in the two
             weeks before"
}
```

Three rules keep an experiment from quietly becoming a chore list. Cohort members get exactly the same taste and voice bar as everyone else — a cohort is a list of people to pay attention to, never a quota of replies to hit, and a hollow "great point!" to someone in the cohort costs more than silence, because it spends your credibility on the exact people you're trying to build it with. Membership is frozen for the whole window — a cohort that changes mid-run has measured nothing, because you no longer know what the number describes. And the metric has to be answerable from the ledger in Chapter 2 — if `xo people` can't see it, it isn't a metric, it's a hope.

To actually run one: pick the handles from your follower analytics, favoring people who post regularly and build things — not your existing circle, since circle members already reciprocate and would contaminate the measurement before it starts. Fill in `cohort`, flip `status` to `active`, set `started`. When the window closes, write the verdict into the same file and never delete it. Verdicts are the entire point of the harness; a finished experiment with no verdict recorded is worse than one that never ran.

## The daily visit — /x-engage

This is the skill that actually does the work between setting up a cohort and measuring it. It visits only named people: everyone in an active cohort, plus circle members from `state/weights.json` who've gone quiet in the ledger — no search, no algorithmic timeline, no strangers. Mixing discovery in would poison the measurement, because you'd no longer know whether an engagement came from the cohort or from something else entirely.

For each person, one visit, human pace: open their profile, read the last few days, pick at most one post worth a real reply. Most days, most people have nothing worth replying to, and that's the expected outcome, not a failure — a cohort member with nothing engageable for two weeks is real data about that relationship, not a gap in the run. What it drafts follows the exact same rules as Chapter 3: same modes, same register, no fabricated conviction. Reach only extends the standard, it never lowers it.

## The measurement — /x-pulse

This is the only skill that reads your notifications, and it does exactly one thing with what it finds: turn it into rows in `pulse.jsonl`. It snapshots your follower count first — every experiment's success metric needs a baseline to compare against — then sweeps notifications and mentions, normalizes each cell into a signal (`like`, `reply`, `repost`, `quote`, `mention`, `follow`), and writes them in one batch through `xo pulse-ingest`, which dedupes on the way in.

The report it produces is the actual payoff: follower delta since last time, who engaged back since the last sweep, and — the number the whole experiment exists to produce — per-cohort reciprocity. Day 6 of 14, four of eleven cohort members have engaged back, here's who's been silent the whole window. That sentence is either true or it isn't, and the ledger is what makes it checkable instead of remembered.

## Promotion is evidence now, not a gut call

`/x-taste`, covered properly in Chapter 6, used to promote a handle from `warm` to `circle` on your feel for the relationship. Now it reads `xo people` first: a real exchange means both directions, not just replies sent. A warm handle with high reciprocity — engaging you more than you engage them — is a real promotion case. A circle handle with zero inbound across a long window isn't an automatic demotion, because some relationships live in DMs or off-platform entirely; it's a question the pass raises for you rather than answers on its own. And a handle mid-experiment never gets touched either way while the cohort window is open — changing their scoring mid-run would be the exact contamination the whole harness exists to prevent.
