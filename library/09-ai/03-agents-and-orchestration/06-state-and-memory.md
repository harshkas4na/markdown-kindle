# State and Memory

**Fast overview:** The naive agent's context grows every step, cost grows quadratically over a run, and by step twenty the goal is buried under tool output. This chapter covers the difference between state and memory (which are constantly conflated), the four strategies for keeping context bounded, the structured-state approach that is usually the right answer, and what long-term memory actually means once you stop hand-waving.

## Why context grows quadratically

Every turn resends the whole history. A 20-step run where each step adds 500 tokens sends 500, then 1,000, then 1,500 tokens, and so on — the sum is proportional to n², not n.

```
20 steps × 500 tokens/step  →  ~105,000 input tokens sent in total, not 10,000
```

Prompt caching mitigates this substantially, since the prefix is stable and only the tail is new, and it does not remove the quality problem: at step 20 the model is reading nineteen tool results, most of them irrelevant, and the original task is far away in the middle of the context where attention is weakest (Book 01, Chapter 3).

**Both problems have the same fix: keep less.**

## State versus memory

Two different things, conflated constantly:

- **State** is what this run knows *now*: the task, what has been established, the current step. It is the working set, it is bounded, and it should be typed.
- **Memory** is what persists *across* runs: user preferences, past interactions, learned facts. It is unbounded and needs retrieval.

Most "agent memory" discussions are really about state management. Get state right first; most products never need real long-term memory.

## The four strategies for bounded context

### 1. Sliding window

Keep the system prompt, the original task, and the last N messages. Trivial, and it loses the middle, which is where the findings are.

Fine for chat, dangerous for agents, because an agent's early tool results are often exactly what it needs at the end.

### 2. Summarisation

When the history exceeds a threshold, compress the older portion into a summary and replace it.

```python
def compress(messages, keep_recent=6):
    head, tail = messages[1:-keep_recent], messages[-keep_recent:]
    if len(head) < 4: return messages
    summary = llm(SUMMARISE_PROMPT.format(history=render(head)))
    return [messages[0],
            {"role": "user", "content": f"[Earlier context summary]\n{summary}"},
            *tail]
```

Effective and lossy in ways that are hard to predict. Rules: always keep the last few messages verbatim; put the summarisation prompt in version control and in the eval suite, because a degraded summariser silently degrades everything downstream; and never summarise the original task, ever.

### 3. Externalise tool results

The best trick and the least used. Tool results go to a store; the context gets a reference and a preview.

```python
def dispatch(call):
    full = TOOLS[call.name](**call.arguments)
    ref = artifacts.put(full)                      # store the whole thing
    if len(full) < 800:
        return full
    return (f"{full[:600]}\n\n[Truncated. Full result stored as {ref} "
            f"({len(full)} chars). Use read_artifact('{ref}', query=...) "
            f"to search within it.]")
```

Now a 40,000-token API response costs 200 tokens of context, and the agent can go back for detail if it needs it — which is retrieval over its own working memory. This is the single most effective fix for the context blowout failure mode.

### 4. Structured state

The one to reach for by default. Instead of accumulating conversation, maintain a typed object and re-render it each step:

```python
@dataclass
class State:
    task: str
    established: list[str] = field(default_factory=list)   # facts found
    open_questions: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    step: int = 0

def render(s: State) -> str:
    return (f"TASK: {s.task}\n\n"
            f"ESTABLISHED:\n" + "\n".join(f"- {e}" for e in s.established) +
            f"\n\nOPEN:\n" + "\n".join(f"- {q}" for q in s.open_questions))
```

Each step: render the state, add the last tool result, ask the model for the next action and the state update. Context stays roughly constant regardless of run length.

What you get: bounded context, inspectable state (you can *look* at what the agent believes, which is enormous for debugging), testable state transitions, and survival across a model swap. What you pay: the model must maintain the state, which is another thing it can do badly, so validate the updates.

This is the shape LangGraph's state model encourages, and it is why that framework is worth taking seriously (Chapter 8).

## Long-term memory, properly

Three genuinely different things get called memory:

**Episodic** — what happened in past sessions. Store run summaries, retrieve relevant ones. This is RAG over your own history, and everything in Book 02 applies: chunking, retrieval quality, staleness, permissions.

**Semantic** — facts about the user or domain learned over time. "Prefers metric units", "is on the enterprise plan", "asked about SOC2 twice". Extracted after a session, stored as structured records, injected when relevant.

**Procedural** — how to do things well here. In practice this is prompt and tool improvement, done by humans reading traces, not something the agent updates about itself.

**The hard parts nobody mentions:**

- **What to remember.** Storing everything makes retrieval worthless. Extract deliberately with a schema.
- **Conflicts.** The user said "metric" in March and "imperial" in July. Which wins? You need recency or explicit supersession, and you need to decide before it happens.
- **Correctness.** A wrong memory poisons every future session and is invisible. This is worse than a wrong answer, because it is persistent.
- **Deletion.** A user asking to be forgotten must actually be forgotten, from memory, embeddings, traces and eval sets (Book 02, Chapter 13).
- **Injection.** If a user can write to memory by saying things, they can plant instructions that fire in later sessions. This is a stored-injection attack and it is real (Book 05).

**The advice:** do not build long-term memory until a specific product need forces it. Structured state plus a per-user preferences record covers most of what people mean, with none of the failure modes.

The append-only, cursor-per-consumer design of `lifelog` is a good model for the storage layer if you do build one: events are appended, corrections are appended rather than mutating history, and each consumer tracks how far it has read. That makes a wrong memory correctable and auditable rather than silently overwritten, which is the property this domain most needs.

## Context engineering, in one list

The discipline of deciding what occupies the window, ordered by impact:

1. **Truncate and project tool outputs at the boundary.** The biggest win, always.
2. **Externalise large artifacts** and reference them.
3. **Keep the task and the state near the top; keep the recent turns at the bottom.** Never let the goal drift into the middle.
4. **Prune tools by state.** Fifteen schemas on every call is thousands of tokens; expose only what is legal now.
5. **Summarise the middle**, never the ends.
6. **Put stable content first** so prompt caching applies.

Every item is a decision you make in code. None is a model capability. That is the point of calling it engineering.

*Connect the dot:* strategy 3, externalising tool results with a search-back tool, turns the agent's working memory into a retrieval problem — which means Book 02's entire toolkit applies to it. Systems compose in this field more than they look like they do.

Next: LangChain, assessed honestly.
