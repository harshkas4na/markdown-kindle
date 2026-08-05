# Multi-Agent Systems

**Fast overview:** Three of forty-four dossiers name multi-agent explicitly, and far more companies describe systems that are multi-agent in marketing and single-agent in fact. This chapter covers the topologies, the two genuine reasons to split, the four costs you always pay, and the position most experienced practitioners hold: a single well-built agent with good tools beats a poorly-motivated committee almost every time.

## What "multi-agent" means

More than one LLM loop, each with its own context, prompt, and usually its own toolset, coordinating on a task.

The critical word is **own context**. Two prompts calling the same model in sequence is a chain. Two loops that each maintain their own conversation and pass messages is multi-agent. The separation of context is the whole difference, and it is both the benefit and the cost.

## The topologies

**Supervisor / orchestrator.** One agent receives the task, delegates to specialists, and assembles the result. The most common and the most controllable: there is one place where the plan lives, one place to put a policy check, and one trace to read.

**Sequential pipeline.** Agent A's output is agent B's input. Researcher → writer → editor. Predictable and easy to evaluate stage by stage. This is really a chain with LLM-shaped stages, which is a good thing.

**Peer network.** Agents message each other freely. Maximum flexibility, and the failure modes multiply: message loops, unresolvable disagreement, and traces that no human can follow. Rarely the right answer in a product.

**Hierarchical.** Supervisors of supervisors. Correct at genuine scale, and a strong smell in a startup.

**Debate / adversarial.** Two agents argue a question, a third adjudicates. Genuinely improves some reasoning tasks. Expensive and usually replaceable by self-consistency for less money.

## The two reasons that hold up

Most stated reasons for multi-agent do not survive scrutiny. Two do:

**1. Context isolation.** A single agent doing research across forty documents drowns in its own context. Spawning a sub-agent per document, each returning a two-paragraph summary, keeps the supervisor's context small while doing forty documents' worth of work. **This is the strongest reason** — it is a context-engineering solution, and it is the same idea as externalising tool results in Chapter 6, one level up.

**2. Genuinely different configurations.** One role needs a reasoning model with a long context and no write access; another needs a fast cheap model with database tools. Different models, different prompts, different tool permissions, different rate limits. Forcing them into one agent means the union of all tools and the maximum of all costs on every step.

Reasons that do **not** hold up on their own:

- *"Specialisation improves quality."* Sometimes, marginally. A single agent with a good system prompt and well-described tools usually matches a committee, for a fraction of the cost.
- *"It mirrors how a human team works."* Org charts are a solution to human bandwidth and communication limits. Neither constraint applies here.
- *"It is more scalable."* Only if the work is genuinely parallel. Otherwise it is the same work with more overhead.

## The four costs you always pay

**1. Cost and latency multiply.** Each agent has its own system prompt, its own tool schemas, and its own loop. A supervisor plus three specialists is four contexts and often 5-10x the tokens of a single agent doing the same work.

**2. Information is lost at every handoff.** Agent A knows something implicitly from its context that never makes it into the message to agent B, and B produces a subtly wrong result confidently. This is the most common real failure and it is hard to see.

**3. Errors compound across agents.** Four agents at 90% each is 66% end to end.

**4. Debugging gets much harder.** Four interleaved traces, and the question "why did the final answer say that" may require reading all of them. Chapter 12 is harder in exactly proportion to the agent count.

## The design rules that make it survivable

If you do split:

**Make handoffs explicit and typed.** Not free-form prose between agents. A schema:

```python
class ResearchResult(BaseModel):
    question: str
    findings: list[Finding]           # each with a claim and a source id
    unanswered: list[str]
    confidence: Literal["high", "medium", "low"]
```

Typed handoffs let you validate the boundary, evaluate each agent independently, and see exactly what was lost. This single decision fixes most of failure mode 2.

**One writer.** Only one agent should be allowed to mutate the world. Every other agent reads and reports. This makes the blast radius one component, and it makes authorisation tractable.

**Give the supervisor the budget.** Total steps and total cost are enforced at the top, not per agent, or four agents each politely respecting a ten-step cap will run forty steps.

**Keep the trace unified.** One run id threaded through every agent and every call, so the whole thing reads as one timeline. Without this, debugging is archaeology.

**Bound the fan-out.** A supervisor that can spawn unlimited sub-agents can spawn unlimited cost. Cap the count.

## Evaluating them

Multi-agent systems need evaluation at three levels, and the third is the one people skip:

1. **Each agent alone**, against its own golden set with fixed inputs. This is the only way to localise a quality problem.
2. **The handoffs.** Is the typed message complete and correct given what A knew? A schema-valid message can still be missing the key finding.
3. **End to end.** The only number that matters to the user, and useless on its own for diagnosis.

Same discipline as splitting retrieval from generation in Book 02, applied to a different decomposition. It is the same idea every time: **measure the components, or you will tune the wrong one.**

## The position to hold in an interview

> I would start with one agent and good tools, and split only when I could point at the specific reason. The reason that actually convinces me is context isolation — when one agent is drowning in its own history, sub-agents that each return a summary are a context-engineering fix and a good one. Different model and permission requirements per role is the other. "Specialists produce better output" I would want to see on an eval before believing, because in my experience the handoff loses more than the specialisation gains.

That answer is confident, specific, gives the conditions under which the other side is right, and it is the position most people who have run these arrive at.

## The one that is actually common and works

Worth naming because it is understated: **a supervisor with parallel read-only sub-agents, each returning a typed summary, and a single writer at the end.**

- Context isolation, which is the good reason.
- Parallelism, so latency does not multiply even though cost does.
- One mutation point, so safety is tractable.
- A clean trace shape: fan out, fan in, act.

If someone asks you to design a multi-agent system, this is the shape to reach for first, and then to argue down to a single agent if the reasons do not hold.

*Connect the dot:* the "one writer" rule is Book 05's blast-radius principle applied at the topology level. In both cases the safety comes from structure — only one component *can* do the dangerous thing — rather than from every component being asked to behave.

Next: MCP, and what it actually standardises.
