# Debugging an Agent Run

**Fast overview:** An agent failed. It ran fourteen steps, called nine tools, and produced a confident wrong answer. Where do you start? This chapter is a procedure — the order to look at things, the questions each step answers, and the instrumentation that has to exist before the incident for the procedure to be runnable at all. It is the agent version of Book 01's debugging chapter, and it is the skill that most reliably separates people who have run agents from people who have built them.

## The prerequisite

You cannot debug what you did not record. Before anything else, a run must produce:

- **A run id** threaded through every call, including sub-agents.
- **Per step:** the full message list sent, the model and version, sampling parameters, the response, tool calls with arguments, tool results (full, or a reference to the stored full version), token counts, cost, latency.
- **The resolved prompts**, not the templates. If you cannot see the exact text sent, you are guessing.
- **State snapshots**, if the agent maintains state.
- **Terminal condition**: finished, cap hit, error, guard rejection.

If this does not exist, stop debugging and build it. Everything below assumes it.

## The procedure

### 1. Read the trace forward, and find the first step that is wrong

Not the last one. The failure you noticed is usually several steps downstream of the cause. Read from step 1 and find the earliest point where the agent did something you would not have done.

This sounds obvious and it is the step people skip, because the wrong final answer is what is in front of them. Nine times in ten the interesting event is at step 3.

### 2. Classify the first wrong step

Six categories, and each points at a different fix:

| What went wrong | Category | Fix lives in |
|---|---|---|
| Called the wrong tool | Selection | Tool descriptions (Ch 3) |
| Right tool, wrong arguments | Argument generation | Parameter schema, descriptions, temperature |
| Right call, unhelpful result | Tool implementation | Return value design (Ch 3) |
| Right result, wrong conclusion | Reasoning | Prompt, model tier, planning pattern |
| Correct everything, then repeated it | Loop | Loop detection (Ch 4) |
| Ran out of steps mid-task | Bounds or efficiency | Caps, tool granularity |

Making this classification explicit is the whole trick. "The agent messed up" is not actionable; "it chose `search_docs` when it needed `get_account`, because both descriptions say they return account information" is a one-line fix.

### 3. Check the context at that step

Print the full message list as the model saw it. Look for:

- **Is the task still visible and near an end of the context?** Or is it buried in the middle at position 40 of 90 (Book 01, Chapter 3)?
- **How much of the context is tool output?** If a single result is 20,000 tokens, the problem is Chapter 6's, not the model's.
- **Are the tool schemas correct?** A schema drift between what you think you registered and what was sent is common and invisible.
- **Is there anything in there that should not be?** Retrieved content, a tool result, or a user message containing instructions is an injection vector (Book 05).

### 4. Determine whether it is systematic or stochastic

Re-run the same task ten times.

- **Fails 10/10** → systematic. Tool descriptions, prompt, schema, or a genuine capability gap. Tractable.
- **Fails 2/10** → stochastic. A borderline decision, ambiguous descriptions, or a distribution that occasionally strays. Harder, and usually fixed by removing the ambiguity rather than by re-prompting.
- **Fails 10/10 on this input, 0/10 on similar inputs** → the input has a property you have not noticed. Diff it against a passing one.

This step is why non-determinism (Book 01, Chapter 4) matters practically: a single failing run tells you almost nothing about the failure rate.

### 5. Bisect with a stronger model

Swap in a frontier model for one step, or for the run.

- **Now correct** → a capability problem at that step. Route that step to a stronger model, or simplify the step so a cheap model can do it.
- **Still wrong** → not a capability problem. The tools, the context or the task framing are at fault, and a bigger model will only be a more expensive way to be wrong.

This is a fast, high-information test and it is underused.

### 6. Replay with a corrected input

If you have checkpointing (Chapter 8), rewind to the step before the failure, correct the tool result or the state by hand, and let it run.

- **Recovers and succeeds** → the fault is upstream, in that tool.
- **Still fails** → the fault is downstream, in the reasoning or the following tools.

Time-travel replay is the single most useful debugging affordance an agent framework provides, and it is the concrete answer to "what does LangGraph give me".

### 7. Generalise, then add an eval case

Search the traces for other runs with the same shape: same tool pair confused, same argument error, same overflow. Fixing one instance with a prompt tweak is how a system prompt becomes 2,000 tokens of accumulated special cases. Fixing the class is engineering.

Then **add the case to the eval set before fixing it**, so the fix is measurable and the regression is caught permanently. This is the step that compounds: every incident makes the system durably better instead of momentarily better.

## The metrics that surface problems before users do

Cheap to compute from the trace, and mostly deterministic:

| Metric | What it catches |
|---|---|
| Steps per run (distribution, not mean) | Efficiency and drift; a bimodal distribution is a story |
| Cap-hit rate | Tasks too hard, or caps too tight |
| Repeated-call rate | Loops, and unhelpful tool results |
| Tool error rate, per tool | A tool whose schema or description is wrong |
| Schema-violation rate | Argument generation problems |
| Tool selection distribution | A tool never chosen is a description problem; one chosen always may be a fallback |
| Cost per run (p50, p95) | The p95 is where the runaway runs hide |
| Human rejection rate, per action type | Where the agent's judgement is worst |
| Silent-success rate | Reported success with no world-state change. The worst failure, and detectable |

The last one requires checking the world rather than the transcript, which is Chapter 4's verification point. It is the metric most worth building and the one almost nobody has.

## The habit

Read traces. Not dashboards, traces — twenty full runs a week, chosen randomly and from the failure tail. Every team that runs agents well does this and describes it as the highest-value hour in their week, because aggregate metrics tell you the rate of a problem and only a trace tells you what the problem is.

It is the same reason Book 02 recommends printing twenty random chunks. In both cases, the aggregate hides the thing you would immediately recognise if you looked at it.

*Connect the dot:* the `x-ops` measurement — 12 posts read, 0 passed the keyword filter, the best post of the day scoring zero — came from looking at a run rather than a metric. The metric said "filter working"; the run said the filter was rejecting everything good. That is exactly this chapter's argument, already demonstrated in his own repo, and it is a genuinely strong story for this topic.

Next: the closing chapter.
