# What This Shelf Is

**Fast overview:** This shelf exists because of a specific, uncomfortable gap. The JobOps pipeline has been sending applications into AI-engineering roles all summer, and the applications are honest — the dossiers name the gaps out loud, and the outreach says "I have not done that" where it is true. But honest is not the same as prepared. If any of those applications converts into a technical conversation, the conversation will go past what the resume claims, and the resume claims a RAG and prompt-chaining pipeline built with LangChain that broke at scale and was removed. That is a true sentence and a thin one. This shelf is the work of making it thick.

## The situation, stated plainly

The evidence in `profile/facts.yaml` for AI work is three projects:

- **REACTOR / ReacDEFI** — a conversational pipeline (RAG, prompt chaining, a vector store, LangChain, Gemini) that turned natural language into deployed on-chain automations handling real money. It worked, then failed under real concurrent load, and the feature was removed rather than shipped flaky.
- **Hashtro** — Gemini in a three-service architecture, with the AI reading a chart and producing trade parameters.
- **rc-agents** — an agent paying $0.30 USDC over x402 for a service, with no human in the loop. Agent-to-contract plumbing rather than model work.

Plus the adjacent-but-real work: JobOps itself is an evaluated agent system with a human gate; `learn-ops`, `x-ops` and `hack-ops` are all agent-shaped pipelines with scorers and guards; the `keywords.test.mjs` incident is a genuine story about a scoring bug that survived undetected for months across 178 leads until a test that asserted a known-bad pair *did not* match finally caught it.

That is a real foundation. It is not the same as depth. Three projects' worth of LangChain usage teaches you the shape of a chain; it does not teach you why your retrieval recall is 61%, what a reranker costs you in p95 latency, how to build a golden set that survives a model version bump, or what to do when an agent that can move money picks the wrong tool. Interviewers at the companies in the pipeline ask exactly those questions, because those questions are their day job.

## What the shelf is not

It is not a LangChain tutorial. Framework APIs move faster than any book, and no interviewer at an early-stage company has ever been impressed by someone reciting the current signature of `create_react_agent`. Where framework code appears here it appears as an illustration of a concept that would still be true if the framework vanished tomorrow — which most of them eventually will.

It is also not a machine-learning course. Nothing here trains a transformer from scratch or derives attention. The seat being applied for is *AI engineer*, not *research scientist*, and the dossiers are unanimous about the difference: Ramain's own bar reads "hands-on agentic systems experience **or** recent research", EON's third role wants publications and causal inference and the dossier says flatly "that is not Harsh". The job is building reliable systems around models somebody else trained. This shelf teaches that job, and covers the model internals only to the depth where not knowing them would make you build the wrong system.

## How it is organised

Eight books, ordered by how often an interviewer will reach for the topic, not by how the field is usually taught:

| # | Book | Why it is where it is |
|---|---|---|
| 00 | **The Gap Map** (this one) | The demand count, the honest answers, the study order |
| 01 | **LLM Foundations for Engineers** | Everything else assumes tokens, context, sampling and embeddings |
| 02 | **RAG in Production** | Named in more applications than any other single technique |
| 03 | **Agents, Tools and Orchestration** | The thing most of these companies are actually building |
| 04 | **Evals and Harnesses** | The most-repeated *requirement* in the whole corpus, and the widest gap |
| 05 | **Guardrails and Agent Safety** | The second half of every eval sentence in every JD |
| 06 | **LLMOps: Serving, Cost, Observability** | Where "it works on my laptop" turns into a product |
| 07 | **Python, FastAPI and ML Fundamentals** | The named language gap, plus fine-tuning and the metrics vocabulary |

Read 00 now, 01 next, then 04 out of order if a conversation is imminent — evals is the highest-leverage chapter set on this shelf and the one most likely to come up in the first fifteen minutes.

## The rule this shelf is written under

Every claim you make in an interview has to be traceable to something you actually did, exactly the way `facts.yaml` governs every line the pipeline generates. Reading a chapter about reranking does not let you say "I've tuned rerankers". It lets you say "I haven't tuned one in production; here's what I'd measure first and why", which is a *better* answer than a vague yes and a far better answer than a confident lie that unravels on the follow-up question.

So the shelf has a second job beyond teaching. Every book ends with a chapter called **"What you can now honestly say"**, which draws the line between the knowledge you now have and the experience you still do not. Learn the material; move the line; never cross it early.

Next: the demand count. Eight topics, ranked by how many of the forty-plus applications asked for each one.
