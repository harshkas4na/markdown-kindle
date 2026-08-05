# What You Actually Have

**Fast overview:** Before adding knowledge it is worth auditing the knowledge already there, because a surprising amount of it is mislabelled. Several things on this list do not look like AI experience and function as AI experience in an interview; a couple of things that look like AI experience are thinner than they read. This chapter takes each piece of real evidence, says what it genuinely demonstrates, and says where it stops.

## REACTOR / ReacDEFI — the headline, and its exact boundary

**What it was:** a conversational pipeline (LangChain, Gemini, a vector store, prompt chaining, retrieval) that took natural language and produced deployed on-chain automations — stop-loss, take-profit, Aave liquidation protection — on Base mainnet, handling real user funds. $9,000 grant, four press features.

**What happened:** it worked, then broke at scale under real concurrent use, and the feature was **removed entirely** rather than shipped flaky on top of money.

**What this genuinely demonstrates:**

1. End-to-end ownership of an LLM feature in production with real consequences attached. Most candidates' LLM experience is a chatbot over documents where a wrong answer costs nothing. A wrong answer here deployed a contract.
2. **Judgment under a reliability failure.** This is the rarest thing on the list and the most valuable. The story is not "I built a RAG pipeline". It is "I built one, it failed in a way I could not make safe, and I removed a feature I had a grant for." Interviewers at companies whose product touches money or operations — Kontigo, Veriqus, airCFO, Pango — will recognise that instinct immediately.
3. Natural-language-in, real-world-action-out. Structurally the same shape as every agentic product in the corpus.

**Where it stops, and this matters:** the failure was diagnosed as a scaling and concurrency failure and answered by removal. It was not answered by *measurement*. There was no golden set, no regression suite over prompt changes, no retrieval recall number, no per-stage latency breakdown. The honest sentence is that the pipeline broke and the decision was correct; the follow-up question — "what did the numbers say?" — currently has no answer. **Books 02, 04 and 06 exist to make sure the next version of that story does.**

One more precision, because `facts.yaml` carries an explicit correction about it: the feature was *removed*, not *hardened*. Never tell it the other way. The hardened version is a better-sounding story and a false one, and the difference between the two is the difference between judgment and fabrication.

## Hashtro — the systems half

Three services (Next.js, a FastAPI ephemeris service, a Solana trading service), Gemini in the loop, per-IP rate limiting, 24-hour TTL caching, Supabase RLS on every table, Privy auth. 160 users in 48 hours.

**Demonstrates:** an LLM as one component inside a real multi-service backend, with the boring production furniture actually present — rate limits, caching, row-level security. Also the only production Python on the list, which matters given sixteen dossiers ask for it.

**Where it stops:** the AI part is a single model call with a structured output. There is no retrieval, no agent loop, no eval. The TTL cache is a *keyed* cache, not a semantic one, which is worth knowing precisely because EON's entire product is the semantic version of that idea (Book 06, Chapter on caching).

## rc-agents — the part nobody else has

An AI agent pays $0.30 USDC via x402 to buy 24 hours of Aave liquidation protection, entirely agent-to-contract with no human in the loop.

**Demonstrates:** one of the earliest working agent-to-service micropayment flows. In agent-infra interviews this is a genuine differentiator — it is structured tool use where the tool costs money and settles on a chain, which is the sharpest possible version of "the agent took a real action". The Orbit dossier reads it correctly: "evidence of building agent-to-service infrastructure, not just calling an LLM API."

**Where it stops:** it is one flow, not an agent architecture. There is no planner, no multi-step trajectory, no recovery from a failed tool call.

## The four ops pipelines — the underrated evidence

JobOps, `learn-ops`, `x-ops`, `hack-ops`. None of them reads as "AI experience" on a resume, and all four are agent systems:

- **JobOps** is an evaluated agent system with a human gate — scouts that score leads A–F, skills that generate under hard constraints (a facts file that outputs must be traceable to, a banned-word list), and a rule that nothing is ever sent automatically. The Scenr dossier's sharpest line is that this makes it "an *evaluated* agent system with a human gate, which is Scenr's exact shape."
- **`x-ops`** contains a measured result worth memorising: a regex-based content scorer was demoted from a **gate** to a **ranking signal** after a run where 12 posts were read, 0 passed the keyword filter, and the best post of the day scored zero because it contained no keyword. That is a real, self-collected observation about the failure mode of brittle filters in front of a model. It is also a perfect answer to "tell me about a time your heuristic was wrong".
- **`learn-ops`** picks reading material from the lifelog and schedules revision at 3/14/45/120 days, chosen as a proportion of the retention horizon per Cepeda 2008 rather than the folk 7/21 spacing. Evidence of reading a paper and letting it change a parameter.
- **`hack-ops`** is an expected-value model over five axes whose stated job is to say no.

**Demonstrates:** system design around models, human-in-the-loop architecture, scoring and gating, and — critically — a *habit of measuring the pipeline against itself*. That habit is what every eval-shaped JD is screening for.

**Where it stops:** none of these has an LLM-as-judge, a golden set with labelled expected outputs, or a regression gate that blocks a change. They score, they do not yet evaluate. Book 04 is the bridge.

## The keywords bug — the best story on the shelf

The scouts matched profile keywords with a bare `includes()` from the start. So `defi` matched *undefined*, `go` matched *going*, and `rag` matched *sto·rag·e*. The bug survived across 178 leads and was found only when a test was written that asserted a known-bad pair **does not** match. The lesson recorded in `learnings.md` is precise: a passing test over positive examples proved nothing, because every positive case still matched. Only the negative assertion had any power.

This is a genuinely excellent interview answer to "tell me about a bug that survived", and it doubles as an eval lesson: **a test suite made only of things that should pass measures nothing.** Book 04's chapter on building a golden set is largely an elaboration of that sentence.

Small irony worth keeping: the bug was a substring match scoring `storage` as retrieval-augmented generation. It appeared in three separate repos before it was fixed properly.

## The adjacent skills that transfer more than they look like they do

- **Smart-contract engineering** — writing code where a wrong branch loses money, with no ability to hotfix after deploy, is the closest thing in ordinary software to the discipline agent guardrails demand. The Ramain outreach draft makes exactly this argument: "the blast radius of a wrong agent decision is bounded by design rather than by a guardrail prompt."
- **`terraform-in-go` / `git-in-go`** — DAG resolution and content-addressed storage, hand-written. A DAG of dependent steps is exactly what an agent graph is, and content addressing is exactly how a prompt/version cache key works.
- **`lifelog`** — an append-only event log with a cursor per consumer, idempotent by content key. This is the correct architecture for agent trace storage and for eval-run history, and he has already built it once for a different reason.

## The honest summary

He has **built** LLM features, **shipped** them where they mattered, and **removed** one when it was not safe. He has not **measured** any of them. He has built agent-shaped pipelines with human gates and scoring, but not eval harnesses with labelled data and regression gates. He works in TypeScript in an ecosystem that works in Python.

Three sentences, three gaps, and they map exactly onto Books 04, 02 and 07.

*Connect the dot:* Chapter 3 turns each of those gaps into a sentence that can be said out loud without either overclaiming or apologising.

Next: the honest-gap scripts.
