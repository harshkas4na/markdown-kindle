# What the Model Actually Does

**Fast overview:** You do not need to derive attention to be a strong AI engineer, and you do need enough of the mechanism to predict how the system will behave. This chapter goes exactly that far: the shape of a transformer, what attention is buying, what the residual stream is, why the KV cache exists and why it is the thing that limits your serving, what mixture-of-experts changed about the economics, and the three training stages that explain why the model is helpful, agreeable, and occasionally confidently wrong.

## The shape

A decoder-only transformer, which is what essentially every chat model is, does this:

1. **Embed.** Each input token integer indexes into a matrix, producing a vector of `d_model` dimensions (a few thousand for a large model). Positional information is added or, in modern models, applied inside attention via rotary embeddings.
2. **Repeat N times** (N is the layer count, from tens to over a hundred):
   - **Attention.** Every position gathers information from earlier positions.
   - **Feed-forward network (MLP).** Each position is transformed independently through a wider hidden layer and back.
   - Both wrapped in normalisation and both added back into a **residual stream**.
3. **Unembed.** The final vector at the last position is multiplied by a matrix of vocabulary size, producing one **logit** per token in the vocabulary.

That is it. Everything the model knows lives in those weights, and everything it is currently thinking about lives in the residual stream.

## The residual stream, which is the useful mental model

Picture a wide highway running from input to output, one lane bundle per token position. Every layer *reads* from the highway, computes something, and *adds* its result back. Nothing is ever overwritten.

This picture explains several observed behaviours:

- Information written early can survive to the end, which is why deep models can maintain long-range consistency.
- Different layers specialise. Early layers do surface-level and syntactic work, middle layers do most of the semantic and factual retrieval, and late layers converge toward the specific output token.
- "Features" appear to be represented as directions in this space, superposed rather than one-neuron-per-concept. This is why interpretability is hard and why you cannot find "the honesty neuron".

## Attention, without the algebra

Each attention head, at each position, produces three vectors from the residual stream: a **query** (what am I looking for), a **key** (what do I offer) and a **value** (what I will hand over). Position *i* compares its query against the keys of all positions *j ≤ i*, softmaxes those scores into weights, and takes the weighted sum of the corresponding values.

That is the whole mechanism, and three properties matter to you:

- **Causal masking.** A decoder can only attend backwards. This is what makes the model autoregressive and is why you cannot edit earlier tokens without recomputing.
- **Multi-head.** Many heads run in parallel with different projections, so different heads learn different relationships. Some track syntax, some track "which entity does this pronoun refer to", some are the famous **induction heads** that implement "I saw this pattern before, continue it" and are largely responsible for in-context learning.
- **Quadratic cost.** With sequence length L, attention compares L positions against L positions. Compute is O(L²·d) for prefill. Doubling context roughly quadruples the attention compute, though in practice the MLPs and memory bandwidth mean total cost scales somewhere between linear and quadratic depending on regime.

FlashAttention did not change the asymptotics; it changed the constants by never materialising the L×L score matrix in high-bandwidth memory. That is why long contexts became affordable in practice without any algorithmic breakthrough in attention itself.

## The KV cache, which is the thing that actually limits you

When generating token 501, everything the model computed for tokens 1 through 500 is unchanged — causal masking guarantees it. So keys and values for previous positions are **cached** rather than recomputed. Without the cache, generating N tokens would cost O(N²) forward passes' worth of work; with it, each new token costs one pass over the cached state.

The cost is memory:

```
kv_bytes ≈ 2 (K and V) × layers × kv_heads × head_dim × seq_len × batch × bytes_per_value
```

For a large model at long context and meaningful batch size, this runs to many gigabytes and frequently exceeds the memory used by the weights themselves. Three things follow:

- **KV cache is why long context is expensive at serving time**, not just at prefill.
- **Grouped-query attention (GQA)** — many query heads sharing a smaller number of key/value heads — exists almost entirely to shrink this. It is the standard now.
- **Paged attention**, the idea behind vLLM, manages KV cache in fixed-size blocks like OS virtual memory instead of contiguous per-request allocations, which removes the fragmentation that previously wasted most of the memory. That is the whole reason vLLM produced such large throughput gains (Book 06).

**Prompt caching**, the feature you buy from an API, is this same cache persisted across requests for a shared prefix. It is why stable content goes at the front of your prompt.

## Prefill versus decode, precisely

| | Prefill | Decode |
|---|---|---|
| What | Process the whole input | Emit one token, repeat |
| Parallel? | Yes, all positions at once | No, inherently sequential |
| Bottleneck | Compute (matrix multiply throughput) | Memory bandwidth (must read all weights per token) |
| User-visible metric | Time to first token | Tokens per second |
| Helped by | More FLOPs, prompt caching | Bigger batches, speculative decoding, quantisation |

The decode bottleneck deserves a sentence of its own because it is counter-intuitive: generating a single token requires streaming every weight in the model from memory into the compute units, and doing almost nothing with each one. The GPU is idle waiting on memory. This is why **batching is close to free for decode** — sixteen requests read the same weights once — and why single-user self-hosted inference is so wasteful.

## Mixture of experts

In an MoE model, the MLP in each layer is replaced by many "expert" MLPs plus a router that sends each token to a small number of them (often two). A model can then have a very large **total** parameter count while only activating a fraction per token.

The engineering consequence: **memory requirements scale with total parameters, compute scales with active parameters.** MoE models are cheap to run relative to their capability and expensive to hold in memory. This is why most frontier models are now MoE, and why "how many parameters" stopped being a useful single number.

## The three training stages, and what each one explains

**1. Pretraining.** Next-token prediction over trillions of tokens of internet-scale text. This is where knowledge and capability come from, and it costs the overwhelming majority of the compute. Key consequence: **the knowledge cutoff**. The model's facts are frozen at the end of pretraining, which is the single strongest argument for retrieval.

**2. Supervised fine-tuning (SFT).** Training on curated instruction/response pairs. This is where "answer the question" replaces "continue the document". A base model given "What is the capital of France?" might plausibly continue with more quiz questions; an SFT'd model answers.

**3. Preference optimisation (RLHF, DPO, and relatives).** Humans (or a model trained on human judgments) rank candidate responses, and the model is optimised toward the preferred ones. This is where helpfulness, formatting habits, refusal behaviour and tone come from.

Stage 3 also explains the model's most annoying properties, and knowing this is a good interview signal:

- **Sycophancy.** Humans rated agreeable answers higher, so the model learned to agree. When you push back on a correct answer, it will often fold. This is a direct, documented consequence of the training objective, not a bug in your prompt.
- **Confident wrongness.** Raters preferred confident, complete answers over hedged ones. "I don't know" was rated poorly. So the model produces fluent answers regardless of whether it has grounds for them.
- **Formatting tics.** Bulleted lists, sectioned answers, the closing summary paragraph. All learned preferences.

More recently, **reasoning training** — reinforcement learning against verifiable outcomes in maths and code — produced models that generate long internal chains before answering. The engineering handle is that these models trade latency and output tokens for accuracy on hard problems, and are usually the wrong choice for simple high-volume tasks.

## What this means for how you build

- **The model is a next-token predictor, so it cannot check its own work unless you give it tokens to do so.** That is the entire mechanism behind chain-of-thought, self-critique and multi-pass pipelines.
- **The knowledge is frozen and lossy, so ground it.** Retrieval is not a hack around a temporary limitation; it is the correct architecture for anything factual and changing.
- **It is optimised to be agreeable, so do not use agreement as a signal.** Asking a model "are you sure?" is not verification. This has direct consequences for LLM-as-judge design in Book 04.
- **Serving cost is dominated by memory bandwidth and KV cache, not by cleverness.** Book 06's decisions all trace back to this paragraph.

*Connect the dot:* the "lost in the middle" behaviour covered next chapter is an attention-allocation phenomenon, and it is the single strongest argument for reranking retrieved chunks rather than dumping fifty of them into a long context.

Next: context windows, and what really happens as they fill up.
