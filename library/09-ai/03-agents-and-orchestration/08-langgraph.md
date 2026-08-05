# LangGraph

**Fast overview:** LangGraph is the answer to "what does a framework give me that a while loop does not", and unlike much of its parent project the answer is substantive. It models an agent as a state machine with typed state, explicit edges and durable checkpoints — which turns out to be exactly the four things Chapter 4 said you need. This chapter covers the model, the three features that are genuinely hard to rebuild, and the honest boundary of when it is overkill.

## The model

Three concepts:

- **State** — a typed object flowing through the graph. Each node receives it and returns updates that are merged in.
- **Nodes** — functions that take state and return a partial update. A node can call a model, call a tool, run arbitrary code.
- **Edges** — transitions. Fixed (`A → B`), or **conditional** (a function inspects the state and returns the next node's name).

```python
from typing import Annotated, TypedDict
from operator import add
from langgraph.graph import StateGraph, END

class State(TypedDict):
    messages: Annotated[list, add]      # reducer: new messages append
    steps: int
    findings: list[str]

def call_model(state: State):
    r = model.invoke(state["messages"], tools=TOOLS)
    return {"messages": [r], "steps": state["steps"] + 1}

def call_tools(state: State):
    outs = [run_tool(c) for c in state["messages"][-1].tool_calls]
    return {"messages": outs}

def route(state: State) -> str:
    last = state["messages"][-1]
    if state["steps"] >= 10:            return END
    if getattr(last, "tool_calls", None): return "tools"
    return END

g = StateGraph(State)
g.add_node("model", call_model)
g.add_node("tools", call_tools)
g.set_entry_point("model")
g.add_conditional_edges("model", route, {"tools": "tools", END: END})
g.add_edge("tools", "model")            # the cycle
app = g.compile(checkpointer=checkpointer)
```

The **reducer** annotation is the piece worth noticing. `Annotated[list, add]` says how concurrent or successive updates to that field combine — append rather than replace. That is what makes parallel nodes safe: two branches can both write to `findings` and the reducer merges them deterministically instead of one clobbering the other.

## The three things that are genuinely hard to rebuild

This is the part that answers the interview question properly.

### 1. Checkpointing and durable execution

Every state transition is persisted. Concretely, this gives you:

- **Resume after a crash.** The process dies at node 7; a new one picks up from the last checkpoint instead of restarting a run that already spent money and made writes.
- **Suspend for human approval.** A run can stop for minutes or days and resume, because the state is in a database, not in a Python stack frame. This is what makes Chapter 9 possible at all.
- **Time travel.** Rewind to an earlier checkpoint, change the state, and re-run from there. As a debugging tool for agents this is genuinely powerful: you can replay the run from step 4 with a corrected tool result and see whether the rest recovers.
- **Threads.** State keyed by a thread id, so a conversation resumes naturally across requests.

Writing this yourself means designing a serialisation format, a store, a resume protocol and a versioning story for state schema changes. It is a project, not an afternoon.

### 2. Interrupts

`interrupt()` inside a node suspends the graph, surfaces a payload to the caller, and resumes with a value when the caller sends one back.

```python
def approve_refund(state: State):
    decision = interrupt({"action": "refund",
                          "amount": state["amount"],
                          "reason": state["reason"]})
    if decision["approved"]:
        return {"result": do_refund(state)}
    return {"result": f"Refused: {decision.get('note', 'no reason given')}"}
```

The value of this is architectural: **the approval is a node in the graph, not an instruction in a prompt.** The agent cannot skip it, cannot be talked out of it, and cannot reach the refund without traversing the edge. That is the enforced-versus-requested distinction, implemented.

You can also interrupt *before* or *after* any node without touching its code, which makes "pause before every write" a configuration rather than a refactor.

### 3. Streaming semantics over a graph

Streaming tokens from the model, plus state updates, plus node-entry/exit events, over a cyclic graph with parallel branches, is fiddly. Getting it right yourself is a week you probably do not want to spend.

## What it does not solve

Be clear about the boundary:

- **It does not design your agent.** The graph, the tools, the state schema and the bounds are all still your problem, and they are the part that determines whether it works.
- **It does not make it observable.** You still need tracing (Book 06). Checkpoints are state, not spans.
- **It does not make it correct.** Every failure mode in Chapter 4 still applies inside a graph.
- **It adds real complexity.** Typed state with reducers, compiled graphs and checkpointer configuration is more machinery than a for-loop, and for a five-step agent with no approval step and no durability requirement, that machinery is pure cost.

## When to use it

**Use it when** the agent is long-running, needs to survive a crash, needs human approval mid-run, has parallel branches whose results must merge, or is complex enough that an explicit graph is easier to reason about than nested conditionals.

**Skip it when** the agent is a short bounded loop with no durability requirement. Chapter 2's eighty lines are genuinely enough, and they are easier to read.

**The general rule:** adopt it when you find yourself building a checkpointer. That is the signal that the problem has outgrown the loop.

## The state-machine payoff

The deeper argument for LangGraph is not the features; it is that it pushes you toward rung 3 of the ladder (Chapter 1).

A well-built graph has named stages and explicit transitions. That means you can enumerate the paths, gate tools by node, put a policy check on an edge, evaluate each node separately, and read a trace as a sequence of stage names. All of those are properties of the state machine, not of the library — the library just makes the state machine the path of least resistance.

Which is why the honest summary is: **LangGraph's main benefit is that it makes you build a state machine, and its main features exist to make state machines durable.**

## The exercise

Build the same agent twice: once as Chapter 2's loop, once as a graph. Same tools, same task. Then add one requirement — "a human must approve any write" — and implement it in both.

In the loop, you will find yourself inventing a way to suspend, serialise and resume. In the graph, it is an `interrupt()` in one node. That contrast, experienced rather than read, is the answer to "why LangGraph", and it takes an afternoon.

*Connect the dot:* the `terraform-in-go` work — DAG resolution and state management, hand-written — is directly relevant here. A LangGraph graph is a DAG with cycles and a state store, and having implemented dependency resolution and state files from scratch is a real, non-obvious credential for reasoning about it.

Next: human-in-the-loop, treated as architecture rather than a checkbox.
