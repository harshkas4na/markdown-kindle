# Hybrid Search and Fusion

**Fast overview:** Vector search is good at meaning and bad at exactness. Keyword search is the reverse. Running both and combining the results is the highest-value structural change most RAG systems can make, and it is cheap. This chapter covers what BM25 is actually computing, the specific queries where embeddings fail badly, reciprocal rank fusion and why it beats score-blending, and how to tune the combination with data.

## The failure that motivates this

Embeddings represent meaning as a direction in a continuous space. That representation is inherently smooth, and some queries are not smooth:

- **Identifiers.** "Error code E4021", "invoice INV-2024-8891", "section 3.2.1(b)". The embedding of `E4021` is near the embedding of `E4022`, which is exactly wrong.
- **Rare proper nouns.** A product name, a person, a codebase symbol the embedding model never saw in training gets tokenised into fragments and embedded as approximately nothing.
- **Negation.** "not available in India" and "available in India" are close. Book 01 covered why.
- **Exact-phrase requirements.** Legal and compliance work where the specific wording is the point.
- **Numbers and units.** "over 500 GB" versus "over 500 MB".

BM25 handles all of these, because it matches terms. Meanwhile BM25 fails at paraphrase — "how do I cancel" will not match "terminating your subscription" — which is exactly what embeddings are good at.

**They fail on disjoint sets of queries.** That is the whole argument, and it is why hybrid retrieval consistently beats either component alone.

## What BM25 is computing

Worth knowing properly, because "we use BM25" said by someone who cannot explain it is a weak answer.

BM25 scores a document for a query by summing, over query terms:

```
score(D,Q) = Σ_t  IDF(t) · ( f(t,D) · (k₁+1) ) / ( f(t,D) + k₁·(1 - b + b·|D|/avgdl) )
```

Three ideas, each with a reason:

1. **IDF (inverse document frequency).** A term appearing in few documents is more informative. "the" scores nothing; "hemodynamic" scores a lot. This is why BM25 handles rare proper nouns so well — rarity is precisely what it rewards.
2. **Saturating term frequency.** `k₁` (typically ~1.2) makes repeated occurrences give diminishing returns. Ten mentions is not ten times more relevant than one. This is the fix for TF-IDF's main weakness.
3. **Length normalisation.** `b` (typically 0.75) discounts long documents, which would otherwise win by containing more of everything.

It has no idea what words mean. It is a very well-tuned counting function, and it has survived thirty years because counting, done carefully, is hard to beat on the queries where the words are the point.

## Fusing the two result lists

You now have two ranked lists. Combining them is where people go wrong.

### The wrong way: blending raw scores

```python
final = alpha * cosine_score + (1 - alpha) * bm25_score   # do not do this
```

Cosine similarity lives in roughly [0,1] with a corpus-dependent distribution. BM25 is unbounded and scales with query length and corpus statistics. They are not commensurable, so `alpha` is meaningless and any tuning of it is overfitting to whatever queries you looked at. Normalising scores first (min-max over the result set) helps a little and remains fragile, because the normalisation depends on the batch.

### The right way: reciprocal rank fusion

RRF ignores scores entirely and uses only **ranks**:

```
RRF(d) = Σ_lists  1 / (k + rank_d_in_that_list)
```

with `k` conventionally 60.

```python
def rrf(*ranked_lists, k=60, top=50):
    scores = defaultdict(float)
    for lst in ranked_lists:
        for rank, doc_id in enumerate(lst, start=1):
            scores[doc_id] += 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)[:top]
```

Why it works so well:

- **Scale-free.** No normalisation, no commensurability problem, no `alpha` to overfit.
- **Robust.** A document ranked 1st in one list and absent from the other still scores well. A document ranked 3rd in both scores better than one ranked 1st in one and 40th in the other.
- **Extends to any number of lists.** Add a third retriever (a different embedding model, a graph traversal, a metadata-boosted query) and nothing changes structurally.
- **The `k` constant damps the top.** Larger `k` flattens the difference between rank 1 and rank 5, which reduces the influence of any single retriever's confidence.

Weighting is possible (`w_i / (k + rank)`) when you have measured that one retriever is genuinely better on your corpus. Start unweighted.

Two variants worth knowing by name: **distribution-based score fusion**, which normalises scores using each list's mean and standard deviation before blending, and can outperform RRF when scores are well-calibrated; and **relative score fusion**, a middle ground. RRF remains the sensible default because it has no failure mode that requires you to understand your score distributions.

## Doing it in one query on Postgres

Because both indexes live in the same database, fusion can happen in SQL:

```sql
WITH vec AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> $1) AS rank
  FROM chunks WHERE tenant_id = $3
  ORDER BY embedding <=> $1 LIMIT 50
),
kw AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(tsv, q) DESC) AS rank
  FROM chunks, plainto_tsquery('english', $2) q
  WHERE tenant_id = $3 AND tsv @@ q
  ORDER BY ts_rank_cd(tsv, q) DESC LIMIT 50
)
SELECT c.id, c.content,
       COALESCE(1.0/(60+vec.rank), 0) + COALESCE(1.0/(60+kw.rank), 0) AS rrf
FROM chunks c
LEFT JOIN vec ON vec.id = c.id
LEFT JOIN kw  ON kw.id  = c.id
WHERE vec.id IS NOT NULL OR kw.id IS NOT NULL
ORDER BY rrf DESC
LIMIT 20;
```

One round trip, one consistent snapshot, one filter applied identically to both halves. This is the concrete payoff of the previous chapter's argument.

Postgres full-text search is not a true BM25 implementation (`ts_rank_cd` is a different scoring function), and it is close enough that the hybrid gain is real. If you need actual BM25, extensions exist, or use a search engine for that half.

## Sparse vectors: the third option

A middle path worth knowing. Models like SPLADE produce **learned sparse** representations: a vector over the vocabulary where most entries are zero, but the non-zero entries include terms the model *expanded* from the text, not just the terms literally present. So a document about "terminating your subscription" gets non-zero weight on "cancel".

This gives you term-matching machinery with semantic expansion, in one retriever, indexable with inverted-index infrastructure. Several vector stores support sparse or hybrid sparse-dense natively. It is a good thing to know about because it demonstrates awareness that the dense/sparse dichotomy is not the whole landscape.

## Tuning with data, not opinions

The whole point of building the golden set is that this chapter's decisions become measurements:

| Configuration | recall@20 | p95 latency |
|---|---|---|
| Vector only | ? | ? |
| BM25 only | ? | ? |
| RRF hybrid | ? | ? |
| RRF hybrid + rerank | ? | ? |

Fill that table on your own corpus. It takes an afternoon once the eval exists, and the result is a defensible architecture plus a genuinely strong interview answer. Also break it down **by query type** — identifier-style queries versus natural-language ones — because the aggregate hides the whole story. Hybrid may add little on average and rescue the 15% of queries that contain a product code, and those 15% may be your most important users.

That per-slice instinct is the same one Book 04 will insist on for evals generally, and this is the cheapest place to practise it.

*Connect the dot:* hybrid search increases the *candidate pool* quality. Reranking, next, fixes the *ordering* of that pool. They compose: retrieve 50 by hybrid, rerank to 5. Neither replaces the other.

Next: reranking, the most reliable single quality win in retrieval.
