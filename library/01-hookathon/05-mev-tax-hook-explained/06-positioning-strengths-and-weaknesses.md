# Positioning — where MevTaxHook is genuinely better, and where it's genuinely worse

Companion to `05-competitive-landscape.md`. That file maps the field; this one makes the actual comparative
judgment call the user asked for: **how is our approach unique and where is it worse than the alternatives.**

## Where MevTaxHook is structurally better than the field

1. **Atomic, custody-free settlement.** Tax and donation happen in the same `beforeSwap` call via
   `beforeSwapReturnDelta` + `PoolManager.donate`. The hook's net currency delta is zero — it never holds a token,
   never needs a withdrawal function, never has a "funds stuck in the hook" failure mode. Compare: EvenFlow (UHI9)
   explicitly needed a *second* reactive-contract mechanism (a time-based cron) just to release its own reserve
   during quiet markets, because its surcharge sits in the hook until triggered. We have no reserve to strand.
2. **Zero external dependencies.** No oracle (unlike "MEV Sharing is Caring," "Redirecting Arbitrage Profits...",
   most of bucket 1), no off-chain AVS/bidding infra (unlike every auction-based hook — EigenLVR, Shield-Auction-Hook,
   Maestro), no FHE coprocessor (unlike ~40 UHI6/7 projects), no second chain or bridge (unlike lambda's
   Hyperliquid hedge). The entire trust surface is `tx.gasprice`, `block.basefee`, and the PoolManager itself.
   Fewer dependencies = smaller audit surface and nothing else that can go down independently of Uniswap v4.
3. **LP-first by design, not as an afterthought.** Most "redistribute MEV" hooks split proceeds between multiple
   parties (ShieldFI: 70–80% to *traders*, MEV-Capturing Auction Hook: 50/50 traders/LPs) or send them to a token
   burn (Uniswap's own PFDA burns UNI). MevTaxHook sends 100% of what it captures to the LPs whose liquidity was
   actually used in that pool, with no protocol-fee skim in between (donations are outside the fee-switch path).
4. **Provable, not probabilistic, on its target chain.** Priority-fee-based mechanisms only work if priority
   ordering is enforced; on Ethereum L1 this is false (builder auctions dominate) and Paradigm's own paper says so.
   Unichain's Flashblocks make it enforced-in-a-TEE, so this hook has a chain where its core assumption is
   actually true — most of the priority-fee-tax attempts in the pre-2025 dataset (bucket 5, UHI2–5) predate that
   guarantee and were built on chains where the assumption was closer to hopeful than provable.
5. **Minimal, auditable surface.** ~190 lines of logic, one state struct per pool, no admin key needed after
   deployment except pool-level config tuning. Compare to the auction/FHE/reactive-contract designs, which each
   carry meaningfully larger attack surface (off-chain bidder collusion, FHE coprocessor bugs, cross-chain message
   relay failure) for a comparable or smaller LP benefit.

## Where MevTaxHook is genuinely weaker than alternatives

1. **Single-chain-dependent thesis.** The entire mechanism's honesty depends on Unichain's Flashblocks priority
   ordering holding. On any chain without that guarantee (including Ethereum L1), the "tax" becomes something a
   sophisticated searcher can simply route around (e.g., by paying the block builder off-path rather than via
   priority fee), silently degrading the hook to "occasionally taxes naive bots" rather than "reliably taxes MEV."
   Auction-based and FHE-based designs don't share this specific fragility — CoW/FHE approaches deny bots the
   *information* rather than relying on fee-ordering honesty, which is a more chain-agnostic guarantee.
2. **Doesn't stop sandwich attacks, only taxes them.** ShieldFI, ISP, AsyncSwapHook, and the FHE bucket actually
   try to *prevent* the attack (block it, hide the info, delay execution). MevTaxHook is closer to Uniswap's own
   PFDA philosophy: let the MEV happen, recapture the value after the fact. A victim of a sandwich still gets a
   worse execution price; they just know the attacker's take is smaller and partially redirected. If "protect the
   trader" (not just "compensate the LP") is the goal, this hook doesn't do that job — bucket 3/4 approaches do.
3. **Static/linear tax curve is a blunt instrument.** `taxPpmFor` is linear-above-exemption with a hard cap — simple
   and auditable, but it doesn't distinguish a legitimate high-priority-fee user (someone who just wants fast
   inclusion, e.g. during network congestion) from an actual arbitrage bot. Behavior-based designs (Dynamic Fees
   for MEV Mitigation, UHI5) and oracle-deviation designs (MEV Sharing is Caring) at least attempt to condition on
   something closer to "is this actually toxic flow," at the cost of extra state/oracle dependency.
2. **No protection against sandwich attacks that don't race on-chain priority at all** — e.g., attacks executed by
   the block builder/sequencer itself (who doesn't need to bid a public priority fee to reorder), or attacks that
   happen via private order flow / off-chain agreements with the sequencer operator. TEE-enforced priority ordering
   mitigates this on Unichain specifically, but it is a chain-operator trust assumption, not a cryptographic one.
4. **Single point of calibration risk.** `taxPpmPerGwei`, `exemptPriorityFee`, and `maxTaxPpm` are owner-set per
   pool with no on-chain price-discovery mechanism. Get the exemption threshold wrong and you either tax real users
   during congestion (bad UX, LPs win, traders lose) or exempt real arb bots (mechanism does nothing). Auction-based
   designs let the *market* set the price of MEV rights each block; we require a human/governance process to tune
   three numbers and hope they stay right as gas market conditions change.
5. **No composability story yet.** CoW-style and TWAMM-style hooks reduce the total amount of MEV *available* to
   extract in the first place (fewer atomic single-block trades to snipe). MevTaxHook doesn't reduce the attack
   surface at all — it operates entirely downstream of an attack that still fully happens, and only redistributes
   the winner's take. If the ecosystem trends toward CoW/batching as the dominant MEV-reduction paradigm (bucket 4
   is the second-largest bucket in the dataset and growing), a pure fee-recapture hook becomes a smaller slice of a
   shrinking pie.
6. **Head-to-head with Uniswap's own protocol-level PFDA is unresolved.** Both mechanisms compete for the same
   captured value on the same pools. It's not yet clear whether a pool can run both PFDA (protocol-level) and this
   hook (pool-level) without one cannibalizing the other's revenue base, or whether LPs/pool deployers will need to
   choose. This is a genuine open question the docs don't currently answer.

## Bottom line

No project found in the 126-entry MEV/LVR dataset, the UHI9 Reactive Network wave, or public UHI10 chatter
implements the exact combination MevTaxHook does: **stateless, oracle-free, atomic priority-fee tax settled via
`beforeSwapReturnDelta` + `donate`, on a chain where priority ordering is TEE-enforced.** The closest analogs each
trade our simplicity for either a different beneficiary split (ShieldFI, MEV-Capturing Auction Hook), a different
signal (oracle deviation, behavior history), or meaningfully more infrastructure (auctions, FHE, cross-chain
reactive contracts). That simplicity is the whole competitive edge — and also exactly what limits the hook to
"redistribute the MEV that happens" rather than "reduce the MEV that's possible," which is the ambition of the
CoW/FHE/TWAMM buckets that make up more than half the existing dataset.
