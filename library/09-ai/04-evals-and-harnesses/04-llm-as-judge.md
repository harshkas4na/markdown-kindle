# LLM-as-Judge

**Fast overview:** For genuinely subjective quality — is this summary faithful, is this answer helpful, is this tone right — you need a judge, and the only judge that scales is another model. This chapter covers how to build one that works: pairwise versus absolute scoring, the four documented biases, rubric design, and the step that separates a real eval from a decorative one — **measuring the judge itself against human labels.** A judge nobody validated produces numbers nobody should act on.

## When you need one

Only when levels 0-3 genuinely cannot answer. That means:

- **Faithfulness** — is every claim supported by the provided context?
- **Relevance** — does the answer address the question asked?
- **Helpfulness / completeness** — would a user be satisfied?
- **Tone and voice compliance** — does this sound like us?
- **Comparative quality** — is A better than B?

Not: does it parse, does it contain the number, does the code run, did the action happen.

## Pairwise beats absolute

**Absolute scoring** — "rate this answer 1-10" — is what everyone builds first and it is weak. LLM scores cluster (almost everything gets a 7 or 8), they are not stable across runs, and they are not comparable across time because the judge's calibration drifts with the model version.

**Pairwise comparison** — "here are two answers, which is better and why" — is substantially more reliable. Relative judgements are easier than absolute ones, for models and humans alike, and the output is exactly what you need when comparing a prompt change to its baseline.

The cost is that pairwise does not give you a standalone number for a single system, and it is O(n²) if you want a full ranking of many variants. The usual compromise: **pairwise for comparisons** (the common case, since most evals compare a change against a baseline) and **rubric-based absolute scoring** for tracking a single system over time, with the calibration caveat understood.

## The four biases

Each is documented, each is measurable, and each has a mitigation. Being able to name them is a strong interview signal.

**1. Position bias.** In pairwise comparison, judges favour one position — often the first, sometimes the last — independent of content.
*Mitigation:* run every comparison twice with positions swapped. Agreement means a real preference; disagreement means a tie. This doubles cost and is non-negotiable.

**2. Verbosity bias.** Longer answers score higher, independent of quality. Preference training rewarded thoroughness.
*Mitigation:* state length expectations in the rubric, penalise unnecessary length explicitly, and check the correlation between length and score on your own data. If it is high, you are measuring length.

**3. Self-preference bias.** A model rates its own outputs, and outputs from its own family, more highly.
*Mitigation:* use a different model family as judge than as generator where possible. At minimum, know the bias exists before comparing two providers with a judge from one of them.

**4. Sycophancy / anchoring.** If the judge sees who produced what, or sees a previous verdict, it conforms.
*Mitigation:* **blind the judge.** No model names, no "this is the new version", no prior scores. Label them A and B, randomised.

A fifth worth knowing: **format bias** — confident, well-structured, bulleted answers score higher than equally correct prose. Same mitigation as verbosity: name it in the rubric and check the correlation.

## Writing the judge prompt

```python
JUDGE = """You are evaluating whether an answer is faithful to its sources.

An answer is FAITHFUL if every factual claim it makes is directly supported by
the sources below. An answer is UNFAITHFUL if it makes any claim that the sources
do not support, even if the claim happens to be true in general.

Saying "I don't know" or "the sources don't cover this" is FAITHFUL.
Stylistic quality, length and tone are irrelevant to this judgement.

<sources>
{sources}
</sources>

<answer>
{answer}
</answer>

Work through the answer claim by claim. For each claim, quote the sentence from
the sources that supports it, or write UNSUPPORTED.

Then output your verdict as JSON:
{{"unsupported_claims": [...], "verdict": "FAITHFUL" | "UNFAITHFUL"}}"""
```

Design points, each doing real work:

- **One dimension per judge.** A judge asked for faithfulness *and* helpfulness *and* tone gives you a blended number you cannot act on. Run three judges.
- **A definition, not an adjective.** "Faithful" is defined operationally, including the edge case (abstention counts as faithful).
- **Explicitly exclude confounds.** Saying "style is irrelevant" measurably reduces style bleeding into the score.
- **Reasoning before verdict.** Autoregression means the verdict field must come *after* the analysis (Book 01, Chapter 6). Reversed, you get a guess plus a rationalisation.
- **Ask for quoted evidence.** Requiring the judge to quote the supporting sentence makes its reasoning checkable by you, and measurably reduces hand-waving.
- **Discrete verdicts, not a 1-10 score**, wherever the dimension allows it. Binary and three-way judgements are far more stable.

Use a **reference answer** when you have one: "here is a known-good answer; does the candidate convey the same information?" is a much easier and more reliable question than judging in the abstract.

## Measuring the judge

**This is the step that separates a real eval from a decorative one, and almost nobody does it.**

A judge is a model with biases producing numbers. If you have not compared it against human judgement, you do not know what those numbers mean.

The procedure:

1. **Sample 50-100 examples** from your eval set, spanning the score range.
2. **Have a human label them** on the same dimension with the same rubric. The domain owner, not you.
3. **Compute agreement** between judge and human. Use Cohen's kappa for categorical verdicts (which corrects for agreement by chance) or correlation for graded scores.
4. **Read every disagreement.** This is where the value is. Disagreements usually reveal that the *rubric* is ambiguous, not that the judge is bad — and fixing the rubric improves human consistency too.
5. **Iterate the judge prompt** until agreement is acceptable. Kappa above 0.6 is usable; above 0.8 is strong. Below 0.4, your judge is measuring something else.
6. **Re-validate whenever the judge model version changes.** Otherwise your metric silently redefines itself.

Two things this buys beyond confidence. It gives you a **stated error bar** on your own metric, so you can say "faithfulness 0.91, and my judge agrees with a human 86% of the time" — which is a far more credible sentence than a bare number. And it gives you the **human-agreement ceiling**: if two humans only agree 80% of the time, expecting a judge to hit 95% is incoherent, and the task definition is the problem.

## Practical guidance

- **Temperature 0** for judges, always.
- **Use a strong model.** Judging is harder than generating. Saving money on the judge is a false economy; the judge is a measuring instrument.
- **Version the judge prompt** and record it in every run. A changed judge changes every historical number, and comparing across a judge change is invalid.
- **Do not gate CI on a judge score alone.** Combine with deterministic scorers, and treat judge movements smaller than the judge's own noise as noise. Run the judge twice on a sample to estimate that noise.
- **Cache judge results** keyed by (judge version, input, output). Re-running an unchanged eval should not re-pay for judging.

## The failure to avoid

Building the judge, getting a number, putting it on a dashboard, and treating it as truth. The number is an estimate produced by an unvalidated instrument with known biases, and treating it as ground truth is how teams optimise their prompts for their judge's preferences rather than for their users.

The discipline is the same as any measurement: **calibrate the instrument, state its error, and be suspicious of movements smaller than its noise.**

*Connect the dot:* Book 03's rule about reflection — that self-critique without an external signal measures the model's agreeableness rather than the output's quality — is the same principle. A judge grounded in sources and a rubric has an external signal. A judge asked "is this good?" does not.

Next: how many examples you actually need, and when a difference is real.
