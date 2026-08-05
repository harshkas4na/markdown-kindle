# Chunking

**Fast overview:** Chunking is where a document becomes retrievable units, and the choice sets a ceiling on everything downstream. Too small and each chunk is a fragment with no context; too large and its embedding is a blurry average of several topics. There is no universally correct size, which is unsatisfying and true, so this chapter gives you the strategies, the trade-off that governs all of them, the decision procedure for your corpus, and the two techniques that let you stop trading.

## The central tension

An embedding is one vector for the whole chunk. That vector is, loosely, an average of the chunk's meaning.

- **Small chunks** produce sharp, specific embeddings that match narrow queries well. And a small chunk often lacks the context to be *useful* once retrieved: "It increased by 12% in that period" is a great match for a query about increases and useless as an answer because *it* and *that period* are unresolved.
- **Large chunks** carry their own context and retrieve worse, because a chunk covering five topics has an embedding that is strongly about none of them. Add that they consume more of your context budget per hit, so you retrieve fewer of them.

So: **retrieval wants small, generation wants large.** Every strategy below is a way of managing that, and the two decoupling techniques at the end are ways of refusing it.

## The strategies

### Fixed-size

Split every N tokens with an overlap. Crude, fast, predictable, and it cuts through sentences and tables indiscriminately. Its real virtue is that it is a fine baseline: implement it, measure it, and only adopt something more complex if the measurement justifies it.

### Recursive character/token splitting

The pragmatic default. Try to split on the largest natural boundary first, and fall back progressively: paragraphs (`\n\n`), then lines, then sentences, then words. Respect a maximum size throughout.

```python
SEPARATORS = ["\n## ", "\n\n", "\n", ". ", " "]

def recursive_split(text, max_tokens, count, seps=SEPARATORS):
    if count(text) <= max_tokens:
        return [text]
    for i, sep in enumerate(seps):
        if sep in text:
            parts, out, buf = text.split(sep), [], ""
            for p in parts:
                cand = buf + sep + p if buf else p
                if count(cand) <= max_tokens:
                    buf = cand
                else:
                    if buf: out.append(buf)
                    buf = p if count(p) <= max_tokens else None
                    if buf is None:
                        out += recursive_split(p, max_tokens, count, seps[i+1:])
                        buf = ""
            if buf: out.append(buf)
            return out
    return [text[:max_tokens]]
```

Good enough for the large majority of prose corpora, and it is what you should benchmark everything else against.

### Document-structure-aware

The best strategy when the documents have real structure, which is more often than people assume. Split on markdown headings, HTML sections, legal clause numbering, patent sections, function boundaries in code. The boundaries the author wrote are almost always better than boundaries you infer statistically.

Crucially, **carry the heading path into the chunk**: a chunk under `## Billing > ### Refunds` should have that prefix in its text, not just in metadata, because it changes the embedding for the better and gives the model the context for free. This is cheap and it is one of the highest-return-per-line changes available.

### Semantic chunking

Embed each sentence, walk through the document, and start a new chunk where consecutive-sentence similarity drops below a threshold — a detected topic change.

Intellectually appealing. In practice: it costs an embedding call per sentence at index time, the threshold is another hyperparameter to tune, and on many corpora it measurably ties with recursive splitting. **Measure before adopting**, and be willing to say that in an interview, because "we tried semantic chunking and it did not beat recursive on our corpus, so we kept the simpler thing" is a much stronger answer than adopting it because it sounds sophisticated.

### Agentic / LLM-based chunking

Give the document to a model and ask it to split it into semantically coherent sections with titles. Highest quality, highest cost, and only defensible for small high-value corpora — contracts, patents, regulatory filings — where a page of documents is worth real money.

## Overlap

Overlap exists because an answer that straddles a boundary would otherwise be split across two chunks, each holding half of it. 10-20% is the usual range.

The costs are real: duplicated storage, duplicated tokens if two overlapping chunks both get retrieved, and near-duplicate results crowding your top-k. Deduplicate at retrieval time by document and position, or merge adjacent hits into one span.

If you use structure-aware chunking, overlap matters much less, because the boundaries are meaningful rather than arbitrary.

## Choosing a size, empirically

The decision procedure, which is the actual answer to "what chunk size should I use":

1. Build the 40-query golden set (Chapter 11), each labelled with which chunk *should* answer it.
2. Index the corpus at 256, 512, 1024 and 2048 tokens, each with 15% overlap.
3. Measure recall@5 and recall@20 for each.
4. Also measure end-to-end answer quality, because the best retrieval size is not always the best generation size.
5. Pick, and record the number in the repo so the next person does not redo it.

Half a day of work. Rough priors to start from, subject to being overturned by the measurement:

| Corpus | Starting point |
|---|---|
| FAQ, support articles | 256-512, structure-aware |
| Technical documentation | 512-1024, split on headings |
| Long-form reports, patents | 1024-2048, split on sections |
| Code | Function/class boundaries, size follows the code |
| Chat/transcripts | By turn group or by speaker span, not by token count |

## The two techniques that decouple retrieval from generation

These are the good answers, and knowing them is what separates a chunking answer from a chunking *opinion*.

### Small-to-big (parent document retrieval)

**Index small, return large.** Embed small precise chunks for matching, but store a pointer from each to its larger parent section. Retrieve on the small chunks, then hand the model the parents.

You get sharp retrieval and complete context, and the tension in the first section of this chapter simply goes away. The costs are storage and a slightly more complex retrieval path. This is the default worth reaching for on any corpus with real document structure.

```python
# index: chunk small, keep a parent id
{"id": "c_881", "text": <200 tokens>, "parent_id": "s_44"}
# retrieve: match on children, dedupe to parents, fetch parent text
```

### Contextual retrieval

Before embedding, prepend to each chunk a one-or-two-sentence description of what it is and where it sits in the document, generated by a cheap model given the chunk and a summary of the document.

So a chunk reading "It increased by 12% in that period" becomes "From the Q3 2025 revenue section of the Acme annual report, discussing subscription revenue: It increased by 12% in that period."

The pronouns resolve, the embedding sharpens, and retrieval quality improves substantially on corpora with this problem. The cost is one cheap LLM call per chunk at index time, made affordable by prompt caching the document summary across all its chunks. It has been reported to produce large reductions in retrieval failure rate and it is worth measuring on any corpus where chunks are context-dependent.

Combine the two — contextual descriptions on small chunks, returning parents — and chunking stops being the thing that limits you.

## The rules to keep

- **Never split a table, a code block or a list mid-structure.**
- **Prefer boundaries the author wrote** over boundaries you compute.
- **Every chunk should be independently comprehensible**, or should be made so by a prefix.
- **Store the token count at index time** so context assembly is arithmetic.
- **Store position and parent ids** so you can expand a hit into its neighbourhood.
- **Re-chunking means re-embedding.** Chunking and embedding-model choice are one migration, not two, so decide them together.

*Connect the dot:* every chunk you produce here becomes a row in Chapter 11's recall calculation. Chunking changes cannot be evaluated without that labelled set, which is why the golden set is built before the chunking experiments, not after.

Next: embedding models, and the one decision in this pipeline you cannot cheaply undo.
