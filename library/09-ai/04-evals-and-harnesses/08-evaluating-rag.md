# Evaluating RAG

**Fast overview:** Book 02 built retrieval evaluation as part of the pipeline. This chapter completes it: the full metric set across both halves, the RAG triad, how to diagnose which component is at fault from the metrics alone, and how to evaluate a system where you have no labelled chunk ids. It is the most immediately applicable chapter in the book, because twenty-one of forty-four dossiers name retrieval.

## The split, restated

**Measure retrieval separately from generation.** If your only number is answer quality, a bad answer is undiagnosable.

Two datasets, or one dataset with two label types:

| | Retrieval eval | Generation eval |
|---|---|---|
| Input | query | query + retrieved context |
| Label | relevant chunk ids | reference answer / rubric |
| Metrics | recall@k, MRR, nDCG | faithfulness, relevance, correctness |
| Fixes it points to | chunking, embeddings, hybrid, reranking | prompt, model, context assembly |

## The RAG triad

A widely-used framing, and useful because it covers the three ways a RAG answer can be wrong:

1. **Context relevance** — is the retrieved material actually relevant to the query? (Retrieval quality, judged without needing chunk-id labels.)
2. **Groundedness / faithfulness** — is every claim in the answer supported by the retrieved context? (Generation quality, given the context.)
3. **Answer relevance** — does the answer address the question that was asked? (Generation quality, given the query.)

The triad's virtue is that it is **reference-free**: all three can be judged from (query, context, answer) with no labelled ground truth. That makes it the only option for online evaluation on production traffic, where nobody labelled anything.

Its limitation is equally important: it cannot detect a **correct-looking answer to the wrong facts**. If retrieval returned a superseded policy, the answer will be relevant, grounded and wrong, and all three scores will be high. Reference-free metrics measure internal consistency, not truth. Say this when the triad comes up; it is the part people miss.

## The metric set

**Retrieval, with labels:**

- `recall@k` — the gate. Is the right chunk in the top k at all?
- `recall@k_retrieve` (e.g. @50) — the ceiling a reranker has to work with.
- `MRR` / `nDCG@k` — how high it ranked.
- `precision@k` — how much of what you sent was noise.

**Retrieval, without labels:**

- Context relevance, judged per chunk. Gives you an approximate precision@k for free.

**Generation:**

- Faithfulness — the most important, and the one a citation requirement makes checkable.
- Answer relevance.
- Answer correctness, against a reference.
- `must_contain` assertions on the critical fact. Deterministic and cheap.

**The escape-hatch metrics** (deterministic, free, and underused):

- `NOT_FOUND` rate on answerable questions → **retrieval failure indicator.**
- `NOT_FOUND` rate on unanswerable questions → should be near 1.0. Below that, the system fabricates.
- Citation rate → fraction of answers citing anything. Drops when retrieval degrades.
- Citation validity → do the cited ids exist. A resolvable hallucination detector at zero cost.

**System metrics:** p50/p95 latency by stage, cost per query, index freshness.

## Diagnosing from the metrics

The point of measuring both halves is that the combination localises the fault:

| recall@5 | faithfulness | answer correct | Diagnosis |
|---|---|---|---|
| Low | — | Low | **Retrieval.** Chunking, embeddings, hybrid, reranking |
| High | Low | Low | **Grounding.** The model ignores or blends context. Prompt, citations, model tier |
| High | High | Low | **The corpus, or the question.** Right chunks, faithful answer, still wrong — usually a superseded document or a question needing synthesis the context does not support |
| High | High | High, users unhappy | **Your eval set is not representative.** Go get real queries |

That table is worth memorising. It converts "the RAG system is bad" into a next action in about ten seconds, and reciting it is a strong answer to "how would you debug a RAG system".

## Evaluating without chunk labels

Labelling which chunk should answer each query is the most tedious part of building a RAG eval, and there are three ways around it:

**1. Generate the labels backwards.** Sample chunks, generate a question each answers, and you have (query, known-correct-chunk) for free. Biased toward the chunk's vocabulary; tag it synthetic and use it for coverage rather than for headline numbers.

**2. Judge context relevance instead.** For each retrieved chunk, ask a judge whether it is relevant to the query. Gives you precision@k without labels, but not recall — you cannot know what you failed to retrieve. **Recall is the number that needs labels**, which is why the labelling work is unavoidable if retrieval quality is your problem.

**3. Pool judgments across configurations.** The classic information-retrieval trick: run several retrieval configurations, take the union of everything any of them retrieved, judge that pool once, and treat it as the ground-truth relevant set. You get comparable recall across all configurations for one round of labelling. Its bias is that a chunk no configuration ever retrieved is invisible, but it is a very efficient way to spend a labelling afternoon.

## Evaluating the components individually

Beyond the two halves, each stage can be evaluated on its own, and each has a cheap test:

- **Parsing.** Coverage (what fraction parsed), structure retention on a sample, and twenty chunks read by a human.
- **Chunking.** Recall at fixed embedding model, swept across sizes.
- **Embedding model.** Recall at fixed chunking, across models.
- **Reranker.** recall@5 before and after, at fixed retrieval, plus its latency cost.
- **Query rewriter.** Recall on the follow-up-question slice specifically. This is the clearest case where the aggregate hides everything (Chapter 6).
- **Context assembly.** Faithfulness at different chunk counts and orderings. This is where you find out empirically whether five beats fifteen on your corpus.

Each is a one-variable sweep against the same dataset, which is exactly what a config-hashed harness makes cheap.

## The deliverable

The configuration table from Book 02, produced by the harness:

| Config | recall@5 | recall@50 | faithful | NOT_FOUND (unans.) | p95 ms | $/q |
|---|---|---|---|---|---|---|
| Vector, 1024 chunks | 0.61 | 0.84 | 0.88 | 0.70 | 410 | 0.0021 |
| + hybrid RRF | 0.71 | 0.92 | 0.89 | 0.72 | 440 | 0.0021 |
| + reranker 50→5 | 0.83 | 0.92 | 0.93 | 0.88 | 680 | 0.0024 |
| + contextual chunks | 0.88 | 0.95 | 0.94 | 0.90 | 680 | 0.0024 |

Note the fourth column. As retrieval improves, the system also gets *better at declining* — because with good retrieval, "nothing relevant came back" is a clearer signal than a pile of weak matches. That kind of second-order observation is what makes an eval table interesting rather than dutiful, and it is exactly the sort of thing to point at in an interview.

## Online RAG evaluation

On production traffic there are no labels, so use what is free:

- **The RAG triad** on a sample, via judge.
- **Citation rate and citation validity**, deterministic, on everything.
- **`NOT_FOUND` rate**, trended. A step change means retrieval broke or the corpus stopped updating.
- **User signals**: regeneration rate, follow-up rephrasing, thumbs, escalation to human. Noisy individually, informative in aggregate.
- **Every `NOT_FOUND` query logged** as a free list of corpus gaps and retrieval misses, triaged weekly into either "add the document" or "add an eval example".

That last loop is the one that compounds. Production tells you what your eval set is missing, and the eval set stops you regressing on what production taught you.

*Connect the dot:* the third row of the diagnosis table — high recall, high faithfulness, wrong answer — is the recency problem from Book 02, Chapter 13. It is the failure that no reference-free metric can see, and the only defence is temporal examples in the golden set with a superseded document as a distractor.

Next: evaluating agents, where the answer can be right for the wrong reasons.
