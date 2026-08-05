# Structured Output

**Fast overview:** The moment an LLM stops talking to a human and starts talking to your code, it has to emit something parseable. Asking nicely produces valid JSON most of the time, and "most of the time" at 100,000 requests a day is a pager at 3am. This chapter covers the four mechanisms for enforcing structure, ranked by strength, what constrained decoding actually does at the sampler, why a well-typed answer can still be wrong, and how to design schemas that make the model's job easier rather than harder.

## The four mechanisms, weakest to strongest

### 1. Prompting and few-shot

"Respond only with JSON matching this shape." Works surprisingly well with capable models and fails in a long tail of specific ways: a markdown code fence around the JSON, a preamble ("Here's the JSON you requested:"), a trailing explanation, single quotes, a trailing comma, an unescaped quote inside a string, or a truncated object because the output hit the token limit mid-structure.

Two or three examples in the exact target format help more than any amount of describing the format in prose. This is the general rule for prompting and it is strongest here.

Use this alone only for prototypes.

### 2. JSON mode

A provider flag that guarantees syntactically valid JSON. Useful and incomplete: you get *valid JSON*, not JSON matching *your schema*. The model can return `{"result": "I don't know"}` when you expected five specific fields, and that parses fine and then explodes two functions later.

### 3. Tool calling / function calling with a schema

You pass a JSON Schema describing a function; the model returns a structured call with arguments. Providers train specifically for this, so it is reliable, and — the underrated part — it is often *better quality* than free-form JSON, because the model has seen enormous amounts of training data in this exact shape.

The trick worth knowing: even when there is no actual tool to call, defining a "tool" whose sole purpose is to receive your extracted data is a well-established way to get schema-conformant structured output. `extract_invoice(vendor, date, total, line_items)` is a fine "tool" that just returns its arguments to you.

### 4. Constrained decoding

The strongest mechanism, and the one worth being able to explain. At every generation step, the sampler consults a state machine derived from your schema (or an arbitrary context-free grammar) and **masks the logits of every token that would produce an invalid continuation** by setting them to negative infinity before softmax. Invalid tokens cannot be sampled because they are not in the distribution.

The output is guaranteed to conform. Not usually — always. Libraries in this space (Outlines, XGrammar, llguidance, and the equivalents built into vLLM and the major providers' "strict" structured-output modes) all implement variants of this.

Three things to know about the costs:

- **Schema compilation is not free.** Building the automaton for a complex schema takes time; cache it per schema rather than rebuilding per request.
- **Not every JSON Schema feature is supported.** Regex patterns, recursive definitions, and some `oneOf`/`anyOf` constructs are commonly restricted in strict modes. Read the provider's supported subset.
- **Over-constraining can degrade quality.** If the model fundamentally misread the task, forcing it down a grammar path produces confidently structured nonsense. Constraint fixes the *format* failure mode and can mask the *comprehension* failure mode, which is worse because it looks healthy.

## The rule regardless of mechanism: validate at the boundary

```python
from pydantic import BaseModel, Field, ValidationError
from typing import Literal

class Extraction(BaseModel):
    vendor: str
    total_cents: int = Field(ge=0)
    currency: Literal["USD", "EUR", "INR"]
    confidence: float = Field(ge=0, le=1)

def extract(text: str) -> Extraction | None:
    raw = call_model(text, schema=Extraction.model_json_schema())
    try:
        return Extraction.model_validate_json(raw)
    except ValidationError as e:
        log.warning("schema_violation", error=str(e), raw=raw[:500])
        return repair(raw, e)      # one retry with the error fed back
```

Points to notice, because each is a real lesson:

- **Validation happens even under constrained decoding.** Defence in depth costs microseconds; a provider flag silently not applying costs an incident.
- **Constraints live in the type**, not in the prompt. `ge=0`, `le=1` and `Literal` are enforced by code, and every constraint you can move from prose into a type is one fewer thing to hope for.
- **The repair path feeds the validation error back to the model.** One retry with "your output failed validation with this error, fix it" resolves the large majority of remaining failures. Cap it at one retry; a second rarely helps and doubles your tail latency.
- **The raw output is logged on failure**, truncated. Without this you cannot debug schema violations after the fact, and schema violations are exactly the class of bug that only appears in production data.

## Designing schemas the model can actually fill

The schema is part of the prompt. Design consequences:

**Use descriptive field names.** `total_amount_in_cents` outperforms `amt`. The name is the instruction.

**Use `description` on every field.** In JSON Schema, `description` is passed to the model and read. This is where you put the disambiguation that would otherwise clutter your prompt.

**Prefer flat over deeply nested.** Every level of nesting is more structure to keep track of and more places to lose the thread. Three levels is a lot.

**Use enums instead of free strings** wherever the value space is closed. `Literal["approved","rejected","needs_review"]` cannot be `"Approved."` or `"approve"`.

**Give the model an escape hatch.** If every field is required and the document does not contain the vendor, the model will invent one — it has no legal way to say "not present". Make fields optional, or add an explicit `not_found` variant. **This single change removes a large category of hallucination**, and it is a genuinely good thing to say in an interview because it reframes hallucination as a schema design problem rather than a model problem.

**Put reasoning fields first.** Because generation is autoregressive, a field emitted earlier conditions everything after it. A schema of `{reasoning, answer}` gives the model tokens to think in before committing; `{answer, reasoning}` produces a guess followed by a post-hoc justification of the guess. **Field order in your schema is a real quality lever**, and it surprises people who have not thought about autoregression.

**Ask for confidence carefully.** Self-reported confidence from an LLM is poorly calibrated — it is a token like any other, not an inspection of the model's internal state. It has *some* signal and should never be treated as a probability. Sample agreement (Chapter 4) is a better uncertainty estimate.

## Streaming structured output

Streaming and structure fight each other: you cannot parse JSON until it is complete. Options, all imperfect:

- **Do not stream structured responses.** Simplest and usually correct. Structured extraction is machine-to-machine; nobody is watching it arrive.
- **Partial parsing.** Libraries that parse incomplete JSON by closing open structures let you render fields as they arrive. Good for a UI filling in progressively.
- **Split the response.** Stream the human-facing prose from one call, and make a separate constrained call for the structured part. Two calls, clean semantics, and often the right answer in a product.

## When not to force structure

Structure has a cost, and it is worth being able to argue the other side. If the task is genuinely open-ended, forcing a rigid schema can hurt. And if you find yourself writing a schema with fifteen optional fields where the model fills in two, the schema is doing classification work that a simpler two-step pipeline (classify, then extract with the schema for that class) would do better.

The general principle: **structure the output as tightly as the task genuinely allows, and no tighter.**

*Connect the dot:* tool calling in Book 03 is this chapter applied to actions rather than data, and every argument in that chapter about tool schema design is the schema-design section above with consequences attached.

Next: prompting, treated as an engineering discipline with version control and tests rather than as folklore.
