# Dynamic Fees and Oracle Hooks

**Fast overview:** two workhorse hook patterns that most real pools want. Dynamic fees let the pool change its LP fee per swap — the direct weapon against Chapter 5's volatility/LVR problem. Oracle hooks rebuild (and improve on) the price feeds that v4 removed from core. Both are "gateway" patterns: powerful enough to matter, simple enough to actually ship, and components inside nearly every ambitious hook in Chapter 12.

## Dynamic fees: the mechanics

A pool opts in at creation by setting its `fee` field to the dynamic-fee flag (`0x800000`, i.e. the top bit of the uint24). From then on the *hook* owns the fee, two ways:

- **Steady-state:** call `poolManager.updateDynamicLPFee(key, newFee)` whenever policy dictates (in `afterSwap`, on a timer, from a keeper...). The pool stores it until next update.
- **Per-swap:** return a fee override from `beforeSwap` (the third return value, a uint24 with the override flag set). Each swap can get its own price — including *per-trader* or *per-direction* pricing.

Fee units are hundredths of a bip (1e6 = 100%; 3000 = 0.30%). LP fees in v4 accrue via Chapter 4's `feeGrowthInside` machinery exactly as in v3 — the dynamic part only changes the *rate* charged as swaps execute.

## Fee policy: what to actually charge

Now the interesting part — policy. Chapter 5 gave the theory: the fee is a no-arbitrage moat whose optimal width scales with volatility and flow toxicity. Concrete policies seen in production and research, roughly in order of sophistication:

**1. Volatility-scaled fees.** Track realized volatility (e.g., squared tick moves over a rolling window — the hook's own observations, see oracle section below) and map it to a fee: calm market 0.05%, normal 0.30%, chaos 1%+. This directly implements "reprice the option": when σ² spikes, LVR (σ²/8, remember) spikes, so the moat must widen. A ~200-line hook captures most of the theoretical benefit.

**2. Asymmetric / directional fees.** Arbitrage flow after a price jump comes in *one direction* — the direction correcting the pool toward the market. Charge that direction more (or momentarily spike it) and you tax arbs specifically while leaving contra-flow cheap. Requires knowing the "right" price — an oracle, or inference from recent flow imbalance.

**3. Toxicity-priced flow.** Classify the *trade*, not the market: size relative to depth, sender history (via hookData attestations), or timing within the block. Priced per-swap via the `beforeSwap` override. This is Chapter 1's Glosten–Milgrom spread, finally implementable: uninformed flow gets the tight spread, suspected-informed flow pays the wide one.

**4. MEV-tax / priority-fee pricing.** On chains with priority ordering (Unichain — Chapter 12), a transaction's priority fee reveals how much its sender values being *first*. Arbs bid high priority (they're racing for the stale quote); retail doesn't. So set `fee ∝ priorityFeePerGas`: effectively an auction where arbitrageurs' bids are collected *as LP fees*. This one idea — the "MEV tax" — turns block-builder market structure into LP revenue, and is the seed of the am-AMM family in Chapter 12. (*Connect the dot:* your MEV-tax hook book on this shelf is precisely pattern 4 — you now have its full intellectual pedigree: Ch. 1 adverse selection → Ch. 5 LVR/auction taxonomy → Ch. 8 delta mechanics → here.)

**5. Surge fees on liquidity events.** Bunni v2 charged elevated fees during/after its own rebalances — acknowledging that *the hook's own predictable rebalancing* creates arb opportunities (Chapter 5's dynamic-weight insight: rebalancing is a sequence of small auctions; surge fees claw back some of what the auction leaks).

Design cautions, learned the hard way by 2025's deployments: clamp fees to sane bounds (an unbounded formula that can hit 100% is a rug lever and will be flagged in audit); make updates *smooth* (fee cliffs create their own MEV — trade just before the cliff); and remember every basis point you charge honest flow routes volume to competitors. Fee policy is spread-setting; Chapter 1's dilemma never goes away, you just get better instruments.

## Oracle hooks: rebuilding the public utility

v4 removed the oracle from core (Chapter 6) — every swap in v3 paid gas maintaining observation buffers most pools never used. The replacement pattern: an `afterSwap` (plus `afterInitialize`) hook records observations *for pools that opt in*, spending gas only where the product is wanted.

The classic build is a port of v3's design (there's a canonical example in the v4 periphery lineage): a ring buffer of `(blockTimestamp, tickCumulative)` observations; `afterSwap` writes at most one observation per block; consumers compute time-weighted average *ticks* between two observations — a geometric-mean TWAP, inheriting v3's manipulation resistance (Chapter 3's principle: cost of keeping the oracle wrong = capital held mispriced across the window, times pool depth).

v4-era improvements over the v3 original, all seen in production hooks:

- **Truncated oracles.** Cap how far the recorded tick can move per block (e.g., ~10 ticks). A manipulator can spike the *pool* price arbitrarily, but the *oracle's* recorded price crawls — making short-window manipulation nearly worthless while honest prices catch up within blocks. This "truncated geomean oracle" is the recommended pattern for lending-protocol consumption.
- **Pay-per-read economics.** The hook can charge consumers (a fee to `increaseCardinality` or per-read via contract call) — oracles as self-funding infrastructure rather than protocol charity.
- **Composite feeds.** A hook aggregating its own pool observations with Chainlink/Pyth, emitting the median — belt-and-suspenders for high-stakes consumers.

Two integration warnings. First, an oracle hook makes *your pool* the truth source others build on: your pool's depth is now their security budget; thin pool + trusted oracle = someone else's exploit. Second, reading oracles *from inside* other hooks (e.g., a dynamic-fee hook consuming its own truncated TWAP — the natural pairing) must handle the cold-start: a fresh pool has no history, and policy code dividing by "observed variance" of nothing has ruined more than one testnet demo.

## The natural pairing: fee policy fed by on-pool oracles

Notice the two patterns want each other. A volatility-scaled fee needs a volatility estimate; the cheapest honest one is the pool's own tick history — which is exactly what an oracle hook records. Production dynamic-fee hooks are usually *one contract doing both*: `afterInitialize` seeds observations, `afterSwap` records ticks and updates the fee for next swap, `beforeSwap` optionally overrides per-trade. Total: maybe 300 lines, and it addresses the single largest measured drain on LP capital (Chapter 5's 5–7% annually).

This is also your calibration point for hookathon ambition: the *best-regarded* small hooks of 2025–2026 are exactly this size and shape — one sharp economic idea (tax the toxic flow / smooth the oracle / gate the risky hours), implemented conservatively on the observation-and-fee surface, no custom accounting, no curve replacement. The catastrophes (next-but-one chapter) all lived on the Chapter 8 surface.

First, though — the workshop. How you actually build, test, and deploy any of this without donating your pool to strangers: Foundry, the v4-template, and the testing discipline that separates shipped hooks from post-mortems.
