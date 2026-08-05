# The Loop and Its Controls

**Fast overview:** An unbounded agent is a system that can spend money in a circle until someone notices. This chapter covers the controls that make the loop safe: the three caps you always need, loop and repetition detection, progress checking, recovery, and the termination conditions that decide when the agent is done. None of it is sophisticated. All of it is absent from most demos, and its absence is what separates a demo from something you would run overnight.

## The three caps

Always all three, because each catches a different failure.

**Step cap.** The blunt instrument. 5-10 steps is enough for most tasks; deep research agents may need 30-50. Its virtue is that it is impossible to argue with.

**Wall-clock cap.** Catches the run where each step is legal and slow. Also what your HTTP timeout needs to align with, and the thing that stops a queue backing up.

**Cost cap.** The one people forget and the one that shows up on the bill. Track tokens per step, convert to dollars, and abort when the run exceeds its budget.

```python
class Budget:
    def __init__(self, max_steps=10, max_seconds=120, max_usd=0.50):
        self.max_steps, self.max_seconds, self.max_usd = max_steps, max_seconds, max_usd
        self.steps, self.usd, self.t0 = 0, 0.0, time.monotonic()

    def charge(self, usage):
        self.usd += cost_of(usage)

    def check(self):
        self.steps += 1
        if self.steps > self.max_steps:                     raise Exhausted("steps")
        if time.monotonic() - self.t0 > self.max_seconds:   raise Exhausted("time")
        if self.usd > self.max_usd:                         raise Exhausted("cost")
```

**Exhaustion should degrade, not crash.** When a cap is hit, ask the model once for its best answer given what it has, and return that with a flag saying it was truncated. A partial answer marked partial is far more useful than an error, and the flag is a metric you can alarm on.

Budgets should also be **per user and per tenant**, not only per run. A cost cap per run does nothing against a user who triggers 4,000 runs.

## Loop detection

The most common agent pathology: the same call, repeatedly, because the result was unhelpful.

```python
seen = Counter()

def key(call):
    return (call.name, json.dumps(call.arguments, sort_keys=True))

k = key(call)
seen[k] += 1
if seen[k] == 2:
    result = (f"You already called {call.name} with these exact arguments and got:\n"
              f"{previous[k]}\nThe result has not changed. Try different arguments "
              f"or a different tool, or answer with what you have.")
elif seen[k] > 2:
    raise LoopDetected(call.name)
```

Note the escalation: the second identical call gets an informative message that often unsticks the model, and the third aborts. Failing immediately on the second is over-eager, because a legitimate retry after a transient failure looks identical.

Detect the softer variants too: **near-identical arguments** (same tool, trivially different query) and **cycles** (A → B → A → B). A sliding window over the last six calls catches most of it.

**Repeated-call rate is one of the best agent health metrics you have.** It is cheap to compute, needs no judge model, and it rises before user complaints do.

## Progress checking

A subtler failure than looping: the agent is doing *different* things and none of them advance the task. Twelve searches, no synthesis.

Two mechanisms:

**Explicit progress state.** Make the agent maintain a small structured record — what it has established, what remains unknown — updated each step. Reviewing it makes stalling visible, and it also compresses context (Chapter 6).

**A periodic supervisor check.** Every N steps, a cheap model call: "here is the task and the last N actions; is this making progress toward the goal? Answer PROGRESS or STALLED with one sentence." On STALLED, inject a redirect or escalate to a human. Costs one small call every few steps and catches drift long before the step cap does.

## Recovery

Bounds stop bad runs. Recovery makes good runs succeed despite bad steps.

**Transient failures retry in code**, invisibly to the model, with backoff and jitter. If the model sees the failure it will "helpfully" change the query, and then you have two problems.

**Argument errors go back to the model** with the specific correction (Chapter 3). This is the main recovery path and it works well.

**Tool unavailability should be stated, with an alternative.** "The billing service is unavailable. You can still read account status with `get_account`."

**A last-resort summarise-and-return.** Whenever a run cannot complete, the user should get what was found and an honest statement of what was not. Never a bare failure.

## Termination

When is the agent done? Four conditions, and a robust loop checks all of them:

1. **The model stops calling tools.** The normal path.
2. **A designated finish tool is called.** `submit_answer(answer, confidence, sources)` is a good pattern: it forces structure on the final output, it makes "the agent decided it was done" an explicit traced event, and it lets you validate the answer before returning it.
3. **A cap is hit.** Degrade as above.
4. **A guard rejects.** A policy violation or a rejected approval terminates the run (Book 05).

The finish-tool pattern is worth adopting by default. Without it, "done" is inferred from the absence of a tool call, which is also what happens when the model gets confused.

## Verification before returning

An agent that reports success it did not achieve is the worst failure mode, because nothing errors and the user believes it.

Cheap defences:

- **Check the world, not the transcript.** If the agent says it created a ticket, query for the ticket. This is a code check, not a model check, and it catches the failure completely.
- **Require citations for factual claims**, as in Book 02, and verify the referenced tool outputs exist in the trace.
- **A critic pass on high-stakes outputs**: a second model call seeing the task and the answer, asked whether the answer actually addresses the task. Cheap, catches obvious misses, and does not catch subtle ones.

## Concurrency and parallel work

Where the task decomposes, run branches in parallel — three independent lookups, or three sub-questions researched at once — and merge. This turns a 12-second sequential run into a 4-second one.

The complications are real: partial failure handling, deduplicating overlapping findings, merge order affecting the final answer, and cost multiplying by the branch factor. Worth it for latency-sensitive multi-source work; not worth it for a three-step run.

## A retry policy that respects idempotency

The interaction between retries and side effects is where real incidents live:

- **Read tools:** retry freely.
- **Write tools:** retry only with the same idempotency key (Chapter 3).
- **Never retry the whole agent run** after a write without checking what already happened. A "just run it again" retry on a partially-completed run double-charges someone.

This is where the smart-contract instinct is directly transferable, and it is a good concrete example to have ready for the "how does your background apply" question.

## What to log per step

Non-negotiable, and cheap to add at the start and painful to add later:

```python
{"run_id": ..., "step": 3, "ts": ...,
 "model": "gpt-4o-mini@2026-05", "prompt_version": "agent-sys-v4",
 "messages_tokens": 4120, "completion_tokens": 88, "usd": 0.0031,
 "tool": "get_account", "args": {...}, "result_preview": "...",
 "result_bytes": 812, "latency_ms": 240,
 "budget_remaining": {"steps": 7, "usd": 0.44}}
```

From this you can reconstruct any run, compute every metric in this chapter, and answer "what did it actually do" without guessing. Chapter 12 is what you do with it.

*Connect the dot:* every control here is a bound on the *system*, enforced in code, rather than an instruction to the model. That distinction — enforced versus requested — is the thesis of Book 05, and the caps in this chapter are its simplest instance.

Next: how the agent decides what to do, and the honest case against the pattern everyone cites.
