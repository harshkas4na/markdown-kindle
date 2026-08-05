# Context Assembly and Citations

**Fast overview:** You have five good chunks. How you render them into a prompt decides whether the model uses them, and whether anyone can check the result afterwards. This chapter covers ordering (which follows directly from lost-in-the-middle), the token budget, expanding hits into their neighbourhoods, prompt structure for grounded answering, and citations — which are the single feature that changes a RAG product from a plausible-answer machine into something a professional will trust.

## Ordering

From Book 01, Chapter 3: attention over long contexts is U-shaped, best at the start and the end.

So the ordering rules:

- **Best chunk first.** If you send five and the model uses one, it should be the good one.
- **Second-best last**, if the context is long enough that the middle is genuinely disadvantaged. Some teams alternate outward from the ends. Measure it; the effect size depends on model and context length.
- **Never rely on the model to sort by relevance.** It will not.
- **Restate the question after the context**, briefly.

There is a competing consideration for corpora where chunks are sequential: **document order** can be more comprehensible than relevance order. If three chunks come from the same section, presenting them in reading order lets the model follow an argument. A reasonable compromise: group by document, order groups by best-chunk relevance, and order within a group by position.

## The token budget, revisited

```python
def assemble(chunks, question, system, max_window=128_000, reserve_out=4_000):
    budget = max_window - reserve_out - count(system) - count(question) - 200  # slack
    selected, used = [], 0
    for c in chunks:                       # relevance order
        if used + c.token_count > budget:
            break
        selected.append(c); used += c.token_count
    return selected
```

Two refinements worth having:

- **A hard floor on chunks.** If the first chunk alone exceeds the budget, truncate it rather than sending nothing. A truncated best chunk beats an empty context.
- **A cap well below the true window.** Just because 128k fits does not mean you should use it. Both cost and quality argue for 4k-8k of retrieved context in most products. The window is a limit, not a target.

## Expanding a hit into its neighbourhood

A retrieved chunk is often the *middle* of the relevant material. Two cheap expansions, both enabled by the `position` and `parent_id` metadata captured at index time:

**Sentence-window / neighbour expansion.** Retrieve on a small chunk, then fetch the chunks immediately before and after it and send the three together. Trivial to implement, and it fixes the "the answer was split across the boundary" failure without any change to chunking.

```python
def expand(hit, store, window=1):
    return store.get_range(hit.doc_id, hit.ord - window, hit.ord + window)
```

**Parent expansion.** The small-to-big pattern from Chapter 3: retrieve children, return parents. Better when documents have real sections.

Deduplicate after expanding — two adjacent hits with window 1 will overlap — and merge contiguous ranges into a single span so the model sees continuous prose rather than repeated fragments.

## The prompt

```python
GROUNDED = """You answer questions using only the sources provided below.

Rules:
- Use only information from the sources. Do not use prior knowledge.
- Cite the source id for every factual claim, like this: [S2].
- If the sources do not contain enough information to answer, reply exactly:
  NOT_FOUND
- If the sources disagree, say so and cite both.

<sources>
{sources}
</sources>

Question: {question}

Answer the question above using only the sources, citing ids."""

def render_sources(chunks):
    return "\n\n".join(
        f'<source id="S{i+1}" title="{c.title}" section="{c.section}" '
        f'updated="{c.updated_at:%Y-%m-%d}">\n{c.content}\n</source>'
        for i, c in enumerate(chunks))
```

Every element is deliberate:

- **Tagged sources** separate data from instructions, which helps comprehension and is the first defence against injection through retrieved content (Book 05).
- **Stable short ids** (`S1`…) rather than UUIDs. Cheap in tokens, easy for the model to reproduce correctly, and mappable back to real ids in your code.
- **Metadata in the tag** — title, section, date — lets the model reason about recency and provenance, and lets it say "according to the 2024 policy" when two sources conflict.
- **An explicit escape token.** `NOT_FOUND` is machine-detectable, which makes it a metric (Chapter 11) rather than a prose apology you have to parse.
- **Explicit conflict handling.** Real corpora contain contradictions, and without instruction the model silently picks one.
- **Instruction repeated after the sources.**

## Citations, and why they change the product

Citations do four things, and only the first is obvious:

1. **They let the user check.** In any professional domain this is the difference between a toy and a tool.
2. **They let *you* check.** A citation is a machine-verifiable link between a claim and a chunk, which makes automated faithfulness scoring possible (Chapter 11).
3. **They constrain the model.** Requiring a citation per claim measurably reduces unsupported statements, because the model has to point at something.
4. **They localise failures.** When an answer is wrong you immediately see whether it cited the wrong chunk (retrieval problem) or cited a chunk that does not support the claim (grounding problem).

### Verifying citations in code

Never trust the model's citation without checking it:

```python
def verify(answer, sources):
    cited = set(re.findall(r"\[S(\d+)\]", answer))
    valid = {str(i+1) for i in range(len(sources))}
    hallucinated = cited - valid          # cited a source that does not exist
    uncited_claims = not cited and "NOT_FOUND" not in answer
    return hallucinated, uncited_claims
```

Citing a non-existent source id is a real and detectable failure, and it is a cheap online metric. So is **citation rate** — the fraction of answers containing at least one citation — which drops when retrieval quality degrades and is therefore a useful production alarm.

For stronger verification, a **claim-level entailment check**: split the answer into sentences, and for each, ask a cheap model whether the cited source entails it. That is the faithfulness scorer, and it is the same machinery as Chapter 11's eval, running online on a sample of traffic.

### Presenting them

Map `S1` back to a real title and link before showing the user. Highlight the supporting span inside the source if you can — storing character offsets at chunk time makes this possible. And show the sources even when the answer is `NOT_FOUND`, because "here is what I found, none of it answers your question" is a far better experience than a bare refusal, and it lets the user judge whether retrieval failed.

## Handling NOT_FOUND well

The escape hatch only helps if the product does something sensible with it:

- **Do not show a raw refusal.** Show what was retrieved, and offer next steps: rephrase, broaden the date range, search a different corpus.
- **Log every one.** The NOT_FOUND rate is one of the best health metrics you have, and the *specific queries* that trigger it are a free list of corpus gaps. Feed them back: either the document is missing (fix the corpus) or retrieval missed it (fix retrieval, and add it to the golden set).
- **Distinguish "not in the corpus" from "retrieval failed"** by checking, offline, whether the answer exists anywhere in the corpus. This is exactly the recall measurement of Chapter 11, run on production misses.

## Multi-turn context

In a chat product the assembled context accumulates. Two rules:

- **Do not re-send the previous turns' retrieved chunks** unless they are still relevant. They bloat the window and anchor the model to stale material. Retrieve fresh per turn.
- **Do keep the conversation summary and the previous answers**, which carry the thread.

The structured-state approach from Book 01 Chapter 3 applies here: keep a small typed object of what has been established, re-render it each turn, and let retrieval be stateless.

*Connect the dot:* the `NOT_FOUND` token, the citation ids and the verification function in this chapter are not three features. They are the instrumentation that makes the next chapter possible. A system with no escape token and no citations cannot be evaluated except by human reading.

Next: the chapter the whole book exists for.
