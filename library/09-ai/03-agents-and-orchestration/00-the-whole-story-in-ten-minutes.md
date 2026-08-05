# The Whole Story in Ten Minutes

**Fast overview:** "Agent" is the most overloaded word in the field, which is inconvenient, because twenty of the forty-four companies in the application corpus describe themselves with it. This chapter fixes a definition, gives the loop in twelve lines, names the four things that make an agent production-grade rather than a demo, and states the position that most agentic products should be less agentic than they are.

## The definition worth using

An **agent** is a system where a model decides the control flow.

That is the whole distinction. In a chain, you decide what happens next: retrieve, then summarise, then format. In an agent, the model decides: it can choose a tool, choose not to, choose to call it again, choose to stop. Autonomy over control flow is the axis, and everything else people mean by "agentic" is a consequence.

This definition is useful because it makes the trade-off obvious. Giving the model control over the flow buys you the ability to handle situations you did not enumerate, and costs you the ability to know what will happen. Every technique in this book is about buying back some of that predictability without giving up the flexibility.

## The loop

```python
messages = [{"role": "system", "content": SYSTEM},
            {"role": "user",   "content": task}]

for step in range(MAX_STEPS):
    r = model(messages, tools=TOOL_SCHEMAS)
    messages.append(r.message)

    if not r.tool_calls:
        return r.message.content              # the model is done

    for call in r.tool_calls:
        result = dispatch(call.name, call.arguments)
        messages.append({"role": "tool",
                         "tool_call_id": call.id,
                         "content": result})

raise StepLimitExceeded(messages)
```

That is an agent. Not an approximation of one — that is what every framework is doing underneath, and building it once by hand is the single best hour you can spend on this topic, because afterwards no framework can mystify you.

Everything else in the field is an answer to one of four questions about those twelve lines:

1. **What tools, and described how?** (Chapters 2-3)
2. **How does the loop stay bounded and recover?** (Chapter 4)
3. **What is in `messages` after step 30?** (Chapter 6)
4. **Who is allowed to approve what?** (Chapter 9, and Book 05)

## What makes it production-grade

Four things, and their absence is what separates a demo from a product:

**Bounds.** A step cap, a wall-clock cap, and a cost cap. All three, always. An agent with no bounds is a system that can spend your money in a loop at 3am.

**Recoverable failures.** A tool that raises should return a *message the model can act on*, not a stack trace and not silence. "The date must be in YYYY-MM-DD format; you sent 'next Tuesday'" gets fixed on the next step. A 500 does not.

**Durable state.** If the process dies at step 7 of 12, the run should resume rather than restart. This is what checkpointing buys, and it is also what makes human approval possible at all, because approval means suspending for minutes or days.

**Observability.** Every step, every tool call, every argument, every result, every token, stored and inspectable. An agent failure at step 9 is undiagnosable without the trace, and you cannot add tracing after the incident.

## The position worth holding

**Most agentic products should be less agentic than they are.**

Autonomy is a cost, paid in predictability, latency, money and debuggability. It should be spent only where the problem genuinely requires it. The honest hierarchy, cheapest and most reliable first:

| Shape | When it is right |
|---|---|
| One model call | The task is one transformation |
| A fixed chain | The steps are known and always the same |
| A router | A small number of known paths, model picks one |
| A state machine with model-filled steps | Known stages, uncertain content — **most business workflows** |
| A bounded agent loop with a small toolset | The sequence genuinely varies per input |
| A multi-agent system | Genuinely separable concerns at real scale |

Most products described as agents belong in row four. The state machine is the underrated answer: you get determinism about *what stages happen*, and the model's flexibility *within* a stage. Being able to say this, and to say when you would move up a row, is a stronger signal than enthusiasm about agents, because it is the thing people who have shipped agents learn and people who have demoed them do not.

The rc-agents work is a genuine example of the useful end of this: an agent paying $0.30 in USDC for a service, with the blast radius bounded by the payment amount rather than by a prompt.

## The failure modes, named

Everything that goes wrong with agents is on this list, and each has a fix in a later chapter:

- **Loops.** Same tool, same arguments, over and over, because the result was unhelpful and the model retried identically.
- **Drift.** By step 15 the agent is doing something adjacent to the task.
- **Wrong tool.** Chose `delete_records` when it wanted `archive_records`, usually because the descriptions were ambiguous.
- **Hallucinated arguments.** Invented a valid-looking id that does not exist.
- **Context blowout.** A tool returned 40,000 tokens of JSON and everything after it is degraded.
- **Compounding error.** Fifteen steps at 98% each is 74% end to end.
- **Silent success.** The agent reports it did the thing. It did not do the thing.

That last one is why agent evaluation cannot only score the final message, and it is the doorway to trajectory evaluation in Book 04.

## What this book covers

| Ch | Topic |
|---|---|
| 1 | What an agent is, and the ladder of autonomy |
| 2 | Tool calling from scratch, with no framework |
| 3 | Designing tools: schemas, descriptions, errors, granularity |
| 4 | The loop and its controls: caps, retries, loop detection |
| 5 | Planning patterns: ReAct, plan-and-execute, reflection |
| 6 | State, memory, and context that grows |
| 7 | LangChain: what it is, what it is not, when to use it |
| 8 | LangGraph: graphs, state, checkpoints, interrupts |
| 9 | Human-in-the-loop as architecture |
| 10 | Multi-agent systems and the cost you always pay |
| 11 | MCP: what it standardises and why it matters |
| 12 | Debugging an agent run |
| 13 | What you can now honestly say |

Next: what an agent is, more carefully, and the ladder of autonomy you should climb reluctantly.
