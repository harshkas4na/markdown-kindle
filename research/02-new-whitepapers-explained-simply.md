# New Whitepapers & Big Ideas, Explained Simply

These are the research ideas people in DeFi are actually talking about in 2025–2026. Each one is explained the same way: **the problem → the idea in one sentence → how it works (simply) → status → what a hook builder can take from it.**

You already know the older foundations from your `learn/` folder (LVR = `learn/08`, MEV = `learn/07`, concentrated liquidity = `learn/04`). Everything below builds on those.

---

## 1. Orbital — concentrated liquidity for MANY stablecoins at once (Paradigm, June 2025)

**The problem.** Uniswap v3/v4 pools hold exactly 2 tokens. But there are now dozens of major stablecoins (USDC, USDT, DAI, PYUSD, USDe…), and connecting them pairwise needs tons of separate pools with scattered liquidity. Curve can hold many tokens in one pool, but LPs can't concentrate their money the way Uniswap v3 lets them.

**The idea in one sentence.** One pool holding *any number* of stablecoins, where LPs can still concentrate their liquidity around the $1 point — like Uniswap v3, but in many dimensions.

**How it works, simply.** Imagine all possible price combinations of 5 stablecoins as points on a globe. "Everything = $1" is one specific spot on that globe. Orbital lets an LP say "I'll provide liquidity only in a *ring* around that spot" (prices near $1) instead of covering the whole globe. Tighter ring = more trading power per dollar. Clever bonus: if one stablecoin totally collapses to $0, the rest of the pool keeps trading the healthy coins at fair prices.

**Status.** Published as a design/whitepaper ([paradigm.xyz/2025/06/orbital](https://www.paradigm.xyz/2025/06/orbital)); Paradigm explicitly invited developers to build it. Implementations are still rare — this is one of the most "open for grabs" pieces of serious math out there.

**Takeaway for you.** Full Orbital is heavy math. But a simplified 3-stablecoin version as a v4 hook, or even just the "depeg containment" feature, would be a standout project. Stablecoins are the #1 growing asset class (see file 03) — the demand side is guaranteed.

---

## 2. am-AMM — auction off the right to run the pool (2024 paper; implemented by Bunni)

**The problem.** Arbitrage bots extract value from LPs (LVR). Fees are a blunt tool: too low and LPs bleed, too high and traders leave.

**The idea in one sentence.** Continuously auction off the role of "pool manager"; the winner pays rent to LPs and in exchange gets to set fees and collect them.

**How it works, simply.** Whoever values controlling the pool the most is usually an arbitrageur — so instead of letting them extract value for free, make them *bid for the privilege*. Their winning bid (the rent) flows to LPs. The manager then sets fees smartly to make their money back. LPs get a steady rent income that automatically prices in how much extraction is happening.

**Status.** Bunni v2 implemented it on Uniswap v4 — then Bunni died from an unrelated accounting bug. The *mechanism* was never disproven; its flagship implementation just disappeared. The [Bunni v2 code is now MIT-licensed / open source](https://github.com/Bunniapp/bunni-v2).

**Takeaway for you.** The best-validated LP-protection mechanism is currently orphaned. Reviving a *minimal, simple* am-AMM hook (without Bunni's complex liquidity-shaping math that caused the hack) is a legitimate niche. Also a cautionary tale: complexity kills — Bunni's exploit was in its fancy extra features, not in am-AMM itself.

---

## 3. MEV Taxes / "Priority Is All You Need" (Paradigm, 2024 — newly practical in 2025-26)

**The problem.** Arbitrage bots race to be first in the block to capture profit (that race's winnings mostly go to block builders/validators, not to the LPs being drained).

**The idea in one sentence.** If transactions are provably ordered by how much priority fee they pay, an app can charge users an extra fee *proportional to their priority fee* — which almost perfectly taxes arbitrage bots (who pay high priority to be first) while barely touching normal users.

**How it works, simply.** A bot that expects $100 profit from arbitraging your pool will pay up to ~$99 in priority fees to win the race. So the priority fee *reveals* how much MEV the transaction captures. A hook that reads it and says "you must also pay the pool 90× your priority fee" converts that hidden profit into LP income. Normal users pay tiny priority fees, so they barely notice.

**Status.** This was theory until **Unichain shipped Flashblocks** (200-250ms blocks built in secure hardware that *provably* order by priority fee — [blog.uniswap.org/flashblocks-are-live](https://blog.uniswap.org/flashblocks-are-live)). Uniswap's own UNIfication proposal now includes a cousin of this (PFDA, below). The "tax goes to LPs" version as a public hook: still wide open.

**Takeaway for you.** Probably the single freshest *mechanism* a beginner can build something real on: the hook logic itself is short (read priority fee in `beforeSwap`, charge extra, donate to LPs), and it only became possible recently, which is why your 556-hook directory barely touches it.

---

## 4. PFDA — Protocol Fee Discount Auctions (Uniswap Labs, part of UNIfication, late 2025)

**The problem.** Same MEV leak, seen from Uniswap's perspective: arbitrage profit leaves the ecosystem.

**The idea in one sentence.** Auction off a short time window during which one address can swap *without paying protocol fees* — arbitrage bots buy these windows, and their payments go to burning UNI.

**How it works, simply.** If you're a bot doing constant arbitrage, protocol fees eat your margin. Uniswap sells you a "fast pass": bid in an auction, win the right to skip protocol fees for a few seconds. Bots' bids ≈ the MEV they expect. Uniswap's own analysis says this could improve effective LP economics by ~$0.06–$0.26 per $10k traded — significant when typical LP profit on $10k of volume is between –$1 and +$1 ([UNIfication](https://blog.uniswap.org/unification)).

**Status.** Approved with UNIfication (passed Dec 2025), rolling out. Proceeds burn UNI rather than paying LPs.

**Takeaway for you.** Understand it because it's the official direction — and notice the gap it leaves: it's tuned for *UNI holders*. An LP-first variant (auction proceeds → LPs) is a distinct, defensible idea.

---

## 5. pm-AMM — an AMM designed for prediction markets (Paradigm, late 2024)

**The problem.** Normal AMM curves are wrong for prediction market shares. A "YES" share is always worth between $0 and $1, its value jumps to exactly $0 or $1 at a known resolution date, and uncertainty shrinks as that date approaches. Uniswap-style curves waste most liquidity at impossible prices and get destroyed near resolution.

**The idea in one sentence.** A purpose-built curve for outcome tokens whose liquidity automatically adapts to the time remaining until the market resolves.

**How it works, simply.** The paper models outcome prices the way finance models options (uncertainty shrinks as expiry nears) and derives the AMM shape that keeps LP losses *uniform over time* instead of exploding at the end. Practically: the pool automatically concentrates liquidity tighter and tighter as resolution approaches, then stops before the final jump.

**Status.** Published at [paradigm.xyz/2024/11/pm-amm](https://www.paradigm.xyz/2024/11/pm-amm). Very few production implementations. Meanwhile prediction markets hit $20B+/month and Kalshi began tokenizing outcomes on-chain — outcome tokens are about to need AMM liquidity everywhere.

**Takeaway for you.** Trend (file 03, prediction markets) + published math + no dominant implementation + near-zero UHI coverage = one of the clearest whitepaper-to-hook opportunities on this list.

---

## 6. EulerSwap — your LP position is also your lending position (Euler, 2025)

**The problem.** Capital in DeFi is lazy: money in an AMM pool just sits waiting for trades; money in a lending market just sits earning interest. You have to choose.

**The idea in one sentence.** An AMM built as a Uniswap v4 hook where the "pool" is actually a lending account — liquidity is borrowed on demand the moment a swap needs it.

**How it works, simply.** When a trader wants to buy tokens the pool doesn't currently hold, the hook *borrows* them instantly from Euler's lending market, using the trader's incoming tokens as collateral. The same dollars earn lending interest AND trading fees, simulating up to ~50x the depth of a normal pool ([whitepaper](https://raw.githubusercontent.com/euler-xyz/euler-swap/7080c3fe0c9f935c05849a0756ed43d959130afd/docs/whitepaper/EulerSwap_White_Paper.pdf)). Fluid DEX proved the concept's power independently: it beat Uniswap's ETH/USDC pool volume with only $6M TVL.

**Status.** Live and growing. Notable limitation: **each EulerSwap pool has exactly ONE liquidity provider** (an operator account). Passive multi-LP versions don't exist yet.

**Takeaway for you.** "Same capital, multiple jobs" is where AMM design is clearly heading. The one-LP-only limitation is a visible open gap, though building on lending infrastructure is intermediate-to-advanced difficulty.

---

## 7. Doppler — fair token launches via built-in Dutch auction (Whetstone, 2024-25)

**The problem.** New token launches get sniped: bots buy the first block, price pumps, retail buys the top, everyone gets dumped on.

**The idea in one sentence.** A v4 hook that runs a *descending-price auction* for new tokens: the price starts high and drifts down until real buyers step in, making sniping pointless.

**How it works, simply.** If the price starts artificially high and only moves down over time, there's no advantage to being the first bot in — buying instantly means overpaying. Buyers reveal genuine demand at their real price. The whole auction happens inside the hook; when it ends, the token graduates to a normal pool. ([Whitepaper](https://www.doppler.lol/whitepaper.pdf))

**Status.** Live and successful — one of the few genuine v4 hook success stories, powering token launch platforms. Proof that the winning hook formula is "hook as invisible engine behind a consumer product," not "hook as standalone pool."

**Takeaway for you.** Study it as the model for how hooks actually win adoption. The launch niche itself is now competitive (Doppler, Flaunch).

---

## 8. FM-AMM / CoW AMM — kill sandwiches with batch auctions (2023-24, relevant background)

**The problem.** Anyone whose trade executes at a specific moment in a specific order can be sandwiched (see `learn/07`).

**The idea in one sentence.** Collect all trades for a short interval, execute them together at ONE uniform clearing price — no ordering within the batch, nothing to sandwich.

**How it works, simply.** If everyone in the batch gets the same price, being "first" means nothing, so front-running is structurally impossible rather than just harder. **Angstrom** (Sorella Labs, backed by $7.5M from Paradigm) shipped this as a Uniswap v4 hook in mid-2025: off-chain batch matching + encrypted orders + on-chain settlement at a uniform price, protecting both swappers and LPs ([launch coverage](https://crypto-economy.com/uniswap-presents-angstrom-new-dex-with-native-mev-protection-for-swappers-and-lps/)).

**Takeaway for you.** This slot is taken by a well-funded team — don't compete head-on. But Angstrom validates that serious people believe hook-based MEV protection is a venture-scale business.

---

## 9. Flashblocks / Rollup-Boost — faster blocks quietly shrink LVR (Flashbots + Uniswap, 2025)

**The problem.** LP losses to arbitrage (LVR) grow with the *time gap* between blocks: more time = bigger price moves = juicier arbitrage against stale AMM prices.

**The idea in one sentence.** Cut block time to 200-250ms using secure hardware (TEEs), and enforce fair, provable transaction ordering while you're at it.

**How it works, simply.** Research shows LVR scales with block time — roughly, 10x faster blocks ≈ ~3x less arbitrage loss. Unichain's Flashblocks deliver ~200ms effective confirmation with the ordering rules (highest priority fee first) enforced *inside tamper-proof hardware*, so contracts can finally trust the ordering ([blog.uniswap.org/flashblocks-are-live](https://blog.uniswap.org/flashblocks-are-live)).

**Takeaway for you.** This is the *enabler* for idea #3 (MEV taxes). Infrastructure-level change → application-level opportunity that older hooks never had.

---

## 10. Honorable mentions (one line each)

- **Fluid "Smart Collateral / Smart Debt"** — even your *debt* can be trading liquidity earning fees; the most capital-efficient DEX design live today ([Fluid docs](https://blog.instadapp.io/fluid-dex/)).
- **Aggregator hooks (UNIfication)** — Uniswap plans to route through *external* liquidity sources via hooks and charge fees on it, turning v4 into an on-chain aggregator ([UNIfication](https://blog.uniswap.org/unification)).
- **Hook data standards (Uniswap Foundation)** — early push to make hooks machine-readable for routers; directly related to Problem 2 in file 01 ([UF blog](https://www.uniswapfoundation.org/blog/developer-guide-establishing-hook-data-standards-for-uniswap-v4)).
- **LVR paper (Milionis et al., 2022)** — the foundation under half this file; you already have it in `learn/08`.

---

## What all of this says, in one paragraph

The research frontier has moved past "tweak the fee." The live ideas are **structural**: change *who gets to extract* (am-AMM, MEV taxes, PFDA), change *when trades settle* (batch auctions, Flashblocks), change *what the capital does while it waits* (EulerSwap, Fluid), and design *purpose-built curves for new asset types* (Orbital for stablecoins, pm-AMM for predictions, Doppler for launches). The pattern in every success story: the hook is an invisible engine inside a product people already want — never a standalone "cool mechanism" looking for users.
