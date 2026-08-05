# Failure Modes

**Fast overview:** "The model hallucinated" is the AI equivalent of "the server was slow" — true, useless, and a sign that nobody localised the fault. This chapter takes the recurring failures of LLM systems one at a time, gives each a mechanism rather than a vibe, and gives each a mitigation that is engineering rather than prompt-wishing. Being able to do this decomposition out loud is one of the clearest signals of someone who has run one of these systems in production.

## Hallucination is at least four different bugs

The word covers several distinct failures with different causes and different fixes. Insisting on the distinction is itself the skill.

**1. Knowledge gap.** The model was never trained on the fact, or it is post-cutoff. It produces a plausible answer because producing an answer is what preference training rewarded (Chapter 2). *Fix: retrieval.* This is what RAG is for.

**2. Retrieval failure disguised as hallucination.** The fact was in the corpus, retrieval did not surface it, and the model answered from parametric memory anyway. Looks identical from the outside and is a completely different bug. *Fix: measure retrieval separately* (Book 02, Chapter 11). This is why recall@k is instrumented independently of answer quality — otherwise you tune the generation prompt for weeks to fix a retriever problem.

**3. Grounding failure.** The right context was retrieved and the model ignored it, blended it with prior knowledge, or over-generalised from it. *Fix: instruction design and a faithfulness scorer.* Require citations, then check whether the cited chunk actually supports the claim.

**4. Instruction-following failure.** The model was asked for a specific format or scope and drifted. *Fix: constrained decoding, validation, escape hatches.*

**The mitigation that generalises across all four:** give the model a legal way to say it does not know, and make that path attractive. A required-fields schema with no `not_found` option is a hallucination generator, as covered in Chapter 6.

## Sycophancy

Push back on a correct answer and the model often reverses. This is a direct consequence of preference training: human raters preferred agreement.

Engineering consequences, all of which come up in real designs:

- **"Are you sure?" is not verification.** It is a request for agreement, and you will get one. Verification means an independent check: a second model with no view of the first answer, a code-executed test, a retrieval lookup.
- **In an LLM-as-judge, never show the judge who produced which answer**, and never show it the previous verdict. Book 04 covers judge bias properly, and this is the largest one.
- **In multi-turn agents, previous outputs anchor later ones.** An agent that made an error at step 2 will tend to defend it at step 7. Bounded steps and fresh-context re-planning both help.

## Prompt sensitivity and brittleness

Small, semantically meaningless changes — reordering few-shot examples, changing a delimiter, swapping "classify" for "categorise" — can move measured accuracy by several points. This is well documented and it is why single-example prompt comparison is worthless.

*Fix:* evaluate on a set, not an example; test with paraphrased inputs; and prefer prompt structures that have held up across multiple models rather than ones tuned to one model's quirks.

## Drift, which comes in three flavours

- **Model drift.** The provider updates the weights behind an unpinned name. *Fix: pin versions; run the suite before migrating.*
- **Data drift.** Your users' inputs change. A support bot trained on last quarter's issues meets this quarter's outage. *Fix: sample production traffic into the eval set continuously; monitor input distribution.*
- **Eval drift.** Your golden set silently stops representing the product. Scenr's dossier states the sharpest version of this: a graded scenario library is "the only source of truth for ninety days, by which time the model version, the prompt, and the scenario library have all moved." *Fix: date every eval example, review the set on a schedule, and treat it as an asset that requires maintenance.*

The third one is the one nobody plans for, and the one most likely to come up at a company whose product is evaluation.

## Cascading and compounding errors

In a chain, per-stage accuracy multiplies. Three stages at 95% is 86%; five is 77%. In an agent loop with fifteen tool calls, a 2% per-step error rate means roughly a 26% chance of at least one error in a run.

Consequences:

- **Measure per-stage, not just end to end.** End-to-end accuracy tells you something is wrong; per-stage tells you where.
- **Design for recovery, not just for correctness.** A tool call that fails should return a useful error the model can act on, not a stack trace or a silent empty result.
- **Cap the loop.** Step limits, wall-clock limits and cost limits. Every agent needs all three (Book 03).

## Degenerate loops

The agent calls the same tool with the same arguments repeatedly; the writer produces the same paragraph three times. Causes: the tool result is unhelpful so the model retries identically, the tool description is ambiguous, or repetition penalties are off in a context that invites repetition.

*Fixes:* detect repeated (tool, arguments) pairs in code and break, return an explicit "you already called this with these arguments and got this result" message, and cap the steps. Detect it in the harness too — repeated-call rate is a cheap and highly informative agent metric.

## Silent quality degradation

The worst class, because nothing errors. Symptoms: nobody complains loudly, retention drifts, support tickets creep up. Causes: a corpus that grew and diluted retrieval, a prompt edited without an eval, a model version change, an embedding model swapped in one service and not another.

This is *the* argument for LLM observability. A traditional service tells you it is broken with a 500. An LLM feature returns 200 OK with a confidently wrong answer. **The absence of errors is not evidence of health**, so you must instrument proxies: eval scores on sampled production traffic, escape-token rate, citation rate, user regeneration/edit rate, escalation-to-human rate. Book 06 builds this.

## Injection and adversarial input

Covered fully in Book 05; noted here so the taxonomy is complete. Direct injection is the user instructing the model to ignore its instructions. **Indirect injection** is the harder one: instructions hidden in retrieved content, a web page, an email, a document. The retrieval pipeline that grounds your model is also an untrusted input path, and this is the failure mode people most consistently underestimate.

## The debugging procedure

When an LLM system is wrong, work top to bottom and stop at the first failure:

1. **Reproduce with the exact inputs.** Trace-level, including the resolved prompt, the model version and the sampling parameters. If you cannot reconstruct the exact prompt from the trace, fix your tracing before debugging anything else.
2. **Was the right context present?** Check retrieval output before touching the model. This eliminates a large fraction of "hallucination" reports in one step.
3. **Was the prompt what you think it is?** Print the fully rendered prompt. Template bugs, empty loops and truncated context are extremely common and invisible from the code.
4. **Is it consistent?** Run it ten times. Failing 10/10 is a systematic problem; 2/10 is a sampling or borderline-case problem and needs a different fix.
5. **Does a stronger model get it right?** If yes, it is a capability problem and routing may fix it. If no, it is a task or context problem and a bigger model will not save you.
6. **Is this one case or a class?** Search the traces for similar inputs. Fixing a class is engineering; fixing a case by adding a line to the prompt is how prompts become 2,000 tokens of accumulated special cases.
7. **Add it to the eval set** before fixing it, so the fix is measurable and the regression is caught forever after.

Step 7 is the one that compounds. Every incident that ends with a new eval case makes the system permanently more robust; every incident that ends with a prompt tweak makes it more fragile.

*Connect the dot:* REACTOR's failure, per Book 00 Chapter 2, was diagnosed by reasoning rather than by this procedure, because none of the instrumentation existed. Steps 1, 4 and 5 would have turned "it breaks at scale" into a component and a number. That gap is the honest heart of the story and the reason this shelf leans as hard as it does on measurement.

Next: the last chapter of this book, on what the reading has actually earned.
