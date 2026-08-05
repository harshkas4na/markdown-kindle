# Prompting as Engineering

**Fast overview:** Prompt engineering has a bad reputation because most of what is written about it is folklore — tricks, magic phrases, and advice that stopped being true two model generations ago. The engineering version is different and duller: a prompt is a production artifact that determines system behaviour, so it gets versioned, reviewed, tested and traced like any other. This chapter covers the techniques that survive scrutiny, the ones that do not, and the infrastructure that turns prompting from a craft into a process.

## The techniques that reliably work

**Be specific about the task, the format and the audience.** Most prompt failures are underspecification. "Summarise this" leaves length, register, audience and what to prioritise unstated, and the model picks. Every unstated decision is a decision the model makes differently on different inputs, which shows up as inconsistency you will later blame on the model.

**Show, do not describe.** Two or three examples in the exact target format beat a paragraph describing the format. Choose examples that cover the *boundaries* of the task, not three variations of the easy case — including one hard or ambiguous example handled correctly is worth more than five clean ones. And keep examples in the same distribution as real input; a few-shot example written in tidier language than your actual users produce will teach the model the wrong input shape.

**Give the model room to reason before it commits.** "Think step by step before answering" is not a magic phrase, it is a request for computation. The model has no scratchpad other than its output tokens, so denying it tokens denies it thinking. This is the mechanism, and knowing the mechanism tells you when it applies: multi-step reasoning, yes; sentiment classification, no, where it just adds latency and cost. On reasoning-trained models it is often redundant or harmful, because the model already does it and instructing it again can disrupt the trained behaviour.

**Put long context before the instruction, and restate the instruction after it.** Straight from the lost-in-the-middle behaviour in Chapter 3. Documents first, task last, and a one-line restatement at the very end is cheap.

**State the failure behaviour explicitly.** "If the context does not contain the answer, reply exactly: NOT_FOUND." Without a legal way to fail, the model will produce something, because producing something is what it was trained to do. Almost every hallucination complaint in a RAG system is partly a missing escape hatch.

**Use delimiters.** XML-ish tags (`<document>`, `<user_query>`) or markdown headers separate instructions from data, which both improves comprehension and is the first line of defence against injection (Book 05). Models are trained on a lot of tagged text and handle it well.

**Assign the persona only when it changes the task.** "You are a compliance analyst reviewing contracts for indemnity clauses" is useful, because it narrows the vocabulary and the priorities. "You are a world-class expert" is noise.

## The techniques that do not work

Worth knowing so you do not cargo-cult them, and worth being able to say out loud because it signals you have actually tested things:

- **Politeness, tipping, threats, emotional appeals.** Studies of these have produced small, inconsistent, model-specific effects that vanish on replication. Do not build on them.
- **"You are the world's leading expert."** No measurable effect on capability in most evaluations. The model does not have a hidden competence setting.
- **ALL CAPS AND EXCLAMATION MARKS.** Some marginal emphasis effect, and mostly it is a sign that the instruction is buried and should be restructured instead.
- **More words.** The most common failure of intermediate prompt writers. Prompts accrete instructions over months, and every addition dilutes attention and costs money. **Deleting from a prompt improves it more often than people expect** — but only if you have an eval to prove it, which is precisely why they never delete.
- **Instructions the model cannot follow.** "Do not hallucinate", "always be accurate", "never make mistakes". These are goals, not instructions. Replace each with a mechanism: retrieval for accuracy, an escape hatch for uncertainty, a validator for format.
- **Negative instructions in general.** "Do not mention pricing" works less reliably than "Discuss only features listed in the context." State what to do.

## The infrastructure

This is the part that separates an AI engineer from someone who is good at chatting with a model.

### 1. Prompts live in version control, with an identity

Not in a Notion page, not inline in a 400-line f-string, not in a database row edited through an admin panel with no history. A file, in the repo, in code review, with a version identifier:

```
prompts/
  extract_invoice/
    v3.md          # current
    v2.md          # kept, because traces reference it
    meta.yaml      # model, temperature, schema, owner, changelog
```

The version identifier goes into every trace. Six weeks from now, "quality dropped on the 14th" becomes a two-minute question instead of an archaeology project.

### 2. Every prompt has an eval set before it has a second version

The rule is simple and almost universally violated: **you may not edit a prompt that has no eval.** Without one, every change is a vibe, and vibes cannot detect the change that fixed your bug and broke three other cases. Book 04 is entirely about this.

### 3. Templating is explicit and injection-aware

```python
from jinja2 import Template

TEMPLATE = Template("""You answer questions using only the documents provided.
If the documents do not contain the answer, reply exactly: NOT_FOUND

<documents>
{% for d in documents %}
<document id="{{ d.id }}" source="{{ d.source }}">
{{ d.text }}
</document>
{% endfor %}
</documents>

<question>{{ question }}</question>

Answer the question using only the documents above. Cite document ids you used.""")
```

Notice: user content and retrieved content are inside tagged regions; the instruction appears before and after the data; there is an explicit failure token; and citation is requested, which makes the answer checkable. Every one of those is a deliberate decision from an earlier section.

### 4. Prompts are tested like code

Three tiers, cheapest first:

- **Assertions** — the output contains no forbidden strings, parses as the schema, is under N tokens, cites at least one document. Fast, deterministic, catches the dumb regressions. (JobOps already has an instance of this idea in its banned-word list.)
- **Golden-set scoring** — the real eval, Book 04.
- **Adversarial cases** — injection attempts, empty context, contradictory documents, an out-of-scope question. These belong in the suite permanently, and each production incident adds one.

### 5. A/B in production, not just offline

Offline evals catch regressions on cases you thought of. Online tests catch everything else. Route a percentage of traffic to the new prompt version, compare on the metric you actually care about, and be honest that most product metrics are noisy enough to need real volume (Book 06).

## Prompt chaining, and when to stop

Splitting a task into several calls — extract, then classify, then draft — usually beats one giant prompt, for reasons that are structural rather than mystical: each call has a narrow task and a small output space, each is separately testable, each can use a different model tier, and a failure is localised to a stage instead of smeared across one opaque response. REACTOR's pipeline was this shape, and the fact that its failure could not be localised to a stage is exactly the lesson.

The costs are real too: more calls means more latency and more places to fail, and errors compound — three stages at 95% each is 86% end to end. So the stopping rule is: **chain when the stages have genuinely different jobs, and merge when a stage exists only because the prompt felt long.**

## The meta-technique: have the model write the prompt

Underused and legitimate. Give a capable model your task description, five example inputs and their correct outputs, and ask it to write a prompt. Then evaluate that prompt against your golden set alongside your hand-written one. It frequently wins, and when it does not, the diff between the two tells you something about the task.

The industrial version of this is automated prompt optimisation (DSPy and similar), which treats the prompt as parameters to be optimised against a metric. It only works if you have a metric, which is one more argument for building the eval first.

*Connect the dot:* every piece of infrastructure in this chapter is a prerequisite for Book 04. A prompt without a version cannot be evaluated, because you cannot say which prompt produced which result.

Next: the arithmetic. What things actually cost, and where the time actually goes.
