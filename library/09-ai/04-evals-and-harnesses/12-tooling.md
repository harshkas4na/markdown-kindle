# Tooling: What to Build and What to Buy

**Fast overview:** There is a healthy market of eval and observability tools, and the question of which to use is asked far more often than it matters. This chapter covers what the categories actually do, what a hosted tool genuinely buys you, why the first version should almost always be a few hundred lines of your own code, and what to look for when you do adopt something.

## The categories

**Tracing and observability.** Capture every LLM call, tool call and chain step as a span, store them, make them searchable. LangSmith, Langfuse, Phoenix/Arize, Braintrust, and the OpenTelemetry GenAI conventions underneath several of them. This is the category worth adopting earliest, because building good trace capture and a UI to browse it is real work with no product differentiation.

**Eval frameworks.** Dataset management, scorers, runners, comparison views. Ragas (RAG-specific metrics), DeepEval, promptfoo (config-driven, CI-friendly), OpenAI Evals, plus the eval halves of the platforms above.

**Prompt management.** Versioning, deployment, A/B routing. Occasionally useful, and frequently a way to move prompts *out* of version control, which is a step backwards. Prefer prompts in the repo.

**Annotation and human labelling.** Queues, rubrics, agreement measurement. Matters once more than one person labels.

**Guardrail libraries.** Covered in Book 05.

## What a hosted tool actually buys you

Be specific, because the honest list is shorter than the marketing and still real:

1. **A trace UI you did not build.** Browsing nested spans, filtering by metadata, diffing two runs. This is the biggest single item.
2. **A dataset UI non-engineers can use.** Your domain expert labelling in a proper interface rather than a spreadsheet you then parse.
3. **Comparison views** across runs, models and prompt versions.
4. **Annotation queues** with agreement tracking.
5. **Production sampling and online judging** wired up already.
6. **Integrations** with the frameworks you use.

Items 2 and 4 are the underrated ones. **The bottleneck in eval work is usually human labelling, not compute**, and a tool that makes a non-engineer productive at labelling is worth more than one with better metrics.

## What to build yourself first

The first version should be your own, for a reason that is not ideological: **building it teaches you what you actually need**, and the requirement usually turns out to be simpler and more specific than any tool's model of it.

A complete first harness is roughly:

```
evals/
  datasets/golden_v1.yaml     # the actual work
  scorers.py                  # ~150 lines
  runner.py                   # ~100 lines
  report.py                   # ~100 lines
  gate.py                     # ~60 lines
  policy.yaml
```

Four hundred lines, one day, and it does everything in Chapters 3 through 7. It also stays yours, so a scorer specific to your domain is a function rather than a plugin.

**Adopt a tool when you hit a specific wall:**

- Non-engineers need to label → dataset UI.
- You are reading traces in a text file → tracing platform.
- Multiple people annotate and disagree → annotation queue with agreement tracking.
- You need online judging on production at volume → the sampling and judging infrastructure.

Not before. "We should use an eval platform" as a starting position usually produces a platform in place of a dataset, which is exactly backwards. **The dataset is the asset; the tool is a viewer.**

## Choosing, if you do

| Question | Why it matters |
|---|---|
| Does it run in CI, headless, with a non-zero exit code? | A tool that only produces a dashboard cannot gate a merge |
| Can I export my data? | Datasets and traces are your assets. Lock-in here is expensive |
| Can I write custom scorers in ordinary code? | Every real product needs a domain-specific scorer |
| Does it support slices and per-slice gates? | Chapter 6. Many tools report only aggregates |
| Self-hostable? | Traces contain customer data and often cannot leave |
| Does it version datasets and record config with runs? | Chapter 7. Reproducibility is not optional |
| What is the pricing model at our trace volume? | Per-trace pricing at production volume surprises people |

The first row is the sharpest filter. A large fraction of eval tools are dashboard-first and CI-second, and a gate that cannot fail a build is a report, not a gate.

## Standards worth knowing

**OpenTelemetry GenAI semantic conventions** define standard span attributes for LLM calls — model, tokens, cost, prompt, completion. Instrumenting to that standard rather than to a vendor's SDK means your traces are portable, and it is the right default for anything you build yourself. It also means your LLM traces sit in the same system as the rest of your service traces, which is where they belong: an LLM call is one span in a request, not a separate universe.

## The pragmatic recommendation

A defensible stack for a small team:

- **Tracing:** adopt a platform, self-hosted if data residency demands it. Instrument to OTel conventions.
- **Datasets:** YAML in the repo, reviewed in PRs. Add a tool's UI later if a non-engineer needs to label.
- **Scorers:** your own code. Borrow metric *definitions* from Ragas and similar; own the implementations.
- **Runner and gate:** your own, in CI, posting the slice table as a PR comment.
- **Online judging:** the tracing platform's sampling, or a cron job over sampled traces.

And the answer to give when asked:

> I would build the first harness myself, because it is about four hundred lines and building it is how you find out what you actually need to measure. I would adopt a tracing platform early, because browsing spans in a text file does not scale and that UI is genuinely hard to build. And I would keep the datasets as files in the repo regardless of what tool we use, because the dataset is the asset and I do not want it living somewhere I cannot diff in a pull request.

*Connect the dot:* the same instinct runs through Book 02 on frameworks and Book 03 on LangChain — own the layer where your product's specificity lives, borrow the commoditised layers. For evals, your specificity is the dataset and the scorers; the viewer is commodity.

Next: the ninety-day plan the dossiers already promised seven companies.
