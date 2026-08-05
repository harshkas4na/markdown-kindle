# The Whole Story in Ten Minutes

**Fast overview:** RAG is the easiest thing in AI engineering to demo and one of the harder things to make good. The demo is fifty lines. The gap between the demo and a system people trust is this whole book. This chapter is the compressed version: the pipeline, the stage that actually fails, the levers in the order they pay off, and the one measurement discipline that turns the whole thing from guesswork into engineering.

## What RAG is, and what it is for

Retrieval-augmented generation: fetch relevant text at query time, put it in the prompt, have the model answer from it.

It exists because of two facts from Book 01. The model's knowledge is frozen at its training cutoff and lossy, so anything factual and changing has to come from outside. And context is expensive and non-uniform in effectiveness, so you cannot just include everything. RAG is a precision mechanism for filling a limited context with the right material.

It also buys three things people forget to mention: **freshness** (update a document, not a model), **access control** (retrieve only what this user may see, which a fine-tune cannot do), and **citation** (an answer that points at a source is checkable, and checkability changes the product).

## The pipeline

Two paths that share a vector space.

**Index time**, done once and on updates:

```
source → parse → clean → chunk → embed → store (+ metadata)
```

**Query time**, done per request:

```
query → transform → embed
      → search (vector + keyword)
      → fuse → rerank → assemble context → generate → cite
```

Nine stages at query time. Every one of them can be the reason your answer was wrong, which is why "the model hallucinated" is not a diagnosis.

## Where it actually fails

Ranked by how often each is the culprit in real systems:

1. **Parsing.** The PDF's table became word salad; the page header repeats in every chunk; the markdown lost its structure. Garbage in the index cannot be fixed downstream by anything. This is the least glamorous stage and the most common failure.
2. **Chunking.** The answer spans a boundary, or the chunk is a fragment with no context, or one chunk contains six unrelated topics so its embedding is a meaningless average.
3. **Retrieval ranking.** The right chunk is in the corpus and comes back at position 23 when you take the top 5.
4. **Generation.** The right context was there and the model ignored it, blended it with prior knowledge, or answered a slightly different question.

Notice that three of the four are upstream of the model. **Most RAG quality work is not prompt work**, and saying so is a good signal in an interview because it is the opposite of where beginners spend their time.

## The levers, in the order they pay off

Roughly, and on most corpora:

| Lever | Typical effect | Cost |
|---|---|---|
| Fix parsing | Large. Sometimes the entire problem | Engineering time, no runtime cost |
| Hybrid search (BM25 + vector) | Large, especially for names, IDs, exact terms | Small latency, more infra |
| Reranking | Large. The most reliable single quality win | ~50-200ms, a model call |
| Better chunking | Moderate to large, corpus-dependent | Re-index |
| Query rewriting | Moderate, big for conversational follow-ups | One extra small LLM call |
| Better embedding model | Moderate | Full re-index |
| Prompt tuning on the generator | Small, once the above are right | Free |
| Bigger LLM | Small for retrieval problems | Expensive |

The last two rows are where people start. That is the mistake this book exists to prevent.

## The measurement discipline

The single most important idea in this book: **measure retrieval separately from generation.**

If you only measure end-to-end answer quality, you cannot tell whether a wrong answer was a retriever failure or a generator failure, so you tune the wrong thing. Split it:

- **Retrieval metrics** — recall@k (did the right chunk come back at all), MRR or nDCG (how high was it), measured against a set of queries with known correct chunks.
- **Generation metrics** — faithfulness (is every claim supported by the retrieved context) and answer relevance, measured given the retrieved context.

Recall@k is the gate. **If the right chunk is not in the top k, no amount of prompt engineering can save the answer.** So instrument retrieval first, get recall respectable, and only then work on generation.

The other half of the discipline: build the labelled set by hand before optimising anything. Forty question/chunk pairs, written by someone who knows the corpus, is enough to make every subsequent decision a measurement instead of an argument. It takes an afternoon and it is the highest-leverage afternoon in this whole book.

## Things that are true and unpopular

- **If your corpus is small — a few hundred pages — you may not need RAG at all.** Put it in the context, or use a keyword search plus a long-context call. Do not build a vector database for 200 documents. Being willing to say this is a credibility signal.
- **Embeddings alone are weak at exact terms**: product codes, error numbers, names, negation. BM25 is not legacy technology; it is the half of hybrid search that handles everything embeddings are bad at.
- **More retrieved chunks usually makes answers worse**, not better, past a small number. Lost in the middle plus distractors.
- **Chunk size has no universal right answer** and anyone who gives you one without asking about your corpus is guessing. It is an empirical decision on your data, which is one more reason for the golden set.
- **Semantic chunking is often not worth its cost.** It is fashionable; on many corpora simple recursive chunking with overlap matches it. Measure before adopting.

## What this book covers

| Ch | Topic |
|---|---|
| 1 | The pipeline end to end, with a minimal working implementation |
| 2 | Ingestion and parsing: PDFs, tables, HTML, code |
| 3 | Chunking strategies and how to choose |
| 4 | Embedding models, dimensions, and the migration problem |
| 5 | Vector indexes: HNSW, IVF, and the recall/latency dial |
| 6 | pgvector versus dedicated vector databases |
| 7 | Hybrid search and reciprocal rank fusion |
| 8 | Reranking with cross-encoders |
| 9 | Query transformation: rewriting, HyDE, decomposition |
| 10 | Context assembly, ordering, and citations |
| 11 | **Evaluating retrieval** — the chapter the rest exist for |
| 12 | Advanced patterns: contextual retrieval, graph RAG, agentic retrieval |
| 13 | Freshness, permissions, and multi-tenancy |
| 14 | What you can now honestly say |

Next: the pipeline, stage by stage, with code small enough to hold in your head.
