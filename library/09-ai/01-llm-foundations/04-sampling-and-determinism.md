# Sampling and Determinism

**Fast overview:** The model gives you a probability distribution; the sampler turns it into a token. That handoff is where temperature, top-k and top-p live, and it is also where most people's mental model is subtly wrong in a way that matters. The headline: temperature 0 does not give you reproducibility, non-determinism is a permanent property of the system rather than a setting you failed to find, and every eval you ever write has to be designed around that fact.

## From logits to a token

The final layer produces one **logit** per vocabulary entry — an unbounded real number, higher meaning more likely. Softmax converts logits to probabilities:

```
p_i = exp(logit_i / T) / Σ_j exp(logit_j / T)
```

`T` is **temperature**, and it is applied *before* the exponential, which is why it works the way it does:

- **T → 0**: the largest logit dominates completely. The distribution collapses to a point mass on the argmax. This is "greedy decoding".
- **T = 1**: the distribution as the model produced it.
- **T > 1**: differences between logits are compressed, so unlikely tokens become relatively more likely. Above roughly 1.5 output degrades quickly toward incoherence.

Temperature does not make the model more creative in any meaningful sense. It makes the model more willing to take its second and third choices, which sometimes reads as creativity and sometimes reads as a hallucinated function name.

## Top-k and top-p

Two truncation strategies applied to the distribution before sampling:

**Top-k** keeps the k highest-probability tokens and renormalises. Simple, and blunt: k=40 is far too permissive when the model is 99% certain, and too restrictive when it is genuinely uncertain across hundreds of plausible continuations.

**Top-p (nucleus)** keeps the smallest set of tokens whose cumulative probability reaches p, then renormalises. This adapts: when the model is confident, the nucleus is one or two tokens; when it is uncertain, the nucleus is wide. p=0.9 to 0.95 is the common default and it is a better default than top-k for the same reason a percentile is a better summary than a fixed count.

**Repetition and frequency penalties** subtract from the logits of tokens already produced. Useful for stopping degenerate loops; harmful in code and structured output, where legitimate repetition is constant (`import`, `self.`, `return`). Default them to zero for structured tasks.

**Min-p**, a newer alternative, keeps tokens whose probability is at least some fraction of the top token's probability. It behaves better than top-p at high temperatures and is worth knowing about as a signal that you read past the defaults.

## What to set, in practice

| Task | Settings | Why |
|---|---|---|
| Extraction, classification, structured output | T = 0 | You want the argmax path, every time |
| Tool/function calling | T = 0 | Hallucinated arguments are the main failure; do not sample into them |
| RAG answering | T = 0 to 0.3 | Grounded, faithful; creativity is not the goal |
| Summarisation | T = 0.3 to 0.5 | Slight variation reads more naturally |
| Brainstorming, copy variants | T = 0.7 to 1.0 | Diversity is the product |
| Generating eval data or synthetic variety | T ≈ 1.0, and vary the seed/prompt | You want spread on purpose |

Set **one** of top-p or temperature, not both, unless you have measured the interaction. Providers' defaults differ; be explicit rather than inheriting whatever the SDK does.

## The non-determinism that surprises people

Set temperature 0, send the identical request twice, and you can still get different outputs. This is not a bug in your code, and the reason is worth understanding because it is a favourite interview question.

**Floating-point addition is not associative.** `(a + b) + c` can differ from `a + (b + c)` in the last bits. GPU kernels sum over many elements in parallel, and the reduction order depends on how work was partitioned — which depends on the batch. On a shared inference server, your request is batched with whatever else arrived at that moment. Different batch composition, different reduction order, marginally different logits.

Almost always this changes nothing, because the argmax is not close. Occasionally two tokens are nearly tied, the tiny difference flips the ordering, a different token is emitted, and because generation is autoregressive that one divergence cascades into a completely different response.

Additional sources on top of that: providers route between hardware generations and inference-stack versions without telling you, MoE routing can be batch-dependent, and a "model version" behind a stable API name can change under you.

**The engineering consequences are the whole point:**

1. **Never write an equality assertion against model output in a test.** It will pass locally and fail in CI for reasons unrelated to your change.
2. **Evals are statistical.** Run N samples, report a rate with a confidence interval, gate on distributions rather than on individual outputs. Book 04 builds this properly.
3. **Anything that must be exactly reproducible must be computed outside the model.** If a downstream system needs a stable identifier, generate it in code.
4. **Cache aggressively.** A cache is the only genuine determinism available: same input, same stored output, guaranteed.
5. **Log the model version and all sampling parameters in every trace.** When behaviour changes next Tuesday, this is what tells you whether it was you.

Some providers offer a `seed` parameter and "best effort" reproducibility with a system fingerprint. Treat it as a debugging aid, not a guarantee.

## Structured output changes the sampling story

Constrained decoding (next-but-two chapter) works by **masking logits**: at each step, tokens that would violate the grammar are set to negative infinity before softmax. Invalid output becomes impossible rather than unlikely.

Worth noticing what this implies. Constraint interacts with temperature — if the model wanted to emit prose and you have masked everything except `{`, you are forcing a path the model assigned low probability, and quality can drop. This is the real reason "just constrain everything" is not free: over-constraining a model that fundamentally misunderstood the task produces well-formed garbage, which is harder to detect than malformed output.

## Reasoning models and the sampling budget

Reasoning models generate an extended internal chain before their visible answer, trained by reinforcement learning against verifiable outcomes. From an engineering seat, three practical facts:

- **You pay for the thinking tokens** even though users may not see them. A "short" answer can cost thousands of output tokens.
- **The effort level is usually a parameter**, and it is a real cost/accuracy dial worth putting in your eval matrix rather than picking by feel.
- **Sampling parameters often should not be touched** on these models; providers frequently recommend defaults because the RL training assumed them.

They are the right tool for genuinely hard, low-volume, latency-tolerant problems: complex code changes, multi-constraint planning, tricky analysis. They are the wrong tool for classification at 10,000 requests a minute.

## Sampling as an eval lever

One technique worth having in your pocket: **self-consistency**. Sample the same question k times at moderate temperature and take the majority answer. On tasks with a discrete correct answer this measurably improves accuracy at k times the cost.

It also gives you a free uncertainty signal. If five samples agree, confidence is high; if they scatter, the model does not know, and *that* is a routing signal — escalate to a bigger model, or to a human. Building a confidence signal out of sample agreement is a genuinely good answer to "how would you know when your system is unsure", which is a question the Envelon and Scenr dossiers both suggest will come up.

*Connect the dot:* the statistical nature of everything in this chapter is the reason Book 04, Chapter 9 spends time on sample sizes and significance. If output were deterministic, evals would be unit tests.

Next: embeddings, and the vector space that all of retrieval runs on.
