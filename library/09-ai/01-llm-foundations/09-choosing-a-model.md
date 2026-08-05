# Choosing a Model

**Fast overview:** "Which model should we use" is asked as a taste question and should be answered as an engineering one. This chapter gives the decision procedure — start from the task and the constraints, not from the leaderboard — explains why public benchmarks mislead, covers routing and fallback as the architecture most production systems converge on, and makes the case for the rule that the correct model is the smallest one that passes your eval.

## Start from constraints, not from capability

Four constraints usually decide the answer before capability enters the room:

1. **Where can the data go?** If it cannot leave your infrastructure, the shortlist is open models, self-hosted, and everything else is moot.
2. **What is the latency budget?** A 700ms voice turn eliminates large reasoning models regardless of how good they are.
3. **What is the volume?** A million requests a day at frontier prices is a budget conversation with a founder, not an engineering decision.
4. **What structure or capability is non-negotiable?** Reliable tool calling, a vision input, a 200k context, guaranteed-conformant structured output. Any of these can rule out otherwise attractive options.

Only what survives all four gets evaluated on quality.

## Why leaderboards mislead

Public benchmarks are useful for a shortlist and dangerous as a decision:

- **Contamination.** Popular benchmarks leak into training data. A high score can partly measure memorisation.
- **Overfitting to the benchmark.** When a number becomes a target it stops measuring the thing.
- **Distribution mismatch.** MMLU measures academic knowledge; your task is extracting fields from invoices. The correlation is real and loose.
- **Arena-style human preference measures preference**, which includes formatting, length and agreeableness. A model that writes prettier answers wins even when it is less accurate.
- **They are averages.** Averages hide exactly the per-slice behaviour that matters. A model can be better overall and much worse on your one important category.

The correct use: shortlist three models from the leaderboards, then run **your** golden set. Fifty labelled examples of your real task settle a question that a month of forum reading will not. This is the same argument as Book 02's on embedding models, and it recurs because it is the central methodological point of this whole shelf.

## The tiers, and what each is for

Roughly three tiers exist across every provider, and thinking in tiers rather than in model names keeps your reasoning portable as names change every few months:

| Tier | Good for | Bad for |
|---|---|---|
| **Small/fast** | Classification, routing, extraction with a clear schema, reranking-ish scoring, high-volume simple generation, guardrail checks | Multi-step reasoning, ambiguous instructions, long-context synthesis |
| **Mid** | The default for most product work: RAG answering, summarisation, tool calling, agent steps | Genuinely hard reasoning, competitive coding |
| **Frontier / reasoning** | Hard analysis, complex multi-file code changes, planning, anything where being wrong is expensive and volume is low | Anything latency-sensitive or high-volume |

**Open-weight models** cut across these tiers and are chosen for control rather than capability: data residency, cost at high steady volume, fine-tuning, and no dependency on a provider's roadmap. The quality gap to closed frontier models has narrowed enough that "we cannot use open models" is no longer a defensible default position, and it is still true that the very top of the capability range is closed.

## Routing, which is where most systems end up

Most mature LLM products are not one model. They are a router:

```python
def answer(query, context):
    difficulty = classify(query)          # small model or a heuristic
    if difficulty == "simple":
        r = call(SMALL, query, context)
        if confident(r):                  # schema-valid, cites, no escape token
            return r
    return call(MID, query, context)      # escalate
```

Three ways to build the router, in ascending order of cost:

- **Heuristics.** Query length, presence of certain intents, whether tools are needed, which customer tier. Free, surprisingly effective, and where to start.
- **A small classifier model.** One cheap call to decide the route. Adds latency; often worth it.
- **Cascade with verification.** Always try cheap first, escalate when a check fails. Best quality-per-cost, worst tail latency, because the escalated path pays for both calls.

The verification step is the interesting part. What counts as "confident"? Schema validity, whether the model emitted your `NOT_FOUND` escape token, agreement across two samples (Chapter 4), a cheap judge model, or a business rule. Designing that check well is most of the engineering, and it is a good thing to be asked about because there is no default answer.

## Fallback, which is not the same thing

Routing optimises cost. **Fallback** handles failure: the provider is down, rate-limiting you, or timing out. Any user-facing feature needs a second path, and the second path should be a different *provider*, not just a different model from the same one, because outages are usually provider-wide.

This requires an abstraction over providers, which every framework offers and which is roughly thirty lines to write yourself. Writing it yourself is often correct, because the frameworks' abstractions leak exactly where the providers differ — tool calling formats, structured output modes, caching semantics — and those differences are the ones you care about.

## Pinning versions

Model names behind an API can point at changing weights. Two rules:

1. **Pin the dated/explicit version in production.** Behaviour changing under you without a deploy is the worst kind of incident because nothing in your change log explains it.
2. **Run your eval suite against the new version before switching**, and diff per-slice. This is the concrete reason the harness in Book 04 pays for itself: model migration goes from a fortnight of anxiety to an afternoon of running a suite and reading a table.

Log the resolved model version in every trace regardless.

## The rule

**The correct model is the smallest one that passes your eval.**

Not the best one you can afford. Not the one on the top of the leaderboard. The smallest that passes, because everything above that threshold is cost and latency you are paying for nothing.

This rule is only executable if the eval exists. Without it, "is the small model good enough" is unanswerable, so teams default to the expensive model out of fear, and pay 20x forever for a margin nobody has measured. That connection — **no eval means no cost control** — is worth stating explicitly in an interview, because it links the two things these JDs care about most and shows you understand why evals are a business concern rather than an engineering nicety.

*Connect the dot:* airCFO, EON and Certa all have JD language about production reliability and cost; the routing architecture in this chapter is the concrete answer to what an AI engineer does about it in week two, after the harness from week one exists.

Next: the failure modes, and what each one is actually caused by.
