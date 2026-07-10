# Designing Your Own Hook — and Where to Go Next

**Fast overview:** the closing chapter turns twelve chapters of theory into a design process: how to pick a problem, choose the minimal hook surface for it, pressure-test the economics, and scope it to something you can actually ship and defend. It ends with the curated reading list — the sources this book was distilled from, ordered by what to read next.

## The design process, step by step

**Step 1 — Name the leak or the product.** Every good hook answers one of two prompts: *"value leaks from [traders | LPs | creators] via [mechanism]; I re-route it"* (the Chapter 5/12 lineage) or *"this financial product wants pool rails"* (the Flaunch/EulerSwap lineage). If you can't fill the blank in one sentence, you have a technology looking for a problem — the most common failed-hackathon genus.

**Step 2 — Choose the minimal surface.** Map the idea to permissions (Chapter 7–8), and take the *least* you can:

| Your idea needs to… | Surface | Risk class |
|---|---|---|
| observe / veto / gate | before-callbacks, no deltas | low (Ch. 7) |
| record / reward / account | after-callbacks, no deltas | low |
| set spreads | dynamic fee flag | low-medium (Ch. 9) |
| take a cut / subsidize | return-delta flags | high (Ch. 8, 11) |
| replace pricing entirely | beforeSwap + full delta consumption | highest |

Each row down doubles your audit bill and your Chapter-11 exposure. The best 2025–2026 small hooks live in the top three rows; only step down when the idea genuinely requires it.

**Step 3 — Red-team the economics before writing code.** Three questions, on paper: Who profits from using this *as designed but against its purpose*? What state can an attacker shape cheaply (dust swaps, donations, timing) that my logic reads? If my parameters are wrong by 10×, who loses? (Chapter 11, Class 6 — the class audits don't cover.)

**Step 4 — Build on the template, climb the ladder.** v4-template, BaseHook or OpenZeppelin's hook library, then unit → fuzz → invariant → fork (Chapter 10). Write your invariants down *first* — they're the spec.

**Step 5 — Ship the demo with honest numbers.** Gas per swap versus vanilla; who pays what fee when; what the admin can and cannot do. Judges (and later, LPs) reward legible trust models — it's also Chapter 11's checklist items 6–8, done in public.

## Worked example: sizing up your own shortlist

The research book at the top of this shelf left a decision dangling. Run the process against its three finalists:

- **MEV-tax hook** — Step 1: LP value leaks to searchers via priority races (Ch. 5); re-route via fee ∝ priority (Ch. 9, pattern 4; Ch. 12, family 1). Step 2: dynamic fee row — *low-medium surface, high concept*. Caveat: needs a priority-ordered chain to demo honestly (Unichain fork test). Strong scope-to-impact ratio.
- **Market-hours hook** — Step 1: product rails for RWA/tokenized-equity pools; gate + reprice by session (Ch. 7 gating + Ch. 9 fees). Step 2: top rows only — *lowest risk*, very legible demo; economic red-team is mild (who arbs the open?— the auction at market open is a real, interesting wrinkle).
- **Guard hook** — Step 1: traders/LPs leak via manipulation spikes; veto + circuit-break (Ch. 7). Step 2: top row. Watch Step 3 hard: your trigger reads manipulable state (Ch. 11, Class 4) — the guard itself must not be gameable into a DoS lever against honest users.

All three are top-three-rows designs — correctly scoped. The differentiator is the *story you can measure*: the MEV-tax hook has the strongest Chapter-12 narrative; market-hours has the cleanest demo; guard has the subtlest failure analysis to defend. That's a taste call, and now an informed one.

## The reading list

Everything below was source material for this book; ordered by what to do next, not by prestige.

**Do first**
- Uniswap v4 docs — concepts & guides (docs.uniswap.org/contracts/v4): the official hook/custom-accounting/BeforeSwapDelta guides are short and current.
- v4-template (github.com/uniswapfoundation/v4-template) + v4-core / v4-periphery sources — read `Hooks.sol` and `PoolManager.sol` once, slowly.
- Cyfrin Updraft's Uniswap v4 course, and Cyfrin's "v4 swap deep dive" / "hooks security deep dive" blog posts — the best free structured walkthroughs.

**Math and mechanics**
- Uniswap v3 whitepaper + the two-part "Primer on Uniswap v3 Math" (blog.uniswap.org) — Chapter 4's material from the source.
- Atis Elsts, "Liquidity Math in Uniswap v3" (technical note) — the derivations, worked.
- RareSkills' pieces on sqrtPriceX96 and tick math; MixBytes' "Uniswap v3 ticks" deep dive.
- Uniswap v4 whitepaper — short; read after Chapters 6–8 and it will feel obvious, which is the point.

**MEV / LVR / mechanism design**
- Milionis, Moallemi, Roughgarden, Zhang — "Automated Market Making and Loss-Versus-Rebalancing" (arXiv 2208.06046): the LVR paper (Ch. 5).
- Adams et al. — "am-AMM: An Auction-Managed Automated Market Maker"; Robinson & White — "Priority Is All You Need" (MEV taxes) (Ch. 12).
- CoW Protocol's LVR explainers and the FM-AMM paper (Canidio & Fritsch); Arrakis' "AMM Renaissance" post — accessible surveys of the defense landscape.

**Security**
- QuillAudits' Uniswap v4 development & hook-security handbook; Hacken's "Auditing Uniswap v4 Hooks" + their open-source hook testing framework.
- Verichains' Bunni post-mortem ("How precision bugs drained millions") — Chapter 11's case study, forensically.
- OpenZeppelin `uniswap-hooks` library — read the base contracts you should be inheriting.

**Ecosystem pulse**
- awesome-uniswap-v4-hooks lists (johnsonstephan / fewwwww on GitHub) — living directories of examples and tools.
- HookRank and DefiLlama's v4 dashboards — which hooks actually get volume (data beats discourse).
- Project docs for the Chapter-12 cast: Angstrom (Sorella), EulerSwap, Flaunch, Bunni's open-sourced repos, Unichain docs.

## Closing the loop

The book began with a missing counterparty and a formula that faked one. Every chapter since has been the same negotiation restated: *who does the work of market making, and who keeps the value it creates?* v2 answered "a formula; arbitrageurs keep the change." v3 answered "LPs work harder; arbitrageurs still keep the change." v4's answer is the honest one: *it's programmable — you decide.* Hooks are the decision surface. The auctions of Chapter 12 are the current best decisions. Your hook, if you build it well, is the next one.

Go build. And when your `beforeSwap` reverts with no reason string at 2 a.m. — Chapter 10 is the one to reopen first.
