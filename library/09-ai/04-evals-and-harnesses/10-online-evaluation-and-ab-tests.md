# Online Evaluation and A/B Tests

**Fast overview:** Offline evals measure a metric you chose on data you curated. They cannot tell you whether users are better off. This chapter covers the other half: continuous evaluation on production traffic, the implicit signals that are more honest than thumbs-up buttons, how to roll out a change safely, and how to run an A/B test that concludes — including the honest admission that many early-stage A/B tests never will.

## What each half can see

| | Offline eval | Online eval |
|---|---|---|
| Sees | Cases you thought of | The real input distribution |
| Ground truth | Labelled | Absent, mostly |
| Speed | Minutes | Days |
| Catches | Regressions on known cases | Everything you failed to anticipate |
| Blind to | The distribution shift you did not model | Whether a specific case regressed |

You need both, and the loop between them is the point: **production surfaces failures, failures become eval examples, the eval prevents their return.**

## What to measure on production traffic

**Deterministic, on everything.** Free, so run them on 100% of requests:

- Schema validity and parse rate.
- Citation rate and citation validity.
- `NOT_FOUND` / refusal rate.
- Banned-content assertions.
- Latency and cost per request.
- Agent metrics: steps, cap hits, repeated calls, tool errors.

**Judged, on a sample.** 1-5% of traffic, or biased toward suspicious requests:

- The RAG triad (context relevance, groundedness, answer relevance).
- Task-specific rubrics.

Sample-biasing is worth doing deliberately: judge more of the requests that hit an edge case, took unusually long, cost unusually much, or came from a segment you are watching. Uniform sampling wastes most of the budget on cases that are fine.

**Implicit user signals.** These are more honest than explicit feedback and mostly free:

| Signal | Interpretation |
|---|---|
| Regeneration / retry | The answer was inadequate |
| Rephrased follow-up | The system misunderstood |
| Copy of the output | It was useful |
| Edit before send (draft flows) | Partially useful, and the diff is a label |
| Abandonment mid-flow | Something went wrong |
| Escalation to a human | The system's boundary, measured |
| Time to next action | Faster is usually better |

**Explicit feedback** — thumbs, ratings — has abysmal response rates and severe selection bias toward the angry. Collect it, weight it lightly, and treat a thumbs-down with a comment as a high-value eval example rather than as a statistic.

The **edit diff** in a draft-and-review flow is the best signal on this list. JobOps produces it naturally: every generated email that gets edited before sending is a labelled correction, and the pattern across edits is precisely what `profile/learnings.md` is for. That is a self-improving loop already built, and it is a genuinely good story for a conversation about online evaluation.

## Rolling out a change safely

Four stages, and skipping to the last is how incidents happen:

**1. Offline eval.** The gate must pass.

**2. Shadow.** Run the new configuration on real traffic in parallel, serve the old one, log both. Compare outputs on the same inputs — the strongest comparison available, because it removes user-variance entirely. Costs double inference on shadowed traffic; sample it.

**3. Canary.** Serve the new version to 1-5% of traffic. Watch the deterministic metrics and the error rate, not the quality metrics, because at 2% for two hours you will not have the volume for quality. This stage catches operational failures: latency regressions, rate limits, crashes.

**4. Ramp.** 5% → 25% → 50% → 100%, with an automatic rollback trigger on the deterministic guardrail metrics.

**The automatic rollback trigger matters more than the ramp schedule.** Define it before the rollout: "if parse rate drops below 0.98 or p95 latency exceeds 2s or error rate exceeds 1%, revert without asking." A human deciding at 2am is not a plan.

## Running an A/B test

**Choose the metric before you start.** The rule that prevents self-deception: name the metric, the expected direction, the minimum effect worth shipping, and the duration, in writing, before the test runs. Otherwise you will find something that moved and believe it.

**Pick a metric close to the change.** This is the practical crux at an early-stage company. Revenue and retention move slowly and noisily; you will not detect a change in them. Proxies with a higher base rate and a tighter link to the change will move detectably:

- Regeneration rate
- Escalation-to-human rate
- Task completion rate
- Citation rate
- Edit distance on drafts
- Time to resolution

**Randomise by user, not by request.** Per-request randomisation gives an inconsistent experience within one session and contaminates the comparison.

**Guardrail metrics.** Always monitor cost, latency and error rate alongside the primary. A quality win that triples cost is a decision for someone else to make, and they can only make it if you measured it.

**Run for whole weeks.** Weekday and weekend traffic differ. Stopping on Thursday because it looks good is the classic error.

**Do not peek and stop early.** Repeatedly checking and stopping when significance appears inflates the false-positive rate substantially. Either fix the duration in advance, or use a sequential test designed for continuous monitoring.

## The honest problem: power

From Chapter 5: detecting a small lift on a low-base-rate metric takes tens of thousands of users per arm. Most early-stage companies do not have that.

The consequences, stated plainly because pretending otherwise is worse:

- **Many A/B tests at a startup will not conclude.** Accept it and choose accordingly.
- **Prefer high-base-rate proxy metrics** over conversion or revenue.
- **Prefer large changes** — testing a whole new approach rather than a prompt tweak.
- **Lean harder on offline evals and shadow comparisons**, which need no user volume at all.
- **For small changes with a clear offline win and no guardrail regression, just ship them.** Waiting six weeks for a test that cannot conclude is not rigour, it is theatre.

Being able to say this is a credibility marker. It shows you understand the statistics well enough to know when the ceremony is not worth performing.

## Closing the loop

The mechanism that makes all of this compound, run weekly:

1. **Sample production failures** — low judge scores, thumbs-down, escalations, `NOT_FOUND` on answerable questions, human rejections.
2. **Cluster them.** Two or three patterns will dominate.
3. **Add representative examples to the golden set**, labelled and sliced, tagged with the incident.
4. **Fix the largest cluster.**
5. **Verify with the harness**, which now contains the case.

Step 3 before step 4, always. A fix without an eval case is a fix that can silently revert.

This weekly loop is the single practice that separates AI products that get better over time from ones that plateau, and it is a completely concrete thing to propose in a first-90-days conversation.

*Connect the dot:* JobOps already runs a version of this loop — outcomes go into `applications/tracker.md`, lessons are harvested into `profile/learnings.md`, and every generating skill reads that file before producing anything. The missing piece is a labelled set and a gate. Being able to say "I have built the feedback loop, I have not built the measurement" is precise, honest, and unusually specific.

Next: drift, and maintaining the set as an asset.
