# 04 — Uniswap v3: Concentrated Liquidity & Ticks

Goal: understand exactly what "concentrated liquidity" means, what a "tick" physically is, and why this upgrade is what made LPing feel like active portfolio management instead of "deposit and forget."

## The wasted-capital problem, made concrete

Recall from article 3: a v2 Pair spreads your liquidity across the *entire* price curve, from 0 to infinity. But ETH/USDC has, in practice, traded somewhere between roughly $1,500 and $4,000 for most of the last couple of years. If your money is mathematically "available" to trade at $0.01 or $10,000,000 per ETH, but the price will realistically never go there, that portion of your capital is just sitting completely idle, earning zero fees, forever.

**Analogy: imagine a toll booth operator who's required, by law, to also staff toll booths on every road in the country, including ones nobody has ever driven on.** Most of their staff sit in empty booths all day. Concentrated liquidity is the toll company realizing: "let me only staff the three booths that actually see traffic, and put my best people there" — same total staff (capital), way more toll collected per person, because it's all concentrated where the actual demand is.

## What "concentrated liquidity" actually means

In v3, an LP doesn't just deposit into "the ETH/USDC pool" anymore — they choose a **price range**: "I want my capital to be active only between $1,800 and $2,200 per ETH." Within that chosen range, their capital behaves like a much smaller, much deeper v2-style pool — meaning it earns a disproportionately larger share of the fees generated while the price is inside that band, because it's not diluted across the whole 0-to-infinity curve.

The tradeoff: the moment the real price of ETH moves outside your chosen range (say it drops to $1,700), your position stops earning any fees at all — it goes fully "out of range," sitting idle, until either the price comes back in, or you manually withdraw and pick a new range. This exact "out of range = idle" state is the specific pain point behind most of the `liquidity-management-incentives.md` category in the hook directory — hooks that auto-rebalance your range, or auto-deploy your idle capital elsewhere while you're out of range, are directly patching this v3-introduced problem.

## Ticks: the actual unit of price

Uniswap v3 doesn't let you pick literally any price as a range boundary — prices are quantized into discrete steps called **ticks**. Each tick represents a 0.01% (1 basis point) price change from the previous tick. So instead of a smooth, continuous price line, v3 works on a very fine-grained staircase of possible prices, and every LP position's range boundaries must land on a tick.

**Analogy: think of ticks like the marks on a ruler.** You could, in theory, want to measure something at 4.5cm, but if your ruler only has marks every 0.01mm, you're still functionally continuous for any real-world purpose — the granularity is fine enough that it feels smooth, but under the hood it's actually a huge, finite list of discrete positions, not truly continuous. This matters practically because it's *why* the contract can track "how much liquidity is active at this exact price" efficiently — it just needs to track how much liquidity crosses in and out at each tick boundary, rather than doing continuous calculus.

Why quantize at all instead of using real numbers? Efficiency and predictability: fixed-point discrete math is cheaper and safer to run on a blockchain (where every computation costs real gas) than continuous floating-point-style math, and having a finite, well-defined set of boundaries makes it possible to efficiently track exactly how much liquidity is active at the current price without scanning every LP position in existence on every single trade.

## What this buys you, and what it costs you

**Capital efficiency**: the headline win. The same dollar amount of liquidity, concentrated in the range where trading actually happens, can provide vastly deeper liquidity (less slippage for traders) than the same dollar amount spread thin across all possible prices.

**Active management burden**: the cost. In v2, you deposit once and you're done — impermanent loss still applies, but there's no "range" to babysit. In v3, choosing too narrow a range means you earn great fees while in-range but go idle constantly as price moves; choosing too wide a range gives you back something closer to v2's "always active but diluted" behavior. There's no free lunch — narrower ranges mean higher potential fee income *and* higher chance of going out-of-range and needing attention.

This exact tension — "I want v3's capital efficiency but I don't want to babysit my range all day" — is the single most common product idea in the entire hook directory: an "auto-rebalancing" or "auto-compounding" hook is, at its core, a piece of code that watches the price and moves your range for you, so a human doesn't have to.

## The one sentence to keep

**Concentrated liquidity lets an LP choose a price range to focus their capital on (measured in discrete steps called ticks) instead of spreading it across every possible price, which multiplies fee income while active — but turns LPing from a "set and forget" activity into something that needs active range management the instant the market moves, which is exactly the gap dozens of hooks in this directory are trying to automate away.**
