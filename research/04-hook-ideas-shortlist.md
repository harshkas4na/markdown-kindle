# The Shortlist: 8 Hook Ideas Worth Considering (Ranked)

This turns the problems (file 01), the whitepapers (file 02), and the trends (file 03) into concrete project ideas. Each idea is scored honestly:

- **Novelty** — how different is it from the 556 hooks already in your `hook-directory/`?
- **User pull** — is there someone who clearly *wants* this today?
- **Beginner-feasibility** — can you realistically build a credible version as your first serious hook?

Scores are ⭐ (weak) to ⭐⭐⭐ (strong). The top 3 are the ones I'd genuinely consider.

---

## 🥇 Idea 1: The "Market Hours" Hook — an AMM that knows when Wall Street is closed

**One-liner.** A hook for tokenized stock pools that changes behavior based on whether the real market is open: normal trading during NYSE hours, wider fees + trade-size limits on nights/weekends, and a short **reopening auction** on Monday morning instead of letting the fastest bot eat the LPs.

**Why now.** Tokenized stocks are arriving at full speed (xStocks, Robinhood, NYSE's own 24/7 venue), and the #1 unsolved structural issue is exactly this: when the reference market is closed, on-chain prices have no anchor, LPs carry all the risk, and Monday's open is a guaranteed arbitrage massacre. Regulators literally list "no circuit breakers" as a blocker.

**Potential users.** Tokenized equity issuers (Backed, Ondo, Dinari, Securitize), RWA platforms, LPs in any stock/ETF pool. These are funded companies — the kind of "user" that can become a job, grant, or acquisition.

**Why it's not in the 556.** Your RWA category (102 hooks) is compliance gating, not market microstructure. Nobody built the closing bell.

**Build sketch (v1 can be small).**
1. `beforeSwap`: check an on-chain market calendar (start with a simple owner-updated schedule; later, an oracle). 
2. Closed hours → apply a higher dynamic fee and per-block trade cap.
3. First N minutes after open → collect swaps into a batch and clear them at one uniform price (or simplest v1: freeze swaps for 10 minutes while an auction determines the reopening price).

**Scores.** Novelty ⭐⭐⭐ · User pull ⭐⭐⭐ · Feasibility ⭐⭐ (v1 with fee-widening + trade caps is very doable; the auction part can come later)

---

## 🥈 Idea 2: The MEV-Tax-for-LPs Hook (Unichain priority ordering)

**One-liner.** On Unichain, read each swap's priority fee in `beforeSwap`; charge an extra fee proportional to it (arb bots pay high priority fees, normal users don't); donate the proceeds to the pool's LPs.

**Why now.** This only became possible when Unichain shipped Flashblocks + provable priority ordering (2025). It's the freshest real mechanism in the ecosystem, the math is published (Paradigm's MEV taxes paper), and Uniswap's own version (PFDA) burns UNI instead of paying LPs — so "the LP-first version" is an obvious, ideologically popular counter-position. Post-fee-switch, LPs need every basis point.

**Potential users.** Every LP on Unichain; pool deployers choosing between a plain pool and a "+MEV rebate" pool. Sponsor alignment is perfect: Unichain was UHI8's dominant track.

**Why it's not in the 556.** Timing — most cohorts predate live Flashblocks. A few hooks gestured at "MEV redistribution," but none could build on real provable priority ordering.

**Build sketch.** Genuinely compact: `beforeSwap` → read `tx.gasprice - block.basefee` → compute `extraFee = k × priorityFee` → collect and donate to LPs via the PoolManager's donate mechanism. The subtlety is calibrating `k` and handling edge cases (contracts batching swaps, refund paths).

**Scores.** Novelty ⭐⭐⭐ · User pull ⭐⭐ · Feasibility ⭐⭐⭐ (smallest core logic of any idea here)

---

## 🥉 Idea 3: The Guard Hook — a circuit breaker for other hooks

**One-liner.** A wrapper that sits between the pool and any "inner" hook, enforcing hard safety invariants (balances never drop faster than X, withdrawals never exceed what the math allows, fees never exceed a cap) — if the inner hook misbehaves, the guard pauses the pool instead of letting it drain.

**Why now.** Bunni died with $8.4M gone *despite audits from Trail of Bits and Cyfrin*. Stream Finance torched the "trust the manager" model. The entire hook ecosystem's growth is bottlenecked on one question — "how can I trust a hook?" — and no standard answer exists.

**Potential users.** Hook developers (a "wrapped in Guard" badge helps them win users — they're your customer), LPs, frontends/aggregators deciding what's safe to route, insurance protocols pricing hook risk.

**Why it's not in the 556.** The 63 "security hooks" defend against bad *tokens* (rugs, scams). Nobody built defenses against bad *hooks*. It's meta-infrastructure, and hackathons chronically underbuild infrastructure.

**Build sketch.** A hook that composes another hook's address, forwards all callbacks, and after each one re-checks invariants (e.g., pool reserves vs. expected deltas; per-block outflow limit). v1 with 2-3 invariants + a pause switch is a complete story. Bonus: publish it as a base contract others inherit.

**Scores.** Novelty ⭐⭐⭐ · User pull ⭐⭐ (developers, not end users — slower adoption but deeper moat) · Feasibility ⭐⭐

---

## Idea 4: pm-AMM Hook — liquidity for prediction market outcome tokens

**One-liner.** Implement Paradigm's pm-AMM curve as a v4 hook: an AMM purpose-built for tokens whose price lives between $0 and $1 and expires at a known date, concentrating liquidity tighter as resolution approaches.

**Why now.** Prediction markets went from $1.2B to $20B+/month; Kalshi is tokenizing outcomes on-chain; the math is published and almost nobody has shipped it. Long-tail markets can't support order books — AMMs are the only structure that works there.

**Potential users.** Prediction platforms extending on-chain, passive LPs wanting outcome-token yield, long-tail market creators.

**Why it's not in the 556.** Prediction markets are nearly absent from your directory — the trend exploded after most cohorts ended.

**Watch out.** You need the custom-curve style of hook (override swap math, e.g. via `beforeSwap` return deltas / NoOp), which is more advanced than fee-tweaking. And testing needs simulated resolution scenarios.

**Scores.** Novelty ⭐⭐⭐ · User pull ⭐⭐ · Feasibility ⭐ (hardest of the top group — real math implementation)

---

## Idea 5: The Boring Vault — provably-safe passive LP after Bunni & Stream

**One-liner.** An auto-rebalancing LP vault hook with a deliberately dumb, fully on-chain strategy (recenter around price once per day, that's it), zero human keys, and invariant checks on every operation — marketed *on* its boringness.

**Why now.** Demand for passive LP yield didn't die with Bunni and Stream — the *supply of trustworthy products* did. "Nothing clever, everything verifiable" is now a selling point.

**Potential users.** Retail passive LPs, DAO treasuries (can't legally hand funds to anonymous curators), refugees from dead products.

**Why it's cautioned.** The irony is brutal: a safety-first vault must itself be bulletproof, and vault accounting is exactly where Bunni died. As a beginner you'd be making a promise ("cannot rug you") that's hard to keep. Great second project after Idea 3 teaches you invariant thinking.

**Scores.** Novelty ⭐⭐ · User pull ⭐⭐⭐ · Feasibility ⭐

---

## Idea 6: Orbital-Lite — a 3-stablecoin concentrated pool with depeg containment

**One-liner.** A simplified version of Paradigm's Orbital: one pool for 3 stablecoins with liquidity concentrated near $1, designed so that if one coin depegs, the other two keep trading normally.

**Why now.** Stablecoins are crypto's biggest product; stablechains (Plasma, Arc, Tempo) are launching; Paradigm published the math and openly invited builders; almost nobody has shipped it.

**Potential users.** Stablecoin issuers seeking deep pools, payment apps, FX-style traders, and every yield strategy that rotates between stables.

**Watch out.** This is the most mathematically demanding idea on the list (n-dimensional geometry → Solidity fixed-point code). Also v4's PoolManager is built around token *pairs* — a 3-asset pool needs creative architecture (e.g., hook-owned reserves with NoOp swaps). Choose this only if the math genuinely excites you.

**Scores.** Novelty ⭐⭐⭐ · User pull ⭐⭐⭐ · Feasibility ⭐

---

## Idea 7: Agent-Safe Pools — execution rails for AI traders

**One-liner.** A hook + small standard that makes a pool safe for AI agents: machine-readable behavior declaration, per-agent spending caps, hard slippage guarantees, and optionally x402-style pay-per-call access.

**Why now.** AI agents are becoming a real trader class (x402, Google's AP2 with PayPal/Mastercard/Amex). Agents need what routers need: pools whose behavior is *predictable by machines* — which conveniently overlaps with Uniswap's own hook-data-standards push.

**Potential users.** Agent framework developers, agent operators, and (indirectly) aggregators — anyone whose software signs transactions without a human watching.

**Honest caveat.** The trend's usage numbers are still shaky (x402 volume fell ~77% from its hype peak before stabilizing). This is a bet on a narrative — great demo appeal, uncertain durable demand.

**Scores.** Novelty ⭐⭐⭐ · User pull ⭐ (future users, few present ones) · Feasibility ⭐⭐

---

## Idea 8: Hook Manifest + Router Adapter — make hooked pools routable

**One-liner.** A tiny on-chain standard where every hook declares "here's exactly how I modify swaps" in machine-readable form, plus a reference router that reads it — attacking the #1 reason hooked pools get no volume.

**Why now.** It's the ecosystem's most load-bearing unsolved plumbing (file 01, Problem 2), and the Uniswap Foundation is actively funding this exact area (hook data standards, $10M grants round targeting protocol tooling).

**Potential users.** Every hook developer, every aggregator, Uniswap Labs itself.

**Honest caveat.** Standards win by adoption, not by code — a solo beginner is unlikely to get 1inch to integrate. Best pursued *through* the Foundation (grant application, collaboration with their standards effort) rather than as a lone hackathon project.

**Scores.** Novelty ⭐⭐ (UF started already) · User pull ⭐⭐⭐ · Feasibility ⭐⭐ (code is easy; adoption is the hard part)

---

## How to choose (my honest take)

- **Want the best story + biggest open field →** Idea 1 (Market Hours Hook). Real trend, funded users, nobody's built it, v1 is scoped small.
- **Want the quickest path to a working, impressive demo →** Idea 2 (MEV Tax for LPs). Least code, newest mechanism, perfect sponsor alignment with Unichain.
- **Want to build a reputation as "the safety person" →** Idea 3 (Guard Hook). The ecosystem's deepest wound (Bunni) with no bandage yet.
- **Love math →** Idea 4 (pm-AMM) or Idea 6 (Orbital-Lite), accepting they're the hardest.
- **A strong combo:** Ideas 1+2 share machinery (both are "conditionally modify fees/behavior in `beforeSwap`") — you could prototype both and keep whichever demos better.

One last pattern from everything researched: **every hook that succeeded (Doppler, Angstrom, EulerSwap, Flaunch) was an invisible engine inside a product someone already wanted** — a launchpad, MEV-free swaps, lending yield. None succeeded as "a cool mechanism looking for users." Whatever you pick, name the user before you write the first line of Solidity.
