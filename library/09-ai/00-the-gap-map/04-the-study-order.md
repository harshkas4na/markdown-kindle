# The Study Order

**Fast overview:** A shelf of eight books is a way to feel productive for six weeks and be no more hireable at the end. This chapter is the plan that prevents that: what to read in what order, what to *build* alongside each book (because none of this converts into an interview answer until it has been built once), and the one hard rule about how much of it can be claimed.

## The principle: read one, build one

Every book on this shelf has a small project attached. Not a portfolio piece, not something to launch. A **two-to-six-hour artifact whose only purpose is to turn a chapter into a sentence with a number in it.**

The difference this makes in an interview is total. "I understand reranking" is worth nothing. "I put a cross-encoder reranker in front of a 400-chunk corpus and recall@5 went from 0.61 to 0.83 and p95 went up 240ms, so on that corpus it was worth it" is worth the whole conversation, and it takes an afternoon to be able to say.

These artifacts should live in one repo. Call it `ai-lab`. It is a lab notebook, not a product, and the README should say so.

## The order

### Week 1 — Book 01, LLM Foundations

Read the whole book. It is the vocabulary tax for everything else, and most of it will be half-known already, which makes it fast.

**Build:** a tokeniser explorer, in one afternoon. Take a few of his own documents (a dossier, a resume, a Solidity file), tokenise them, and produce the actual numbers: tokens per document, cost at three model price points, how many fit in a context window, how the count changes for code versus prose versus JSON. Then a second script that calls one model with temperature 0 twenty times on the same prompt and diffs the outputs, so determinism stops being a theory.

**The sentence you earn:** how to reason about context and cost from first principles rather than by guessing.

### Weeks 2–3 — Book 02, RAG in Production

The longest book and the highest-demand topic, 21 of 44 companies. Do not rush it.

**Build:** the retrieval bench. One corpus, ideally something he knows well enough to judge answers on (the Reactive Network docs, or his own thirteen Medium articles). Then, in order:

1. Naive fixed-size chunking, one embedding model, cosine top-k. Get it working end to end.
2. **Write 40 question/answer pairs by hand before optimising anything.** This is the golden set and it is the point of the whole exercise.
3. Measure recall@k and MRR on the naive version. Write the number down.
4. Change one thing at a time: chunk size, chunk overlap, semantic chunking, a different embedding model, hybrid BM25 plus vector, a reranker. Record the number and the latency after each.

The deliverable is a table with about six rows in it. That table is the single most valuable artifact this shelf can produce, because it is simultaneously a RAG answer, an eval answer and a "how do you make decisions" answer.

### Week 4 — Book 04, Evals and Harnesses

Out of numeric order, deliberately. By now there is a golden set from Week 3 and it will make every chapter concrete.

**Build:** promote the Week 3 bench into a real harness. A dataset file, a runner, per-slice reporting, an LLM-as-judge scorer for the answers (with a human-labelled sample to measure the judge itself, which is the step everyone skips), and a CI job that fails the build when a metric regresses past a threshold. Then run it against a prompt change and watch it catch something.

**The sentence you earn:** the answer to script 1 in the previous chapter, upgraded from "I would" to "I did".

### Week 5 — Book 03, Agents and Orchestration, plus Book 05, Guardrails

Read together. They are the same topic seen from two sides.

**Build:** one agent, built twice. First as a hand-rolled loop in about eighty lines — a while loop, a tool schema, a switch on the tool name, a step cap. Then the same agent in LangGraph. Building it by hand first is not a detour; it is what makes you able to answer "what does LangGraph actually give you" with something other than marketing copy.

Give it three tools where one is destructive, then bound the destructive one properly: a typed schema, a policy check outside the model, an approval interrupt, an audit line per call. Then try to talk the agent into misusing it, and write down what worked.

**The sentence you earn:** the difference between a guardrail in the prompt and a guardrail in the architecture, demonstrated rather than asserted.

### Week 6 — Book 06, LLMOps, and Book 07, Python and ML Fundamentals

**Build (LLMOps):** wire tracing through the Week 5 agent so every run has spans, token counts and cost. Then build a semantic cache in front of it and measure hit rate against exact-match caching on a realistic query distribution. That last measurement is EON's entire product thesis, and having a number for it makes that application a different conversation.

**Build (Python):** port the Week 3 retrieval bench from whatever it was written in to Python and FastAPI, with pydantic models on every boundary, async throughout and pytest around the scorer. The point is not the service. The point is that the next time a JD says "build reliable systems in Python", the honest answer includes something that is not four years old.

## How to spend a session

Ninety minutes, and it splits three ways:

- **30 minutes reading**, one or two chapters, in the reader with highlights on.
- **45 minutes building**, on that week's artifact.
- **15 minutes writing**, in `ai-lab/notes/`, answering one question in your own words with no source open. This last block is the one that actually creates recall, and it is the one that gets skipped. `learn-ops` already encodes the reason: revision at 3/14/45/120 days beats rereading, and you cannot revise what you never articulated.

## The claiming rule

This is the hard rule and it is worth putting in bold.

**Reading moves what you can discuss. Building moves what you can claim. Shipping to users moves what goes on the resume.**

Three tiers, three different verbs, and they never blur:

| Tier | Earned by | Legitimate phrasing |
|---|---|---|
| Discuss | Reading a chapter | "My understanding is…", "I'd want to measure…" |
| Claim | Building the artifact | "I built a bench that measured…", with the number |
| Resume | Shipping it where it mattered | A bullet in `resume.md` |

Nothing from this shelf goes into `profile/facts.yaml` on the strength of having been read. The lab repo is public and linkable, so a built artifact can be *shown*, which is stronger than a resume line anyway. And per the repo's own rules, if something here does become a claim, it goes into `facts.yaml` first and the pipeline picks it up from there.

## Calibrating the plan

Six weeks assumes real sessions most days. If the pipeline produces an interview in week two, the correct response is not to abandon the plan; it is to read Book 00 Chapter 3 again, read Book 04's first three chapters, and go in honest. The scripts are built for exactly that situation.

*Connect the dot:* every artifact above is also a `learn-ops` entry and a lifelog `ship` event when it works. The systems for keeping this current already exist; this shelf just supplies the material.

Next: the question bank. Roughly sixty questions the rest of the shelf answers, so that reading has something to aim at.
