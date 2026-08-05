# Vector Indexes and Approximate Search

**Fast overview:** Comparing a query against every vector is exact and does not scale. Approximate nearest-neighbour indexes trade a little recall for orders of magnitude of speed, and the entire art is knowing which dial you are turning and what it costs. This chapter covers HNSW and IVF at the level where you can tune them, the recall/latency/memory triangle, why metadata filtering is harder than it looks, and how to measure your own index's recall rather than trusting a default.

## Why approximate

Exact search over N vectors of dimension d is O(N·d) per query. At a million chunks and 1,536 dimensions that is over a billion floating-point operations per query. Fine at 10,000 vectors, impossible at scale with a latency budget.

Approximate nearest neighbour (ANN) indexes achieve sublinear search by only examining a fraction of the vectors, at the cost of occasionally missing a true neighbour. **Recall** here means: of the true top-k, how many did the index actually return? 0.95 recall@10 means it found 9.5 of the true 10 on average.

The crucial framing: **ANN recall is a *separate* loss from retrieval quality.** If your embedding model gives you recall@10 of 0.80 against your golden set, and your index has ANN recall of 0.95, you are compounding two losses. Most teams never measure the second one and attribute all their misses to the first.

## HNSW

Hierarchical Navigable Small World is the default in most vector stores, and understanding it takes one picture: a **multi-layer graph** where each node is a vector connected to its approximate neighbours. Upper layers are sparse and span long distances; lower layers are dense and local. Search starts at the top, greedily walks toward the query, drops a layer, walks again, and so on to the bottom layer where the final candidates are collected.

It is a skip list for metric spaces: coarse hops first, fine hops last.

**The parameters, and what each one costs:**

| Parameter | Meaning | Increase it → |
|---|---|---|
| `M` | Connections per node | Better recall, more memory (linear), slower build |
| `ef_construction` | Candidate list size while building | Better graph quality, much slower build, no query cost |
| `ef_search` | Candidate list size at query time | Better recall, slower queries |

The one to know cold is **`ef_search`**, because it is the runtime dial. It must be at least `k`, and raising it explores more of the graph. Going from 40 to 200 might take recall from 0.92 to 0.99 and triple query latency. **That is a product decision, and you should be able to show the curve rather than assert a default.**

Typical starting points: `M` 16-32, `ef_construction` 100-200, `ef_search` 50-100. Then measure.

HNSW's real costs: it is memory-resident (the graph plus vectors must fit in RAM for good performance), builds are slow for large corpora, and **deletions are awkward** — most implementations tombstone rather than remove, so a corpus with heavy churn degrades until rebuilt.

## IVF (inverted file)

Cluster the vectors into `nlist` cells with k-means; each vector belongs to its nearest centroid. At query time, find the `nprobe` nearest centroids and search only those cells.

Cheaper to build than HNSW and lower memory, with a sharper failure mode: if the true neighbour sits in a cell you did not probe, it is invisible. Vectors near a cell boundary are systematically at risk.

- `nlist` ≈ √N is a common heuristic.
- `nprobe` is the runtime recall dial, exactly analogous to `ef_search`.

**IVF-PQ** adds product quantisation: split each vector into sub-vectors, quantise each against a small learned codebook, and store codes instead of floats. Enormous memory savings (often 10-30x) at a real accuracy cost, mitigated by rescoring the top candidates with full vectors. This is how billion-scale indexes fit on sensible hardware.

**Choosing between them:** HNSW for best recall/latency when memory allows, which covers the majority of application-scale corpora (under ~10M vectors). IVF-PQ when the corpus is too large to hold as floats. Flat (exact) when N is small — and it is worth saying plainly that under about 50,000 vectors, exact brute force in numpy is often faster than an index, and always simpler.

## Filtering, which is harder than it looks

Almost every real query is filtered: this tenant's documents, this date range, this document type, what this user is allowed to see. Combining a filter with ANN is genuinely difficult.

**Pre-filtering** — filter first, then search within the survivors. Correct results, and it can defeat the index entirely: an HNSW graph built over the whole corpus cannot be walked over an arbitrary subset, so implementations fall back to brute force over the filtered set. Fine when the filter is highly selective and slow when it is not.

**Post-filtering** — search first, then discard non-matching results. Fast, and it silently under-returns: ask for 10, retrieve 10, discard 8 that fail the filter, return 2. The naive fix is over-fetching (retrieve 100 to get 10), which works until the filter is selective enough that even 100 is not enough.

**Filtered search** — the index applies the predicate during traversal. This is what good vector stores implement, with varying degrees of sophistication, and it is a genuine differentiator between them.

**The pattern that always works** for a hard partition like tenancy: **separate indexes or namespaces per tenant.** The filter becomes a routing decision rather than a search constraint, and correctness stops being a tuning problem. This is the right default for multi-tenant systems, and it is the answer to give when asked how you would isolate customers' data (Chapter 13).

## Measuring your index's recall

Nobody does this and it takes an hour:

```python
# 1. take 500 random queries from your workload (or your golden set)
# 2. compute exact top-k by brute force (slow, offline, fine)
# 3. run the same queries through the index
# 4. recall = |exact ∩ approx| / k, averaged

def ann_recall(queries, k, exact_fn, index_fn):
    total = 0
    for q in queries:
        e = set(exact_fn(q, k))
        a = set(index_fn(q, k))
        total += len(e & a) / k
    return total / len(queries)
```

Then sweep `ef_search` and plot recall against p95 latency. You now own a curve instead of a default, and you can answer "why is `ef_search` 80?" with "because at 80 we get 0.97 recall at 12ms, and 200 gets us 0.99 at 35ms, and the extra 0.02 was not worth 23ms in our budget."

That sentence is what an interviewer at an infra-flavoured company is listening for.

## Distance metrics, briefly

Cosine for text embeddings, essentially always. Inner product is equivalent when vectors are normalised and is sometimes faster. Euclidean (L2) is monotonically related to cosine for normalised vectors, so it ranks identically. Hamming for binary quantised vectors.

The failure mode is configuring the index with a different metric than the one your vectors assume. Results come back, ranked wrongly, with no error. Assert it at startup by checking a known pair.

## Build, update and rebuild

Operational realities that decide which store you pick (Chapter 6):

- **Build time.** HNSW over millions of vectors takes real time and CPU. Budget it.
- **Incremental inserts** are supported by HNSW and degrade graph quality slowly. Occasional rebuilds keep it healthy.
- **Deletions** tombstone. A corpus with high churn needs periodic compaction.
- **Rebuild strategy.** Build the new index alongside, verify with the golden set, swap atomically. Same shape as the embedding migration in Chapter 4, and for the same reason.

*Connect the dot:* `ef_search` is a knob on the same trade-off as `k` in retrieval and `top_n` in reranking: how many candidates do you consider, and what does considering more cost. A well-tuned pipeline sets all three together against one latency budget, which is why Chapter 8 revisits this.

Next: where to put the vectors, and whether Postgres is enough.
