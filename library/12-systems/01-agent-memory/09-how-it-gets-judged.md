# How It Gets Judged

**Fast overview:** Every system like this is easy to build and easy to keep building. The hard part is agreeing, before any of it exists, on the number that would prove it was not worth it. This chapter is that number, the honest list of ways it could still fail, and what it cost.

## The measurement, agreed in advance

> **After three weeks in one repo: what fraction of digest lines were confirmed or acted on, versus ignored?**

Confirmation and refutation are both explicit commands, which makes this countable rather than a feeling. The baseline was captured before the first memory was written: 246 of 246 sessions had left nothing behind, 90 of those hours in one repo.

If the number stays near zero, **the digest is noise**. The response is to shrink it or tighten the admission rule, not to add features. That commitment is written into the system's own documentation, where the next session will read it, because the failure mode of this kind of project is a slow accumulation of capability that nobody uses and nobody is willing to delete.

## Rolled out to exactly one repo

The trial runs in `builder-ops` alone for two weeks.

The reasoning is simple: a bad digest wired into twelve repos at once is twelve polluted sessions and no way to work out which rule was wrong. And `builder-ops` is the repo where a wrong memory does the least damage and where the payoff is most visible, since the promotion feed lands there anyway.

## What could still go wrong

**The write side never gets used.** This is by far the biggest risk and it is the one the built-in memory directory already lost to. Everything downstream is worthless if sessions do not write. The floor helps by guaranteeing coverage data exists regardless, and the digest naming silent sessions makes the gap visible rather than invisible, but neither of those actually writes a memory. That still takes a session choosing to.

**The digest becomes wallpaper.** Injected context that is always slightly useful and never decisive gets skimmed and then ignored. The 35-line budget and the ranking are defences against this, but the real defence is the admission rule staying harsh.

**Client material leaks through mining.** The path-based guard is a floor and there is a known gap above it, documented in an earlier chapter. This one relies on a human rule and it is the sharpest residual risk in the system.

**It becomes a junk drawer.** The graduation path is the defence: a memory confirmed enough times leaves the store and becomes a rule in the contract. If that path is never exercised, the store only grows.

## What it cost

Three days of work by the original estimate, delivered in one long session across five phases, each independently useful:

- the store, the object model and the CLI
- the digest and its three guards
- deterministic session capture, coverage, and a nightly schedule
- transcript mining and reviewed backfill
- promotion, and the feed into the findings register

Fifty-three tests, all covering invariants that would corrupt the read path *silently* rather than crash: a duplicate that inflates the ranking signal, a fork in the checkpoint chain, a client entry that lost its marking, a decayed open loop still being served as current. The cosmetics are untested on purpose. A misaligned column announces itself; a memory that quietly stopped being true does not.

Zero dependencies, in a portfolio where that is a standing rule. A memory system that needs a package install before it can answer a question is a memory system that gets skipped, and a two-year-old repo should still answer without a lockfile that no longer resolves.

The running cost is close to zero by design, which is the number that actually kills systems like this. It is written by sessions and read by sessions. There is nothing to open, nothing to maintain, and no daily attention competing with the eleven other pipelines that already have some.

## The last word

The strongest argument for the whole thing is still the first table in this book, and it is worth restating with what is now known about it.

Two hundred and forty-six sessions. Ninety hours in one repo alone. Nothing kept.

Not because anything was broken, and not because nobody cared. Because there was nowhere to put it, and no habit of putting it there, and no way to find out that either of those was true.

The store does not fix that on its own. What it does is make the gap **countable**, which is the only thing that has ever made a habit stick.
