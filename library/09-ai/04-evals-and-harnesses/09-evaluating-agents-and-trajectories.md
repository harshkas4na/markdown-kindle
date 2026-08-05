# Evaluating Agents and Trajectories

**Fast overview:** Scoring an agent's final message is necessary and nowhere near sufficient, because the answer can be right for the wrong reasons, or the agent can report success it did not achieve. This chapter covers the three levels of agent evaluation — outcome, trajectory, and step — the environment problem that makes agent evals genuinely harder than everything else in this book, and the metrics that surface agent pathologies before users do.

## Why the final answer is not enough

Four failures that a final-answer score misses entirely:

1. **Right answer, wrong path.** The agent guessed, or used prior knowledge instead of the tool. It will not generalise, and it looks perfect.
2. **Silent success.** "I've created the ticket." No ticket exists. The message scores well; the world is unchanged.
3. **Correct but ruinous.** The right answer after 40 steps and $4.00, when 6 steps and $0.05 was available.
4. **Correct with a side effect.** The answer is right and it also deleted something on the way.

So agent evaluation needs three levels.

## Level 1 — outcome

Did the task get done? And critically: **check the world, not the transcript.**

```python
def check_outcome(example, run) -> dict:
    return {
        "final_correct": judge_answer(example, run.final_message),
        "state_correct": example.verify(world_after=snapshot()),  # the real check
        "no_side_effects": snapshot().diff(example.expected_changes) == {},
        "within_budget": run.steps <= example.max_steps and run.cost <= example.max_cost,
    }
```

`example.verify` is a function that queries the actual system: does the ticket exist, does it have the right fields, is the refund recorded. This is a **programmatic scorer** (Chapter 3) and it is the strongest one available, because it cannot be talked into agreeing.

`no_side_effects` is the check nobody writes. Snapshot the environment before and after, diff it, and assert the diff is exactly what was expected. It catches the class of failure where the task succeeded and something else broke.

## Level 2 — trajectory

Was the *path* reasonable? Several ways to score it, in ascending order of tolerance:

**Exact match against a reference trajectory.** The agent must call exactly this tool sequence. Far too brittle for anything real — many valid paths exist.

**Order-free tool set match.** Did it call the necessary tools, regardless of order and extras? Reasonable, and it ignores efficiency.

**Precision and recall over tool calls.** Recall = fraction of necessary tools called; precision = fraction of calls that were necessary. Low precision means wandering; low recall means it skipped a step. This pair is the most informative cheap trajectory metric.

**Required-and-forbidden.** The pragmatic default:

```yaml
trajectory:
  must_call:    [get_account, check_refund_policy]
  must_precede: [[check_refund_policy, issue_refund]]   # ordering constraints
  must_not_call: [delete_account, escalate_to_legal]
  max_calls_of: {search_docs: 3}
```

This encodes what actually matters — the policy check happened *before* the refund, the destructive tool was never touched — without over-specifying the path. It is also directly a safety property, which makes it gate-able with zero tolerance.

**Judge the trajectory.** Give a model the task and the full trace and ask whether the approach was sound and efficient. Flexible, expensive, and subject to every bias in Chapter 4. Useful for a qualitative slice, not for a gate.

## Level 3 — per step

Isolate individual decisions, which is what lets you localise a problem:

- **Tool selection accuracy.** Fix the context, ask for the next action, check the tool. Twenty examples, and it isolates description quality from everything else. **This is the cheapest and most diagnostic agent metric there is.**
- **Argument accuracy.** Schema-valid and semantically right.
- **Stopping accuracy.** Did it stop when it had enough, or keep going / stop early? Both failures are common and neither shows up in a final-answer score.
- **Recovery.** Inject a tool failure at step 3 and check whether it recovers. This is a dedicated eval slice and it is worth having.

## The environment problem

Agents act on the world, so evaluating them requires a world to act on. This is the hard part and the reason agent evals are genuinely more work than RAG evals.

Options:

**Mocked tools.** Deterministic canned responses per tool call. Fast, free, fully reproducible, and it cannot catch anything about how real systems behave. Good for tool-selection and trajectory evals.

**A seeded test environment.** A real database, real services, reset to a known state before each run. Slower, and it is the only way to check outcomes against the world. **This is the correct default for outcome evals**, and building the reset harness is most of the work.

**Recorded-and-replayed interactions.** Capture real tool responses once, replay them. A middle ground with the usual staleness problem.

**Production shadow.** Run the agent read-only against real data, evaluate its *proposals* without executing them. Excellent for realism, and it only evaluates the read half.

The practical stack: mocks for the fast CI tier, a seeded environment for the nightly full run, shadow mode for realism checks before a release.

Scenr's whole product is essentially this problem — provisioned, deliberately-broken stacks that an agent works in while an eval agent watches. Worth understanding well before that conversation.

## The metrics dashboard

From the traces, mostly deterministic:

| Metric | What it catches |
|---|---|
| Task success rate (world-verified) | The headline |
| Silent-success rate | Claimed success, no state change. **The worst failure** |
| Steps per run, distribution | Efficiency and drift. Bimodal is a story |
| Cost per run, p50 and p95 | The p95 is where runaways hide |
| Cap-hit rate | Tasks too hard or caps too tight |
| Repeated-call rate | Loops and unhelpful tool results |
| Tool error rate, per tool | A specific tool's schema or description is wrong |
| Tool selection distribution | A never-chosen tool is a description problem |
| Forbidden-tool-call rate | Must be zero. Gate at zero |
| Human rejection rate, per action type | Where the agent's judgement is weakest |
| Recovery rate after injected failure | Robustness |

Silent-success rate deserves its own line in any conversation about agent evaluation, because it is the failure mode most likely to embarrass a company and the one least likely to be instrumented.

## Multi-turn and multi-agent

**Multi-turn** evaluation needs simulated users: a model playing a user with a goal and a persona, following a script or improvising. This works and it introduces a second unvalidated model into your measurement, so validate the simulator the same way you validate a judge — does it behave like real users on a sample of real conversations?

**Multi-agent** (Book 03, Chapter 10) needs all three levels applied at three scopes: each agent alone with fixed inputs, each handoff for completeness, and the system end to end. Without per-agent evaluation you cannot localise, which is the same argument as splitting retrieval from generation.

## Statistical caution

Agents have higher variance than single calls, because non-determinism compounds across steps. A single run tells you very little.

- **Run each task 3-5 times** and report the success *rate*, not a binary.
- **Expect wide intervals.** A 70% success rate over 30 tasks run once has an interval of roughly ±16 points.
- **Measure your noise floor** by running the identical configuration twice, as in Chapter 5. For agents this number is usually larger than people expect, and knowing it is what stops you chasing phantom regressions.

## The honest summary

Agent evaluation is the least mature part of this field. There is no consensus metric set, the environment problem is genuinely hard, and most companies building agents are doing this badly or not at all.

That is exactly why it is worth being good at, and it is a reasonable thing to say out loud:

> Agent evals are the part of this I would expect to spend the most time on, because there is no standard answer. What I would build first is the boring half that is standard: verify outcomes against the world rather than the transcript, so silent success is detectable, and put forbidden-tool assertions in the trajectory check with a zero-tolerance gate. Those two catch the failures that actually hurt, and neither needs a judge model.

*Connect the dot:* the required-and-forbidden trajectory spec is an eval expressing a guardrail. The same constraint appears twice on this shelf: enforced at runtime in the dispatch path (Book 05), and asserted in the eval so a regression in the enforcement is caught. Belt and braces, and the eval is what tells you the belt is still there.

Next: online evaluation, where offline cannot see.
