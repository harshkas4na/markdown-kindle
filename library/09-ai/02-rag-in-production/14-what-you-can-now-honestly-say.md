# What You Can Now Honestly Say

**Fast overview:** The line-drawing chapter for the highest-demand topic in the corpus. Twenty-one of forty-four companies asked for retrieval, and the resume already says "RAG pipeline with LangChain". This chapter says exactly how much thicker that sentence just got, what it still does not cover, and the one artifact that turns the whole book into a claim.

## What reading this book earned

You can now discuss, with mechanism:

- **The full pipeline**, eleven stages, and which of them actually fails. Including the point most people miss: three of the four common failures are upstream of the model.
- **Why parsing decides your ceiling**, what breaks per format, and the specific problem tables pose.
- **The chunking tension** — retrieval wants small, generation wants large — and the two techniques (small-to-big, contextual retrieval) that dissolve it rather than trading it.
- **Why an embedding model change is a full re-index**, and the five-step migration that makes it survivable.
- **What HNSW is doing**, what `ef_search` trades, and why ANN recall is a separate loss from retrieval quality that almost nobody measures.
- **Why pgvector is usually the right default**, stated as a decision procedure with the specific conditions under which it stops being right.
- **Why BM25 is not legacy** — the disjoint failure sets argument — and why RRF beats score blending.
- **Why a cross-encoder cannot be a retriever**, and how reranking lets you retrieve more while sending less.
- **Query transformation**, and specifically that conversational rewriting is the one nearly every chat product needs.
- **Citations as instrumentation** rather than decoration, and the escape token as a metric.
- **The measurement discipline**: retrieval scored separately from generation, recall@k as the gate, per-slice reporting, and a regression gate in CI.
- **The operational half**: incremental sync by content hash, deletion's four consequences, recency, and permissions as a security boundary rather than a filter.

That is a genuinely strong retrieval foundation and it is still discussion-tier until something is built.

## What it did not earn

- You have not **operated** a retrieval system at scale. No experience of an index that stopped fitting in memory, a nightly sync that silently stalled, or a corpus that grew until precision collapsed.
- You have not **measured** any of this on a real corpus. Every number in this book is illustrative. None of them is yours.
- You have not **tuned** a reranker, an `ef_search`, or a chunk size against real data.
- You have not **run a migration** between embedding models with production traffic on it.
- You have not built **graph RAG** or multimodal retrieval, and this book only described them.

And the specific honest boundary for the existing resume claim: REACTOR's pipeline used retrieval, prompt chaining and a vector store with LangChain, and it was never measured. The claim is real. The claim is that it was *built*, not that it was *evaluated*, and the interviewer who asks "what was your recall" must get "I did not measure it, and here is what I would measure now" rather than an invented number.

## The artifact: `retrieval-bench`

One repo, and it converts most of this book into claims. Two days.

**Day 1 — get a corpus and a baseline.**
Pick something you know well enough to judge answers on. His own thirteen Medium articles, or the Reactive Network docs, are ideal because he can label ground truth without research. Build the naive pipeline from Chapter 1: fixed chunks, one embedding model, cosine top-5, a grounded prompt with citations and a `NOT_FOUND` token.

**Day 1, afternoon — the golden set.**
Forty questions, hand-written, each labelled with the chunk id that should answer it. Include the hard cases deliberately: five with no answer in the corpus, five identifier-style, five follow-ups with pronouns, five whose answer spans a boundary. Tag each with a slice. **This is the actual deliverable of the whole exercise.**

**Day 2 — the table.**
Run the harness across configurations, changing one thing at a time, recording recall@5, recall@50, faithfulness, p95 latency and cost per query:

1. Baseline
2. + hybrid (BM25 + RRF)
3. + cross-encoder reranker, 50 → 5
4. + contextual chunk prefixes
5. + conversational query rewriting
6. Chunk size sweep: 256 / 512 / 1024 / 2048

Then report per slice, not just the aggregate, and write two paragraphs in the README about what surprised you. Something will.

**What this earns, verbatim:**

> I built a retrieval bench over my own corpus with a forty-question labelled set. Hybrid plus a reranker moved recall@5 from 0.61 to 0.83 and cost 240ms at p95. Contextual chunk prefixes added another four points. The interesting part was per slice: on identifier-style queries, hybrid alone moved recall by thirty points, and on plain lookups it moved almost nothing, which is why the aggregate would have made me reject it.

That paragraph is stronger than any resume bullet, it is checkable in a public repo, and it directly answers the retrieval question at twenty-one of the forty-four companies.

## Eight questions to answer out loud

1. Walk me through a RAG pipeline. Now tell me which stage fails most often and why.
2. A user says the system hallucinated. What are the first three things you check?
3. What chunk size should I use? (The correct answer starts with a question.)
4. Why do I need BM25 if I have embeddings?
5. Why can't I use a cross-encoder as my retriever?
6. What is recall@k and why does it come before answer quality?
7. I want to switch embedding models on a live system. Walk me through it.
8. How do you stop a user retrieving a document they are not allowed to see?

## Where to go next

**Book 04, Evals and Harnesses.** Chapter 11 of this book was a specialised instance of it; Book 04 generalises to judge models, statistical significance, online evaluation and agent trajectories. It is also the topic the dossiers say these companies actually care most about.

**Book 03, Agents**, if the target company is agent-shaped rather than document-shaped. Chapter 12's agentic retrieval is the doorway.

*Connect the dot:* the single sentence that carries across both is the one this book was built around. **Measure the components separately, or you will spend months tuning the wrong one.** That is true of retrieval versus generation, and it is true of every multi-stage system, which is why it is worth saying in an interview about anything.

Next: Agents, Tools and Orchestration.
