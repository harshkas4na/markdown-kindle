# What an Agent Actually Is

**Fast overview:** Before the mechanics, the taxonomy — because the most common expensive mistake in this field is building row five of the ladder when row three would have worked. This chapter defines the ladder of autonomy properly, gives the test for which rung a problem belongs on, and makes the case for the state machine as the shape most business problems actually want.

## The ladder

**Rung 0 — one call.** Input, prompt, output. Classification, extraction, summarisation, drafting. Predictable latency, predictable cost, trivially testable. An enormous amount of shipped AI product value is here and stays here.

**Rung 1 — a chain.** Fixed sequence of calls with code in between. Retrieve, then answer, then verify. You control the flow; the model fills in the steps. Each stage is separately testable, and a failure is localised to a stage. REACTOR's pipeline was this shape.

**Rung 2 — a router.** One classification decides which of N known paths runs. Still fully predictable — you enumerated the paths — but now the system handles a heterogeneous input distribution. The query router in Book 02 Chapter 9 is this.

**Rung 3 — a state machine with model-filled steps.** Stages are fixed in code; transitions are mostly deterministic with some model-decided branches; the content of each stage comes from the model. Loan application intake, support ticket triage and resolution, document processing pipelines. **This is where most business workflows belong** and it is the rung people skip.

**Rung 4 — a bounded agent loop.** The model chooses tools and sequence from a small toolset, within hard caps. Correct when the sequence genuinely varies per input in ways you cannot enumerate: research tasks, debugging, multi-source investigation.

**Rung 5 — multi-agent.** Several loops with separate contexts and roles, coordinating. Correct rarely, and covered honestly in Chapter 10.

## The test

Ask: **could I write down every path this system might take?**

- **Yes, and there are few** → rung 1 or 2.
- **Yes, and there are many but the *stages* are fixed** → rung 3.
- **No, genuinely not** → rung 4.
- **No, and the work also splits into independently-specialisable roles at real volume** → consider rung 5, then decide against it once, then reconsider.

The follow-up question that keeps you honest: **what does the system do when it is wrong, and how would I know?** Predictability is worth paying for wherever being wrong is expensive, and higher rungs have less of it.

## The state machine, argued properly

Rung 3 deserves the most space because it is the most underrated.

Take support-ticket resolution. An agent-loop version gives the model tools — search knowledge base, look up account, issue refund, escalate — and lets it work. Attractive, and it means every ticket takes an unpredictable number of steps, the refund tool is reachable from any state, and "why did it refund that" requires reading a trace.

The state machine version:

```
classify → gather_context → propose_resolution → [check policy] → execute → confirm
                 ↑                                      ↓
                 └──────────── need more info ──────────┘
```

Stages are code. The model classifies, extracts, drafts, decides one branch. The refund tool is only reachable from `execute`, and only after `check policy` passed. The number of stages is bounded by construction rather than by a step cap.

What you get: predictable cost and latency, each stage separately evaluable (which is the Book 02 lesson generalised), a policy check that cannot be skipped because it is an edge in the graph rather than an instruction in a prompt, and a trace that reads as a sequence of named stages rather than as twelve tool calls.

What you give up: the ability to handle a ticket whose resolution needs a path you did not draw. Which is a real cost, and is usually smaller than it feels, because the long tail can escalate to a human.

**The line worth remembering:** an agent's flexibility is most valuable at the edges of a workflow and most dangerous at its centre. Put the model where the input is messy, and put the state machine where the consequences are.

## Where the smart-contract instinct transfers

This is a genuine and non-obvious connection worth being able to make.

A smart contract cannot be hotfixed after deployment, so its safety comes from structure: state is explicit, transitions are enumerated, invariants are checked before state changes, and a function that must not be callable in a state simply is not callable in that state. You do not write a comment asking callers to behave.

An agent that can spend money or change records has the same requirement and usually none of the discipline. "Always confirm with the user before refunding" in a system prompt is a comment asking the model to behave. The equivalent of a `require` statement is a policy check in the dispatch path that the model cannot route around.

That is the argument the Ramain outreach draft in the corpus makes — the blast radius bounded by design rather than by a guardrail prompt — and it is the strongest available framing for why a Solidity background is relevant to an agent-infrastructure seat. Book 05 is this idea worked out fully.

## Agent, workflow, chain: the vocabulary

Because the words appear in JDs and are used inconsistently:

- **Workflow** — usually rungs 1-3. Predefined path, model inside the steps.
- **Agent** — usually rung 4. Model decides the path.
- **Agentic** — marketing for anything from rung 1 up. When a JD says "agentic", read the rest of the posting to find out which rung they mean, and ask in the interview. Asking is a good signal.
- **Autonomous** — usually means "runs without a human in the loop", which is an orthogonal axis to the rung and the one that matters for safety.

Two axes worth separating explicitly in conversation: **how much control the model has**, and **how much a human sees before an action lands**. A rung-4 agent with human approval on every write is far safer than a rung-2 router that writes to production autonomously. The dossiers' repeated phrase "governed" is about the second axis, not the first.

## The honest starting question

When someone describes an agentic product, the useful question is not "which framework". It is:

> What is the smallest amount of autonomy that solves this, and what happens when it is wrong?

Asking that, in an interview at an agent company, is close to the highest-signal thing available, because it is the question their own engineers argue about internally.

*Connect the dot:* JobOps is a rung-3 system with a hard human gate — scouts and skills run as defined stages, and nothing is ever sent or submitted automatically. That gate is architectural rather than requested, which is exactly the distinction Chapter 9 and Book 05 build on.

Next: the loop, written from scratch.
