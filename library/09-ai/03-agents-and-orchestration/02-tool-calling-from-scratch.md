# Tool Calling from Scratch

**Fast overview:** Build the loop once with no framework and it stops being magic permanently. This chapter writes a complete working agent in about eighty lines, explains exactly what the model is and is not doing at each point, and names the five things the naive version gets wrong — each of which is a later chapter. Do this before reading anything about LangGraph.

## What tool calling actually is

The model does not call your function. It cannot. It emits **text** — structured tokens that your SDK parses into a name and a JSON object of arguments. Your code decides whether to call anything at all.

That sentence is the whole security model of agents, and it is worth saying out loud in an interview: **the model proposes, your code disposes.** Every guardrail in Book 05 lives in the gap between the proposal and the call.

Under the hood, providers train models to emit a particular token structure for tool calls, and the API layer converts your JSON Schema tool definitions into a prompt segment. The abstraction leaks in small ways per provider, which is why a thin adapter is worth owning.

## The whole thing

```python
import json, time
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o-mini"

# ---------- 1. the tools ----------

def search_docs(query: str, limit: int = 5) -> str:
    hits = retrieve(query, k=limit)
    return "\n\n".join(f"[{h.id}] {h.text[:600]}" for h in hits) or "No results."

def get_account(account_id: str) -> str:
    acct = db.accounts.get(account_id)
    if acct is None:
        return f"No account with id {account_id!r}. Use search_accounts to find one."
    return json.dumps({"id": acct.id, "plan": acct.plan, "status": acct.status})

TOOLS = {"search_docs": search_docs, "get_account": get_account}

SCHEMAS = [{
    "type": "function",
    "function": {
        "name": "search_docs",
        "description": (
            "Search the product documentation for passages relevant to a natural-"
            "language query. Returns up to `limit` passages with their ids. Use this "
            "for questions about how the product works, policies, or pricing. Does "
            "not know anything about specific customer accounts."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Natural-language search query, not keywords."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "get_account",
        "description": (
            "Look up one customer account by its exact id (format: acct_XXXXXXXX). "
            "Returns plan and status. Only call this with an id you have seen in the "
            "conversation or in another tool's output. Never guess an id."),
        "parameters": {
            "type": "object",
            "properties": {"account_id": {"type": "string",
                                          "pattern": "^acct_[a-z0-9]{8}$"}},
            "required": ["account_id"],
            "additionalProperties": False,
        },
    },
}]

# ---------- 2. the loop ----------

SYSTEM = """You are a support assistant.
Use the tools to find information before answering. Never state a policy or an
account fact you have not read from a tool. If you cannot find something, say so.
When you have the answer, reply to the user directly without calling a tool."""

MAX_STEPS = 8
MAX_SECONDS = 30

def run(task: str):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    started = time.monotonic()
    trace = []

    for step in range(MAX_STEPS):
        if time.monotonic() - started > MAX_SECONDS:
            return "Timed out.", trace

        r = client.chat.completions.create(
            model=MODEL, messages=messages, tools=SCHEMAS,
            tool_choice="auto", temperature=0)
        msg = r.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content, trace

        for call in msg.tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments)
            except json.JSONDecodeError as e:
                out = f"Error: arguments were not valid JSON ({e})."
            else:
                fn = TOOLS.get(name)
                if fn is None:
                    out = f"Error: no tool named {name!r}. Available: {list(TOOLS)}"
                else:
                    try:
                        out = fn(**args)
                    except TypeError as e:
                        out = f"Error: bad arguments for {name}: {e}"
                    except Exception as e:
                        out = f"Error: {name} failed: {type(e).__name__}: {e}"

            trace.append({"step": step, "tool": name, "args": args, "result": out[:2000]})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": out[:8000]})

    return "Step limit reached without an answer.", trace
```

That runs. It is a real agent.

## What each part is doing

**`tool_choice="auto"`** lets the model choose. `"required"` forces at least one tool call; `{"type":"function","function":{"name":"x"}}` forces a specific one. Forcing is useful for the first step of a workflow where you know a lookup must happen.

**`temperature=0`** because hallucinated arguments are the main failure mode and you do not want to sample into them.

**Multiple tool calls per message.** Modern models emit several in parallel when the calls are independent. The inner loop handles that; running them concurrently is a straightforward optimisation.

**Every error path returns a string to the model**, never raises. This is the most important design decision in the whole file. `"No account with id 'acct_9999'. Use search_accounts to find one."` gets corrected on the next step. An exception ends the run.

**`out[:8000]`** truncates tool output before it enters the context. Without this, one verbose API response destroys the run (Chapter 4).

**The trace list** is separate from `messages` because messages are for the model and the trace is for you. Same events, different consumers, different retention.

## The five things this gets wrong

Each is a later chapter, and knowing what is missing is more valuable than the code itself.

**1. No loop detection.** Nothing stops the model calling `search_docs("refund policy")` five times. Chapter 4.

**2. Context grows unbounded.** Every tool result stays in `messages` forever. At step 8 with three verbose results you are already at thousands of tokens, and cost grows quadratically over the run because the whole history is resent each time. Chapter 6.

**3. No durability.** Process dies at step 5, everything is lost. No pause for human approval is possible. Chapters 8 and 9.

**4. No authorisation.** `get_account` will fetch any account. The permission check belongs in the dispatch path, not in the prompt. Book 05.

**5. No structured trace or cost accounting.** The trace holds strings, not spans, and nothing records tokens or dollars per step. Book 06.

## The parallel-call optimisation

Since independent tool calls arrive together, run them together:

```python
with ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(dispatch, c): c for c in msg.tool_calls}
    results = {futures[f].id: f.result() for f in as_completed(futures)}
for call in msg.tool_calls:                  # preserve order in messages
    messages.append({"role": "tool", "tool_call_id": call.id,
                     "content": results[call.id]})
```

Order matters when appending to `messages` even though execution order does not. Providers vary in strictness about tool result ordering; matching the call order is always safe.

## Streaming with tools

Streaming complicates the loop, because tool call arguments arrive as fragments that must be accumulated per call index before parsing. The pattern: buffer `delta.tool_calls[i].function.arguments` into a per-index string, and only parse when the stream finishes with `finish_reason == "tool_calls"`.

Worth knowing and worth avoiding early. Stream the final answer, not the intermediate steps, unless the product genuinely shows the agent's work.

## The exercise

Type this file out — do not copy it — with two tools of your own over data you have. Then deliberately break it:

- Rename a tool in `TOOLS` but not in `SCHEMAS` and watch what the model does with the error message.
- Remove the `pattern` from `account_id` and see whether it starts inventing ids.
- Make `search_docs` return an empty string instead of `"No results."` and watch the loop degrade.
- Set `MAX_STEPS = 2` and see what the failure looks like from the user's side.

Forty minutes, and it produces genuine intuition about which failures come from the model and which come from your plumbing. That distinction is the thing interviewers are actually probing when they ask about agents.

*Connect the dot:* the third bullet above is the whole of Chapter 3. An unhelpful tool result and an ambiguous tool description cause more agent failures than any model limitation, and both are entirely yours to fix.

Next: designing tools the model can actually use.
