# Why Evals Are the Bar

**Fast overview:** The rest of this book is technique. This chapter is the argument, built from the application corpus rather than from opinion, because knowing *why* a company wants this changes how you talk about it. Thirteen dossiers name evals; in seven of them the seat exists to build them; and the pipeline's own research independently arrived at "measure it first" as the opening move for seven different companies without being told to.

## The evidence

From the dossiers, in the companies' own language:

**Certa.** The JD names "golden sets, prompt unit tests, offline checks, online A/Bs" as the evaluation bar. The dossier's read is unusually direct: *"Most 'AI Engineer' postings are 80% prompt engineering. This one explicitly wants golden-set evals, offline/online testing, and production RAG levers (chunking, re-ranking, embedding choice), which is the actual hard part of shipping LLM features that enterprises trust."*

**Envelon AI.** Required: *"eval harnesses and guardrails that make an agent acting autonomously on live speech something we can actually trust."* And the detail that makes it decisive — the CEO's previous company was voice-AI agent **testing and evaluation**. He is hiring for the discipline he already practised.

**Scenr.** The product *is* an eval agent. The dossier identifies their hardest unsolved problem as decay: a graded scenario library *"is the only source of truth for ninety days, by which time the model version, the prompt, and the scenario library have all moved. A prompt tweak that shifts Debugging by 0.4 across the board is invisible."*

**Ramain.** Names *"evals or harnesses"* as owned surface in the posting.

**Aurjobs.** Sells "unbiased" candidate screening on the pricing page. The dossier's proposed first move: *"Put an eval harness on the screening ranker before touching the model... A labelled set and a regression run on every prompt change turns that into a number they can show a prospect."*

**EON.** JD asks for *"evaluation harnesses, datasets"*, for a semantic-caching inference layer where the entire product question is how much staleness a cache hit may introduce. Their measurement problem is their business model.

**Pango, airCFO, Patenova.** All three have a dossier-drafted opening plan whose step one is instrumenting before changing.

## The pattern that matters

Seven independent companies, seven independently-written research passes, and the same recommended first move: **measure it before you touch it.**

That convergence is not a coincidence about the research process. It is what the problem looks like from the outside. These are companies with an LLM feature in production, a founder who suspects it is worse than it should be, and no number that says so. The seat is open because somebody has to build the instrument.

Which means the interview will probe it. Not as a checkbox — as the core competence.

## Why so few candidates can answer

Because evals are the least fun part of the job and the last thing people learn.

Building a RAG pipeline is satisfying: it works, it demos, it feels like progress. Writing 200 labelled examples by hand is tedious, produces nothing demoable, and its value only appears the third time it stops you shipping a regression. So most engineers with two years of LLM experience have shipped several pipelines and evaluated none of them.

**That is the arbitrage.** The demand is high, the supply is low, and the barrier is patience rather than talent. It is also, conveniently, the gap most cheaply closed by someone who already has the temperament — the repo already contains a `reachability.test.mjs` that backtests a geo filter against historical leads and *must stay at zero false negatives*, and a `keywords.test.mjs` written specifically to assert that a known-bad pair does not match. Those are evals. They are not called that, and they are exactly the instinct.

## The three business arguments, in the order they land

When a founder asks why they should let you spend week one on measurement rather than features:

**1. It is how you stop paying 20x for the model.** The correct model is the smallest that passes. Without a suite, nobody can answer whether the cheap model is adequate, so the expensive one stays. This is usually the single largest line in an AI product's cost structure, and it is unlockable in a week.

**2. It is how you survive a model change.** Providers deprecate and update. With a suite, migration is running a table. Without one, it is a two-week outage of confidence.

**3. It is how you go faster.** A team with no eval eventually stops touching the prompt, because every change is unfalsifiable. The suite is what makes iteration safe. **Evals are a velocity feature disguised as a quality feature**, and framing them that way is what gets them funded.

## What "an eval harness" actually means to these companies

Worth being precise, because the phrase is used loosely and the interviewer means something specific:

- A **dataset** of real inputs with known-correct outcomes, owned by whoever in the company is the authority on correctness.
- **Scorers** appropriate to the task, mostly deterministic, with judges where quality is subjective and the judge itself validated.
- A **runner** that executes it against a versioned configuration and saves the artifacts.
- **Per-slice reporting**, because the aggregate hides the regression.
- A **gate** in CI that blocks a merge on a drop.
- A **feedback loop** from production failures back into the dataset.

If you can name those six and say what each is for, you are already ahead of most candidates for these roles, and the rest of this book is how to build each one.

## The honest position to hold

Do not claim to have run this. The claim is:

> I have not owned an eval harness in production. What I have is the instinct it comes from: I shipped a scoring pipeline whose keyword matcher counted "storage" as a hit for "RAG" for 178 leads, and the reason it survived is that every test I had was a positive case that still passed. The fix was an assertion that a known-bad pair does not match. That is the same lesson as a golden set full of easy examples, and it is why the first thing I would build here is a set of cases the current system gets wrong.

That is honest, it is specific, and it demonstrates the exact idea the rest of the discipline is built on.

*Connect the dot:* the "name the gap in the first line, then spend the answer on the move" shape is from Book 00, Chapter 3. This is that shape applied to the highest-stakes question in the corpus.

Next: the golden set, which is where the work actually is.
