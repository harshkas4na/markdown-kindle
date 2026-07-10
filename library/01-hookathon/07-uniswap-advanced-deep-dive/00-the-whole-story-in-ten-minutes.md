# The Whole Story in Ten Minutes

This book teaches Uniswap the way you'd want to learn a good story: first the whole plot at high speed, so your mind has a skeleton to hang details on — then each chapter re-tells one act slowly, with all the math, code, and consequences. Read this chapter fast. Don't stop to fully understand anything. Everything here gets its own deep chapter later.

## Act 1 — The problem (Chapters 1–2)

Markets need *market makers*: someone always willing to buy and sell, quoting two prices and living off the gap. On Wall Street that's a firm with servers next to the exchange. On a blockchain in 2017, nobody could do that job — blocks were slow, gas was expensive, and order books on-chain were unusable.

Uniswap's answer was almost embarrassingly simple: replace the market maker with a formula. Put two tokens in a pot, and enforce one rule — after every trade, the product of the two reserves must not decrease:

```
x · y = k
```

That single equation *is* a market maker. It always quotes a price (the ratio of reserves), it always has inventory (the reserves themselves), and it automatically charges more per unit as you buy more (slippage), which is exactly what a human market maker does when someone big walks in. Chapter 2 derives everything from this equation: spot price, execution price, slippage, LP share value, and the famous *impermanent loss* — the fact that a pool passively sells winners and buys losers, so LPs underperform simply holding the tokens whenever prices move.

## Act 2 — The workhorse and the upgrade (Chapters 3–4)

**Uniswap v2** (2020) is the industrial version of the formula: any ERC-20 pair, LP shares as tokens, a manipulation-resistant *TWAP price oracle*, and *flash swaps* (take tokens out first, pay by the end of the transaction). Its architecture — a minimal, trustless *core* and a friendly, replaceable *periphery* — became the design pattern half of DeFi copied. v2 still runs today, unchanged, securing billions. Understand v2 and you understand 80% of every AMM ever built.

**Uniswap v3** (2021) attacked v2's big waste: liquidity spread uniformly from price 0 to price ∞, when trading happens in a narrow band. v3 lets each LP pick a *price range* [Pa, Pb] and concentrate capital there — up to ~4000× more capital-efficient. The machinery that makes this work is the heart of the chapter: the price line chopped into *ticks* at multiples of 1.0001, prices stored as square roots in 96-bit fixed point (`sqrtPriceX96`), the liquidity value `L`, and swaps that walk tick to tick, using only the liquidity that's "in range" at each step. A v3 position is no longer a passive share — it's a bet on a range, mathematically equivalent to selling an option. This math survives unchanged in v4, which is why we need it before hooks.

## Act 3 — The villain (Chapter 5)

Now the uncomfortable act. A pool's price only updates when someone trades against it, so the pool is always slightly *stale* versus the wider market. Arbitrageurs correct it — and every correction is money taken from LPs. Formalized, this is **LVR (loss-versus-rebalancing)**: the systematic cost of being the counterparty to better-informed traders. Research pegs it at roughly 5–7% of liquidity per year for major pools — often more than fee income. Meanwhile traders get *sandwiched* by bots that see their pending swap and trade around it — one slice of the broader phenomenon called **MEV** (maximal extractable value). Chapter 5 makes both precise. Keep them in mind through everything that follows, because *most interesting hooks exist to fight exactly these two leaks.*

## Act 4 — The reinvention (Chapters 6–8)

**Uniswap v4** (January 2025) changes the plumbing and opens the logic.

Plumbing: instead of one contract per pool, *every pool lives inside one singleton* `PoolManager`. Multi-hop swaps stop moving tokens between pool contracts; instead the singleton keeps a running tab. That tab is **flash accounting**: during a transaction, balances are tracked as signed *deltas* in transient storage (EIP-1153 — storage that auto-erases at the end of the transaction, ~20× cheaper). You `unlock` the manager, do any number of swaps/liquidity changes inside a callback, and only the *net* amounts move as real token transfers at the end. The rule is simply: all deltas must be zero before the lock closes.

Logic: **hooks**. A hook is your own contract that the PoolManager calls at up to ten lifecycle points — before/after initialize, add liquidity, remove liquidity, swap, donate. Which callbacks fire is encoded *in the hook contract's address itself* (the low 14 bits are permission flags — hence "address mining" with CREATE2). With the *delta-returning* permissions, a hook can go beyond observing: it can take a cut of a swap, replace the x·y=k curve entirely with its own math, or fully "no-op" the pool's swap and settle it some other way. That's Chapter 8's territory — `BeforeSwapDelta`, custom curves, async swaps — the deepest and most dangerous part of v4.

The consequence: a pool is no longer a product, it's a *platform*. Fees can be dynamic (Chapter 9). Oracles can be built to taste. And every idea from Act 3 — MEV taxes, auction-based arbitrage, dynamic fees that price out toxic flow — becomes a weekend of Solidity instead of a new protocol.

## Act 5 — Practice and consequences (Chapters 10–11)

Chapter 10 is the workshop: building hooks with Foundry, the v4-template, mining the hook address, testing against a local PoolManager, fuzzing your invariants. Chapter 11 is the morgue: how hooks fail. The headline case is **Bunni** — the most sophisticated LP-optimization hook of 2025, audited by top firms, drained of $8.4M in September 2025 through a *rounding direction* bug in its liquidity redistribution math, and shut down a month later. The lesson generalizes: in v4, every hook is its own trust domain; the pool is only as safe as the weirdest code attached to it. You'll learn the standard vulnerability classes (permission/implementation mismatch, delta mis-accounting, reentrancy through callbacks, rounding, donation/manipulation of hook state) and the checklist that catches them.

## Act 6 — The frontier (Chapters 12–13)

Finally, the state of the art as of mid-2026. v4 is live on 15+ chains with roughly $355B cumulative volume; hooks have produced real, novel financial machinery: **EulerSwap** (swap liquidity that simultaneously earns lending yield), **Angstrom** (batch auctions at a uniform clearing price to neutralize sandwiches and return arb value to LPs), **Flaunch** (token launchpads with programmable fee flows), plus research designs like the **am-AMM** (auction off the right to be first in the block, pay LPs the proceeds) and **MEV taxes** on priority fees, and Unichain's 250ms flashblocks squeezing LVR by making prices less stale. Chapter 13 closes with how to *design* a hook of your own — which is, after all, why this book is on your shelf.

## How to read

- Chapters build strictly on each other. The math of Chapter 2 is reused in 4; 4's tick machinery is assumed in 6–8; 5's villains motivate 9 and 12.
- Formulas are written in plain code blocks; every symbol is named when introduced.
- When you see "*connect the dot*" — that's a deliberate callback to an earlier chapter. Those links are the actual point of the book.

Turn the page. We start where markets started: with the problem of the missing counterparty.
