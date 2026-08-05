# The Harness and the Regression Gate

**Fast overview:** The dataset and the scorers are the substance; the harness is what makes them run on every change instead of once. This chapter builds it: the runner, the config hash that makes a result reproducible, artifact storage, the CI integration, and the gate design that catches regressions without becoming the alarm everyone mutes.

## What the harness is

Four responsibilities, and it is worth keeping them separate in the code:

1. **Load** a versioned dataset.
2. **Run** each example against a versioned configuration, in parallel, capturing everything.
3. **Score** with the scorer stack.
4. **Report** aggregate and per-slice, with deltas against a baseline, and **decide** pass or fail.

## The runner

```python
@dataclass(frozen=True)
class Config:
    model: str
    prompt_version: str
    temperature: float
    retrieval: dict          # k, reranker, chunk size, embed model
    judge_model: str
    judge_prompt_version: str

    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:12]

@dataclass
class RunResult:
    example_id: str
    output: str
    scores: dict[str, float | bool]
    slices: list[str]
    latency_ms: float
    cost_usd: float
    artifacts: dict          # retrieved ids, resolved prompt, trace, judge reasoning
    error: str | None = None

def run_eval(dataset, pipeline, cfg: Config, workers=8) -> Run:
    run_id = f"{dt.datetime.utcnow():%Y%m%dT%H%M%S}-{cfg.hash()}"
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(lambda e: run_one(e, pipeline, cfg), dataset.examples))
    run = Run(run_id=run_id, config=cfg, dataset_version=dataset.version,
              git_sha=git_sha(), results=results, started=..., finished=...)
    store.save(run)          # every artifact, not just the numbers
    return run
```

The details that make it usable six months later:

**The config hash.** Without it you cannot answer "what produced this number", and every historical result becomes uninterpretable. Include the judge version — a judge change silently redefines the metric.

**The dataset version and the git SHA.** Three things determine a result: code, config, data. Record all three.

**Save every artifact, not just scores.** The resolved prompt, the retrieved chunk ids, the agent trace, the judge's reasoning. When a slice regresses you need to *look* at what happened, and re-running is both expensive and non-deterministic.

**Parallelism, with a token-aware rate limiter.** A 300-example eval serially at 2s each is ten minutes, and an eval that takes ten minutes stops being run on every change. At 8 workers it is 75 seconds. Speed is a correctness property here, because it determines whether the thing is used.

**Errors are results, not crashes.** One example that throws should not lose the run. Record the error, count it, and report the error rate as its own metric.

## Caching

Evals are re-run constantly, and most re-runs change one thing. Cache aggressively, keyed by content:

```python
key = sha256(f"{cfg.hash()}|{example.id}|{dataset.version}")
```

A prompt change invalidates the generation cache but should not invalidate **judge** results for unchanged outputs, so key judge results separately by `(judge_version, input, output)`. On a typical iteration this cuts eval cost by most of it.

## The gate

```python
def gate(run: Run, baseline: Run, policy: dict) -> Verdict:
    failures = []
    for name, rule in policy["slices"].items():
        cur  = run.score(name)
        base = baseline.score(name)
        if cur.n < rule.get("min_n", 15):
            continue                                   # too small to judge
        if "min" in rule and cur.mean < rule["min"]:
            failures.append(f"{name}: {cur.mean:.3f} below floor {rule['min']}")
        if "max_drop" in rule and (base.mean - cur.mean) > rule["max_drop"]:
            failures.append(f"{name}: dropped {base.mean - cur.mean:.3f} "
                            f"(limit {rule['max_drop']})")
    for name, rule in policy.get("budgets", {}).items():
        if run.metric(name) > rule:
            failures.append(f"{name}: {run.metric(name)} exceeds {rule}")
    return Verdict(ok=not failures, failures=failures)
```

**Two kinds of threshold, and you want both:**

- **Absolute floors** stop the system shipping below a known-acceptable bar, and they are what protects you when the baseline itself has drifted downward over many small "acceptable" drops.
- **Relative drops** catch the change that is still above the floor and is nonetheless a regression.

**Budgets belong in the gate too.** Cost per example and p95 latency are gate-able, and putting them there is what stops quality improvements silently tripling the bill.

**The `min_n` guard** is what stops small slices generating noise alarms. A slice below the threshold is reported and not gated.

## CI integration

```yaml
on:
  pull_request:
    paths: ['prompts/**', 'src/retrieval/**', 'src/agent/**', 'evals/**', 'config/**']

jobs:
  eval:
    steps:
      - run: python -m evals.run --dataset golden_v9 --config config/prod.yaml
      - run: python -m evals.gate --baseline-ref origin/main --policy evals/policy.yaml
      - uses: actions/upload-artifact@v4          # the full run, always
      - run: python -m evals.comment              # post the slice table on the PR
```

Design points:

**Trigger on the paths that matter.** Prompts, retrieval code, agent code, config, and the eval set itself. Not every commit — a README change should not spend $3.

**Post the slice table as a PR comment.** This is the highest-leverage piece of the whole setup: the reviewer sees the per-slice deltas and the newly-failing example ids inline, which turns "looks fine" into an actual review of the change's behaviour.

**Upload the artifacts every time**, including on pass. When something is discovered two weeks later, you want the run.

**Keep the fast tier separate.** Level 0-2 scorers over the whole set run in seconds and cost nothing; run those on every commit. The judge tier runs on PRs. A nightly full run against the larger set catches drift.

## Baselines

What do you compare against? Three options, and a good setup has all three:

- **The current `main`.** The default for a PR. Answers "does this change make things worse".
- **A pinned reference run.** Answers "how far have we come" and catches slow multi-PR decay that pairwise-with-main never notices. Each individual PR drops 0.5 points within tolerance; twenty PRs later you are 10 points down and nothing ever went red.
- **A trivial baseline.** No retrieval, or a fixed canned answer, or the smallest model. Answers "is the complexity earning anything" — a genuinely useful and rarely-run comparison.

The pinned-reference check is the one that catches the failure mode nobody plans for. Run it weekly.

## Cost control

A 300-example eval with judges is real money per run, and CI runs a lot.

- **Tier it.** Deterministic scorers on every commit; judges on PR; full set nightly.
- **Sample for the fast tier.** 60 stratified examples across slices for the quick check, full set before merge.
- **Cache judge results** as above.
- **Cap eval spend** and alert on it. An eval harness that quietly costs more than the product is a real thing that happens.

## The thing that makes it stick

An eval harness dies when it becomes slow, noisy or ignored. The three properties that keep it alive:

1. **Fast enough to run on every change** (under two minutes for the PR tier).
2. **Quiet enough that red means something.** If it is red half the time, it is decoration.
3. **Visible in the workflow**, as a PR comment, not on a dashboard someone has to remember to open.

Those are engineering-culture properties rather than statistical ones, and they are what determine whether the harness is still in use in six months. Saying that in an interview signals that you have thought about the failure mode of the *process*, not just the code.

*Connect the dot:* the config hash, the artifact store keyed by run id, and the append-only run history are the same design as `lifelog` — content-addressed, immutable, replayable. Once the runs are immutable and identified, "why did this number change" is answerable by diffing two runs rather than by memory.

Next: applying all of this to a RAG system.
