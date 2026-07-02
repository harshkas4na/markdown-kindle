# 09 — Oracles & TWAP

Goal: understand why "just read the pool's current price" is a trap, and what the two real fixes (time-averaging, and external oracles) actually do differently.

## Why a smart contract can't just "know" a price

A smart contract only knows what's inside the blockchain it lives on — it has no built-in ability to reach out to the internet and check Binance's ETH price. If a hook (or any DeFi contract) needs to know "what is ETH actually worth right now," that information has to be brought on-chain by *something* — and the question of "what is that something, and can it be trusted or manipulated" is the entire oracle problem.

## The naive, dangerous answer: just read the pool's current spot price

The simplest possible option is: look at the ratio of tokens currently sitting in the AMM pool itself (article 1's `x` and `y`), and treat that as "the price." The problem: **this price can be manipulated within a single transaction, cheaply, using a flash loan.**

Here's how that attack works: a flash loan lets you borrow an enormous amount of money with zero collateral, *as long as you pay it back within the same transaction*. An attacker can (1) flash-borrow a huge amount of USDC, (2) dump it all into a thin ETH/USDC pool in one trade, wildly distorting the pool's implied price for that single transaction, (3) trigger some *other* contract that naively reads this pool's current spot price as ground truth (e.g. a lending protocol deciding "is this loan under-collateralized?"), tricking it into a bad decision, (4) profit from that bad decision, and (5) pay back the flash loan — all inside one atomic transaction, leaving the pool's price back to normal a block later as if nothing happened, but with the attacker walking away with stolen funds.

**Analogy: imagine a judge who determines the "official" price of a house purely by looking out the window at the very last house sale on the street — even if that sale happened five seconds ago and involved someone secretly overpaying on purpose, one time, specifically because they knew the judge was watching.** A single, recent, easily-staged data point is a terrible source of truth precisely because it's *cheap to fake, temporarily, on purpose.*

## Fix #1: TWAP — Time-Weighted Average Price

Instead of trusting the instantaneous, right-now price, a **TWAP** averages the pool's price *over a window of time* — say, the last 30 minutes. Uniswap v2 and v3 both maintain this kind of running average internally, as a built-in feature, specifically so other contracts can query "give me the average price over the last N minutes" instead of the manipulable spot price.

Why this defeats the flash-loan attack: a flash loan only lasts one transaction, one block. To meaningfully move a 30-minute average, an attacker would need to sustain a distorted price across many blocks — which costs real, ongoing capital at risk over that whole window (other arbitrageurs would also be trading against the distorted price the whole time, fighting the manipulation), rather than a free, single-block, no-risk trick. It doesn't make manipulation *impossible*, but it makes it expensive and risky enough that it's no longer a free lunch.

**Same house-price analogy, fixed**: instead of trusting the single most recent sale, the judge now averages every sale on the street over the last month. Someone could still try to fake a high average by making several overpriced purchases over that whole month — but now it costs them real money for a sustained period, with real risk that someone else undercuts them along the way, instead of one clever five-second trick.

## Fix #2: External oracles (Chainlink, Pyth)

TWAP is good, but it's still only ever *this specific pool's* history — a thinly-traded pool's TWAP can still be nudged more easily than a deeply liquid one. The other major approach is to not rely on any single on-chain pool at all, and instead use a dedicated **oracle network** — a separate system whose entire job is to pull price data from many real-world exchanges, aggregate it, and publish a trusted value on-chain for other contracts to read.

**Chainlink** is the most widely used example: an independent network of node operators, each fetching price data from multiple centralized and decentralized exchanges, whose individual reports get aggregated (typically via a median, to resist any single bad-actor node) into one published on-chain price, updated on a regular cadence or when the price moves past a threshold. **Pyth Network** is a newer, increasingly popular alternative with a different data-sourcing model (pulling directly from trading firms and exchanges as "first-party" data publishers) and generally faster/more frequent updates.

The tradeoff versus TWAP: external oracles add a dependency on a system outside the pool itself — you now have to trust that oracle network's own security model (how many node operators, how are they incentivized, can they be bribed or go offline), rather than trusting only the economics of the pool you're already using.

## Why this shows up so often in the hook directory

Any hook whose logic depends on knowing "the real price" for anything beyond the pool's own trade math — depeg detection for stablecoins, pricing an option, deciding whether a trade is "informed" (moving toward the real price) or "arbitrage-y" (moving away from it, per article 8's directional fees) — needs a reliable price source that isn't just the pool's own easily-nudged spot price. That's why Oracle appears as a tag on 75 different hooks across nearly every other category — it's not really its own separate product idea, it's a dependency almost every other category quietly needs.

## The one sentence to keep

**A smart contract has no native way to know a "real" price, so it must import one — the naive option (reading the pool's current spot price) is cheaply manipulable within a single transaction via flash loans, which is why serious hooks instead rely on either a time-averaged price (TWAP, built into Uniswap itself, which makes manipulation expensive and risky rather than free) or an external, independently-aggregated oracle network like Chainlink or Pyth.**
