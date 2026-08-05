# The Whole Story in Ten Minutes

**Fast overview:** This is the book that matters most. Not because evals are the most interesting topic on the shelf, but because the application corpus says, repeatedly and in the companies' own words, that this is the thing the seat exists to do. This chapter compresses the whole discipline: what an eval is, the one idea that makes a suite worth anything, the five components of a harness, and the argument that connects measurement to cost control and model migration.

## What an eval is

A dataset of inputs with known-good outcomes, plus a scorer, plus a runner, plus a report. That is all.

The confusion comes from the word covering four different activities that share machinery:

| Kind | Question it answers | When it runs |
|---|---|---|
| **Assertions** | Does the output satisfy hard rules? | Every change, seconds |
| **Golden-set eval** | Is the output good, against labelled data? | Every change, minutes |
| **Online eval** | Is production output good on real traffic? | Continuously, sampled |
| **A/B test** | Does variant B beat A on a product metric? | Days to weeks |

You need all four eventually, in that order of construction, and the first one is nearly free.

## The one idea

**A test suite made only of cases that should pass measures almost nothing.**

This is the most important sentence in the book and it comes from his own repo. The JobOps scouts matched keywords with a bare `includes()`, so `rag` matched *sto·rag·e*, `defi` matched *undefined*, and `go` matched *going*. The bug survived across 178 leads. Tests existed. Every test was a positive case — a keyword that should match, matching — and every one of them still passed, because the bug never broke a positive case. It was caught only when someone wrote an assertion that a **known-bad pair does not match**.

Generalised: a scorer, a golden set or a guardrail has power in proportion to the cases it could fail. Forty easy lookups prove that the easy path works, which nobody doubted. The examples that earn their place are the ones the current system gets wrong, the ones near a boundary, and the ones that should return nothing at all.

Every design decision in this book descends from that sentence.

## The five components

**1. The dataset.** Inputs with expected outcomes, sliced, dated, provenance-tagged. Forty examples is enough to make decisions; 150-300 is enough to trust the number. Built by hand, by the person who knows what right looks like.

**2. Scorers.** Deterministic where possible — schema validity, exact match, contains, regex, citation resolves, latency under budget. Judges only where the quality is genuinely subjective. Cheap scorers first, always.

**3. The runner.** Executes the dataset against a versioned configuration, in parallel, saving every artifact. Records the config hash: model, prompt version, temperature, retrieval settings.

**4. The report.** Aggregate **and per slice**. The aggregate on its own is the single most common way an eval suite lies to a team.

**5. The gate.** In CI, on every change to prompts, retrieval or config. Absolute floors and relative drops, on the aggregate and on slices.

## Why this is a business concern, not an engineering nicety

Three arguments, and being able to make all three is what makes an eval answer sound senior rather than dutiful.

**Cost.** The correct model is the smallest that passes your eval. Without an eval, "is the cheap model good enough" is unanswerable, so teams pay for the expensive one out of fear. **No eval means no cost control**, permanently.

**Migration.** A model version changes under you. With a suite, migration is an afternoon and a table. Without one, it is a fortnight of anxiety and a rollback.

**Velocity.** Without an eval, every prompt change is a gamble, so people stop changing prompts. The suite is what makes iteration safe, and iteration is where quality comes from.

That third one is the argument that lands with founders: **evals do not slow you down, they are the thing that lets you go fast without breaking what already works.**

## The traps

Named here, unpacked later:

- **The aggregate that lies.** A change lifts the mean and destroys one slice. Report per slice or you will ship it.
- **Judging with a judge nobody measured.** An LLM judge is a model with biases. If you have not compared it against human labels on a sample, you do not know what your numbers mean.
- **Evaluating on the data you tuned on.** Hold out a test split.
- **Single-example comparison.** Prompts are sensitive enough that one example proves nothing. Book 01, Chapter 4.
- **Under-powered comparison.** Twenty examples cannot detect a three-point difference. Chapter 5 does the arithmetic.
- **The stale set.** Scenr's dossier says it best: the library is the only source of truth for ninety days, by which time the model, the prompt and the corpus have all moved.
- **Measuring only the final answer** on an agent, where the answer can be right for the wrong reasons.

## What this book covers

| Ch | Topic |
|---|---|
| 1 | Why evals are the bar in this corpus, in the companies' own words |
| 2 | Building the golden set: sources, size, labelling, hard cases |
| 3 | Scorers, deterministic first |
| 4 | LLM-as-judge: biases, rubrics, and measuring the judge |
| 5 | How many examples, and when a difference is real |
| 6 | Slices, and the aggregate that lies |
| 7 | The harness and the regression gate in CI |
| 8 | Evaluating RAG, end to end |
| 9 | Evaluating agents and trajectories |
| 10 | Online evaluation and A/B tests |
| 11 | Drift, and maintaining the set as an asset |
| 12 | Tooling: what to build and what to buy |
| 13 | The first ninety days, which seven dossiers already promised |
| 14 | What you can now honestly say |

Next: the case, made from the corpus itself.
