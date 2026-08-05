# Evaluating Retrieval

**Fast overview:** This is the chapter the rest of the book exists for. Without it, every decision in Chapters 2 through 10 is a preference. With it, each one becomes a measurement, and the sentence "I improved recall@5 from 0.61 to 0.83 by adding a reranker, at 240ms of p95" becomes available to you. This chapter builds the golden set, defines the metrics that matter and the ones that mislead, separates retrieval scoring from generation scoring, and turns the whole thing into a harness that runs in CI.

## The one idea

**Measure retrieval separately from generation.**

If the only number you have is "was the answer good", then when it is bad you cannot tell whether the right chunk was never retrieved or was retrieved and ignored. Those have completely different fixes, and teams that do not separate them spend months tuning generation prompts for a retriever problem.

Split it into two questions with two datasets:

1. **Did the right material come back?** → recall@k, MRR, nDCG. Needs (query → correct chunk ids).
2. **Given that material, was the answer good?** → faithfulness, answer relevance, correctness. Needs (query, context → good answer).

**Recall@k is the gate.** If the answer is not in the retrieved set, nothing downstream can fix it. Fix recall first.

## Building the golden set

The afternoon that pays for everything.

### Where the queries come from

In descending order of value:

1. **Real user queries**, if you have traffic. Sample across the distribution, and deliberately over-sample the hard tail.
2. **Questions from the people who own the domain** — support staff, the founder, the subject expert. They know what gets asked.
3. **Synthetic questions generated from chunks.** For each of N sampled chunks, ask a model "what question would this chunk answer?" This gives you (query, known-correct-chunk) pairs for free, which is exactly the labelling you need.

Synthetic data has a known bias: generated questions use the chunk's own vocabulary, so they are easier than real questions and inflate your recall. Use it to bootstrap, then replace it with real queries as traffic arrives, and **label every example with its provenance** so you can report the two separately.

### How many

- **40 is enough to make decisions.** It will detect the difference between a good change and a bad one.
- **150-300 is enough to trust the number** and to slice it meaningfully.
- **Below 20, you are measuring noise.**

Start at 40. The perfect eval set you never build is worth nothing compared to the imperfect one you have on Thursday.

### What each example contains

```yaml
- id: q_017
  query: "What is the refund window for annual plans?"
  relevant_chunk_ids: ["c_8812", "c_8813"]      # the ground truth
  expected_answer: "30 days from the purchase date."
  answer_must_contain: ["30 days"]
  slice: ["policy", "simple-lookup"]
  provenance: real-user
  added: 2026-08-03
  notes: "Also appears in the 2024 policy with 14 days — must prefer current."
```

Every field earns its place. `relevant_chunk_ids` makes retrieval measurable. `slice` makes per-slice reporting possible, which is the most important reporting feature there is. `added` lets you detect a stale set. `notes` captures why the example is hard, which is the thing that gets lost.

### Cover the hard cases deliberately

A set of 40 easy lookups measures nothing, for exactly the reason the `includes()` keyword bug from `learnings.md` survived 178 leads: **every positive case still passed.** Only an example that *should* fail under the current system tells you anything.

So deliberately include: questions with no answer in the corpus (expected `NOT_FOUND`), questions whose answer spans two documents, questions about superseded material where the current version must win, identifier queries, negation queries, follow-up questions with pronouns, and questions phrased in vocabulary the corpus never uses.

## The retrieval metrics

Given retrieved list `R` (ordered) and ground-truth set `G`:

**Recall@k** — the fraction of relevant chunks that appear in the top k. The primary metric, because it is the ceiling.

```python
def recall_at_k(retrieved, relevant, k):
    return len(set(retrieved[:k]) & set(relevant)) / len(relevant)
```

**Precision@k** — the fraction of the top k that are relevant. Matters because irrelevant chunks are distractors that cost context and quality. Usually secondary to recall.

**MRR (mean reciprocal rank)** — `1/rank` of the first relevant result, averaged. Good when there is one right answer and position matters.

**nDCG@k** — discounted cumulative gain, normalised. The right metric when relevance is graded rather than binary (this chunk is perfect, that one is partially useful) and when position matters throughout the list. Heavier to label; use it when you have graded judgments, and MRR when you do not.

**Hit rate@k** — did *any* relevant chunk appear. Coarse and useful as a headline.

Report **recall@k for several k**. The curve is more informative than any single number: recall@5 tells you what the generator sees, recall@50 tells you what a reranker has to work with, and the gap between them is exactly the value a reranker can add.

## The generation metrics

Given the retrieved context and the produced answer:

**Faithfulness / groundedness.** Is every claim in the answer supported by the context? The most important generation metric, because an unsupported claim is a hallucination regardless of whether it happens to be true. Measured by decomposing the answer into claims and checking entailment against the context, usually with a judge model (Book 04).

**Answer relevance.** Does the answer address the question asked? Catches the failure where the model answers a nearby question.

**Answer correctness.** Compared against `expected_answer`. Use `answer_must_contain` assertions for cheap deterministic checking where a specific fact must appear, and a judge for the general case.

**Context precision/recall as seen by the answer.** Did the answer use the relevant chunks, or the distractors? Useful for diagnosing whether extra retrieved chunks are helping or hurting.

**The escape-hatch metrics**, which are cheap, deterministic, and underrated:

- **NOT_FOUND rate** on questions that *have* answers — this is a retrieval failure indicator.
- **NOT_FOUND rate** on questions that do not — this should be near 1.0, and if it is not, the system is fabricating.
- **Citation validity rate** — do cited ids exist.

Those three need no judge model, run in milliseconds, and catch a surprising share of real regressions.

## The harness

```python
@dataclass
class Result:
    id: str; slice: list[str]
    recall_5: float; recall_50: float; mrr: float
    faithful: float; correct: bool
    latency_ms: float; cost_usd: float

def run(dataset, pipeline) -> list[Result]:
    return [evaluate(ex, pipeline) for ex in dataset]     # parallelise this

def report(results):
    print(agg(results, "ALL"))
    for s in all_slices(results):
        print(agg([r for r in results if s in r.slice], s))
```

Requirements that make it useful rather than decorative:

- **Deterministic ordering and a fixed dataset version**, so two runs are comparable.
- **Per-slice output always**, not on request. The aggregate hides everything.
- **Latency and cost per example**, so quality is never evaluated in isolation from what it costs.
- **Full artifacts saved per run** — the retrieved ids, the assembled prompt, the answer — so a regression can be inspected rather than just observed.
- **A run id and a config hash** recording the model, prompt version, chunk size, k, and reranker. Otherwise you cannot reproduce your own result from last month.

## The regression gate

```yaml
# CI, on any change to prompts/, retrieval/, or config
- run: python -m evals.run --dataset golden_v7 --out results.json
- run: python -m evals.gate --baseline main --results results.json \
        --min recall_5=0.80 --min faithfulness=0.90 \
        --max-drop recall_5=0.02 --max p95_latency_ms=1500
```

Two kinds of threshold, and you want both. **Absolute floors** ("recall@5 must be at least 0.80") stop the system shipping below a known-acceptable bar. **Relative drops** ("must not fall more than 0.02 versus main") catch the change that is still above the floor and is nonetheless a regression.

Gate on slices too, not just the aggregate. A change that lifts overall recall by 0.03 while dropping the `identifier-query` slice by 0.20 is a regression, and the aggregate will happily wave it through.

## Two things people get wrong

**Evaluating on the data you tuned on.** If you tuned chunk size against the golden set, the golden set can no longer tell you how the system generalises. Hold out a test split you look at rarely, exactly as you would with any model.

**Treating the set as finished.** Scenr's dossier states the failure precisely: a graded library is the only source of truth for ninety days, by which time the model, the prompt and the corpus have all moved. Add every production failure as a new example, review the set on a schedule, and date everything. A golden set is a maintained asset, not an artifact.

## The table this produces

Run the harness across configurations and you get the artifact this entire book has been building toward:

| Config | recall@5 | recall@50 | faithful | p95 ms | $/query |
|---|---|---|---|---|---|
| Vector, 1024-token chunks | 0.61 | 0.84 | 0.88 | 410 | 0.0021 |
| + hybrid (RRF) | 0.71 | 0.92 | 0.89 | 440 | 0.0021 |
| + reranker (50→5) | 0.83 | 0.92 | 0.93 | 680 | 0.0024 |
| + contextual chunks | 0.88 | 0.95 | 0.94 | 680 | 0.0024 |
| + query rewrite | 0.89 | 0.95 | 0.94 | 880 | 0.0026 |

Six rows. Every architectural claim in this book, tested on your own corpus, with the cost of each. **That table is the deliverable**, and it converts every honest-gap script about retrieval into a claim with a number.

*Connect the dot:* Book 04 generalises everything here — judge models, statistical significance, online evaluation, agent trajectories — but the shape is already visible: a labelled set, per-slice metrics, a gate in CI, and a discipline about what the numbers do and do not prove.

Next: the patterns for when plain retrieval is not enough.
