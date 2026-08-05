# Scorers, Deterministic First

**Fast overview:** A scorer turns an output into a number. The instinct in this field is to reach immediately for an LLM judge, and that instinct is wrong: judges are slow, expensive, non-deterministic and themselves unvalidated. This chapter covers the deterministic scorers that should run first, why they catch more than people expect, the text-similarity metrics that mislead, and how to build a scoring stack that only escalates to a judge where it genuinely has to.

## The hierarchy

Cheapest and most reliable first. Run every level; escalate only when the level above cannot answer.

| Level | Scorer | Cost | Determinism |
|---|---|---|---|
| 0 | Structural assertions | Microseconds | Total |
| 1 | Exact / contains / regex | Microseconds | Total |
| 2 | Programmatic checks (does it run, does it resolve) | Milliseconds | Total |
| 3 | Similarity metrics | Milliseconds | Total |
| 4 | LLM-as-judge | ~1s, $ | None |
| 5 | Human | Minutes, $$$ | Approximately |

**The rule: never use level 4 for something level 0-2 can answer.** A schema violation does not need a judge's opinion.

## Level 0 — structural assertions

Free, deterministic, and they catch the failures that actually break your product:

```python
def structural(output, example) -> dict:
    return {
        "parses":        parses_as(output, example.schema),
        "under_budget":  count_tokens(output) <= example.max_tokens,
        "no_banned":     not any(w in output.lower() for w in BANNED),
        "cites":         bool(re.findall(r"\[S\d+\]", output)) or "NOT_FOUND" in output,
        "citations_resolve": all(int(i) <= len(example.sources)
                                 for i in re.findall(r"\[S(\d+)\]", output)),
        "no_pii_leak":   not PII_RE.search(output),
    }
```

Every one is a real production failure mode and none needs a model. JobOps already runs a version of this: the banned-word list (`leverage`, `passionate`, `thrilled`, `seamless`) and the em-dash ban are exactly level-0 assertions on generated text, enforced in the pipeline rather than requested in a prompt.

Note `citations_resolve` in particular. A model citing `[S7]` when only five sources were provided is a detectable hallucination, caught by a regex, at zero cost.

## Level 1 — exact, contains, regex

**Exact match** is correct for classification, extraction of a canonical value, routing decisions, and structured field comparison. It is wrong for anything prose-shaped, where it will report failure for a perfect answer phrased differently.

**Contains / must-not-contain** is the underrated workhorse. `must_contain: ["30 days"]` verifies the one fact that matters without constraining the wording. `must_not_contain: ["yes"]` catches a refusal that failed to refuse. Cheap, precise, and easy for a domain expert to write, which matters because they are the ones labelling.

**Regex** for formats: dates, ids, currency, phone numbers.

The failure mode of all three is brittleness — `"30 days"` fails on `"thirty days"`. Mitigate by normalising before comparison, allowing alternatives (`any_of: ["30 days", "thirty days"]`), and reserving them for facts whose form is genuinely fixed.

## Level 2 — programmatic checks

The strongest scorers available, and available more often than people think, because they check *the world* rather than the text:

- **Does the generated code run, and do the tests pass?** Binary, objective, uncheatable.
- **Does the generated SQL execute, and return the expected rows?**
- **Does the extracted entity exist in the database?**
- **Did the agent's claimed action actually happen?** (Book 03's silent-success detector.)
- **Is the generated JSON valid against the real downstream consumer?**

Whenever you can convert a quality question into a "does it work" question, do. This is the same move as generate-and-verify in Book 03, Chapter 5, and it is why coding tasks are the easiest LLM domain to evaluate rigorously and the one where progress is most credible.

## Level 3 — similarity metrics, and their traps

**BLEU / ROUGE.** N-gram overlap with a reference. Built for translation and summarisation, and they correlate poorly with quality for open-ended generation: a correct answer with different words scores badly, and a fluent wrong answer that reuses reference vocabulary scores well. **Do not use them as a primary quality metric for LLM output.** Knowing why they are inappropriate is a better answer than using them.

**Embedding similarity (BERTScore and relatives).** Cosine between the output's and reference's embeddings. Better than n-gram overlap for paraphrase, and it inherits every embedding weakness from Book 01: negation is nearly invisible, so "the refund window is 30 days" and "the refund window is not 30 days" score close to identical. Dangerous as a correctness metric for exactly the statements that matter.

**Where similarity metrics are legitimately useful:** as a *change detector* rather than a quality score. "This prompt change altered 40% of outputs substantially" is real information, and it tells you where to look, without claiming the changes were bad.

## The stack

```python
def score(example, output) -> Score:
    s = Score()
    s.update(structural(output, example))
    if not s["parses"]:
        return s.fail("unparseable")           # stop; nothing else is meaningful

    s.update(assertions(output, example))      # contains / must-not / regex
    if example.programmatic:
        s.update(run_programmatic(output, example))

    if example.needs_judge and s.passed_hard_checks:
        s.update(judge(example, output))       # only now, and only if warranted
    return s
```

Two design points worth stating:

**Short-circuit on hard failures.** An unparseable output does not need a quality score, and judging it wastes a call and pollutes the average with a number that means nothing.

**Only some examples need a judge.** In a well-built set, half the examples are checkable deterministically. Marking `needs_judge` per example cuts eval cost and runtime substantially, which matters because an eval that takes twenty minutes stops being run on every change.

## Aggregating

- **Report each scorer separately.** A single blended "quality score" hides which dimension moved and is the second most common way an eval suite lies. Faithfulness and conciseness are different things and a change can trade one for the other.
- **Use pass/fail for hard requirements**, means for graded ones. "94% parse" and "mean faithfulness 0.87" are both useful; "mean quality 0.91" is not.
- **Always report the failure list**, not just the number. The number tells you something changed; the list tells you what.
- **Report cost and latency alongside quality**, always. A configuration that is two points better and 3x the price is a decision, not an improvement, and separating them lets someone make it.

## Weighting

Not all examples matter equally. A safety-critical refusal case failing is worse than a stylistic miss. Two ways to express this:

- **Weight examples** in the aggregate. Simple, and it obscures what happened.
- **Gate categories separately.** "Refusal cases must be 100%; quality cases must average above 0.85." Clearer, and it maps to how people actually reason about risk.

Prefer the second. A hard requirement should be a hard gate, not a heavy weight that a good average can outvote.

*Connect the dot:* levels 0-2 are ordinary software testing applied to a probabilistic system, and they are where a strong backend engineer has an immediate advantage. Most of what makes an eval harness good is not AI-specific; it is dataset hygiene, deterministic assertions, CI integration and honest reporting.

Next: LLM-as-judge, for the cases that genuinely need one.
