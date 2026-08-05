# What the Applications Actually Asked For

**Fast overview:** Guessing what to study is how people waste months. The JobOps repo removes the guessing, because every application it produced carries a `dossier.md` that quotes the posting's own requirement language. Forty-four of those dossiers exist. This chapter counts what they ask for, which turns a vague sense of "I should learn more AI stuff" into a ranked list with numbers attached — and the ranking has one genuine surprise in it.

## The count

Every number below is the count of **companies whose dossier or JD names the topic**, out of 44 dossiers in `applications/` as of 2026-08-03.

| Rank | Topic | Companies | Where it lands on this shelf |
|---|---|---|---|
| 1 | RAG / retrieval | **21** | Book 02 |
| 2 | Agentic systems / AI agents | **20** | Book 03 |
| 3 | LLM work generally | 17 | Book 01 |
| 4 | Python / FastAPI | 16 | Book 07 |
| 5 | Evals, harnesses, golden sets | **13** | Book 04 |
| 6 | LangChain / LangGraph / LlamaIndex | 8 | Book 03 |
| 7 | Guardrails | 6 | Book 05 |
| 8 | Vector DBs / embeddings / pgvector | 5 | Book 02 |
| 9 | Observability / tracing / Langfuse | 5 | Book 06 |
| 10 | Latency budgets | 4 | Book 06 |
| 11 | Inference / vLLM / serving | 3 | Book 06 |
| 12 | Multi-agent orchestration | 3 | Book 03 |
| 13 | MCP (Model Context Protocol) | 3 | Book 03 |
| 14 | NLP on long documents / knowledge graphs | 3 | Book 07 |
| 15 | Tool calling / function calling | 2 | Book 03 |
| 16 | Voice / speech / real-time audio | 2 | Book 07 |
| 17 | Fine-tuning | 1 | Book 07 |

Half of the corpus wants RAG. Nearly half wants agents. Both of those are unsurprising and both are already on the resume in some form.

## The surprise: evals are the real bar

The raw count puts evals fifth. Read the dossiers and it is first, because of *how* the requirement is phrased. RAG shows up as a technology the company uses. Evals show up as **the thing the seat is being opened to fix**:

- **Certa** — the JD itself calls out "golden sets, prompt unit tests, offline checks, online A/Bs" as the evaluation bar. The dossier's own read: "Most 'AI Engineer' postings are 80% prompt engineering. This one explicitly wants golden-set evals, offline/online testing, and production RAG levers (chunking, re-ranking, embedding choice), which is the actual hard part."
- **Envelon AI** — "eval harnesses and guardrails that make an agent acting autonomously on live speech something we can actually trust." The dossier notes the CEO's previous company was a voice-AI *testing and evaluation* company. He is hiring for the thing he did before.
- **Scenr** — the product *is* an eval agent. The dossier's headline observation is that their own hardest unsolved problem is that a graded scenario library decays: "a prompt tweak that shifts Debugging by 0.4 across the board is invisible."
- **Ramain** — names "evals or harnesses" as owned surface in the posting.
- **Aurjobs** — sells "zero bias" screening on the pricing page with, as far as the dossier could tell, nothing measuring it.
- **EON** — "evaluation harnesses, datasets" in the JD, for a semantic-caching inference layer where the whole product question is how much staleness a cache hit is allowed to introduce.
- **Pango, airCFO, Certa, Patenova** — all four have a dossier-drafted "first 90 days" plan whose step one is *put an eval harness on the thing before touching the model*.

That pattern is the single most important fact in this chapter. The pipeline's own research has, independently, arrived at the same opening move for seven different companies: **measure it first**. If that is the move the applications promise, it is the move the interview will probe, and it is the thing to be genuinely good at.

## The second pattern: guardrails always travel with evals

Six dossiers name guardrails, and in five of them the phrase is joined to evals in the same sentence ("eval harnesses and guardrails", "governed by design", "bumpers to keep it on the rails"). This is not two topics. It is one topic with two halves: **evals tell you how often the system is wrong, guardrails bound what happens when it is.** Railway's own marketing line for it is "your AI wants to nuke your database". Kontigo's is an LLM that can move USDC inside a WhatsApp chat.

Book 04 and Book 05 should be read back to back for that reason.

## The third pattern: Python is a language gap, not a topic gap

Sixteen dossiers name Python or FastAPI. The EON dossier is blunt about the position this puts him in: "JD says 'build reliable systems in Python' for all three roles. Harsh has one production Python service." The Ramain dossier says the same thing differently: "No Python-first ML production experience; his agent work is TypeScript/Node orchestration around hosted models."

This is a different kind of gap from the others. It is not that the concepts are unknown — it is that the concepts are known in the wrong language. The whole AI ecosystem's centre of gravity is Python, every library in this shelf's examples is Python-first, and an interviewer who asks him to sketch a retrieval service will expect Python on the whiteboard. Book 07 exists for this, and it is the cheapest gap on the list to close because the ideas transfer; only the syntax and idioms do not.

## What is *not* worth studying yet

Equally useful. The count says these are near-zero demand in this corpus, so they are not where the next month goes:

- **Fine-tuning** — one company (Aurjobs, which pairs it with distributed inference). Worth one chapter so the vocabulary is there and the "when would you fine-tune instead of RAG" question has a real answer. Not worth a project.
- **Voice / real-time audio** — two companies. Envelon is one of them and it is a genuinely strong lead, so one chapter, aimed at latency budgets rather than at DSP.
- **Training or research ML** — zero. EON's research seat and Ramain's research half are explicitly out of scope per their own dossiers. Reading a paper a week is a fine habit; it is not preparation for these interviews.
- **Prompt engineering as a discipline unto itself** — the phrase appears, but never as the seat's difficulty. Certa's dossier says it outright: the hard part is not prompt-writing. Prompting gets one chapter in Book 01, framed as an engineering practice (versioning, testing, diffing) rather than a bag of tricks.

## The one-line version

Half the corpus wants **retrieval**, half wants **agents**, and the ones that make the seat sound hard want **someone who can prove the thing works and bound it when it doesn't**. Everything else is a rounding error you learn on the job.

*Connect the dot:* this ranking is exactly the order of Books 01 through 07, with one deliberate exception — evals is Book 04 rather than Book 02 only because it is impossible to write about evaluating retrieval before explaining retrieval. If a first-round call is on the calendar this week, read 04 first anyway.

Next: the other side of the ledger. What is actually in the evidence file, stated at the level of detail an interviewer will push it to.
