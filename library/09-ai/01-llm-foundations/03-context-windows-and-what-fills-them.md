# Context Windows and What Fills Them

**Fast overview:** The context window is the model's entire world for one request: no memory before it, nothing after it. Large windows created a widespread belief that retrieval is obsolete, and that belief is wrong for three separate reasons — cost, latency, and the measurable fact that models do not use long contexts uniformly. This chapter covers what the window really is, what competes for space inside it, how to budget it, how to manage a conversation that outgrows it, and the effect that decides the layout of every RAG prompt you will write.

## What the window is

The context window is the maximum number of tokens in a single forward pass: system prompt, conversation history, tool definitions, tool results, retrieved documents, the user's message, and the output being generated, all counted together. Windows in current models range from tens of thousands to a million-plus tokens.

Two clarifications that come up constantly:

- **The window is shared between input and output.** A 128k window with 120k of input leaves 8k for the answer, and models will silently produce a truncated response or error. Reserve output space explicitly.
- **The window is per request, not per session.** The model has no memory between calls. A chat that "remembers" is a client resending the whole history every turn, which is why long conversations get more expensive linearly and why context management is a real engineering task rather than a framework feature.

## What competes for the space

In a mature agentic application the user's actual message is often the smallest thing in the window:

| Component | Typical size |
|---|---|
| System prompt | 200 – 3,000 tokens |
| Tool/function definitions | 100 – 500 tokens per tool, and this adds up fast |
| Conversation history | Unbounded, grows every turn |
| Retrieved chunks | 1,000 – 20,000 tokens |
| Tool call results | Wildly variable, and the usual cause of blowouts |
| User message | 10 – 500 tokens |
| Reserved for output | 500 – 4,000 tokens |

The two entries to watch are tool definitions and tool results. Fifteen tools with verbose JSON schemas is several thousand tokens on *every single call* before anything happens. And a tool that returns a raw API response can dump 30,000 tokens of nested JSON into the window in one step, blowing the budget and burying the relevant field. Both have the same fix: **truncate and summarise at the tool boundary, in code, before the result reaches the model.**

## Lost in the middle

The most important empirical result about long context, first shown clearly by Liu et al. in 2023 and reproduced repeatedly since: when the answer to a question is placed in a long context, retrieval accuracy is highest when it sits near the **beginning** or the **end**, and measurably worse when it sits in the **middle**. The curve is U-shaped, and the degradation is large enough to matter — not a rounding error.

Newer models have improved on the raw needle-in-a-haystack version of this test, and the effect has not disappeared, particularly once the task requires combining several pieces of information rather than finding one distinctive sentence.

**Design consequences, all of which you should be able to state:**

1. **Put the most relevant retrieved chunk first, or last.** Not buried at position 12 of 20. This is why the output *order* of a reranker matters, not just which chunks it selects.
2. **Put the instruction after the long context**, not before it. When 40,000 tokens of documents sit between your instruction and the model's answer, the instruction is competing with all of them. Restating the task briefly at the end is cheap and measurably effective.
3. **Fewer, better chunks beat more chunks.** Five well-ranked chunks routinely outperform twenty loosely-ranked ones, and cost a quarter as much. This is the single most useful thing to know when someone proposes "just retrieve top-50 and let the long context sort it out".

## The long-context-versus-RAG argument, settled

You will be asked this. The honest answer has four parts:

- **Cost.** Stuffing a 300k-token corpus into every request, versus retrieving 4k of it, is a 75x difference on the input side of the bill. At any real volume this is the entire argument.
- **Latency.** Prefill is compute-bound and scales with input length. Time to first token on a 300k-token prompt is seconds, not milliseconds. For anything interactive this alone rules it out.
- **Accuracy.** Lost-in-the-middle plus distractor sensitivity means more irrelevant context actively degrades answers. Retrieval is a precision mechanism, not just a compression one.
- **Freshness and access control.** A retrieval layer can filter by permission, recency and source. A giant prompt cannot, and "the model saw a document this user is not allowed to see" is a security incident.

**And the honest counter-argument**, which makes the answer sound like judgment rather than dogma: when the corpus is genuinely small (a single contract, one codebase file, a 30-page report), when the question requires holistic understanding rather than lookup ("summarise the tone shift across this whole document"), or when prompt caching makes a stable large prefix nearly free, long context is simply the better and simpler engineering choice. Do not build a vector database for 200 documents.

## Managing a conversation that outgrows the window

Four strategies, and real systems combine them:

**Truncation.** Drop oldest messages. Trivial, and it loses the beginning of the conversation, which is often where the user stated the goal. Always pin the system prompt and usually the first user message.

**Summarisation.** When history crosses a threshold, ask the model to compress the older portion into a summary and replace it. Effective, and it is lossy in ways that are hard to predict, so summarise the *old* portion and keep the last few turns verbatim. Keep the summarisation prompt in version control and in the eval suite, because a bad summariser degrades everything downstream invisibly.

**Retrieval over history.** Store every turn, embed it, retrieve relevant past turns per request. Scales indefinitely and breaks temporal continuity, so it works better for "what did the user say about X" than for "continue what we were doing".

**Structured state.** The one people underuse. Instead of keeping conversation, keep a typed object — the facts extracted so far, the current step, the decisions made — and re-render it into the prompt each turn. Bounded size, inspectable, testable, and it survives a model swap. This is what LangGraph's state model encourages and it is the right default for anything task-shaped rather than chat-shaped.

## Budgeting, concretely

Do this arithmetic explicitly in code rather than hoping:

```python
WINDOW        = 128_000
RESERVE_OUT   =   4_000
system        = count(system_prompt)
tools         = count(tool_schemas)
history       = count(recent_messages)

available_for_context = WINDOW - RESERVE_OUT - system - tools - history

chunks, used = [], 0
for c in reranked_chunks:          # already in relevance order
    if used + c.token_count > available_for_context:
        break
    chunks.append(c); used += c.token_count
```

Two details worth noticing. Chunks carry their token count as **metadata computed at index time**, so assembly is arithmetic rather than re-tokenising a corpus per request. And the loop `break`s rather than `continue`s, because chunks are in relevance order and skipping a large chunk to fit a small less-relevant one is usually the wrong trade — though a knapsack variant is defensible if you have measured it.

## Effective versus advertised window

A model advertising 1M tokens does not perform equally across all of it. Advertised length is the architectural maximum; **effective** length is where accuracy holds up on your task. Public long-context benchmarks (needle-in-a-haystack variants, RULER, and multi-hop long-context sets) consistently show degradation well before the advertised limit, and the gap is worse for tasks needing several facts combined than for single-fact lookup.

If your product depends on long context, **measure it on your own data**: take real documents, place a known fact at 10%, 30%, 50%, 70% and 90% depth, and ask for it. Half a day of work, and it gives you a number for your specific corpus rather than a vendor's. It is also, conveniently, a small eval harness, which is exactly the artifact Book 04 is about.

*Connect the dot:* the reason Book 02 spends so long on rerankers is this chapter. A reranker's job is to make "five chunks, best first" possible, which is what the attention behaviour described here rewards.

Next: sampling, and why "temperature 0" does not mean what people think it means.
