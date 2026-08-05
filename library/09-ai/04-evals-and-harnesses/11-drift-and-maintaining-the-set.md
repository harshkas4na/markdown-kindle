# Drift, and Maintaining the Set

**Fast overview:** An eval set is not an artifact you build once. It is an asset with a maintenance cost, and if you skip the maintenance it degrades silently into something that agrees with you about a product that no longer exists. This chapter covers the four kinds of drift, the specific decay of a graded library that Scenr's dossier identifies as their hardest unsolved problem, and the review process that keeps a set honest.

## The four kinds of drift

**1. Model drift.** The provider changes the weights behind a name, or you migrate. Every calibration shifts. *Defence:* pin explicit versions; run the suite before switching; record the resolved version in every trace and every run.

**2. Data drift.** Your users' inputs change — a new customer segment, a product launch, a competitor's outage sending you different traffic. Your set represents last quarter's distribution. *Defence:* sample production traffic into the set continuously; monitor input characteristics (length, topic mix, language) for step changes.

**3. Corpus drift.** In a RAG system, the documents change. A chunk id your set references was deleted. A question whose answer used to be "30 days" is now "14 days" and your `expected` field is wrong, so the system fails an eval by being *right*. *Defence:* reference documents by stable id plus content hash; run a validity check over the set as part of CI; date every expected answer.

**4. Eval drift.** The subtlest. The set stops representing what the product is for, because the product moved and the set did not.

## The ninety-day decay

Scenr's dossier states the problem precisely, and it is worth quoting because it is the sharpest formulation of a general truth: a graded scenario library *"is the only source of truth for ninety days, by which time the model version, the prompt, and the scenario library have all moved. A prompt tweak that shifts Debugging by 0.4 across the board is invisible."*

Two distinct failures are packed into that sentence.

**The set decays as a representation.** Ninety days of product development later, it tests things that no longer matter and omits things that now do.

**The scores decay as a measurement.** If the judge model, the rubric, or the scenario library changed, then a score from March and a score from June are not the same quantity. A uniform 0.4 shift across every dimension looks like a real quality change and is actually a recalibration.

**The defence against the second failure is an anchor set.** Hold out a small set — 20-30 examples — that is **frozen**: never edited, never extended, always run with a **pinned judge version**. Its absolute scores are meaningless as quality; its job is to measure the measurement. When the anchor moves and nothing else changed, your instrument moved, and every trend line needs recalibrating from that date.

This is the eval equivalent of a calibration weight in a lab, and proposing it is a genuinely strong answer to "how would you stop the eval library from decaying" — which is exactly the question a company whose product is evaluation would ask.

## Detecting eval drift

Signals that the set has gone stale:

- **The score is pinned near the ceiling.** If everything passes at 0.97, the set stopped discriminating. Add harder examples.
- **Production failures are not represented.** Take ten recent real failures and run them. If the set would not have caught any of them, it is not measuring your product.
- **Slices have gone empty or tiny** because the product changed shape.
- **The `added` dates are all old.** Look at the age distribution. If nothing has been added in two months, the loop from Chapter 10 is not running.
- **Nobody looks at the failures.** A gate that passes silently for weeks is either a very good system or a set that stopped asking anything.

## The review cadence

**Weekly** — add production failures. Fifteen minutes, and it is the highest-value habit in this book.

**Monthly** — read the failure list end to end; check the age distribution; check whether any slice has shrunk below the reporting threshold; verify chunk ids and expected answers still resolve.

**Quarterly** — the real review. Is this set still measuring the product? Retire examples that no longer represent anything, revalidate the judge against fresh human labels, re-examine whether the slices are still the right cuts, and re-derive the input distribution from production.

**On any model or judge change** — run the anchor set, record the shift, and annotate the trend line at that date.

## Retiring examples

People add and never remove, and the set grows into an expensive slow thing where most examples are decoration.

Retire an example when the behaviour it tests no longer exists, when it duplicates another example's coverage, or when it has passed every run for a year and tests nothing near a boundary. **Do not delete it — mark it retired and keep it**, so a future question about the set's history is answerable and so an accidentally-removed capability can be re-checked.

Growing to 300 well-chosen examples is better than growing to 1,200 mostly-redundant ones. Cost, runtime, and the attention people give the failure list all scale with size, and a suite nobody reads is a suite that does nothing.

## Versioning the set

The set is code. Version it accordingly:

```
evals/datasets/
  golden_v9.yaml        # current
  golden_v8.yaml        # kept; runs from July reference it
  anchor_v1.yaml        # frozen, never edited
  CHANGELOG.md
```

Every run records the dataset version. Comparing runs across versions is invalid, and the harness should refuse to compute a delta between different dataset versions rather than silently producing a meaningless number. That refusal is a small piece of engineering that prevents a whole class of confident wrong conclusions.

## Ownership

An eval set with no owner rots. Someone has to be responsible for the weekly addition, the quarterly review, and the judgement calls about what belongs.

At a startup this is the AI engineer, which is to say it is the person reading this. Worth saying explicitly in an interview, because it reframes evals from a task to a role:

> An eval set is an asset with a maintenance cost, and the failure mode is that everyone agrees it is important and nobody owns it. I would want to own it, and I would want the weekly loop to be a fifteen-minute habit rather than a quarterly project, because the examples that make a set worth anything come from production failures and those arrive continuously.

*Connect the dot:* `profile/learnings.md` in JobOps is exactly this asset — a maintained file of harvested lessons that every generating skill reads before producing anything, updated from outcomes rather than from memory. The discipline is already there; what is missing is the labelled set and the gate that turn lessons into a number.

Next: what to build and what to buy.
