# Query Transformation

**Fast overview:** The user's raw words are frequently the worst possible search query: too short, full of unresolved pronouns, phrased nothing like the corpus, or containing three questions at once. Transforming the query before it hits the index is cheap, often high-impact, and the stage most commonly missing from a system that "works but feels dumb on follow-up questions". This chapter covers rewriting, expansion, HyDE, decomposition and routing, plus when each is worth its extra call.

## The asymmetry problem, restated

Book 01 established that queries and documents are different kinds of text. A query is short, interrogative and uses the user's vocabulary. A document is long, declarative and uses the author's vocabulary. Embedding models trained asymmetrically handle some of this; they cannot handle a query that is genuinely underspecified.

Query transformation is the stage where you fix that in the application rather than hoping the model does.

## Conversational rewriting: the one everybody needs

The single most common real failure in a chat-based RAG product:

```
User: What is the refund window for annual plans?
Bot:  Thirty days from purchase.
User: What about monthly?
```

"What about monthly?" embedded alone retrieves nothing useful. It has no subject.

The fix is a small model call that rewrites the follow-up into a standalone query using the conversation history:

```python
REWRITE = """Rewrite the user's latest message as a standalone search query.
Resolve all pronouns and references using the conversation. Output only the query.

Conversation:
{history}

Latest message: {message}
Standalone query:"""
```

`"What about monthly?"` → `"refund window for monthly plans"`. One cheap call, and it converts a broken product into a working one. **If you build only one transformation, build this one.**

Details that matter: use a small fast model, cap the history you pass, and pass the *rewritten* query to retrieval while giving the *original* to the answering model, because the original carries tone and intent the rewrite flattens.

## Query expansion

Generate several phrasings of the same question, retrieve for each, fuse the results with RRF.

```python
def multi_query(q, n=3):
    variants = llm(f"Write {n} different phrasings of this question, "
                   f"one per line:\n{q}").splitlines()
    lists = [search(v) for v in [q, *variants]]
    return rrf(*lists)
```

This directly attacks vocabulary mismatch — the user says "cancel", the document says "terminate", and one of the three variants bridges it. Costs one LLM call plus N embedding calls plus N searches, all parallelisable.

When it helps most: heterogeneous corpora, users whose vocabulary differs from the authors', and any domain with heavy synonymy (medical, legal). When it does not: corpora where users and documents already share vocabulary, where it adds latency for nothing.

## HyDE

Hypothetical Document Embeddings, and the trick is a good one. Instead of embedding the question, ask a model to **write a plausible answer**, then embed *that* and search with it.

```python
def hyde(q):
    fake = llm(f"Write a short passage that would answer this question. "
               f"It does not need to be factually correct.\n{q}")
    return search_by_vector(embed([fake])[0])
```

The rationale: a hypothetical answer is structurally a document — declarative, in document vocabulary, similar length — so it sits closer in embedding space to the real answer than the question does. It converts an asymmetric search into a symmetric one.

Real caveats worth stating, because HyDE is often oversold:

- It works best when the model has **some** domain knowledge. On a corpus of purely internal, private facts the hypothetical answer is fabrication with no useful signal, and it can drag retrieval off-topic.
- It adds a full generation call to the critical path, which is expensive latency for a *pre*-retrieval step.
- Fusing HyDE results with plain-query results (RRF again) is more robust than replacing.

Worth measuring, not worth assuming.

## Decomposition

Some questions are several questions:

> "How does our refund policy compare to the one we had in 2024, and which changed more, the window or the eligibility rules?"

One retrieval cannot serve this. Decompose into sub-questions, retrieve for each, and answer from the union:

```python
subs = llm(f"Break this into independent sub-questions, one per line. "
           f"If it is already a single question, output it unchanged.\n{q}").splitlines()
context = dedupe([c for s in subs for c in retrieve(s)])
```

This is the boundary where retrieval starts becoming agentic (Chapter 12). The important judgement is knowing when a question needs it, because running decomposition on every query triples cost for the 85% that are simple. A cheap classifier — or a heuristic like "contains 'and' plus a comparative" — routes it.

## Routing

Not every question should hit the vector index at all:

| Query type | Correct handling |
|---|---|
| "What is our Q3 revenue?" | SQL against the warehouse, not retrieval |
| "Summarise this document I just uploaded" | Long context, no retrieval |
| "Hi" | No retrieval, canned response |
| "What is the refund policy?" | Vector retrieval |
| "Error code E4021" | Keyword-weighted retrieval |
| "Compare policy A and B" | Decompose, then retrieve |

A router in front of retrieval is one small classification call, and it fixes an entire category of bad answers — specifically the ones where the system confidently retrieves *something* for a question that was never a retrieval question. This is also the honest answer to "when is RAG the wrong tool", made operational.

Postgres, again, makes the multi-index version of this easy: route between a vector query, a full-text query and an actual SQL query without leaving the database.

## Filter extraction

An underused transformation: pull structured filters out of the natural-language query.

> "What did we say about pricing in the 2025 contracts?"

→ `query: "pricing"`, `filters: {doc_type: "contract", year: 2025}`

This is a structured-output call (Book 01, Chapter 6) with a schema listing your available filter fields. It converts a semantic search over everything into a semantic search over the right subset, which improves precision far more than any embedding change.

The failure mode to guard: an over-eager extractor that invents a filter and returns zero results. Make every filter field optional, and fall back to unfiltered search when the filtered search returns nothing.

## The cost/benefit table

Each transformation adds latency and a failure point. Be deliberate:

| Technique | Added latency | When it earns its place |
|---|---|---|
| Conversational rewrite | ~200ms | Any multi-turn product. Nearly always |
| Filter extraction | ~200ms | Corpora with strong structured metadata |
| Routing | ~150ms | When some questions are not retrieval questions |
| Multi-query expansion | ~300ms + N searches | Vocabulary mismatch between users and corpus |
| HyDE | ~500ms | Model has domain knowledge; measured to help |
| Decomposition | ~400ms + N searches | Genuinely compound questions |

Note the compounding: rewrite plus route plus expansion is 650ms before retrieval starts. Apply them conditionally, not universally, and let the router decide which ones this query needs.

## The measurement

Every technique in this chapter is evaluated the same way: recall@k on the golden set, before and after, plus latency. But the aggregate will understate the good ones, because most transformations help a *subset* of queries a lot and the rest not at all.

So slice the golden set by query type — follow-up questions, identifier queries, compound questions, simple lookups — and report per slice. Conversational rewriting might move overall recall by three points and move follow-up-question recall by thirty. **The first number would get the feature rejected; the second gets it shipped.**

That is the per-slice argument again, and it is the third time this shelf has made it. It is the single most transferable idea in Book 04.

*Connect the dot:* every technique here is a small LLM call in the request path, which means every one of them is a prompt that needs versioning, tracing and its own eval (Book 01, Chapter 7). A rewriter that silently degrades takes your whole retrieval quality with it and looks like an embedding problem.

Next: assembling the retrieved material into a prompt, and making the answer checkable.
