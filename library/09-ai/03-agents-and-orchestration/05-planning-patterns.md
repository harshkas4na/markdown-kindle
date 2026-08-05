# Planning Patterns

**Fast overview:** ReAct, plan-and-execute, reflection, tree search. Four named patterns for how an agent decides what to do, each with a paper behind it and a reputation ahead of it. This chapter explains each mechanically, gives the honest case for and against, and lands on the position that matters in practice: modern tool-calling models already do most of ReAct natively, and the more useful choice is usually between planning up front and deciding as you go.

## ReAct

**Reason + Act**, from the 2022 paper. The model alternates between a written thought and an action:

```
Thought: I need the customer's plan before I can check refund eligibility.
Action: get_account(account_id="acct_1a2b3c4d")
Observation: {"plan": "annual", "status": "active"}
Thought: Annual plans have a 30-day window. I need the purchase date.
Action: get_order(order_id="ord_77")
...
```

**Why it worked.** In 2022, models had no native tool calling and no reasoning training. Making the model write its reasoning before acting gave it tokens to compute in (Book 01, Chapter 2), and it made agents dramatically more reliable at a stroke.

**The honest case against it today.** The pattern as originally specified — parse `Thought:`/`Action:`/`Observation:` out of free text — is obsolete. Native tool calling gives you structured, validated calls instead of a regex over prose that breaks when the model writes a colon in the wrong place. And reasoning-trained models already interleave thinking and acting without being told to.

**What survives, and it is the important part:** the *idea* that the model should reason before acting. In a modern loop you get this by allowing a text field alongside tool calls, or by using a reasoning model, or by a `thought` parameter on your finish tool. You do not get it by parsing `Thought:` lines.

**How to talk about it:** "ReAct is the ancestor of every tool-calling loop, and native tool calling replaced its mechanism while keeping its insight." That answer shows you know the history and are not applying it uncritically, which is what the question is testing.

## Plan-and-execute

Generate a full plan first, then execute the steps.

```
Plan:
  1. Look up the customer account
  2. Retrieve their most recent order
  3. Check the refund policy for their plan
  4. Compute eligibility
  5. Draft the response
Execute step 1... step 2...
```

**Advantages that are real:**

- **Cost.** Planning happens once with a strong model; execution can use a cheap one per step. On a long task this is a large saving.
- **Inspectability.** The plan is a reviewable artifact — you can show it to a user for approval *before* anything runs, which is a much better approval UX than approving each action.
- **Parallelism.** Independent steps in the plan can run concurrently.
- **Less drift.** The goal is written down and re-read, rather than living twenty messages back.

**The weakness:** plans made without information are frequently wrong. Step 2 reveals that the premise of step 3 was false, and a rigid executor marches on.

**The fix, which is the actual production pattern:** **re-planning**. Execute a step, check whether the plan still makes sense, revise if not. This is plan-and-execute with a feedback edge, and it captures most of the benefit of both approaches.

**When to prefer it:** long tasks (10+ steps), tasks where a human should approve before execution, tasks with expensive steps worth ordering deliberately.

**When not to:** short tasks, where planning is pure overhead, and highly uncertain tasks where the first observation invalidates everything.

## Reflection and self-critique

Produce output, critique it, revise.

```
draft = generate(task)
critique = critique_model(task, draft)      # what is wrong with this?
final = generate(task, draft, critique)     # fix it
```

**Where it genuinely helps:** tasks with **verifiable** feedback. Code that can be run against tests, output that can be schema-validated, claims that can be checked against retrieved sources, a plan that can be checked against a policy. The critique has ground truth to stand on.

**Where it is theatre:** pure self-critique with no external signal. Book 01 explained why — the model is trained to be agreeable, so "is this good?" gets "yes", and "find problems with this" gets invented problems. Self-critique without ground truth produces confident revisions that are not improvements, and it costs 2-3x.

**The rules that make it work:**

1. **Ground the critique in something external.** Test results, a validator, retrieved sources, an explicit rubric.
2. **Use a separate call with a fresh context**, not "now check your work" in the same conversation, where the previous answer anchors everything.
3. **Cap the iterations at 1-2.** Improvement plateaus fast and then reverses.
4. **Measure it.** Reflection is expensive and its value varies enormously by task. This is exactly the kind of thing that should be a row in an eval table rather than an assumption.

The strongest version is the **generate-and-verify** loop where the verifier is code: write the function, run the tests, feed failures back. That is not really reflection, it is a compiler in the loop, and it works far better than anything the model says about itself.

## Tree search and best-of-N

Explore several paths, score them, keep the best. Tree-of-thoughts and its relatives.

Honest assessment: rarely worth it in a product. The cost multiplies by the branch factor, latency goes up correspondingly, and the scoring function is the hard part — a model scoring its own branches has all the calibration problems above.

The cheap, useful cousin is **best-of-N with an external scorer**: generate N candidate answers, pick using something objective (do the tests pass, does it validate, does it cite real sources). And **self-consistency** (Book 01, Chapter 4) for tasks with a discrete answer, where majority vote over samples is simple and effective.

Know the family, use the cheap members.

## Choosing

| Task shape | Pattern |
|---|---|
| Short, tool-mediated, varied | Plain tool-calling loop |
| Long, multi-step, expensive steps | Plan-and-execute with re-planning |
| Needs human approval before acting | Plan-and-execute; approve the plan |
| Output is checkable by code | Generate-and-verify |
| Output is subjective prose | Single pass, then measure whether reflection helps |
| Discrete answer, accuracy critical | Self-consistency over samples |
| Genuinely separable roles at scale | Multi-agent (Chapter 10), reluctantly |

## The meta-point

Every pattern here is a way of spending more compute to get a better answer, and each has a cost multiplier attached: reflection 2-3x, self-consistency 5x, tree search 10x+.

So the question is never "which pattern is best". It is: **on my eval set, which pattern moves the score enough to justify its multiplier?** Sometimes plain single-pass with better tool descriptions beats an elaborate pattern with bad ones, and you only find that out by measuring.

That framing — patterns as compute/quality trade-offs to be measured rather than doctrines to be adopted — is the answer that sounds like someone who has run these in production.

*Connect the dot:* the "ground the critique in something external" rule is the same principle as Book 04's warning about LLM-as-judge. A model evaluating without ground truth is measuring its own preferences, whether it is judging its own draft or someone else's.

Next: state and memory, and what is in `messages` after step thirty.
