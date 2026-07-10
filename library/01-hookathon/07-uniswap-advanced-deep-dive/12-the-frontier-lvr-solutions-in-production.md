# The Frontier — LVR Solutions in Production

**Fast overview:** Chapter 5 taxonomized the defenses against MEV and LVR; this chapter tours the ones that made it to production or serious research by mid-2026 — the am-AMM and MEV taxes (sell the arb right), Angstrom and CoW AMM (uniform prices / remove the stale quote), Unichain's flashblocks and priority ordering (shrink the window), and the LP-management renaissance. This is the intellectual frontier your hookathon project competes on, so each design comes with its tradeoffs, not just its pitch.

## Family 1 — Sell the sniping right: am-AMM and MEV taxes

The insight (Chapter 5): if arbitrage profit against your pool is inevitable, don't prevent it — **auction it and pay LPs the proceeds**.

**The am-AMM** (auction-managed AMM, Adams et al. 2024): continuously auction the role of *pool manager*. The winner pays LPs an ongoing rent, and in exchange receives the pool's swap fees and — crucially — the right to set fees, including *zero for themselves*. The winning bidder is naturally the best arbitrageur: they arb the pool at zero fee (capturing LVR), so they bid ≈ expected LVR as rent. Result: LVR is transformed from a leak into a *priced, competitively-bid revenue stream* for LPs. The rent auction runs perfectly happily as hook machinery (bids escrowed in ERC-6909, manager role checked in `beforeSwap` — every mechanism from Chapters 6–9 in one design). Bunni v2 shipped am-AMM elements before its death; several successors carry the design forward.

**MEV taxes** (Robinson & White, 2024): on chains ordered by priority fee, charge each transaction `fee ∝ priorityFeePerGas` (Chapter 9's pattern 4). Searchers racing to arb your pool bid up priority — the tax converts their bids into LP income, approximating the am-AMM's outcome *without running an auction yourself*: the block builder's auction is repurposed. Limitation: requires credibly priority-ordered chains (Unichain, some OP-stack L2s with strict rules) — on mainnet, builder side-deals leak around it.

Tradeoffs, both designs: LPs take on *manager/searcher centralization* (one entity per pool per epoch), rent/tax calibration risk, and — always — new code surface (Chapter 11).

## Family 2 — Remove the stale quote: batch auctions and uniform prices

Sandwiches (Chapter 5) need *ordering within* your trade — front, victim, back. Kill intra-batch ordering and you kill the sandwich.

**Angstrom** (Sorella Labs, launched 2025, ~$700M+ monthly volume by mid-2026): a hook where swaps don't execute on arrival; a decentralized network of staked validators batches each block's orders and settles them all at **one uniform clearing price** — no one trades ahead of anyone, so sandwiching is geometrically impossible, and the batch's clearing process internalizes the arbitrage (external arbs have nothing stale to hit; the value returns to LPs and traders). Only network-approved batches can execute swaps — enforced via `beforeSwap` gating (Chapter 7's access-control pattern at industrial scale). Tradeoffs: batch latency, a validator set to trust/stake, and off-chain infrastructure most hook teams can't run.

**CoW AMM / FM-AMM** (live on Balancer since 2024, formalized by Canidio & Fritsch): the pool only trades via batch solvers who must *outbid each other* for the right to rebalance it — arbitrageurs compete their profit away *to the pool*. The academic name is function-maximizing AMM; the measured result: LVR largely captured. Not a Uniswap hook, but the design many hooks imitate.

**Oracle-anchored pools**: simpler cousin — `beforeSwap` repricing the pool from a fast oracle before executing, so arbs find no gap. Imports oracle risk wholesale (Chapters 9 and 11): you're only as unstale as your feed, and only as safe as its manipulation cost.

## Family 3 — Shrink the window: Unichain

**Unichain** — Uniswap Labs' OP-stack L2, live since early 2025, ~$70B v4 volume by mid-2026 — attacks LVR at the *chain* layer. Two mechanisms:

- **Flashblocks (~250ms sub-blocks)** via a TEE-based block builder: quotes go stale for a quarter-second instead of twelve. LVR per unit time scales with staleness (Chapter 5: arb profit ~ variance accumulated between corrections, and σ²·Δt shrinks linearly in Δt) — faster blocks mechanically starve the arb.
- **Priority ordering guarantees** make MEV-tax hooks (Family 1) actually enforceable — the chain commits to fee-ordered inclusion, so `priorityFeePerGas` is an honest signal.

The strategic read: Uniswap vertically integrated down the stack because the deepest MEV/LVR fixes live *below* the AMM. Tradeoff: another chain's trust assumptions (TEE builder, stage-of-decentralization caveats), and liquidity fragmentation across the 15+ deployment chains.

## Family 4 — The LP-management renaissance

v3 made LPing a job (Chapter 4); hooks try to automate the job *inside the pool*. Bunni v2 was the flagship (autonomous liquidity-distribution functions + surge fees + am-AMM rent — and Chapter 11 tells the rest). Its death didn't kill the category: vault-style managers (Arrakis, Gamma lineage) now deploy as hooks; **EulerSwap** (2025's breakout, from the Euler lending team) makes the deepest move — LP capital lives in lending vaults, *earning yield and serving as collateral*, while a custom-curve hook (Chapter 8's endgame) prices swaps against that same inventory. One dollar doing three jobs; the AMM dissolves into the money market. Watch its risk ledger though: rehypothecation means a lending-market failure is now also a DEX failure — composability compounds returns *and* correlations (Chapter 11, Class 6 thinking).

Honorable mention outside the LVR war: **Flaunch** (Base) — a memecoin launchpad as a hook suite: creator fee streams, programmatic buybacks ("progressive bid wall"), launch-window sell restrictions. Not defense — *product* — and a reminder that hooks are a general platform, not just an MEV arms race. The 2,500+ deployed hooks skew heavily toward such product experiments.

## Reading the frontier as one picture

Line the families up against Chapter 5's taxonomy and one pattern jumps out: **every serious design moves value that used to leak to searchers/builders back toward LPs and traders, by making someone bid for what they used to take.** Auctions all the way down — rent auctions (am-AMM), priority auctions (MEV tax), solver auctions (CoW, Angstrom), builder auctions (flashblocks). The AMM of 2026 is best understood as a *mechanism-design venue* where the curve (Chapter 2) is just the fallback pricing when no better auction clears.

That's also your design compass for the hookathon: the winning entries of 2025–2026 each picked *one* leak, *one* auction-or-fee mechanism to re-route it, and shipped it at Chapter-9 scale with Chapter-10 discipline and Chapter-11 humility. The final chapter turns this compass into a concrete design process — and closes the book where it started: with your shortlist.
