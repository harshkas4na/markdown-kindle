# Embeddings

**Fast overview:** An embedding turns text into a vector so that "similar" becomes arithmetic. Everything in retrieval, semantic caching, clustering and deduplication rests on that trick. This chapter covers what the vector actually represents, why cosine is the default distance, the three properties that cause most production surprises (asymmetry, model incompatibility, and similarity not meaning relevance), how to choose a model and dimension, and the specific ways embeddings quietly fail.

## What an embedding is

An embedding model maps a piece of text to a fixed-length vector — commonly 384 to 3,072 dimensions — trained so that texts with similar meaning have vectors pointing in similar directions.

The training objective is **contrastive**: given a batch of (text, related-text) pairs, pull each pair together and push everything else apart. Which pairs count as "related" during training defines what the model considers similar, and this is the crux. A model trained on (question, answer) pairs learns that a question and its answer are close, even though they share few words. A model trained on (sentence, paraphrase) pairs learns something different. **There is no universal notion of similarity, only the one the training data encoded.**

An embedding model is usually an encoder (bidirectional attention, so every token sees every other token) with a pooling step — mean-pool the token vectors, or take the vector at a designated `[CLS]` position — followed by normalisation. Some modern embedding models are decoder-only LLMs adapted for the task, which is why the good ones now cost roughly what small chat models cost.

## Cosine similarity, and why

```
cos(a, b) = (a · b) / (‖a‖ ‖b‖)
```

Cosine measures the angle, discarding magnitude. It is the default for a reason: in these spaces magnitude tends to track incidental properties like text length and token frequency, while direction carries the semantics. A one-sentence and a three-paragraph statement of the same idea should be close, and cosine makes them close.

Practical detail worth knowing: most providers return **already-normalised** vectors (unit length). When vectors are normalised, cosine similarity and dot product are identical, and Euclidean distance is a monotone function of both. So the "which distance metric" question is often moot — but only if you actually normalised. Mixing normalised and unnormalised vectors in one index produces silently wrong rankings, and it is a real bug people ship.

Cosine's blind spot: it has no notion of **direction of implication**. "The service is available in India" and "The service is not available in India" are extremely close in embedding space. Negation is poorly represented, and this is a genuine, widely-reproduced weakness. If your domain hinges on negation or numeric comparison, embeddings alone will not carry it, and that is an argument for hybrid search (Book 02).

## The three properties that cause production surprises

### 1. Embeddings from different models are mutually meaningless

Each model has its own space. A vector from model A and a vector from model B cannot be compared, and the comparison will not error — it will return a plausible-looking number that means nothing. Consequences:

- **Changing your embedding model means re-embedding the entire corpus.** For a large corpus this is hours of compute and real money, and it must be done atomically or behind a version flag, because a half-migrated index returns garbage.
- **Store the model name and version alongside every vector.** This is the single cheapest piece of insurance in a retrieval system and it is routinely skipped.
- **The query must be embedded with the same model as the documents.** Obvious, and it is broken constantly in code where indexing and querying live in different services with independently-configured clients.

### 2. Query and document are not symmetric

The best retrieval models are trained **asymmetrically**: a short question should retrieve a long passage that answers it, which is a different relation from "these two paragraphs are about the same thing".

Many models implement this with **instruction prefixes** — you prepend something like `search_query: ` to queries and `search_document: ` to documents, or a task instruction string. Getting this wrong is a silent quality bug: everything works, retrieval is just meaningfully worse than it should be, and nothing in the logs tells you. **Read the model card. Use the prefixes it specifies.**

### 3. Similarity is not relevance

Two texts can be close in embedding space and useless to each other. A query about "how do I cancel my subscription" is close to a document about "why customers cancel subscriptions" — same topic, wrong answer.

This gap is structural. A bi-encoder embeds the query and the document *independently*, so no computation ever compares them jointly; the only interaction is a dot product at the end. That is what makes it fast enough to index millions of documents, and it is why a **cross-encoder reranker** — which puts query and document through a model together — is so much better at judging relevance and so much slower. The standard architecture, covered properly in Book 02, is: bi-encoder retrieves 50 candidates cheaply, cross-encoder reorders them expensively, top 5 go to the LLM.

## Choosing a model and a dimension

The decision factors, roughly in order of importance:

1. **Quality on *your* data.** Public leaderboards (MTEB and successors) are a starting point and are widely overfit. The only number that matters is recall@k on your own 40-question golden set, which takes an afternoon to build and settles the argument permanently.
2. **Dimension and cost of storage.** 1M chunks at 1,536 float32 dimensions is about 6 GB of raw vectors before index overhead. At 384 dimensions it is 1.5 GB. This matters for memory-resident indexes.
3. **Max input length.** Many embedding models truncate at 512 tokens, silently. If your chunks are 800 tokens, a third of each chunk is being ignored and you will not be told. Check the limit; make it a hard assertion in your indexing code.
4. **Multilingual need**, if the corpus is not all English.
5. **Self-hosted or API.** Embedding is cheap and highly parallel, and a small open model on a modest GPU is often the right answer at scale. Also the only answer when the data cannot leave.

**Matryoshka embeddings** are worth knowing: models trained so that the first N dimensions of the vector are themselves a usable embedding. That lets you store a truncated 256-dimension vector for a fast first pass and the full vector for precision, without running two models. It is a good thing to mention because it demonstrates you have read past the basics.

## Where embeddings are used beyond RAG

- **Semantic caching.** Embed the incoming query, look for a stored query above a similarity threshold, return the cached answer. This is EON's product thesis, and the entire difficulty is the threshold: too high and hit rate is negligible, too low and users get an answer to a question they did not ask. Book 06 covers how to pick it with data rather than by feel.
- **Deduplication and clustering.** Near-duplicate detection over a corpus; grouping support tickets by theme without predefined categories.
- **Classification without training.** Embed a handful of labelled examples per class, embed the input, assign the nearest class centroid. Startlingly effective, needs no training run, and gives you a baseline to beat before anyone reaches for fine-tuning.
- **Recommendation and "more like this"**, which is the same nearest-neighbour query pointed at a different corpus.

## The quiet failure modes

- **Silent truncation at the model's input limit.** Covered above. The most common one.
- **Embedding the wrong text.** Embedding a chunk that consists mostly of a boilerplate header means every chunk in the corpus is similar to every other. Strip boilerplate before embedding.
- **Distance concentration in high dimensions.** As dimensionality grows, the distances between random points converge, so the *spread* of similarity scores narrows. This is why absolute cosine thresholds do not transfer between models or corpora, and why "similarity > 0.8 means relevant" is a rule that will betray you. Calibrate thresholds per model, per corpus, against labelled data.
- **Stale vectors.** The document was edited; the vector was not re-computed. Version your chunks and make re-embedding part of the write path, not a nightly job you forget about.
- **Ignoring metadata.** A chunk's date, source, author and permissions do not live in the vector and cannot be recovered from it. Filtering has to happen in the database layer, and how that interacts with approximate indexes is a real problem covered in Book 02.

## The lab exercise

Twenty minutes, high value. Embed twenty sentences from your own domain, including deliberate traps: a pair that differ only by negation, a pair that are topically identical but one answers a question and one asks it, a pair with the same words in different order. Print the full similarity matrix and look at it. You will learn more about what your embedding model believes than from any amount of reading, and you will have a concrete example ready when someone asks what embeddings are bad at.

*Connect the dot:* the asymmetry point here is the reason Book 02's chapter on query transformation exists. If a query and a good answer are structurally different kinds of text, then rewriting the query into something that looks more like the answer (HyDE) is a natural move.

Next: getting structure out of the model reliably.
