# How Many Examples, and When a Difference Is Real

**Fast overview:** "Prompt B scored 84% and prompt A scored 80%, so B is better" is the most common false conclusion in this field. With 50 examples, that gap is well inside noise. This chapter does the arithmetic — enough of it to size a dataset, to know when a result is real, and to answer the question properly when an interviewer asks. It is the chapter that makes the difference between running evals and doing evaluation.

## Why this matters more here than elsewhere

Two sources of variance stack:

1. **Sampling variance.** Your 50 examples are a sample from the space of possible inputs. A different 50 would give a different number.
2. **Model variance.** The same input produces different outputs across runs, even at temperature 0 (Book 01, Chapter 4).

Ordinary software tests have neither. That is why eval results need statistics and unit tests do not, and it is why "it worked when I tried it" is not evidence.

## The confidence interval on a pass rate

For a pass rate `p` measured over `n` examples, the standard error is:

```
SE = sqrt( p × (1 − p) / n )
```

and a 95% interval is roughly `p ± 1.96 × SE`.

| n | p = 0.80 | 95% interval | Width |
|---|---|---|---|
| 20 | 0.80 | 0.62 – 0.98 | ±18 pts |
| 50 | 0.80 | 0.69 – 0.91 | ±11 pts |
| 100 | 0.80 | 0.72 – 0.88 | ±8 pts |
| 300 | 0.80 | 0.755 – 0.845 | ±4.5 pts |
| 1000 | 0.80 | 0.775 – 0.825 | ±2.5 pts |

Read the second row again. **With 50 examples, a measured 80% could really be 69% or 91%.** Any comparison of two configurations differing by less than about ten points on 50 examples is uninterpretable.

Report intervals, not point estimates. `0.80 ± 0.11 (n=50)` is honest; `80%` implies a precision you do not have.

## Comparing two configurations

The naive approach compares two independent proportions and needs large samples. There is a much better way, and it is the one to know.

**Use paired comparison.** Both configurations run on the *same* examples, so example difficulty cancels out. What matters is only the examples where they **disagree**.

**McNemar's test**: let `b` = examples A passed and B failed, `c` = examples B passed and A failed. Under the null hypothesis they are equal.

```python
from statsmodels.stats.contingency_tables import mcnemar
# table: [[both pass, A pass B fail], [A fail B pass, both fail]]
print(mcnemar([[38, 4], [10, 8]], exact=True))
```

Here A and B agree on 46 of 60 examples; of the 14 disagreements, B wins 10 and A wins 4. Pairing means you are testing 14 observations, not 60, which is far more powerful than comparing 80% against 70% independently.

For graded scores rather than pass/fail, the paired equivalents are a paired t-test or, better for non-normal score distributions, a **bootstrap**:

```python
def bootstrap_diff(a_scores, b_scores, n=10_000):
    diffs = np.array(b_scores) - np.array(a_scores)      # paired
    means = [np.mean(np.random.choice(diffs, len(diffs), replace=True))
             for _ in range(n)]
    return np.percentile(means, [2.5, 97.5])
```

If the interval excludes zero, the difference is real at that level. Bootstrap is the practical default: it makes no distributional assumptions, it is ten lines, and it works for any metric including weird composite ones.

## Sizing the dataset

Work backwards from the smallest difference you care about.

- To reliably detect a **10-point** difference: roughly 100-200 examples.
- To detect **5 points**: roughly 400-800.
- To detect **2 points**: thousands.

Which yields the practical guidance:

- **40-60 examples** is a *screening* tool. It reliably catches large regressions and big wins. That is genuinely useful and it is what you build first.
- **150-300** is a *decision* tool for typical changes, and supports four or five slices.
- **Anything below 20** should not produce a decision.

**The corollary people miss:** if your change only moves the metric by two points on 200 examples, you cannot tell whether it helped, and you should probably ship the simpler option. Small unverifiable improvements are not worth their complexity.

## Handling model non-determinism

Two configurations may differ only because of sampling. Defences:

- **Temperature 0 everywhere in the eval**, unless the eval is specifically about diverse output.
- **Run each example k times** (k = 3-5) and score the mean or the majority for tasks with a discrete answer. Multiplies cost, and it converts model variance from a confound into a measured quantity.
- **Report the variance.** A configuration that scores 0.85 ± 0.02 across repeats is more trustworthy than one at 0.87 ± 0.15, and the second one's extra two points are worthless.

**Measure your own noise floor once.** Run the *identical* configuration twice on the full set and look at the difference. That number is the smallest movement you are entitled to believe. If re-running the same config gives you ±3 points, then a 2-point "improvement" is nothing. Doing this once, and knowing the number, is one of the most credible things you can say about your own harness.

## Multiple comparisons

Test twelve prompt variants at p < 0.05 and roughly one will look significant by chance. This is how teams convince themselves a variant works and then watch it fail in production.

Defences: **pre-register** which variant you expect to win and why; apply a correction (Bonferroni is crude and fine — divide your threshold by the number of comparisons); or treat multi-variant sweeps as *exploration* that generates a hypothesis, then confirm the winner on the held-out test split.

## Online A/B tests need much more

Offline eval measures a metric you chose on data you curated. An online A/B measures user behaviour, which is far noisier: baseline conversion rates are low, variance is high, and effects are small.

Rough sense of scale: detecting a 1-point absolute lift on a 10% baseline conversion rate takes on the order of tens of thousands of users per arm. Most startups do not have that traffic, and the honest consequence is that **many product-level A/B tests at an early-stage company are under-powered and will not conclude.**

That is not an argument against running them. It is an argument for choosing metrics closer to the change — a proxy with higher base rate, like citation rate, escalation rate, or regeneration rate, will move detectably where revenue will not. Chapter 10 covers this.

## The answers to have ready

Two questions come up, and clean answers to both are disproportionately impressive:

> **"How many examples do you need?"**
> Depends on the difference I need to detect. Forty is a screening tool that catches big regressions and is worth having on day one. A hundred and fifty to three hundred is where I would want to be before making decisions on typical changes, because below that the confidence interval on a pass rate is wider than most of the changes I care about.

> **"Prompt B scored four points higher. Ship it?"**
> Not yet. On fifty examples that is inside noise. I would want the paired comparison rather than the two aggregates, because pairing removes example difficulty and gives much more power on the same data, and I would want to know my harness's own noise floor from re-running the same config twice. If the disagreement pairs favour B significantly and the slices are not hiding a regression, then yes.

*Connect the dot:* the `x-ops` finding — 12 posts read, 0 passing a keyword filter — is a tiny sample and it was still decisive, because the effect was total rather than marginal. That is the correct use of a small sample: it can prove something is badly broken, and it cannot adjudicate a four-point difference. Knowing which situation you are in is the skill.

Next: slices, and the aggregate that lies.
