# What You Can Now Honestly Say

**Fast overview:** The line-drawing chapter for the topic that matters most. Thirteen dossiers name evals and in seven of them the seat exists to build them, which makes this the widest gap and the highest-leverage thing on the shelf. This chapter says what the reading earned, what it did not, and gives the single build that converts the whole book into a claim.

## What reading this book earned

You can now discuss, with mechanism:

- **Why a suite of cases that should pass measures nothing**, with a real story behind it, and why that governs the composition of a golden set.
- **How to build a golden set**: sources ranked, sizes justified, who labels and why it must be the domain owner, what an example contains, and the 40/25/15/10/10 composition.
- **The scorer hierarchy**, and why a judge should never do a job a regex can do.
- **LLM-as-judge properly**: pairwise over absolute, the four biases and their mitigations, rubric design with reasoning before verdict, and — the part almost nobody does — **validating the judge against human labels and reporting the agreement rate.**
- **The statistics**: the confidence interval on a pass rate, why 50 examples cannot adjudicate a four-point difference, paired comparison and McNemar, bootstrap intervals, and measuring your harness's own noise floor.
- **Per-slice reporting**, and the concrete example of a change that lifts the mean by three points while destroying refusals.
- **The harness**: config hashing, artifact storage, caching, tiered CI, and gates with both absolute floors and relative drops.
- **RAG evaluation**, including the diagnosis table that turns three metrics into a next action.
- **Agent evaluation**: outcome verified against the world rather than the transcript, trajectory assertions of required-and-forbidden tools, per-step tool selection accuracy, and the environment problem.
- **Online evaluation**: implicit signals over explicit feedback, the shadow/canary/ramp rollout, and the honest admission that many startup A/B tests are under-powered.
- **Drift**, including the anchor set as a calibration instrument for your own measurement.
- **A first-90-days plan** that is sequenced, political and executable.

## What it did not earn

Be strict, because this is the topic where overclaiming would be most damaging.

- You have not **built an eval harness in production**. Not one line of it against real traffic.
- You have not **run an LLM judge**, and so have never seen a judge/human agreement number of your own.
- You have not **caught a regression with a gate**, which is the moment the whole discipline justifies itself and the moment you can only describe secondhand.
- You have not **labelled a set with a domain expert**, which is where most of the real difficulty lives.
- You have not **run an A/B test** on an LLM feature.

What is genuinely yours, and it is not nothing:

- **The keywords bug and its fix.** A substring matcher scoring `storage` as a `rag` hit across 178 leads, surviving because every test was a positive case, caught only by an assertion that a known-bad pair does not match. That is the central idea of this book, learned the expensive way, in his own repo.
- **`reachability.test.mjs`.** A backtest asserting that a geo filter loses zero of twenty historical A/B leads, which must stay at zero. That is a regression gate with a zero-tolerance threshold on a safety-critical slice. It is not called an eval and it is one.
- **The `x-ops` demotion.** A regex scorer moved from gate to ranking signal after a measured run where 12 posts were read and 0 passed. That is a measurement changing an architecture, which is the entire point.

The honest sentence: **he has built scorers and assertions in his own systems, and learned the central lesson of eval design from a real bug. He has never owned an eval harness for an LLM feature in production.**

## The artifact: `eval-lab`

Two days on top of the retrieval bench from Book 02, and it converts most of this book.

**Day 1 — the harness.**
Take the 40-question set from `retrieval-bench` and promote it. Add slices, provenance, difficulty and dates. Add the should-fail category — ten questions with no answer in the corpus, expecting `NOT_FOUND`. Build the scorer stack: structural assertions, contains, citation validity, refusal detection. Build the runner with config hashing and artifact storage. Report per slice.

**Day 2 — the judge, and the number that matters.**
Build a faithfulness judge with the rubric design from Chapter 4. Then do the step nobody does: **label 50 of the examples yourself, blind, and compute agreement with the judge.** Read every disagreement and fix the rubric.

Then measure the noise floor: run the identical configuration twice and record the difference.

Then wire a gate in a GitHub Action and **deliberately push a bad prompt change** to watch it go red.

**What this earns, verbatim:**

> I built a harness over my own corpus: forty labelled examples, six slices, deterministic scorers first, and one faithfulness judge. The judge agrees with my own labels 84% of the time, so I quote its numbers with that caveat attached. My harness's noise floor from re-running the same config twice is about two points, so I do not believe anything smaller than that. The most useful thing it showed me was a prompt change that improved the aggregate by three points and dropped the refusal slice from 0.85 to 0.40, which is exactly the regression the average would have hidden.

That paragraph is the highest-value thing on this entire shelf. It contains a validated judge, a stated error bar, a noise floor, and a caught regression — four things that most candidates for these roles cannot claim, and all of it true after two days.

## Ten questions to answer out loud

1. Build me a golden set. How many, from where, labelled by whom?
2. Why is a test suite made only of passing cases close to worthless?
3. When is exact match right, and when does it actively mislead?
4. What are the biases of an LLM judge, and how do you know yours is any good?
5. Prompt B scored four points higher on fifty examples. Ship it?
6. Give me an example of a change that improves the average and is still a regression.
7. What does a regression gate gate on, and where does it live?
8. How do you evaluate an agent, where the answer can be right for the wrong reasons?
9. My eval set is six months old. What is wrong with it?
10. Walk me through your first ninety days here.

Questions 4, 6 and 10 are the ones most likely to decide a conversation at the companies in this corpus.

## Where to go next

**Book 05, Guardrails and Agent Safety.** It is the other half of every eval sentence in every JD, and Chapter 9's forbidden-tool assertions are already its first idea.

Then **Book 06** for the observability that makes online evaluation possible, and **Book 07** for the Python and the metrics vocabulary.

*Connect the dot:* the sentence this whole book turns on came from his own repo, not from a paper. `rag` matched `storage`, every test passed, and only the negative assertion caught it. That is worth remembering not as a story to tell but as a habit to keep: **when you build a check, ask what it could fail on. If the answer is nothing, you have built a decoration.**

Next: Guardrails and Agent Safety.
