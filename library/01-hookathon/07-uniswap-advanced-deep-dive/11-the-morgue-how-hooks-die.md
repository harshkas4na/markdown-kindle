# The Morgue — How Hooks Die

**Fast overview:** v4's architecture moved risk out of core and into hooks — and the incident record agrees: core has held; hooks have bled. This chapter is the taxonomy of hook failure — six vulnerability classes with the reasoning behind each — anchored by the definitive case study: Bunni, the audited, sophisticated, $60M-TVL hook that died of a rounding direction in September 2025. Read this chapter twice: once as a builder, once as an attacker.

## The threat model shift

In v2/v3, auditing a pool meant auditing Uniswap — one battle-tested codebase securing every pair identically. In v4, **every hooked pool is a distinct protocol**: core guarantees custody and delta conservation (Chapter 6), and *nothing else*. The hook's code, admin keys, upgradeability, oracles, and economic logic are all part of the pool's trust surface. Security firms' 2025–2026 consensus: hook audits are protocol audits, priced and scoped accordingly. For users the question changed from "is Uniswap safe?" to "what is attached to this pool and who controls it?"

With that frame, the six ways hooks die:

## Class 1 — Permission/implementation mismatch

Chapter 7's sharp edge, now as an exploit class. Flag set without the callback implemented → every such operation reverts → **bricked pool** (users' LP positions can become un-withdrawable if `beforeRemoveLiquidity` reverts — a hostage situation, not just downtime). Callback implemented without the flag → the enforcement logic *silently never runs* — your KYC gate, your circuit breaker, your fee: decorative. The insidious part: both bugs pass superficial tests (deploy-to-arbitrary-address test setups — Chapter 10's `deployCodeTo` — can mask a wrong production mining config). Audit item #1 for a reason: mechanical to check, catastrophic to miss.

## Class 2 — Delta mis-accounting

Chapter 8's power, misused. The PoolManager verifies deltas *net to zero* — it cannot verify they're *fair*. Recurring shapes:

- **Specified/unspecified confusion**: correct for exact-input, wrong for exact-output (or for the reverse direction). Result: swaps that over- or under-pay, harvestable in a loop.
- **Sign errors**: crediting where you meant to debit — sometimes self-draining (the hook pays traders), sometimes user-draining.
- **Unsettled hook deltas**: hook takes a cut but never settles → every swap reverts (DoS); or settles from the wrong balance → slow insolvency.
- **Multi-hop poisoning**: deltas that look right for a lone swap but compose wrong inside a longer route's unlock (Chapter 8's warning; test composed paths).

The one-line summary auditors repeat: **conservation is not correctness** — the ledger balancing tells you nothing about whether the *amounts* were right.

## Class 3 — Rounding and precision (the Bunni case)

The star exhibit. **Bunni v2** was among the most ambitious hooks live: a "Liquidity Distribution Function" reshaping LP capital across ranges automatically per trade (autonomous Chapter-4 range management — the holy grail), surge fees (Chapter 9), am-AMM ideas (Chapter 12), ~$60M TVL, audits from Trail of Bits and Cyfrin.

On 2 September 2025, an attacker drained ≈ **$8.4M** (≈$2.4M Ethereum, ≈$6M Unichain). Mechanism, simplified: Bunni's withdrawal/rebalance math contained a **floor-rounding** step whose error the attacker could *accumulate in their favor* — carefully sized swaps and withdrawals nudged the LDF into a state where each iteration over-credited the attacker slightly; repeat until material; sandwich the recalculated liquidity for profit. Emergency controls stopped the bleeding; the team, unable to fund a secure relaunch, shut down that October and open-sourced the code.

Three durable lessons:

1. **Rounding direction is adversarial territory.** Every division in money code must round *against* the counterparty who chooses the transaction. (v2 knew this — Chapter 3's MINIMUM_LIQUIDITY — and fuzzing finds it, Chapter 10.)
2. **Audits check code against spec; nobody checks the spec against an adversary.** The LDF was *specified* imprecisely; auditors verified faithful implementation of a flawed design. Economic-logic review — game-theoretic red-teaming of the mechanism itself — is a separate discipline you must buy or do.
3. **Complexity is the real attack surface.** The exploit lived in Bunni's most innovative subsystem. Every clever moving part is a place adversaries can shape state. Chapter 9's closing advice — small sharp hooks over grand machines — is this lesson, pre-paid.

## Class 4 — Reentrancy and mid-state reads

v4 allows reentrancy inside unlock (Chapter 6) — safe for *core's* ledger, dangerous for *your* state. If your hook makes any external call (token callbacks in weird ERC-20s, oracle pushes, reward payouts), the callee can re-enter a pool operation *while your hook's storage is mid-update*, or read your half-written state from another pool you serve. Related: **hook-state manipulation without reentrancy** — e.g., `donate()` (Chapter 6) or dust swaps shifting whatever variable your logic keys on (an average, a reserve ratio) right before a victim's trade. Defenses: your own reentrancy guards on state-mutating callbacks, effects-before-interactions, and never trusting intra-transaction spot readings of manipulable values (Chapter 3's oracle lesson, again).

## Class 5 — Governance, upgradeability, and the rug surface

"Immutable pool, mutable hook" (Chapter 7). If the hook is a proxy, or its parameters are owner-set, then the pool's rules are whatever the key-holder says tonight: fee → 100% (a rug lever — Chapter 9's clamp advice), allowlist → attacker-only, oracle → attacker's contract. Not hypothetical: 2025's incident list includes upgraded-hook rug-pulls alongside honest bugs. If you hold such powers, timelock them, bound them in code (max fee, min delay), and say so loudly; if you review hooks, `owner()` and upgrade slots are stop one.

## Class 6 — Economic and oracle failures

No bug, wrong mechanism. Fee formulas that misprice and get farmed; incentive designs where the profitable strategy hurts LPs (JIT games around your own rebalances — Chapter 5's dynamic-weight auctions, unpriced); consuming a *spot* price or thin-pool TWAP an attacker can bend (Chapter 9's truncated-oracle territory); async-swap hooks (Chapter 8) whose custody window becomes a free option on volatility. The test isn't "does the code match intent" but "is the intent an equilibrium" — simulate adversarial strategies, not just usage.

## The checklist

Before any hook touches real money:

1. Flags ↔ implementations verified *on the mined production address*, not just in tests.
2. Every delta path tested for all four (direction × exact-in/out) quadrants, plus composed multi-hop.
3. Every division audited for rounding direction; fuzz + invariant suites green (Chapter 10's ladder, all four rungs).
4. External calls enumerated; reentrancy through each modeled.
5. Manipulable inputs (donations, dust swaps, oracle reads) — what happens if each is adversarially set this block?
6. Admin powers: enumerated, bounded in code, timelocked, disclosed.
7. Economic red-team: who profits from using the mechanism *as designed but not as intended*?
8. Pause switch + monitoring on events (you'll have minutes, not hours — Bunni's controls are why $8.4M wasn't $60M).
9. Independent audit *including economic review* — and treat it as one filter, not absolution (Bunni had two good firms).

The architecture did its job: v4 core has processed hundreds of billions without loss while hooks around it failed — the blast radius stayed per-pool. Your job is to keep your pool out of the statistics. Now, with fear properly calibrated — the frontier: what the survivors are building.
