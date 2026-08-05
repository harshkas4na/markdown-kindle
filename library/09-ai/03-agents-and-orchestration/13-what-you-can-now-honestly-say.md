# What You Can Now Honestly Say

**Fast overview:** The line-drawing chapter for the second-largest topic in the corpus. Twenty of forty-four companies are building agents, and the existing evidence is real but narrow: rc-agents is one agent-to-service payment flow, and the ops pipelines are agent-shaped with human gates. This chapter says exactly how much the reading moved, and gives the one build that closes most of the remaining gap in a weekend.

## What reading this book earned

You can now discuss, with mechanism:

- **The ladder of autonomy**, and the argument that most agentic products belong on rung 3, the state machine, rather than rung 4.
- **The loop itself** — you have written it, so no framework can mystify you, and you can say what any of them is doing underneath.
- **That the model never calls your function.** It emits text; your code dispatches. That sentence is the entire security model.
- **Tool design as the primary interface**: descriptions as the most important text in the system, granularity heuristics, state-gated toolsets, and errors as the model's input rather than your exception.
- **The three caps**, loop detection with escalation, progress checking, and the finish-tool termination pattern.
- **ReAct's actual history** — that native tool calling replaced its mechanism while keeping its insight — and the honest case against reflection without an external signal.
- **State versus memory**, and the four strategies for bounded context, with externalising tool results as the biggest single win.
- **A defensible position on LangChain**, including what it cost on REACTOR specifically.
- **What LangGraph gives you that a loop does not**: checkpoints, interrupts, streaming over a cyclic graph — and that its deeper benefit is making you build a state machine.
- **Human-in-the-loop as architecture**, including approval fatigue as the failure that voids the safety property, and reversibility as a way to need fewer gates.
- **When multi-agent is justified** (context isolation, differing configurations) and the four costs you always pay.
- **What MCP standardises**, the model/application/user control split, and why tool descriptions from third-party servers are untrusted input.
- **A debugging procedure** that starts by finding the first wrong step rather than the last.

## What it did not earn

- You have not **run an agent in production** against real users, so you have no numbers for step distributions, cap-hit rates or silent-success rates.
- You have not **shipped LangGraph**. Read and built, not shipped. Say exactly that.
- You have not **operated a multi-agent system**, and should not imply otherwise.
- You have not **written or operated an MCP server** until you do the exercise in Chapter 11, which is an afternoon.
- **rc-agents remains one flow, not an architecture.** It is a genuinely differentiating credential — agent-to-contract payment with no human in the loop — and it is not a planner, a trajectory, or a recovery path.

The honest framing for the whole topic: he has built **agent-shaped systems with human gates** (JobOps, x-ops, hack-ops, learn-ops) and **one agent-to-service payment flow** (rc-agents). He has not built a general tool-calling agent that plans, recovers and runs unattended. The first set is more relevant than it sounds, and it is not the second.

## The artifact: `agent-lab`

One weekend, and it closes most of the gap.

**Step 1 — the hand-rolled loop.** Chapter 2, typed out, with three tools over data you have: a read tool, a search tool, and one destructive tool (`delete_note`, over a scratch database). Add the three caps, loop detection with escalation, and a finish tool. Log every step in the schema from Chapter 4.

**Step 2 — break it deliberately.** Make a tool return nothing useful. Make two tool descriptions ambiguous. Remove a schema constraint and watch it hallucinate an id. Record what each failure looks like in the trace. **Write down what you saw** — this is the material that makes the debugging chapter yours rather than read.

**Step 3 — the same agent in LangGraph.** Typed state, conditional edges, a checkpointer. Then add the requirement "a human must approve any delete" to both versions. In the loop, you will build a suspend/resume mechanism. In the graph, it is `interrupt()`. That contrast is the answer to "why a framework".

**Step 4 — try to talk it into misusing the destructive tool.** Direct instructions in the user message; instructions hidden in a document the search tool returns. Then enforce the policy in the dispatch path instead of the prompt, and try again. Write down what changed. This is the bridge to Book 05 and the strongest single demonstration on this shelf.

**Step 5 — twenty tasks, measured.** Tool selection accuracy, steps per run, repeated-call rate, cap-hit rate, cost per run. A table.

**What this earns:**

> I built the same agent twice, once as a bare loop and once as a graph, and the thing that actually justified the framework was durability: adding a human approval step meant suspending a run for an arbitrary time, which is a checkpointer, and I would rather use one than write one. Separately I measured tool-selection accuracy across twenty tasks at 85%, and every miss was two tool descriptions that overlapped, not the model. Fixing the descriptions moved it to 100% without touching the prompt.

That second sentence is worth more than any framework claim, because it demonstrates the diagnostic instinct rather than the tooling.

## Ten questions to answer out loud

1. What is the difference between a chain and an agent?
2. Write me the agent loop. What terminates it?
3. Does the model call your function? (The answer is no, and the follow-up is why that matters.)
4. My agent picks the wrong tool 20% of the time. What do you check first?
5. What are the three caps and what does each catch?
6. What does LangGraph give me that a while loop does not? Name three things.
7. When would you split into multiple agents, and what does it cost you?
8. What is MCP standardising, and what is the security risk that comes with it?
9. My agent said it created the ticket and it did not. How do you detect that class of failure?
10. Where would you put the human, and how would you know the gate was working?

Question 9 is the one most likely to separate you from other candidates, because most people have not thought about verifying against the world rather than the transcript.

## Where to go next

**Book 05, Guardrails and Agent Safety**, immediately. It is the second half of every sentence in this book, and step 4 of the artifact above is already its first exercise.

**Book 04, Evals**, if the interview is closer than the study plan. Agent trajectory evaluation lives there and it is the question that follows "how do you know it works".

*Connect the dot:* the thread running through this entire book is **enforced versus requested**. Caps are enforced; "please stop when you have the answer" is requested. An approval edge is enforced; "always confirm first" is requested. A state-gated toolset is enforced; "do not use the refund tool during intake" is requested. Every time you can move a property from the prompt into the architecture, do it. That is the whole of Book 05, and it is the strongest available bridge from a smart-contract background to an agent-infrastructure seat.

Next: Evals and Harnesses.
