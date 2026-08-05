# Embedding Models in Practice

**Fast overview:** Book 01 covered what an embedding is. This chapter covers the operational reality: how to choose a model with evidence rather than a leaderboard, the four settings that are silently wrong in most codebases, how to run the migration you will eventually have to run, and how to batch and cache the embedding workload so it is neither slow nor expensive.

## Choosing, with evidence

The procedure is the same one this shelf keeps repeating, because it keeps being the answer:

1. **Shortlist three** from public leaderboards, spanning a range: one small/fast, one strong API model, one open model you could self-host.
2. **Run all three against your 40-query golden set** and compare recall@5 and recall@20 on your corpus.
3. **Weigh in cost, dimension and input limit.**
4. **Pick, record the reasoning in the repo, and move on.**

An afternoon. The alternative is arguing from benchmarks built on corpora that are nothing like yours.

The factors that decide it in practice:

| Factor | Why it matters |
|---|---|
| Recall on your data | The only quality number that counts |
| Max input tokens | Frequently 512 or 8192. If your chunks exceed it they are silently truncated |
| Dimension | Storage and index memory scale linearly |
| Asymmetry support | Whether it expects query/document prefixes |
| Multilingual | Only if your corpus needs it |
| API or self-host | Data residency, cost at scale, and latency predictability |
| Rate limits | Indexing a large corpus through an API can take days at a low limit |

## The four settings that are silently wrong

Each of these produces a working system with quietly degraded quality and no error anywhere.

**1. Chunks exceed the model's input limit.** The model truncates. You are embedding the first half of every chunk and searching over it. Fix: assert it.

```python
MAX_INPUT = 8192
assert all(count_tokens(c) <= MAX_INPUT for c in chunks), "chunk exceeds embed limit"
```

**2. Missing instruction prefixes.** Many strong models are trained with task prefixes (`search_query:` / `search_document:`, or a natural-language instruction). Omitting them, or applying the document prefix to queries, costs real recall. Read the model card; there is no way to infer this.

**3. Normalisation mismatch.** Some providers return unit vectors, some do not. If your index computes cosine it may normalise for you, or it may compute a dot product and assume you did. Normalise explicitly at write time and at query time, and stop thinking about it.

**4. Query and document embedded by different models.** Happens when indexing and serving live in different services with independently-configured clients, and it survives code review because both sides look correct in isolation. Fix: one shared config, and store the model identifier with every vector so a mismatch is detectable.

That last one is a good bug to have an opinion about, because it is the same class as the `includes()` keyword bug from `learnings.md`: a silent correctness failure that every positive test still passes. The defence is the same too — assert the thing that should *not* be true. Write a test that embeds a known query with the serving path, embeds a known-matching document with the indexing path, and asserts the similarity is above a floor. If the models diverge, that test fails and nothing else will.

## Dimensions, truncation and Matryoshka

Storage arithmetic:

```
1,000,000 chunks × 1,536 dims × 4 bytes = ~6.1 GB of raw float32 vectors
```

Plus index overhead — HNSW roughly doubles it. That is a memory-resident-index conversation.

Two ways to shrink it:

- **Matryoshka models**, trained so that a truncated prefix of the vector is itself a valid embedding. Store 512 of 1,536 dimensions and lose surprisingly little recall. Measure the loss on your golden set rather than assuming.
- **Quantisation.** Store `int8` instead of `float32` for a 4x reduction, or binary (1 bit per dimension) for 32x with Hamming distance, then rescore the top candidates with full-precision vectors. Binary-plus-rescore is a genuinely effective pattern at large scale and worth knowing by name.

Both are examples of the same shape: a cheap approximate first pass, then an expensive precise second pass over a small candidate set. That shape recurs everywhere in retrieval — it is also exactly what reranking is (Chapter 8).

## Batching and throughput

Embedding is embarrassingly parallel and the naive loop is 100x slower than it needs to be.

```python
def embed_all(texts, batch=256, workers=8):
    batches = [texts[i:i+batch] for i in range(0, len(texts), batch)]
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(embed_batch_with_retry, batches))
    return [v for r in results for v in r]
```

Details that matter for a real indexing run:

- **Batch size** is bounded by the provider's per-request token limit, not just item count. Compute it from token counts.
- **Retry with backoff on 429**, and respect `Retry-After`. A large indexing job will hit rate limits; the question is whether it degrades or dies.
- **Checkpoint progress.** A four-hour indexing run that fails at hour three and restarts from zero is a bad afternoon. Write completed chunk ids as you go.
- **Cache by content hash.** Re-indexing a corpus where 2% of documents changed should cost 2% of the embeddings. This is the `content_hash` field from Chapter 2 earning its place.

```python
def embed_cached(text, cache):
    h = hashlib.sha256((EMBED_MODEL + "\x00" + text).encode()).hexdigest()
    if h in cache: return cache[h]
    v = embed([text])[0]; cache[h] = v
    return v
```

Note the model name in the hash input. Without it, a cache built under one model silently serves vectors from another after a switch, which is the migration bug in its most insidious form.

## The migration you will eventually run

You will change embedding models — a better one ships, or costs change, or you move to self-hosting. Every vector in the corpus becomes invalid at once. Plan for it rather than discovering it.

**The pattern that works:**

1. **Version the index.** Chunks carry `embed_model`, and the store has a namespace or collection per model version. Never one table with mixed vectors.
2. **Build the new index alongside the old**, from the same chunks. Both are queryable.
3. **Run the golden set against both.** This is the moment the eval set pays for itself completely: a decision that would otherwise be a leap of faith becomes a table.
4. **Shadow the new index on live traffic** without serving it, and compare retrieved-set overlap and, if you can, downstream answer quality.
5. **Cut over behind a flag**, keep the old index for a rollback window, then delete.

Doing this once, and being able to describe those five steps, is a strong signal in an interview because it is unmistakably the description of someone who has thought past the demo.

## Fine-tuning an embedding model

Occasionally correct, and much cheaper than people assume. If your domain has vocabulary the general model does not know — internal product names, a specialist legal or medical register, an unusual notation — a fine-tuned embedding model can materially beat a general one.

You need training pairs: (query, relevant chunk). Sources include real user queries paired with the chunk that produced a good answer, and synthetic queries generated by asking a model "what question would this chunk answer?" — which is also, conveniently, how you bootstrap a golden set when you have no traffic.

The training objective is contrastive (multiple-negatives ranking loss is the standard), and `sentence-transformers` makes it a short script. A few thousand pairs is enough to see movement.

The honest caveat: this is a real project with a real maintenance burden — a training pipeline, a model artifact to version, and a re-index every time you retrain. Exhaust hybrid search and reranking first. They are cheaper and usually give you more.

*Connect the dot:* the "cheap approximate pass, expensive precise pass" shape appears three times on this shelf: binary quantisation plus rescore here, ANN plus exact rescore in Chapter 5, and bi-encoder plus cross-encoder in Chapter 8. Naming the pattern once makes all three easy to remember.

Next: what the index is actually doing when it finds nearest neighbours in six million vectors in four milliseconds.
