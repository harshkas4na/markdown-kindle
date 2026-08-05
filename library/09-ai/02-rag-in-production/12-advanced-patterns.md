# Advanced Patterns

**Fast overview:** Plain retrieve-then-generate handles the large majority of questions. This chapter covers the patterns for the rest: contextual retrieval, which is cheap and should probably be your default; agentic retrieval, where the model decides what to search for and when to stop; graph RAG, which is powerful, expensive and over-recommended; and multimodal retrieval. Each gets the same treatment — what it fixes, what it costs, and how you would know whether you need it.

## Contextual retrieval

Covered briefly in Chapter 3 and worth restating here because it is the highest return-per-effort item on this list.

**The problem:** a chunk pulled out of its document loses the context that made it meaningful. "The limit was raised to 50 in the second phase" is unretrievable and uninterpretable.

**The fix:** at index time, prepend a short generated description situating the chunk.

```python
CONTEXTUALISE = """<document_summary>{summary}</document_summary>
<chunk>{chunk}</chunk>

Write one or two sentences situating this chunk within the document, so that it
can be understood on its own. Answer with the sentences only."""
```

The economics work because of prompt caching: the document summary is the stable prefix across every chunk of that document, so you pay full price once and cached price thereafter. Public reports of this technique show substantial reductions in retrieval failure rate, and combining it with hybrid search and reranking compounds.

**Cost:** one cheap LLM call per chunk at index time, plus a re-index. **When to skip:** corpora where chunks are already self-contained (FAQ entries, standalone articles).

## Agentic retrieval

Instead of one retrieval, give the model a search tool and let it decide what to search for, read the results, and search again.

```
question → [ search("refund policy") → read
           → search("annual plan terms 2026") → read
           → enough? ] → answer
```

**What it fixes:**

- **Multi-hop questions.** "Who signed the contract with the vendor we onboarded after the 2025 audit?" requires finding the audit date, then the vendor, then the contract. No single query retrieves that.
- **Underspecified questions**, where the first search reveals what the second should be.
- **Exploratory research**, where the stopping point is not known in advance.

**What it costs:** several LLM calls and several retrievals per question, so seconds of latency and multiples of the cost. It also introduces every agent failure mode from Book 03 — loops, drift, unbounded cost.

**The controls that make it viable:** a hard cap on search calls (3-5 is usually plenty), a repeated-query detector, a running token budget, and an explicit "answer now with what you have" fallback when the cap is hit. Never let it run unbounded.

**The routing rule:** do not make everything agentic. Classify the question first, and send simple lookups down the cheap single-shot path. A system where 85% of queries cost 400ms and 15% cost 4 seconds is a good product; one where everything costs 4 seconds is not.

**Self-RAG and corrective RAG** are named variants worth knowing: the model critiques the retrieved chunks for relevance before using them, and re-retrieves (or falls back to web search) when they are inadequate. The valuable idea underneath is a **relevance gate between retrieval and generation** — checking that what came back is actually usable rather than assuming it. That check is cheap and worth having even in a non-agentic pipeline.

## Graph RAG

Build a knowledge graph from the corpus — entities as nodes, relationships as edges — then answer by traversing it, optionally combined with vector retrieval.

**Where it genuinely wins:** questions about *relationships* and *aggregates over a corpus* rather than about facts stated in a passage. "Which customers are connected to this supplier through more than one contract?" or "What are the main themes across these 400 support tickets?" A vector search cannot answer either, because no single chunk contains the answer — it is a property of the whole corpus.

**How it is built:** an extraction pass over each chunk pulling entities and relations into a graph, entity resolution to merge duplicates ("Acme Corp" and "Acme Corporation"), then community detection over the graph with generated summaries per community. Query time traverses the graph and/or retrieves community summaries.

**What it costs, honestly:** an LLM call per chunk for extraction, plus community summarisation, on a corpus-sized workload. That is a real bill, a real pipeline, and a real maintenance burden — every document update has to update the graph, and entity resolution is a permanent source of subtle wrongness.

**The recommendation:** graph RAG is over-recommended relative to how often it is the right answer. The test is whether your important questions are genuinely relational or genuinely corpus-level. If they are lookups phrased in interesting ways, hybrid search and reranking will get you there for a fraction of the cost. If someone proposes graph RAG, the right question is "which of our questions does plain retrieval fail on, and how many are they?"

A cheaper middle path that captures much of the value: **extract structured metadata** (entities, dates, document relationships) into ordinary database columns during ingestion, and use them as filters and boosts. You get relational filtering without building or maintaining a graph.

## Multimodal retrieval

When the corpus is diagrams, screenshots, scanned forms or slides, text extraction loses the content. Two approaches:

**Caption and index text.** Run a vision model over each image, generate a description, index the description. Simple, uses your existing text pipeline, and quality is capped by the caption.

**Embed the images directly** with a multimodal embedding model into a shared image/text space, so a text query can retrieve an image. Better fidelity, requires a store holding both modalities and a model whose shared space is actually good.

For document-heavy corpora, an increasingly common pattern is to skip text extraction entirely: embed **page images** and retrieve pages, then pass the page images to a vision-language model to answer. This sidesteps every PDF parsing problem in Chapter 2, at the cost of vision-model tokens per query. Worth knowing as an option, particularly for the patent/contract style of corpus where layout carries meaning.

## Structured plus unstructured

The most common real requirement, and the one most often botched: some questions are searches and some are queries.

> "What did our top three customers by revenue say about pricing?"

Revenue ranking is SQL. What they said is retrieval. The answer needs both.

The architecture is a router (Chapter 9) plus tools: a text-to-SQL tool over the warehouse and a retrieval tool over documents, with the model composing them. This is agentic retrieval with a heterogeneous toolset, and it is the shape of most "AI over our company's data" products — airCFO's "retrieval/RAG context layer over all our tools" is exactly this.

The hard part is not the LLM. It is that text-to-SQL is unreliable on real schemas, so the practical version restricts it: a curated set of parameterised queries the model selects and fills, rather than free SQL generation. That is a guardrail (Book 05) and it is also just better engineering.

## How to decide you need any of this

The honest procedure, which is also the interview answer:

1. **Build the golden set and measure the plain pipeline.**
2. **Read the failures.** Not the aggregate, the actual failed examples.
3. **Classify them.** How many failed because the answer needed two hops? Because the question was relational? Because the chunk lacked context? Because the source was an image?
4. **Adopt the pattern that addresses the largest bucket**, and measure again.

Adopting graph RAG because it is interesting, before step 3, is how six-week projects become six-month projects that do not move the number.

*Connect the dot:* agentic retrieval is the bridge to Book 03. Once the model chooses what to search and when to stop, you have an agent, and every control in that book — step caps, loop detection, trace inspection, trajectory evaluation — starts applying to your retrieval system.

Next: keeping the corpus fresh, and keeping tenants apart.
