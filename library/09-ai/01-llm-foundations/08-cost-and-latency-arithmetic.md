# Cost and Latency Arithmetic

**Fast overview:** Being able to do this arithmetic out loud is one of the fastest ways to sound like an engineer rather than an enthusiast, and it is the skill that most often decides an architecture. This chapter gives you the cost model, the latency model, worked examples at real scale, and the handful of levers that move each — ordered by how much they actually move.

## The cost model

```
cost_per_request = input_tokens  × price_in
                 + output_tokens × price_out
                 + cached_input  × price_cached   (usually a large discount)
```

Three structural facts to internalise:

1. **Output tokens cost several times input tokens.** Typically 3x to 5x. This follows directly from prefill being parallel and decode being sequential (Chapter 2). A verbose response format is therefore a much bigger deal than a verbose prompt.
2. **Model tier moves cost by 10x to 100x.** Small models are dramatically cheaper than frontier models. No prompt optimisation you ever do will move the bill as much as choosing the right tier.
3. **Cached input can be an order of magnitude cheaper than fresh input.** This changes the design of your prompt layout, not just your budget.

Prices change constantly; do not memorise numbers, memorise ratios. In an interview, "output is roughly 4x input, and the small tier is roughly 20x cheaper than the large one" is exactly the right level of precision.

## A worked example

A support assistant. 100,000 requests per day. Each request: 500-token system prompt, 3,000 tokens of retrieved context, 200-token user question, 400-token answer.

**Naive, everything on the frontier model, no caching.** At illustrative prices of $3/M input and $15/M output:

```
input  = 3,700 tok × 100k = 370M tok/day → 370 × $3  = $1,110/day
output =   400 tok × 100k =  40M tok/day →  40 × $15 =   $600/day
                                                  total ≈ $1,710/day ≈ $51k/month
```

Now apply the levers, in descending order of impact:

**Lever 1 — route by difficulty.** Measure first: suppose 70% of questions are routine and a small model answers them just as well on your golden set. At $0.15/M in and $0.60/M out, that 70% costs about $63/day instead of $1,197. **Saving: roughly $1,130/day.** This is the single biggest lever in almost every system, and it is only available to you if you have an eval that proves the small model is adequate.

**Lever 2 — prompt caching.** The 500-token system prompt is identical every time. If the retrieved context also has a stable portion, put everything stable at the front. Cached reads at roughly a tenth the price on the shared prefix are a straightforward win. **Saving on this example: a few percent of input cost, more if your stable prefix is large.** Note that in agent loops, where the entire growing conversation is resent every turn, caching is transformative rather than marginal.

**Lever 3 — trim the context.** Five well-ranked chunks instead of fifteen loosely-ranked ones. 3,000 tokens becomes 1,200. **Saving: about 45% of remaining input cost**, and per Chapter 3 the answers usually get *better*. Free money that people leave on the table because "more context can't hurt".

**Lever 4 — semantic caching.** If 20% of questions are near-duplicates of previous ones, a semantic cache serves them for the price of one embedding call. **Saving: about 20% of everything.** Threshold selection is the hard part (Book 06).

**Lever 5 — shorten the output.** Instruct for brevity, or return structure the UI expands. A 400-token answer becoming 250 saves nearly 40% of output cost.

Stack the first four and $51k/month becomes something in the region of $6-8k/month, on the same product. **That is the conversation an AI engineer is hired to have**, and it is worth rehearsing until the arithmetic comes out smoothly, because a version of it appears in interviews constantly.

## The latency model

```
total ≈ network + queue + prefill + (output_tokens × time_per_output_token)
```

- **Time to first token (TTFT)** = network + queue + prefill. Dominated by input length and by how loaded the provider is.
- **Time per output token (TPOT)**, or its reciprocal, tokens per second. Dominated by model size and batch conditions.
- **Total** for a 400-token answer at 50 tok/s is 8 seconds of decode, and no prompt tuning will fix that. **Output length is the dominant term in perceived latency for anything longer than a sentence.**

Rules of thumb worth carrying: small models are several times faster per token than large ones; prefill of a few thousand tokens is typically a few hundred milliseconds; a long context prompt can put TTFT into whole seconds; and provider tail latency (p99) is frequently 3-5x the median, which is why timeout and retry policy is a real design decision rather than a default.

## Streaming is a latency *perception* lever

Streaming does not reduce total time; it reduces time-to-first-visible-token from 8 seconds to 400ms, and that is the number users actually experience. Any user-facing generation should stream.

Where it does **not** help: structured output consumed by code, and any pipeline stage whose result feeds another stage. A chain of three streamed calls is not faster than three unstreamed ones; only the last one's stream is visible to anyone.

## Latency budgeting

Give every component an allowance and design against it, rather than assembling components and measuring what you get. A conversational assistant with a 2-second target:

| Stage | Budget | Notes |
|---|---|---|
| Request handling, auth | 20 ms | |
| Query embedding | 40 ms | small model, or cached |
| Vector search | 30 ms | HNSW at moderate `ef_search` |
| Reranking (top 50 → 5) | 120 ms | the usual thing that gets cut first |
| Prompt assembly | 10 ms | |
| LLM TTFT | 600 ms | |
| Streaming to visible answer | remaining | |

If reranking does not fit, you now know what you are trading and can decide with a number. Book 04's harness should measure quality *at* each latency configuration, which turns "should we rerank" from an opinion into a two-column table.

For a voice agent the budget is far tighter — the conversational turn threshold where a pause starts to feel unnatural is around 700ms to 1s end to end, which has to cover speech recognition, the model, and speech synthesis. This is why voice-agent architectures look so different, and it is the substance behind the honest-gap script on voice in Book 00.

## Concurrency, throughput and rate limits

Providers limit both requests per minute and **tokens per minute**, and the token limit binds first in most RAG applications, since each request carries thousands of input tokens. A client that only tracks request counts will hit 429s it cannot explain.

Build the boring things: a token-aware client-side limiter, exponential backoff with jitter on 429 and 5xx, a circuit breaker so a provider outage fails fast instead of queueing forever, and a fallback provider for anything user-facing. None of this is AI-specific and all of it is what makes an LLM feature production-grade. Hashtro's per-IP rate limiting and TTL caching is the same instinct applied one layer out, and it is legitimate evidence of the habit.

## Self-hosting: the crossover

Roughly: a GPU instance capable of serving a mid-size open model costs on the order of $1 to $3 per hour on demand, so about $700 to $2,200 a month running continuously. Under vLLM with good batching it can serve a substantial token throughput.

The honest analysis has four parts, and giving all four is what makes the answer sound senior:

1. **The crossover exists and is volume-dependent.** Below a few million tokens a day, an API is almost always cheaper once engineering time is counted.
2. **Utilisation is the hidden variable.** A GPU you rent for 24 hours and use for 3 costs 8x its apparent price. Bursty traffic favours APIs strongly.
3. **Non-cost reasons often decide it anyway.** Data residency, privacy, no external dependency, a fine-tuned model, or predictable latency without a provider's queue.
4. **Engineering cost is real.** Someone owns the deployment, the upgrades, the GPU incidents and the capacity planning. At a startup that person is the whole AI team.

## The instinct to build

Every architecture decision in this field should come with three numbers attached: **what it costs, what it adds to p95, and what it does to the eval score.** A proposal with only the third is incomplete, and a proposal with only the first two is how products get cheap and bad. Getting into the habit of stating all three is, more than any specific technique in this book, what makes someone sound like they have shipped this before.

*Connect the dot:* Book 06 takes every lever in this chapter and shows the implementation — tracing to get the numbers, caching to move them, and rollout to change them safely.

Next: choosing a model, which is where most of this arithmetic actually gets applied.
