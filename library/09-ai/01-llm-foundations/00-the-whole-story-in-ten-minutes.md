# The Whole Story in Ten Minutes

**Fast overview:** This chapter is the entire book compressed, so that everything after it is elaboration rather than revelation. If you read only this chapter you will still be able to hold a coherent conversation about how these systems work. If you read the rest, this is the map that keeps the pieces in relation to each other.

## One sentence

A large language model is a function that takes a sequence of integers and returns a probability distribution over the next integer, and every product you have ever used that felt like intelligence is that function called in a loop with increasingly clever things stuffed into its input.

Everything in AI engineering is a consequence of that sentence. Retrieval is stuffing the right things into the input. Agents are the loop with tools bolted on. Evals are checking whether the outputs of the loop are any good. Guardrails are limiting what the loop is allowed to do. Serving is running the loop cheaply. Keep coming back to it.

## Text goes in as integers

The model has no concept of characters or words. A **tokeniser** chops text into pieces from a fixed vocabulary — usually 50,000 to 200,000 entries — and maps each to an integer. Common words are single tokens; rare words fragment; whitespace and punctuation cost real tokens; code and JSON fragment much worse than English prose. Roughly, English is about 0.75 words per token, which is where the folk rule "1,000 tokens is about 750 words" comes from. Code can be half that efficient, and heavily punctuated JSON worse again.

**Why you care as an engineer:** every price, every context limit and every rate limit in this industry is denominated in tokens. If you estimate in characters you will be wrong by an ecosystem-dependent multiple. And the same information expressed as prose rather than JSON can cost a third as much, which is an actual lever on the bill.

## The model produces one token at a time

Given the input sequence, the model produces a **logit** for every token in the vocabulary — a raw score. Softmax turns those scores into probabilities. A **sampler** picks one. That token is appended to the sequence and the whole thing runs again.

That autoregressive loop is why:

- Output tokens are far more expensive than input tokens (each one is a separate forward pass, while the input is processed in parallel).
- Streaming exists at all. You are watching the loop.
- The model cannot "think ahead" except by writing tokens down, which is exactly why chain-of-thought and reasoning modes work: giving the model tokens to spend is giving it computation.

## Two phases with completely different performance characteristics

**Prefill** processes your whole input at once. It is compute-bound and parallel, and it determines your **time to first token**.

**Decode** produces output tokens one at a time. It is memory-bandwidth-bound and sequential, and it determines your **tokens per second**.

This split explains almost every serving decision in Book 06. Batching helps decode enormously and prefill less. Prompt caching attacks prefill. A long prompt with a short answer and a short prompt with a long answer have completely different cost and latency shapes even at the same total token count.

## Attention is why context is expensive

The mechanism that lets a token at position 900 be influenced by a token at position 4 is **attention**: each token attends to every earlier token. That is quadratic in sequence length for compute in the naive formulation, and the **KV cache** (the stored keys and values for every previous token, kept so decode does not recompute them) grows linearly with context and is usually the actual memory wall.

Practically: a 200,000-token context window is a real capability and an expensive one, models do not attend uniformly across it (material in the middle of a long context is retrieved less reliably than material at the start or end, the well-documented "lost in the middle" effect), and "just put everything in the context" is a real architecture with real costs rather than a free lunch that makes retrieval obsolete.

## Sampling: temperature 0 is not determinism

The sampler has knobs. **Temperature** scales the logits before softmax: below 1 it sharpens the distribution toward the most likely token, above 1 it flattens it. **Top-k** restricts sampling to the k most likely tokens. **Top-p** (nucleus) restricts it to the smallest set whose probabilities sum to p.

Temperature 0 means "always take the argmax", and it still is not reproducible across runs in practice, because floating-point non-associativity in batched GPU kernels means the logits themselves differ slightly depending on what else was in the batch. Two nearly-tied tokens can swap order. **Design as if the model is non-deterministic, because it is.** This single fact is the reason evals are statistical rather than assertion-based, and it is a common interview question.

## Embeddings are a different output of the same machinery

An **embedding** is a fixed-length vector representing a piece of text, produced by a model trained so that texts with similar meaning land near each other. Similarity is almost always cosine, because direction carries the meaning and magnitude mostly carries length artifacts.

Three facts that matter more than the definition:

1. **Embeddings from different models are not comparable.** Different spaces entirely. Changing your embedding model means re-embedding the whole corpus. This is the most expensive irreversible-feeling decision in a RAG system, which is why Book 02 spends a chapter on it.
2. **Similar is not the same as relevant.** A query and a document can be topically close and useless to each other. This gap is precisely what rerankers exist to close.
3. **Embeddings have no notion of recency, authority or correctness.** They will happily retrieve the confidently wrong deprecated document.

## Structure has to be enforced, not requested

Asking for JSON in the prompt gets you JSON most of the time, and "most of the time" is a production incident. The mechanisms that actually work, in ascending order of strength: few-shot examples, a JSON mode flag, tool/function calling with a schema, and constrained decoding (masking the logits so that only tokens allowed by the grammar can be sampled). The last one cannot produce invalid output because invalid tokens are never available to sample.

The engineering rule: **validate at the boundary anyway** (pydantic in Python, zod in TypeScript), and have a repair path. Structure enforcement reduces failures; it does not eliminate the semantically-wrong-but-well-typed answer.

## Prompts are code

A prompt determines system behaviour, changes break things, and changes need review. Therefore prompts belong in version control with a version identifier attached, they belong in an eval suite, and every trace should record which prompt version produced it. Prompts living in a Notion page and pasted into a dashboard is the single most common way an AI product becomes unmaintainable.

The techniques that reliably help: be specific about the task, show examples rather than describing them, give the model room to reason before it answers, put the instruction after long context rather than before, and state the failure behaviour explicitly ("if the context does not contain the answer, say so"). The techniques that reliably do not: politeness, threats, "you are a world-class expert", and adding more words in general. A longer prompt dilutes attention and costs money.

## The cost model, in one formula

```
cost = (input_tokens × input_price) + (output_tokens × output_price)
```

Output is typically several times the price of input. Prompt caching can drop the price of repeated input prefixes by an order of magnitude, which is why stable content goes at the *front* of a prompt and variable content at the back. And the model tier you pick usually moves cost by 10x to 100x, which is a bigger lever than any prompt optimisation you will ever do.

**The engineering instinct to build:** most production LLM systems should route. Cheap fast model for the common case, expensive model for the hard case, with a classifier or a confidence signal deciding. The eval harness is what tells you whether the cheap path is good enough, which is one more reason evals come before optimisation.

## What this book covers next

| Ch | Topic |
|---|---|
| 1 | Tokens and tokenisers, in detail, with the counting you should actually do |
| 2 | What the model is doing: transformers to the depth an engineer needs |
| 3 | Context windows, prefill/decode, KV cache, lost in the middle |
| 4 | Sampling, determinism, and reasoning models |
| 5 | Embeddings: spaces, similarity, dimensions, and the choices they force |
| 6 | Structured output and constrained decoding |
| 7 | Prompting as engineering, with versioning and testing |
| 8 | Cost and latency arithmetic, with worked numbers |
| 9 | Choosing a model, and why the smallest one that passes is correct |
| 10 | Failure modes: hallucination, sycophancy, drift, and what each one is really caused by |
| 11 | What you can now honestly say |

Next: tokens. The unit everything else is denominated in.
