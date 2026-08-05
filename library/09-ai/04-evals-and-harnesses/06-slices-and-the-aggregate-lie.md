# Slices, and the Aggregate That Lies

**Fast overview:** A single number is the most dangerous artifact an eval harness produces, because it is exactly what a busy team wants and exactly what hides the thing they need to know. This chapter is about per-slice reporting: why an average can improve while the product gets worse, how to choose slices, how to gate on them, and why this is the technique most worth demonstrating in an interview.

## The failure, concretely

A support assistant, 200 eval examples, and a change to the retrieval prompt:

| | Before | After |
|---|---|---|
| **Overall** | 0.81 | **0.84** |

Ship it. Three points is a good change.

Now the slices:

| Slice | n | Before | After |
|---|---|---|---|
| Simple lookup | 90 | 0.88 | 0.94 |
| Multi-document | 40 | 0.79 | 0.85 |
| Follow-up questions | 35 | 0.76 | 0.83 |
| **Refusals (no answer exists)** | **20** | **0.85** | **0.40** |
| Identifier queries | 15 | 0.73 | 0.75 |

The change made the model more willing to answer. That helped four slices and destroyed the fifth: the system now invents answers to questions with no answer in the corpus, 60% of the time.

**The aggregate went up. The product got materially worse and more dangerous.** In a compliance, finance or medical context this is the regression that ends up in a postmortem.

This is not a contrived example. It is the single most common way eval suites mislead, because the metric everyone watches is the one that averages the failure away.

## Why averages hide this structurally

Two reasons, and both are worth being able to state:

1. **Slices differ in size.** The 20-example refusal slice is 10% of the set, so a 45-point collapse costs the aggregate 4.5 points, which was more than offset by gains elsewhere.
2. **Slices differ in importance.** Refusals are safety-critical and simple lookups are not. The aggregate weights them by count, and count has nothing to do with consequence.

**The general principle: a mean over heterogeneous groups answers no question anyone actually has.**

## Choosing slices

Slice by anything where you would want to know the answer separately. Practically:

**By input type.** Simple lookup, multi-hop, comparison, follow-up, out-of-scope, identifier-heavy. This is usually the most informative dimension.

**By expected outcome.** Should-answer versus should-refuse. Almost always worth separating, because the two failure modes are opposite and one is far more dangerous.

**By difficulty.** Easy / medium / hard, labelled at authoring time. A change helping easy cases and hurting hard ones is a common and important pattern.

**By domain or feature area.** Billing, technical, account, policy. Directly actionable, and it maps to who owns the fix.

**By source characteristics.** Long documents versus short, tables versus prose, recent versus archival.

**By tenant or segment**, in a multi-tenant product. A change that helps 90% of customers and breaks your largest one is not an improvement.

**By provenance.** Real versus synthetic examples. If a gain appears only on synthetic data, it is an artifact of how the synthetic data was generated.

Aim for **4-8 slices with at least 20-30 examples each**. Below 20, the per-slice interval is so wide that the slice generates false alarms and gets ignored, which is worse than not having it.

Slices can overlap. An example can be `[multi-hop, billing, hard]`, and reporting each independently is correct.

## Reporting

```
CONFIG   prompt=v12  model=gpt-4o-mini@2026-05  k=5  reranker=on
DATASET  golden_v9 (n=213)   BASELINE  main@a3f21c

SLICE               n    score   Δ vs base   flag
------------------------------------------------------
ALL               213    0.842     +0.031
simple-lookup      90    0.941     +0.058
multi-doc          40    0.850     +0.061
follow-up          35    0.829     +0.071
refusal            20    0.400     -0.450    ** REGRESSION **
identifier         15    0.750     +0.020

FAILURES (new since baseline): ev_0031 ev_0044 ev_0102 ... (12)
COST  $0.0023/example    P95 LATENCY  740ms
```

Requirements for the report to be useful rather than decorative:

- **The aggregate is one line among many**, not the headline.
- **Deltas against a named baseline**, not absolute numbers alone.
- **A visual flag on any slice regression**, so nobody has to notice it.
- **The list of newly-failing example ids**, because the number tells you something changed and only the examples tell you what.
- **The config**, so the run is reproducible.
- **Cost and latency**, so quality is never read in isolation.

## Gating on slices

The gate (Chapter 7) must check slices, not just the aggregate:

```yaml
gates:
  overall:
    min: 0.80
    max_drop: 0.02
  slices:
    refusal:          {min: 0.95, max_drop: 0.00}   # safety-critical: no drop allowed
    identifier:       {min: 0.70, max_drop: 0.05}
    default:          {max_drop: 0.05}              # every other slice
```

Note that `refusal` has a zero-drop tolerance. Some slices are not tradeable. Encoding that in the gate is how you make a safety property survive a busy release week, and it is far more reliable than a code reviewer remembering to check.

**The failure to guard against:** the noisy slice that fires constantly and gets suppressed. If a 15-example slice trips on every run because its interval is ±20 points, either grow it or set its tolerance from its measured noise. A gate everyone ignores is worse than no gate — it teaches the team that red is normal.

## Slice discovery

You will not think of every slice up front. Two ways to find the ones you missed:

**Read the failures and look for a pattern.** Twenty failing examples usually contain two or three clusters. When you spot one, it becomes a new slice label, applied retroactively.

**Automated slice finding.** Cluster failing examples by embedding, or run a decision tree over example metadata against pass/fail. Tools exist for this; a manual read of the failure list finds most of it at a startup's scale.

Either way, **when you find a systematic weakness, it becomes a labelled slice with its own gate.** That is how an eval suite grows teeth over time rather than just growing larger.

## The interview move

Per-slice reporting is the single most demonstrable eval idea, because you can state it in thirty seconds and it lands:

> The number I would not trust is the average. On my own retrieval bench, hybrid search moved overall recall by three points, which on its own would have got the feature rejected. Sliced, it moved identifier-style queries by thirty points and simple lookups by almost nothing. The aggregate was hiding the entire effect. So the first thing I would add to an existing harness is slices and a per-slice gate, because the regression that hurts you is almost never the one that shows up in the mean.

That answer demonstrates the technique, brings a number, and implies the diagnostic instinct, all at once.

*Connect the dot:* Book 02 made this argument three times — for hybrid search, for query transformation, and for chunk size — and it was the same argument each time. Slicing is not an eval technique. It is a general habit of refusing to let an average answer a question about a heterogeneous population.

Next: the harness itself, and the gate in CI.
