# What Uniswap Is Actually Struggling With (Mid-2026)

This file answers one question: **what hurts Uniswap right now that nobody has properly solved with a hook yet?**

Each problem below follows the same format:
- **What's going wrong** — in plain words
- **Why 556 UHI hooks didn't solve it** — checked against your `hook-directory/` folder
- **Who would use a solution** — the potential users
- **The hook opportunity** — what you could actually build

Read this together with `04-hook-ideas-shortlist.md`, which turns these problems into concrete project ideas.

---

## Problem 1: Most v4 hooks are ghost towns (the trust problem)

**What's going wrong.**
Over **1,300 hooks** have been deployed on Uniswap v4 (tracked on [HookRank](https://hookrank.io/)), but real trading volume is concentrated in a tiny handful. Even worse: v4 as a whole still does *less* daily volume than v3 (~$186M vs ~$427M on Ethereum at one recent snapshot). A year and a half after launch, most liquidity never migrated.

The single biggest reason is **trust**. In v3, you only had to trust Uniswap itself. In v4, every pool's safety depends on whatever custom hook is attached to it. Then in September 2025, **Bunni** — the most celebrated hook project, audited by top firms (Trail of Bits, Cyfrin) — got exploited for **$8.4M** through a math rounding bug and [shut down permanently](https://www.coindesk.com/business/2025/10/23/bunni-dex-shuts-down-cites-recovery-costs-after-usd8-4m-exploit). The message everyone took away: *even audited hooks can kill you.*

Right now there is **no standard way** for a normal user, an LP, or an aggregator to answer: "is this hook safe to touch?"

**Why the 556 UHI hooks didn't solve it.**
Your directory has 63 "security hooks," but almost all of them protect against *bad tokens* (rug pulls, scam coins) — not against *bad hooks*. Nobody built the meta-layer: safety infrastructure for the hooks themselves.

**Who would use a solution.**
- Every LP deciding whether to deposit into a hooked pool
- Frontends and aggregators deciding whether to route through a hooked pool
- Hook developers who want a way to *prove* they're safe (they'd pay for this)
- Insurance protocols

**The hook opportunity.**
- A **"guard" wrapper hook**: sits around any other hook and enforces hard safety rules (e.g., "pool balances can never drop more than X% in one block," "withdrawals always get at least what the math says"). If an inner hook misbehaves, the guard freezes the pool instead of letting it drain. Think of it as a circuit breaker *for hooks*, not for tokens.
- A **hook safety registry / scoring system** that aggregators and wallets can read on-chain.
- This is the "picks and shovels" play: you win whenever *anyone else's* hook succeeds or fails.

---

## Problem 2: Hooked pools don't get routed (the chicken-and-egg problem)

**What's going wrong.**
When you swap on Uniswap's website or through an aggregator (1inch, CoW Swap, etc.), a routing algorithm decides which pools your trade goes through. That algorithm needs to *simulate* each pool: "if I put in X, how much do I get out?"

For a plain pool, that's easy math. For a hooked pool, the hook can do *anything* — change the fee mid-trade, pull liquidity, add conditions. Routers can't safely predict that, so **they mostly skip hooked pools entirely**. Research confirms this is an open problem ([Optimal Routing in the Presence of Hooks](https://thogiti.github.io/2025/02/15/Understanding-Uniswap-v4-hooks-optimal-routing-AMM.html)).

The result is a death spiral: no routing → no volume → no fees → LPs leave → even less reason to route there. This, alongside trust, is *the* reason hooks haven't taken off.

Uniswap knows this — the [UNIfication proposal](https://blog.uniswap.org/unification) includes "aggregator hooks" and the Foundation started a [hook data standards](https://www.uniswapfoundation.org/blog/developer-guide-establishing-hook-data-standards-for-uniswap-v4) effort. But it's early and unsolved.

**Why the 556 UHI hooks didn't solve it.**
Because it's not a hook — it's *infrastructure around hooks*. Everyone built pools; almost nobody built the plumbing that lets routers understand pools. (Your directory's "order types & routing" category — 74 hooks — is about limit orders and auctions, not about making hooks routable.)

**Who would use a solution.**
- Every hook developer (their pool finally gets traffic)
- Aggregators and solvers (more liquidity sources = better prices)
- Uniswap Labs/Foundation themselves (they're actively funding this area)

**The hook opportunity.**
- A **"hook manifest" standard**: a small on-chain declaration every hook can publish saying "here is exactly how I change swap behavior, in a machine-readable way," plus a reference router that reads it. 
- A **"router-safe" hook template**: a base contract that guarantees predictable behavior so any pool built on it is automatically routable.
- This is less flashy than a trading strategy, but it's what the ecosystem is visibly missing, and the Foundation gives grants for exactly this.

---

## Problem 3: LPs still lose money — and the fee switch just made it worse

**What's going wrong.**
The oldest problem in AMMs is still unsolved at scale: passive LPs bleed money to arbitrage (LVR — see your `learn/08` file). Research keeps confirming that for volatile pairs, fees usually don't cover the loss.

Then in December 2025, Uniswap governance passed **UNIfication**: the protocol now takes a cut of trading fees (roughly 1/4 to 1/6 of what LPs earn) and uses it to buy and burn UNI ([The Defiant](https://thedefiant.io/news/defi/uniswap-passes-unification-fee-switch-proposal)). Great for UNI holders — but it's a **direct pay cut for LPs** who were already barely breaking even. LPs are now the most squeezed group in the whole ecosystem, and they're the ones every pool depends on.

Meanwhile, competitors attack exactly this weakness: **Fluid DEX** makes the *same capital* work as lending collateral AND trading liquidity at once (up to 39x efficiency, [OAK Research](https://oakresearch.io/en/reports/protocols/fluid-new-defi-standard-unify-dex-lending)), and **EulerSwap** does something similar with Uniswap v4 hooks + lending.

**Why the 556 UHI hooks didn't solve it.**
This is the most-attacked problem in your whole directory (~40% of hooks touch dynamic fees, 126 touch MEV/LVR). But almost all of them are *simulations and demos* — none became a trusted product LPs actually use. The ideas that work in research (am-AMM, MEV taxes, batch auctions) need serious engineering + trust, which hackathon projects never got to.

**Who would use a solution.**
- Passive LPs (retail people who just want yield without babysitting positions)
- DAO treasuries providing liquidity for their own token
- Anyone who left after the fee switch cut their income

**The hook opportunity.**
- The freshest angle: **MEV-tax hooks on Unichain** (see Problem 4) — recapture arbitrage profit and give it back to LPs.
- **Lending-integrated LPing** (EulerSwap-style but for multiple LPs — EulerSwap only supports ONE liquidity provider per pool instance; a multi-LP version is an open gap).
- Honest warning: "dynamic fees" as a pitch is completely saturated. If you go here, your edge must be *distribution and trust*, not another fee formula.

---

## Problem 4: Unichain unlocked a brand-new MEV weapon — and almost nobody has used it yet

**What's going wrong (actually: what's newly possible).**
Unichain (Uniswap's own L2) now runs **Flashblocks**: blocks every ~200-250ms, built inside secure hardware (TEEs) that *provably* orders transactions by priority fee ([Uniswap blog](https://blog.uniswap.org/flashblocks-are-live), [Rollup-Boost](https://writings.flashbots.net/introducing-rollup-boost)).

Why this matters: there's a famous idea called the **MEV tax** ("Priority Is All You Need" by Paradigm, explained simply in `02-new-whitepapers-explained-simply.md`): if you can trust transaction ordering, a smart contract can automatically *charge arbitrage bots most of their profit* and hand it to LPs. On Ethereum mainnet this doesn't work (ordering isn't trustworthy). **On Unichain, since Flashblocks went live, it works.** Faster blocks alone also shrink LVR because arbitrageurs get smaller price gaps to exploit.

Uniswap Labs itself is building one version of this (the Protocol Fee Discount Auction in UNIfication — but that one burns UNI rather than paying LPs). The "give it to LPs" version is wide open.

**Why the 556 UHI hooks didn't solve it.**
Timing. Most cohorts built before Flashblocks + provable priority ordering existed. A few hooks played with "MEV redistribution" concepts, but building on the *live, real* mechanism is genuinely new territory.

**Who would use a solution.**
- LPs on Unichain (their returns directly improve)
- Uniswap Foundation (UHI's biggest sponsor track is literally Unichain — 100 integrations in your tracker, 60% of UHI8 was cross-chain/Unichain)
- Arbitrage bots would *pay* it (unwillingly, but by design)

**The hook opportunity.**
- An **LP-rebate MEV-tax hook**: in `beforeSwap`, read the transaction's priority fee; charge high-priority transactions (= arbitrage bots racing to be first) an extra fee proportional to their priority fee; donate it to the pool's LPs. Conceptually simple, very demo-able, and perfectly aligned with what the sponsor wants to see.

---

## Problem 5: The "smart vault" vacuum — Bunni is dead and the curator model blew up

**What's going wrong.**
Normal people can't manage concentrated liquidity (choosing price ranges, rebalancing — see your `learn/04`). They need vaults that do it for them. Two things just destroyed this market's supply side:

1. **Bunni** (the best v4 auto-managing LP product) died from its exploit in late 2025.
2. The **curator model** — "deposit here, a professional manages your money" — had a catastrophic 2025-26: Stream Finance lost **$93M** of user funds through an opaque off-chain manager, its stablecoin crashed 77%, and the contagion froze $160M+ and left Euler with $137M bad debt ([S&P Global](https://www.spglobal.com/ratings/en/regulatory/article/digital-assets-brief-stream-finances-collapse-highlights-defi-contagion-risks-s101661035), [Tiger Research](https://reports.tiger-research.com/p/collapse-of-the-defi-jenga-the-stream-eng)). Analysts warn ~$8B sits in similar structures.

So the demand (passive LP yield) is fully intact, but users no longer trust (a) clever hook math after Bunni, or (b) human managers after Stream. What's missing is a vault where **you don't have to trust anyone** — every rule is on-chain, verifiable, with hard limits.

**Why the 556 UHI hooks didn't solve it.**
Liquidity management is your directory's #2 category (153 hooks), but they're all *strategies*. The market gap isn't a smarter strategy — it's **provable safety of a simple strategy**. Nobody built "the boring vault that mathematically cannot rug you."

**Who would use a solution.**
- Retail passive LPs (the biggest underserved group in DeFi)
- DAO treasuries (they legally/socially can't hand funds to anonymous curators)
- Ex-Bunni and ex-curator-vault users looking for a home

**The hook opportunity.**
- A **transparent, rules-only rebalancing hook**: dead-simple strategy (e.g., keep liquidity centered around the current price, rebalance at most once a day), zero human control, invariant checks on every action (inspired directly by how Bunni died: their withdrawal math could pay out more than it should — your hook re-verifies balances after every operation and reverts if anything is off).

---

## Problem 6: Tokenized stocks trade 24/7 — but the real market closes (the "weekend problem")

**What's going wrong.**
Tokenized stocks are exploding: Kraken's xStocks, Robinhood's tokenized equities, and now the **NYSE itself is building a 24/7 tokenized stock venue** ([CoinDesk](https://www.coindesk.com/markets/2026/01/19/nyse-to-launch-24-7-blockchain-powered-tokenized-stock-and-etf-trading)). But there's a structural flaw nobody has solved for AMMs:

**When the real stock market is closed (nights, weekends), a tokenized Tesla pool has no anchor price.** No oracle to arbitrage against. Regulators specifically flag this: thin weekend liquidity is easy to manipulate, and there are **no circuit breakers** on-chain like real markets have. And when the real market reopens Monday after weekend news, whoever trades first against the stale AMM price extracts money from LPs — it's LVR in its most brutal form.

Traditional markets solved this a century ago with **opening auctions** and trading halts. On-chain AMMs have… nothing.

**Why the 556 UHI hooks didn't solve it.**
Your RWA category (102 hooks) is almost entirely *compliance* — KYC gates, whitelists. Market *microstructure* for assets-with-a-closing-bell (halts, reopening auctions, weekend fee curves) is essentially untouched. This is a real, growing, unsolved niche.

**Who would use a solution.**
- Tokenized equity issuers (Backed, Ondo, Securitize, Dinari — real companies with budgets)
- Exchanges bringing stocks on-chain
- LPs in RWA pools (they currently get destroyed every Monday morning)
- This is also where all institutional interest in 2026 is pointed (see `03-defi-trends-2026.md`)

**The hook opportunity.**
- A **market-hours-aware hook**: knows the NYSE calendar; during closed hours it widens fees (compensating LPs for the extra risk) or restricts trade size; at Monday open it runs a short **reopening auction** (batch all pending trades, settle them at one fair clearing price) instead of letting the fastest bot eat the LPs. Novel, explainable in one sentence, and aimed at a market that's arriving *right now*.

---

## Problem 7: Prediction market outcome tokens are coming on-chain with no good AMM

**What's going wrong.**
Prediction markets went mainstream: from ~$1.2B/month in early 2025 to **$20B+/month in early 2026** ([TRM Labs](https://www.trmlabs.com/resources/blog/how-prediction-markets-scaled-to-usd-21b-in-monthly-volume-in-2026)). Kalshi and Polymarket own ~97% of it — using order books, not AMMs, because classic AMMs are *bad* at prediction markets (a "share of YES" behaves nothing like a token: its price lives between $0 and $1, it expires at a known date, and it jumps to exactly $0 or $1 at resolution).

Now **Kalshi has started tokenizing outcomes on-chain** (starting with Solana), which means outcome tokens will need permissionless secondary liquidity everywhere — and Paradigm already published the math for a proper prediction-market AMM (**pm-AMM**, explained in file 02), which almost nobody has productionized as a Uniswap v4 hook.

**Why the 556 UHI hooks didn't solve it.**
Prediction markets barely appear in your directory at all — it's arguably the biggest 2026 consumer trend with the least UHI coverage.

**Who would use a solution.**
- Prediction market platforms extending on-chain
- Market makers who want passive exposure to outcome-token spreads
- Long-tail markets that order books can't serve (order books need active market makers; AMMs don't)

**The hook opportunity.**
- A **pm-AMM hook**: implement Paradigm's prediction-market curve as a v4 hook, with an expiry-aware liquidity schedule (concentrate liquidity more tightly as resolution approaches) and a freeze-at-resolution guard.

---

## Problem 8: Uniswap is spot-only in a perps world (know about it, probably don't build it)

**What's going wrong.**
Hyperliquid runs ~**70% of all on-chain perpetual futures**, doing $180B+ monthly — more than every other venue combined ([CoinDesk](https://www.coindesk.com/markets/2026/01/19/hyperliquid-extends-lead-in-perp-dex-race-as-rivals-volumes-fade)). Perps are where crypto's real trading volume lives, and Uniswap has zero presence there. Meanwhile Solana DEXes flipped Ethereum DEXes in spot volume ($117B vs $52B in January 2026).

**Why you probably shouldn't build this.**
Building perps on an AMM via hooks means solving funding rates, liquidations, and margin — a quant-heavy, high-risk project (only 21 of 556 UHI hooks even attempted derivatives, and none stuck). Included here for completeness: it's Uniswap's biggest *strategic* gap, but it's a bad first project. If the leverage theme attracts you, EulerSwap-style lending integration (Problem 3) is the saner entry.

---

## The one-paragraph summary

Uniswap's 2026 problems are not "we need a better fee formula" — that race is over-crowded and mostly lost. The real gaps are: **trust** (nobody can tell a safe hook from a time bomb — Problem 1, 5), **plumbing** (hooked pools are invisible to routers — Problem 2), **a brand-new mechanism nobody has exploited** (provable priority ordering on Unichain enables MEV taxes for LPs — Problem 4), and **new asset classes arriving without market structure** (tokenized stocks with closing bells, prediction market outcome tokens — Problems 6, 7). The best opportunities are where a trend is arriving *right now* and the 556 previous hooks simply predate it.

---

## Sources

- [Uniswap Review 2026: v4 Hooks, Fee Switch Economics](https://cryptoadventure.com/uniswap-review-2026-v4-hooks-fee-switch-economics-and-the-dex-reality/) · [HookRank](https://hookrank.io/)
- [Bunni shutdown — CoinDesk](https://www.coindesk.com/business/2025/10/23/bunni-dex-shuts-down-cites-recovery-costs-after-usd8-4m-exploit) · [Bunni exploit analysis — QuillAudits](https://www.quillaudits.com/blog/hack-analysis/bunni-v2-exploit)
- [UNIfication — Uniswap blog](https://blog.uniswap.org/unification) · [Fee switch passes — The Defiant](https://thedefiant.io/news/defi/uniswap-passes-unification-fee-switch-proposal)
- [Optimal routing with hooks — paper review](https://thogiti.github.io/2025/02/15/Understanding-Uniswap-v4-hooks-optimal-routing-AMM.html) · [Hook data standards — Uniswap Foundation](https://www.uniswapfoundation.org/blog/developer-guide-establishing-hook-data-standards-for-uniswap-v4)
- [Flashblocks live on Unichain](https://blog.uniswap.org/flashblocks-are-live) · [Rollup-Boost — Flashbots](https://writings.flashbots.net/introducing-rollup-boost)
- [Stream Finance collapse — S&P Global](https://www.spglobal.com/ratings/en/regulatory/article/digital-assets-brief-stream-finances-collapse-highlights-defi-contagion-risks-s101661035) · [Tiger Research retrospective](https://reports.tiger-research.com/p/collapse-of-the-defi-jenga-the-stream-eng)
- [NYSE 24/7 tokenized venue — CoinDesk](https://www.coindesk.com/markets/2026/01/19/nyse-to-launch-24-7-blockchain-powered-tokenized-stock-and-etf-trading) · [How tokenized stocks trade 24/7](https://www.tokenizedpod.com/learn/tokenized-stocks-24-7-trading)
- [Prediction markets scale to $21B/mo — TRM Labs](https://www.trmlabs.com/resources/blog/how-prediction-markets-scaled-to-usd-21b-in-monthly-volume-in-2026)
- [Hyperliquid dominance — CoinDesk](https://www.coindesk.com/markets/2026/01/19/hyperliquid-extends-lead-in-perp-dex-race-as-rivals-volumes-fade)
- [Fluid DEX — OAK Research](https://oakresearch.io/en/reports/protocols/fluid-new-defi-standard-unify-dex-lending) · [EulerSwap](https://www.euler.finance/blog/introducing-eulerswap)
