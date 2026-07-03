# Research Pack: What To Build Next (July 2026)

**The question this folder answers:** *"What is Uniswap struggling with that nobody has solved with a hook — and who would actually use the solution?"*

Everything here was researched from live 2025–2026 sources (news, whitepapers, protocol blogs, post-mortems) and cross-checked against your `hook-directory/` folder (556 past UHI hooks) so the ideas are genuinely new, not repeats of what previous cohorts built. Written in plain language — every term is explained or points to your `learn/` folder.

## Read in this order

| File | What it gives you | Time |
|---|---|---|
| `01-uniswap-unsolved-problems-2026.md` | The 8 real problems Uniswap has **right now**, why 556 hooks didn't fix them, and who the users would be | ~15 min |
| `02-new-whitepapers-explained-simply.md` | The 9 research ideas everyone's talking about (Orbital, MEV taxes, pm-AMM, am-AMM, EulerSwap, Doppler, Angstrom…), each explained simply | ~15 min |
| `03-defi-trends-2026.md` | Where DeFi's money and attention actually are in 2026 — and what's dead (don't build restaking or "dynamic fees") | ~10 min |
| `04-hook-ideas-shortlist.md` | 8 concrete project ideas, honestly scored for novelty, users, and beginner-feasibility, with a ranked recommendation | ~15 min |

## The TL;DR if you only read one paragraph

Uniswap's fight in 2026 is not about fee formulas (that's the most over-built idea in your entire directory — 218 of 556 hooks). The real gaps: (1) **nobody can tell a safe hook from a time bomb** since the Bunni hack, (2) **hooked pools are invisible to routers**, so they get no volume, (3) **Unichain's new Flashblocks made "MEV taxes for LPs" possible for the first time** and almost nobody has built on it, and (4) **new asset classes are arriving without market structure** — tokenized stocks that trade 24/7 while Wall Street sleeps, and prediction-market outcome tokens with no suitable AMM. Meanwhile LPs just took a pay cut from the fee switch, making anything that boosts LP income swim with the current. My top three picks, in order: the **Market-Hours Hook for tokenized stocks**, the **MEV-Tax-for-LPs Hook on Unichain**, and the **Guard Hook (circuit breaker for other hooks)** — reasoning and build sketches in file 04.

## The single most important lesson from the research

Every v4 hook that actually succeeded (Doppler, Angstrom, EulerSwap, Flaunch) was an **invisible engine inside a product people already wanted**. Every hook that failed was a clever mechanism looking for users. Pick your user first, then your mechanism.
