# Building the Golden Set

**Fast overview:** The dataset is 80% of the work and 100% of the value. Everything else — scorers, runners, dashboards — is machinery around it, and machinery around a bad dataset produces confident wrong numbers. This chapter covers where examples come from, how many you need, who labels them, what an example contains, and the composition rule that decides whether the set has any power at all.

## The composition rule

Start here, because it governs everything else.

**An eval set's power is proportional to the fraction of its examples that the current system could fail.**

Forty examples the system already handles perfectly measure nothing except that the happy path works. The set earns its keep through examples that are hard, ambiguous, adversarial, or supposed to return nothing.

A rough target composition:

| Category | Share | Why |
|---|---|---|
| Representative / typical | 40% | The distribution you actually serve |
| Hard but valid | 25% | Where quality differences show up |
| Should-fail / out-of-scope | 15% | The system must decline, not invent |
| Adversarial | 10% | Injection, contradiction, manipulation |
| Regression cases from real incidents | 10%, growing | Permanent protection against repeats |

That third row is the `learnings.md` lesson made structural. A support bot must answer "what is the refund window" and must **not** answer "what will your stock price be next year". If your set has no examples of the second kind, you have no evidence the system knows its own boundaries — and boundary violations are what embarrass companies.

## Where examples come from

In descending order of value:

**1. Real production traffic.** The gold standard, and available only once you have users. Sample across the distribution and **deliberately over-sample the tail**: the longest queries, the ones with lowest confidence, the ones users rephrased or regenerated.

**2. Real failures.** Every incident, complaint, thumbs-down and human rejection becomes an example. This is the highest-value stream that exists, and it is free. A rejection with a reason (Book 03, Chapter 9) is already a labelled failure case.

**3. Domain experts.** For a new product, the person who *is* the authority — the support lead, the compliance officer, the founder — writing thirty questions they know are hard. An hour of their time is worth a week of yours.

**4. Synthetic generation.** For each of N sampled documents or scenarios, ask a model to generate a question it answers, or a plausible user request.

Synthetic data has a documented bias: generated questions borrow the source's vocabulary, so they are easier than real ones and inflate your score. Use it to bootstrap on day one, replace it as traffic arrives, and **tag provenance on every example** so you can report synthetic and real separately. A number that moved only on the synthetic slice has not moved.

## How many

- **20** — below this you are measuring noise. Do not make decisions on it.
- **40** — enough to make a directional decision between two configurations. This is the "you have no excuse" number: one afternoon.
- **150-300** — enough to trust the aggregate and to slice it into four or five meaningful groups with 30+ examples each.
- **1,000+** — enough to detect small effects and to slice finely. Rarely worth building by hand; usually accumulated.

The arithmetic behind this is Chapter 5. The practical rule: **build 40 today rather than 300 next quarter.** An imperfect set that exists beats a perfect one that does not, and the first 40 will teach you what the next 100 should contain.

## Who labels

This is a governance question, not a technical one, and getting it wrong invalidates everything.

**The labeller must be the authority on correctness for that domain.** For a legal product, a lawyer. For a support bot, the support lead. For a screening ranker, whoever owns the hiring standard. An engineer labelling a domain they do not own produces a set that measures the engineer's guesses.

The practical version at a startup: the engineer drafts labels, the domain owner reviews and corrects in a spreadsheet, and disagreements get resolved and **written down as a rubric**. That rubric is a real artifact — it is what makes labels consistent over time and it is the input to the judge prompt in Chapter 4.

**Measure inter-annotator agreement** on a sample if more than one person labels. If two experts disagree on 30% of examples, no model will do better than 70% and you have just discovered that your task definition is ambiguous. That discovery is worth more than the eval.

## What an example contains

```yaml
- id: ev_0142
  input:
    query: "Can I get a refund on my annual plan after 45 days?"
    context: {plan: annual, purchased: "2026-06-01"}
  expected:
    outcome: refuse
    must_contain: ["30 days"]
    must_not_contain: ["yes", "we can process"]
    reference_answer: >
      No. Annual plans have a 30-day refund window and this purchase is 45 days old.
      Offer a pro-rated credit instead.
  slices: [policy, refusal, annual-plan]
  provenance: real-user
  difficulty: hard
  added: 2026-08-04
  source_incident: INC-221
  notes: >
    The system said yes here in production because it retrieved the 2024 policy,
    which had a 60-day window. Tests the recency preference, not just the answer.
```

Every field earns its place:

- **`expected.outcome`** as a category, not just prose, so a deterministic scorer can check it.
- **`must_contain` / `must_not_contain`** are free, deterministic, and catch a surprising share of regressions with no judge call.
- **`reference_answer`** for a judge to compare against, which is far more reliable than judging in the abstract (Chapter 4).
- **`slices`** — the most important field after the input. Chapter 6.
- **`provenance`** and **`difficulty`** so you can report subsets honestly.
- **`added`** so a stale set is visible.
- **`notes`** capturing *why the example is hard*, which is the thing that gets lost and the thing a future maintainer needs.

Store it as YAML or JSONL **in the repo, in version control**, reviewed in PRs. Not in a spreadsheet somebody owns, not in a SaaS tool you cannot diff. The dataset is code and it should be treated as code, including a version tag so a result from March is reproducible.

## Splitting

Once the set is over ~100 examples, split it:

- **Dev set** (~70%) — look at it constantly, tune against it.
- **Test set** (~30%) — look at it rarely, ideally only before a release.

The reason is ordinary overfitting. If you tuned chunk size, the prompt and the reranker against the same 200 examples, your score on those 200 no longer predicts anything about new inputs. The test split is what tells you whether the improvements generalised.

At 40 examples, splitting is not viable and you accept the overfitting risk knowingly. Say so out loud rather than pretending.

## Bootstrapping when you have nothing

Day one at a new company, no traffic, no labels. The sequence:

1. **Read whatever exists** — support tickets, sales call notes, the FAQ, Slack. Real questions are already written down somewhere.
2. **Write 20 examples yourself** in an hour, guessing at correctness.
3. **Take them to the domain owner** and have them correct you. This meeting is worth more than the examples: their corrections *are* the rubric.
4. **Generate 40 synthetic examples** from the corpus to fill coverage gaps, tagged as synthetic.
5. **Run the current system** against all 60 and read every failure. This is the fastest way to understand a product you just joined, and it produces the first honest quality number the company has had.
6. **Ship the number**, with its caveats, in week one.

Step 6 is the political move that matters. A number, however rough, changes the conversation from opinion to evidence, and it is what the dossiers' "first 90 days" plans are all reaching for.

*Connect the dot:* the "should-fail" category is the `includes()` bug generalised. The `reachability.test.mjs` backtest in JobOps — which asserts that no historical A/B lead is lost by the geo filter, and must stay at zero — is exactly a should-fail eval, already built. That is a legitimate thing to point at.

Next: scorers, and why the cheap deterministic ones come first.
