# Reranking

**Fast overview:** Retrieval gives you fifty plausible chunks in a defensible order. A reranker gives you the five best in the right order, and it does so by doing something the retriever architecturally cannot: looking at the query and the document together. This chapter explains the bi-encoder/cross-encoder distinction that makes it work, the latency it costs, how to choose k and top_n, the LLM-based and late-interaction alternatives, and how to prove the whole thing is worth it.

## Why the retriever cannot do this

A bi-encoder — your embedding model — encodes the query and the document **independently**. The document's vector was computed months ago with no knowledge of any query. The only interaction between them is a dot product at the very end.

That independence is what makes indexing possible: precompute every document once, and search is cheap forever. It is also a hard ceiling on quality, because no computation ever *compares* the two texts.

A **cross-encoder** concatenates query and document and runs them through a transformer together, so every token of the query attends to every token of the document. It outputs a single relevance score. It is dramatically better at judging relevance, and it is unusable as a retriever: scoring one million documents means one million forward passes per query.

So the architecture is forced:

```
hybrid retrieve top 50   (cheap, approximate, recall-oriented)
      ↓
cross-encoder rerank      (expensive, accurate, precision-oriented)
      ↓
top 5 into the prompt
```

Recall first, precision second. This is the same "cheap wide pass, expensive narrow pass" pattern as binary quantisation with rescore, and as ANN with exact rescore. Naming it once makes the whole pipeline feel inevitable.

## What it buys

Reranking is, on most corpora, the single most reliable quality improvement available. The reason is that retrieval scores and relevance diverge in predictable ways: topical similarity, near-duplicate boilerplate, and chunks that mention the query terms without answering the question all rank highly for a bi-encoder and get correctly demoted by a cross-encoder.

The second, underrated benefit is that reranking lets you **retrieve more and send less**. Without a reranker, you pick k as a compromise: too small and you miss the answer, too large and you flood the context with distractors that hurt quality (Book 01, Chapter 3). With a reranker you can set k=50 or k=100 for recall, and still send only the best 5, so both halves improve at once.

## The cost

A cross-encoder pass over 50 candidate chunks is one batched inference. Order of magnitude: tens to a couple of hundred milliseconds, depending on model size, chunk length and whether it is a hosted API (add a network round trip) or local.

This is a real chunk of an interactive latency budget, and it is the item most often cut. The right way to decide is the table from Book 01, Chapter 8: quality *at* each latency configuration, then pick with the number in front of you.

```python
def retrieve(query, k_retrieve=50, top_n=5):
    candidates = hybrid_search(query, k=k_retrieve)          # ~30ms
    scored = reranker.rank(query, [c.text for c in candidates])  # ~120ms
    return [candidates[i] for i, _ in scored[:top_n]]
```

Ways to buy the latency back:

- **Rerank fewer candidates.** The gain from 100 to 50 is usually small; from 50 to 20 it starts to bite. Measure the curve.
- **Truncate chunk text** passed to the reranker. Cross-encoder cost grows with sequence length.
- **Use a smaller reranker.** The small ones are fast and still much better than no reranker.
- **Run it in parallel** with anything else in the request path.
- **Skip it for easy queries.** If the top hybrid result is far ahead of the rest by score margin, reranking will not change the order. A margin-based bypass is a cheap trick and it works.

## Choosing k and top_n

Two numbers, tuned together against the golden set:

- **k (candidates retrieved).** Governed by **recall@k**. Set it where the recall curve flattens. If recall@20 is 0.88 and recall@50 is 0.94 and recall@100 is 0.95, then 50 is the knee and 100 buys nothing.
- **top_n (chunks sent to the model).** Governed by end-to-end answer quality and context cost. Usually 3-8. Past that, lost-in-the-middle and distractors start costing more than the extra coverage gains.

The failure to avoid is tuning them independently. Increasing k with a fixed top_n is nearly free quality (the reranker filters the extra noise). Increasing top_n without a reranker is usually negative.

## The alternatives

### LLM-as-reranker

Prompt a general model to score or order the candidates. Flexible — you can express criteria a cross-encoder does not know about ("prefer more recent documents", "prefer official policy over forum posts") — and slower and more expensive. Two useful forms:

- **Pointwise:** score each chunk 0-10 for relevance. Parallelisable, and scores are poorly calibrated across chunks.
- **Listwise:** give the model all candidates and ask for a reordering of ids. Better quality because it compares directly, and it is limited by context and by position bias.

Use it when your relevance criteria are genuinely bespoke, or as a quality ceiling to measure your cheap reranker against.

### Late interaction (ColBERT-style)

A middle ground: encode each *token* of query and document separately, then score by summing, for each query token, its maximum similarity to any document token. This keeps most of the cross-encoder's fine-grained matching while allowing document embeddings to be precomputed and indexed.

The cost is storage — one vector per token instead of per chunk — which is why it stayed niche. It is worth knowing by name because it is the answer to "is there anything between a bi-encoder and a cross-encoder", and there is.

### Metadata-aware reordering

Not everything is semantic. Boosting by recency, source authority, or document type is often the highest-value reranking you can do, and it is a few lines of arithmetic:

```python
def adjust(score, chunk):
    age_days = (now - chunk.updated_at).days
    recency  = 0.9 ** (age_days / 180)     # halve-ish per year
    authority = {"policy": 1.2, "forum": 0.8}.get(chunk.doc_type, 1.0)
    return score * recency * authority
```

For a corpus with a lot of superseded material, this fixes more real complaints than any model change. "The system quoted a deprecated policy" is a ranking bug, not a hallucination.

## Diversity: MMR

If your top 5 are five near-identical chunks from the same document, you have wasted four slots. **Maximal marginal relevance** selects iteratively, at each step preferring a candidate that is relevant *and* dissimilar to what is already selected:

```
MMR = argmax_d [ λ · rel(d, q) − (1 − λ) · max_{s ∈ selected} sim(d, s) ]
```

λ around 0.7 is a reasonable start. Simpler alternatives that often do just as well: cap chunks per document at two, or merge adjacent chunks from the same document into one span. Try the simple version first.

## Proving it is worth it

The measurement that settles the argument:

| Configuration | recall@5 | faithfulness | p95 latency | cost/query |
|---|---|---|---|---|
| Hybrid, top 5 | | | | |
| Hybrid top 50 → rerank → 5 | | | | |
| Hybrid top 100 → rerank → 5 | | | | |
| Hybrid top 50 → LLM rerank → 5 | | | | |

Four rows, one afternoon, and it produces the exact sentence the honest-gap script in Book 00 was reaching for. It is also the artifact worth putting in the lab repo, because a table like this in a public repo is more convincing than any resume bullet about retrieval.

*Connect the dot:* reranking is the reason Chapter 3's chunking tension relaxes. With a reranker you can afford small precise chunks (good retrieval) and expand them to parents before generation (good context), because the reranker is doing the precision work in between.

Next: fixing the query before it ever reaches the index.
