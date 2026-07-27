# Competitive Landscape — MEV-Tax-for-LPs vs. everything else in MEV/LVR hooks

Research date: 2026-07-25. Sources: `PROJECTS/VIBECODED/markdown-kindle/library/01-hookathon/03-hook-directory/categories/mev-lvr-protection.md`
(126 cataloged MEV/LVR hook projects from UHI2–UHI8), Paradigm's "Priority Is All You Need" (2024), Uniswap's
UNIfication/PFDA docs, Unichain Flashblocks docs, and live X/web research on UHI9 and UHI10 (2026-07-25).

## 1. What we built, in one paragraph

`MevTaxHook` reads `tx.gasprice - block.basefee` (the priority fee) in `beforeSwap`, computes a tax linear in that
priority fee above a per-pool exemption threshold (capped), takes it out of the swap's specified amount via
`beforeSwapReturnDelta`, and atomically donates it to the pool's in-range LPs via `PoolManager.donate` in the same
call — never holding a token, never touching non-priority-fee-paying users, and working on static-fee, dynamic-fee,
and native-currency pools alike. The mechanism is Paradigm's published "MEV tax" idea, aimed specifically at LPs
instead of at burning a token, and it only becomes *provable* (rather than just "probably true") because Unichain's
Flashblocks enforce priority ordering inside a TEE.

## 2. The taxonomy: six ways teams have attacked MEV/LVR (2022–2026)

From the 126-project dataset, every MEV/LVR hook falls into one of six buckets:

1. **Dynamic/directional fees that tax likely-arbitrage flow** — fee moves with a *signal* correlated with toxic
   flow (oracle deviation, volatility, order imbalance). ~30 projects.
2. **Auction-based MEV redistribution (am-AMM style)** — a manager bids for the right to arbitrage/manage the pool;
   bid revenue flows to LPs (EigenLVR, LVR Auction Hook, Shield-Auction-Hook, AuctionPool, Maestro/UHI9). ~15 projects.
3. **Encrypted/private order flow (FHE)** — hide trade direction/size until after commit so bots can't sandwich
   (ShadowSwap, CipherFlow, ZK-JIT, FheatherX, Chimera Protocol...). The single largest bucket — **40+ projects**,
   almost entirely UHI6/UHI7, almost entirely Fhenix-dependent.
4. **CoW / batching** — match opposing intents before touching the pool (CoWSwap, UniCow, RecorrHook, EigenMatch
   CoW Hook, LeanSwap/UHI8). ~20 projects.
5. **Priority-fee-aware fees** — charge more when the tx's priority fee looks like a bot racing to be first. This is
   the bucket we're in. ~5 projects explicitly ("DAMM", "Priority is all you need + Hook.ninja", "Dynamic Fees for
   MEV Mitigation", "MEV Sharing is Caring" — though that last one uses oracle deviation, not priority fee, as the
   signal).
6. **TWAMM** — break large trades into many small pieces over time (Confidential MEV-Protected TWAMM, TWAMM-X,
   SliceX). ~5 projects.

Reference: Milionis/Moallemi/Roughgarden/Zhang on LVR (2022); Flashbots MEV research; am-AMM design; CoW Protocol;
Paradigm's TWAMM research; Fhenix FHE-on-EVM.

## 3. Nearest neighbors — and why none of them are actually us

| Project (cohort) | Mechanism | How it differs from MevTaxHook |
|---|---|---|
| **"Priority is all you need" (+Hook.ninja & indexer)** (UHI4) | Increases pool fee when priority fees are high | Closest by name/concept. But it's a **fee multiplier on the swap fee** (subject to Uniswap's protocol fee switch / PFDA skimming a cut), not a **separate donate-based tax with `beforeSwapReturnDelta`**. No exemption threshold design described; no explicit "normal users pay zero" guarantee. |
| **DAMM (dynamic amm)** (UHI2) | Dynamic pool fees based on "swappers' stated preference" + higher fee for identified-MEV txs | Detection-based ("identified as MEV"), not a continuous linear function of the priority fee itself. Unclear settlement path — LP fees go through the standard fee mechanism, not an atomic donate. |
| **Dynamic Fees for MEV Mitigation** (UHI5) | Adjusts fee "based on user's behavior" | Behavior-history-based (reputation/pattern), not a stateless per-tx priority-fee read. Requires tracking user behavior over time — more state, more attack surface. |
| **MEV Sharing is Caring** (UHI4) | Fee based on deviation between pool price and a Chainlink reference price | Different signal entirely (price deviation, needs an oracle dependency) vs. ours (priority fee, needs zero oracles). Detects *that* an arb happened, not *who* is racing for it. |
| **Redirecting Arbitrage Profits to LPs...** (UHI5) | Fee increases as trade moves away from oracle price, redirecting to LPs | Same *goal* (arb profit → LPs) as us, but oracle-deviation signal + presumably standard fee accrual, not tx-level priority-fee tax + atomic donate. Also needs a live oracle feed (extra trust/failure surface); we need none. |
| **ShieldFI** (UHI5) | Detects/blocks sandwiches, redistributes 70–80% of captured MEV | Redistributes to **traders**, not LPs — different beneficiary. Also detection/blocking (binary), not tax (continuous, permissionless). |
| **EigenLVR / LVR Auction Hook / Shield-Auction-Hook / AuctionPool / MEV-Capturing Auction Hook** (UHI5–7) | Auction the right to arbitrage/manage the pool first; proceeds to LPs | Structurally different mechanism class (bucket 2, not 5). Auctions need an off-chain bidding process, often an AVS (EigenLayer) for settlement — real infra dependency and off-chain trust assumptions. Our hook is a single, permissionless, no-off-chain-component `beforeSwap` check. |
| **Maestro** (UHI9, Reactive Network) | Harberger-auction pool manager, rent flows to LPs block by block | Cross-chain reactive-contract architecture (watches Pyth feed on one chain, manages Unichain pool). Far more moving parts; manager risk (who wins the auction can misbehave, hence needs the kind of invariant-guarding our own **Guard Hook** project addresses). |
| **lambda** (UHI9, Reactive Network) | Auto-hedges LP LVR exposure with a Hyperliquid perp short via a reactive contract | Solves the *same pain* (LPs bleed ~11%/yr to arbitrageurs) via an entirely different mechanism: derivatives hedging, not fee redistribution. Needs a second venue (Hyperliquid), a bridge, and continuous position management — much higher complexity and a second protocol's counterparty risk. |
| **EvenFlow** (UHI9, Reactive Network) | Surcharge when trading turns against LPs, held in reserve, released via a reactive cron | Structurally close in *spirit* (surcharge → LPs) but needs a reactive contract to drip the reserve back during quiet periods — a real gap our hook doesn't have, because we never hold funds: the donate happens atomically inside the same tx as the tax, so there's no reserve that can get "stranded" when the market goes quiet. This is arguably the sharpest point of comparison found in this research: **EvenFlow's own postmortem describes exactly the failure mode our atomic-donate design structurally avoids.** |
| **CrossHedge** (UHI9, won UF prize track) | Redirects LP impermanent-loss leakage into a yield product (~14% modeled APY) via an external vault | Vault/yield-product framing, not an in-protocol tax. Different target: IL broadly, not specifically priority-fee-signaled MEV. |

## 4. The literature we're implementing vs. departing from

- **Paradigm, "Priority Is All You Need" (2024)** — the source of the "MEV tax" mechanism itself: charge a
  function of the priority fee, direct proceeds to a chosen beneficiary. Paradigm's paper is explicit that **this
  only works where block proposers strictly follow competitive priority ordering** — true on OP-stack chains with
  that guarantee, *not* true on Ethereum L1 (builder auctions dominate there). This is exactly why the hook's own
  docs describe it as "provably meaningful only on Unichain" — that's not marketing, it's the actual constraint in
  the source research. Nobody in the pre-2026 dataset could build this for real, because Flashblocks (provable
  priority ordering in a TEE) only shipped in 2025.
- **Uniswap's own PFDA (Protocol Fee Discount Auction)** — live in 2026 as part of UNIfication. It auctions the
  right to swap fee-free for a window; winning bid is **burned** (UNI holders benefit). This is the direct,
  protocol-level competitor to our idea, and the split is stark: **PFDA sends internalized MEV to UNI holders,
  MevTaxHook sends it to the LPs whose liquidity was actually used.** Early PFDA analysis shows it lifting LP
  returns by only $0.06–$0.26 per $10k traded — i.e., LPs get a sliver even in Uniswap's own design; our hook's
  entire, unshared proceeds go to LPs instead.

## 5. UHI10 — the theme confirms the bet, but no public comparables exist yet

Atrium Academy's own framing of UHI10 (posted 2026-04-23, confirmed via X): the Hookathon theme is **"The Fair Flow
Frontier: MEV protection and sustainable low-fee liquidity,"** explicitly covering dynamic fee hooks, **"return
delta hooks... where MEV recapture mechanisms live"** (exactly our hook's mechanism), and coincidence-of-wants.
Atrium frames the expected output as "swap ordering randomization, fee-rebate systems, or MEV auction hooks" —
our hook is closest to their "fee-rebate systems" category, built a few months ahead of the cohort's own official
Hookathon window. As of this research (2026-07-25), no public UHI10 project write-ups or X posts describing a
directly competing priority-fee-tax-to-LPs hook were found — searches for `#UHI10 MEV tax`, `"MEV tax" hook
Uniswap priority fee LP`, and general UHI10 hookathon chatter returned no matching projects. This is a genuine
"nobody's shipped this yet in public" gap, not an absence-of-search-effort gap — but it also means the field is
about to get crowded with directly-competing entries once UHI10 hookathon submissions land, since the cohort is
being pointed at this exact mechanism class.
