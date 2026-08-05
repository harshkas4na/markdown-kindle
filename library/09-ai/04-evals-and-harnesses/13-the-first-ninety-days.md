# The First Ninety Days

**Fast overview:** Seven dossiers in the corpus contain a first-90-days plan whose step one is "put an eval harness on it before touching the model". Those plans were written to be *said* in an interview, and they need to be executable if said. This chapter turns them into a concrete week-by-week plan for the general case, plus the two-minute version to deliver out loud, plus the politics of proposing measurement to a team that wants features.

## The problem you are walking into

The situation at almost every company hiring for this is the same: an LLM feature in production, a founder who suspects it is worse than it should be, complaints that arrive as anecdotes, and nobody able to say whether last month's prompt change helped. Somebody makes a change, someone else says it feels better, and that is the entire quality process.

Your job in the first ninety days is to replace "feels better" with a number, and then to use the number.

## Week 1 — get a number, any number

**Do not build a platform. Get one honest measurement.**

- **Days 1-2: read.** The prompts, the pipeline, the traces if any exist, the last twenty support complaints. Then talk to whoever owns correctness — the support lead, the compliance person, the founder — and ask what "wrong" looks like to them. Their answer is your rubric.
- **Day 3: 20 examples.** Real inputs from real traffic or real tickets, with your best guess at correct outputs.
- **Day 4: take them to the domain owner** and let them correct you. The corrections are worth more than the examples.
- **Day 5: run the current system against all 20**, score with the crudest scorers that work, and **read every single failure**.

**Deliverable:** the first honest quality number the company has had, with its caveats stated. Something like "on 20 real cases the system is right 13 times, and 4 of the 7 failures are the same problem".

That artifact changes the conversation permanently. It is also the fastest way to understand a product you just joined.

## Weeks 2-3 — make it a harness

- Grow to 60-100 examples, including the should-fail and adversarial categories from Chapter 2.
- Label slices. Four to six, at least 20 examples each.
- Build the deterministic scorer stack. Schema, contains, citations, refusal detection.
- Build the runner with config hashing and artifact storage.
- Put it in CI on the prompt and pipeline paths, reporting only — **no gate yet.**
- Post the slice table as a PR comment.

**Reporting before gating is deliberate.** Let the team see the numbers on their own changes for two weeks before anything blocks them. A gate imposed on day one, on a metric nobody trusts, gets disabled by week three.

## Weeks 4-5 — the judge, and the first real finding

- Build one judge for the one dimension that matters most, usually faithfulness.
- **Validate it against 50 human-labelled examples.** Report the agreement number alongside every score from then on.
- Run the full configuration matrix: current versus obvious alternatives (a cheaper model, a different k, hybrid retrieval, a reranker).

**Deliverable:** the table. Quality, cost and latency for five or six configurations. This is where the harness starts paying for itself, and it usually contains at least one surprise — most often that a much cheaper model is adequate for a large share of traffic, or that a component everyone assumed was helping is not.

## Weeks 6-8 — turn on the gate, close the loop

- Enable the gate with conservative thresholds, absolute floors plus relative drops, zero tolerance on the safety-critical slice.
- Wire online evaluation: deterministic metrics on 100% of production traffic, judged sampling at 1-5%.
- Start the weekly loop: sample production failures, cluster, add to the set, fix the biggest cluster.
- Add the anchor set (Chapter 11) so future recalibrations are detectable.

## Weeks 9-12 — use it

Now the harness exists, spend it on the things it unlocks:

- **Route to a cheaper model** on the slices where the eval says it is adequate. This is usually the largest cost win available and it was unavailable before.
- **Ship the pipeline improvements** the configuration matrix identified, one at a time, each gated.
- **Run the first real A/B** on a proxy metric with enough base rate to conclude.
- **Do a model migration** deliberately, to prove the process works before you are forced into one.

**Deliverable at 90 days:** a measured system, a gate that has caught at least one real regression, a documented cost reduction, and a weekly loop that runs without you reminding anyone.

## The politics

Proposing measurement to a team that wants features is a real conversation, and it goes better with three moves:

**1. Frame it as speed, not rigour.** "Right now nobody can change the prompt without risk, so nobody does. This makes changing it safe." Founders buy velocity; they are lukewarm on process.

**2. Attach it to money in week one.** "Once we can measure it, we can find out whether the cheap model is good enough for the 70% of traffic that is routine." That is a concrete number with a dollar sign, available in week four, and it funds everything else.

**3. Deliver something in week one.** The 20-example number. Not a design doc, not a tool evaluation. A finding. Nobody argues with a finding.

The failure mode to avoid is spending three weeks choosing an eval platform. That is the version of this project that gets cancelled.

## The two-minute version

For the interview, compressed:

> Week one I would not build anything. I would find twenty real cases, get the person who actually owns correctness to tell me what right looks like on them, run the current system, and read every failure. That gives the company its first honest quality number and it tells me where the problem is.
>
> Weeks two and three I would turn that into a harness: sixty to a hundred examples with slices, deterministic scorers first, in CI, reporting on every pull request but not gating yet, because a gate on a metric nobody trusts gets switched off.
>
> Weeks four and five, one judge for faithfulness, validated against fifty human labels so I can state the agreement rate, and then the configuration matrix — quality, cost and latency across the obvious alternatives. That table is usually where you find out whether a cheaper model would do, which is the thing that pays for the whole project.
>
> After that, turn on the gate, wire the online metrics, and run the weekly loop where production failures become eval cases. The thing I would want to be true at ninety days is that somebody other than me has been stopped from shipping a regression by a gate they trust.

That answer is specific, sequenced, honest about the politics, and it ends on the right success criterion — adoption by other people, not existence of the artifact.

## Adapting it

The plan changes shape by company:

- **Agent-heavy** (Envelon, Scenr, Rem Labs, Pango): the environment problem is the long pole. Budget weeks 2-3 for a seeded test environment, and put forbidden-tool trajectory assertions in first because they are cheap and they are safety.
- **RAG-heavy** (Certa, airCFO, Patenova, Veriqus): split retrieval and generation from day one, and get the chunk-id labels done early because everything depends on them.
- **Ranking** (Aurjobs): the metrics are precision@k and nDCG, and the sensitive part is the fairness claim on the pricing page. Measure it before anyone else does.
- **Caching / inference** (EON): the eval is a staleness/hit-rate frontier, not a quality score. The question is how much staleness a cache hit may introduce, and the deliverable is a curve.

*Connect the dot:* Book 00, Chapter 3's honest-gap script for evals ends with a "the move" paragraph. This chapter is that paragraph expanded, which means that after reading it the script gets shorter and more confident without becoming less true.

Next: the closing chapter.
