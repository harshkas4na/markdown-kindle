# Designing Tools

**Fast overview:** Most agent failures blamed on the model are tool design failures. The description was ambiguous, the granularity was wrong, the error message was useless, or the output buried the answer in 30,000 tokens of JSON. This chapter treats the toolset as the primary interface you are designing — because it is — and gives the rules that make an agent work with a mediocre model rather than requiring a frontier one.

## The tool description is the most important text in your system

More important than the system prompt. The description is what the model uses to decide *whether* and *when* to call the tool, and it is read in competition with every other tool's description.

**Write it for a competent new colleague who has never seen your system.** Include:

- **What it does**, in one sentence.
- **When to use it**, and — this is the part everyone omits — **when not to**.
- **What it returns**, in shape and detail.
- **Constraints and gotchas**: id formats, whether it is expensive, whether it writes anything.

```python
# Bad
"description": "Gets user data"

# Good
"description": (
    "Fetch one user's profile and subscription state by exact user id "
    "(format: usr_XXXXXXXX). Returns email, plan, status, and signup date. "
    "Read-only and fast. Use this when you already have a user id. "
    "To find a user by name or email, use search_users instead — this tool "
    "will fail on anything that is not an exact id, and you must never guess an id.")
```

The differences that matter: the id format is stated so the model produces the right shape; the alternative tool is named, which is what prevents misuse; and "never guess an id" addresses the specific hallucination this tool invites.

**Test descriptions the way you test prompts.** They are prompts. When an agent picks the wrong tool, the first fix is not a system-prompt instruction — it is disambiguating the two descriptions.

## Granularity

The single hardest design judgement, and there is a genuine trade-off:

**Too fine-grained** — twenty tools like `get_user_email`, `get_user_plan`, `get_user_status` — costs schema tokens on every call, floods the model's choice space, and turns one logical operation into six steps with six chances to go wrong.

**Too coarse** — one `do_everything(action, params)` tool — moves the real decision into a free-form parameter the model gets wrong, and destroys your ability to authorise, validate or rate-limit per operation. It is the tool-design equivalent of a single endpoint that takes a SQL string.

**The heuristics:**

- **One tool per user-meaningful operation.** `refund_order` is a thing a person does; `set_order_field` is not.
- **Aim for five to fifteen tools per agent.** Past twenty, selection accuracy degrades noticeably. If you need more, split into sub-agents by domain (Chapter 10) or gate tools by state (below).
- **Separate reads from writes** as distinct tools, always, even when the underlying API is one endpoint. This makes authorisation and approval policies expressible in terms of the tool name.
- **Bundle what is always done together.** If the model must call `find_order` then `get_order_lines` every time, make one tool.

**State-gated toolsets** are the underused answer to tool sprawl: expose only the tools that are legal in the current stage. During intake, the refund tool does not exist. This shrinks the choice space, and it is also a guardrail that the model cannot argue its way past.

## Parameters

Everything from Book 01's structured-output chapter applies, because a tool call *is* structured output.

- **Descriptive names.** `start_date_iso` beats `d1`.
- **Descriptions on every parameter**, including the format.
- **Enums for closed sets.** `status: Literal["open","closed","pending"]` cannot be `"Open "`.
- **Constraints in the schema** — `pattern`, `minimum`, `maximum`, `maxItems`. Under strict/constrained modes these are enforced at the sampler, and even without it they instruct.
- **Defaults for optional parameters**, so the model does not have to decide.
- **`additionalProperties: false`** so invented parameters are rejected loudly.
- **Few parameters.** Every one is a chance to be wrong. If you have nine, the tool is probably two tools.

**Avoid free-form structured strings.** A parameter that takes SQL, or a JSON blob, or a path expression, moves the hard decision into a place you cannot validate. Enumerate the operations instead. This is the same argument as the curated-query approach to text-to-SQL in Book 02, Chapter 12.

## Return values

The tool result goes straight into the context, so its design is a context-budget decision.

**Return text the model can read, not raw API JSON.** A REST response with forty fields, nested envelopes and hypermedia links is mostly tokens with no information. Project it:

```python
def get_order(order_id: str) -> str:
    o = api.orders.get(order_id)
    return (f"Order {o.id}: {o.status}, placed {o.created:%Y-%m-%d}, "
            f"total {o.total_cents/100:.2f} {o.currency}, "
            f"{len(o.lines)} line items, customer {o.customer_id}. "
            f"Refundable: {'yes' if o.refundable else 'no'}.")
```

Forty tokens instead of eight hundred, and the model reads it better.

**Truncate, and say that you did.** Never silently. `"...(showing 5 of 137 results; refine the query or ask for a specific page)"` tells the model both that there is more and how to get it.

**Include ids the model will need next.** If the next step requires an order id, return the ids. If it does not need them, leave them out — they are expensive tokens with no meaning.

**Make the units and format unambiguous.** `total_cents` not `total`. ISO dates, always. This is where quiet, expensive errors come from.

## Errors are the model's input, not your exception

The rule from Chapter 2, stated fully because it is worth the space.

A tool failure should return a message that tells the model **what went wrong** and **what to do about it**:

```python
# useless
raise ValueError("invalid date")

# useful
return ("Error: start_date must be ISO format YYYY-MM-DD; you sent 'next Tuesday'. "
        "Resolve relative dates yourself before calling this tool. Today is 2026-08-03.")
```

The taxonomy of tool errors and the right response to each:

| Error | Return to the model | Also do |
|---|---|---|
| Bad arguments | Exactly what was wrong and the correct format | Count it as a metric |
| Not found | That it was not found, and which tool finds things | |
| Permission denied | That it is not permitted **without** revealing what exists | Alert; this may be an attack |
| Transient (timeout, 503) | Only after your retries failed, and say it was transient | Retry in code first, invisibly |
| Rate limited | That it is rate limited and to try a different approach | Back off in code |
| Genuine bug | A generic failure message, no stack trace | Alert, log fully |

Two rules underneath: **retry transient failures in your code**, not by asking the model to try again, because the model will change something else while retrying. And **never leak internals** into the model's context, both because stack traces are tokens and because they end up in outputs.

## Idempotency and side effects

Agents retry. Networks fail after the write succeeds. A model calls the same tool twice because the first result looked ambiguous.

Every mutating tool should therefore take an **idempotency key** and be safe to call twice:

```python
def refund_order(order_id: str, amount_cents: int, idempotency_key: str) -> str:
    if prior := refunds.get(idempotency_key):
        return f"Already refunded (idempotency key seen): refund {prior.id}."
    ...
```

This is ordinary payments engineering, and it is exactly the discipline that transfers from smart-contract work, where a replayed transaction is a standing threat rather than an edge case. Saying so is a strong, specific answer to "how does your background apply here".

## Latency

Every tool call is a round trip inside a loop, so a 2-second tool in a 6-step run is 12 seconds. Budget tools like anything else: cache read-heavy tools, batch where the schema allows (`get_orders(ids: list[str])` beats six calls), and for genuinely slow operations return a handle immediately and let the model poll or let the run suspend (Chapter 9).

## The tool eval

Tools deserve their own tests, separate from the agent:

- **Selection accuracy.** Given a task, does the model pick the right tool? Twenty tasks, check the first tool call. This isolates description quality from everything else.
- **Argument accuracy.** Are the arguments valid and correct? Schema violation rate is a cheap, deterministic metric.
- **Error recovery.** Force each error path and check the agent recovers rather than looping or giving up.
- **Unit tests on the tool functions themselves.** They are ordinary code and they mostly are not tested, because they live in a file called `tools.py` that feels like configuration.

*Connect the dot:* selection accuracy is the cheapest agent metric there is and the most diagnostic. When an agent underperforms, measuring it first tells you whether you have a description problem or a reasoning problem, which is the same "localise before you tune" discipline as splitting retrieval from generation in Book 02.

Next: the loop's controls, and how to stop an agent that will not stop.
