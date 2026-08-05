# What You Can Now Honestly Say

**Fast overview:** The closing chapter of every book on this shelf does the same job: it draws the line between what the reading earned and what it did not, so the claiming rule from Book 00 stays enforceable. This one also gives the two lab artifacts that convert the reading into something showable, and the six questions to answer out loud before moving on.

## What reading this book earned

You can now discuss, with mechanism rather than vocabulary:

- **Why tokenisation determines cost, and why code and JSON cost more than prose.** Including the specific reason: BPE merges are frequency-driven, so text unlike the training corpus fragments.
- **Why the model cannot count letters**, and the general rule that character-level tasks belong in code.
- **The prefill/decode split**, and why it explains batching, prompt caching, streaming, and why output tokens cost more than input tokens.
- **What the KV cache is** and why it, not the weights, is usually the memory wall in serving.
- **Why long context is not free**, in three separate currencies: money, latency, and the measurable lost-in-the-middle accuracy effect.
- **Why temperature 0 is not determinism**, with the floating-point-non-associativity reason, and why that fact forces evals to be statistical.
- **What an embedding is**, why two models' embeddings are incomparable, why query and document are asymmetric, and why similar is not the same as relevant.
- **Four mechanisms for structured output**, what constrained decoding does at the sampler, and why field order in a schema is a quality lever.
- **Which prompting techniques survive scrutiny and which are folklore**, and what prompt infrastructure looks like when it is done properly.
- **The cost and latency arithmetic**, with the five levers ranked, and the argument that no eval means no cost control.
- **The failure taxonomy**, including the four distinct bugs that all get called hallucination.

That is a genuinely solid foundation, and it is worth being precise about its status: **it is discussion-tier**. It makes you able to reason correctly in a conversation. It does not entitle you to a resume line.

## What it did not earn

Be strict here, because this is the calibration the interview is testing.

- You have not **served** a model. Nothing here means you have deployed vLLM, sized a GPU, or debugged an OOM under load. Book 06 covers the theory; the practice is still absent.
- You have not **measured** lost-in-the-middle, latency, or cost on real traffic. You know the effects exist. You do not have a number from your own system.
- You have not **built** a structured-output pipeline under production error rates, so you do not know what your schema violation rate is or what actually causes it.
- You have not **fine-tuned or trained** anything, and this book did not touch that.

The phrasing that stays honest: "my understanding is", "what I'd expect", "what I'd measure first". Not "I've found that".

## The two artifacts to build

Both are short and both convert a chapter into a claim.

**Artifact 1 — `token-lab`.** The counter from Chapter 1, pointed at your own documents. Output a table: chars, tokens, chars/token, cost at three tiers. Include the same content as prose and as JSON so the multiple is visible. **Twenty minutes**, and it makes the cost conversation concrete.

**Artifact 2 — `sampling-lab`.** Two scripts. The first calls one model twenty times at temperature 0 with an identical prompt and reports how many distinct outputs came back — this either confirms non-determinism on your provider or gives you a more interesting answer. The second implements self-consistency: sample a hard question five times at T=0.7, take the majority, and compare accuracy and agreement rate against a single T=0 sample on twenty questions.

**Two hours**, and it earns a sentence with a number in it: *"On my own twenty-question set, five-sample majority voting moved accuracy from X to Y at 5x the cost, and the disagreement rate was a usable confidence signal."* That sentence is worth more in an interview than this entire book.

Third artifact, optional and high-value if a RAG-heavy company is in play: the **needle-at-depth test** from Chapter 3. Take a real long document, plant a fact at five depths, ask for it twenty times at each depth, plot accuracy against depth. Half a day, and it is simultaneously a long-context answer, an eval answer, and a demonstration that you check claims rather than repeat them.

## Six questions to answer out loud

No notes. If any answer takes more than ninety seconds or contains no mechanism, reread that chapter.

1. Why does the same JSON payload cost more tokens than the same information as a sentence?
2. What is the difference between prefill and decode, and which one does prompt caching help?
3. Why can't I compare an embedding from model A with one from model B, and what would go wrong if I tried?
4. Temperature is 0 and I get two different answers. Explain.
5. I have 3,000 tokens of retrieved context and one instruction. Where does the instruction go, and why?
6. A user reports the model hallucinated. What are the first three things you check, in order?

## Where to go next

Book 02, RAG in Production, is the natural continuation and the highest-demand topic in the corpus — 21 of 44 companies. It builds directly on Chapters 3 and 5 of this book.

If an interview is imminent, jump to Book 04 instead. Chapters 1 through 3 of that book plus the honest-gap scripts in Book 00 are the highest-yield ninety minutes available on this shelf.

*Connect the dot:* everything in Book 02 is an application of two facts established here — that attention does not treat a long context uniformly, and that embedding similarity is not relevance. Retrieval engineering is largely the business of working around those two facts.

Next: RAG in Production.
