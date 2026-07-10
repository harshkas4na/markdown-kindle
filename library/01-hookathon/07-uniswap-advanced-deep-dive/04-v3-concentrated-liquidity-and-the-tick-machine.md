# v3 — Concentrated Liquidity and the Tick Machine

**Fast overview:** v3 (May 2021) lets each LP concentrate capital into a chosen price range instead of spreading it from 0 to ∞, multiplying capital efficiency up to ~4000×. The implementation — ticks, the liquidity value `L`, square-root prices in Q64.96 fixed point, per-tick fee accounting — is the densest machinery in Uniswap, and it is carried into v4 *unchanged*. Every hook you ever write sits on top of this machine, so this chapter earns its length.

## The idea in one picture

A v2 pool's liquidity supports trading at every price from 0 to ∞. But ETH/USDC trades between, say, 2,500 and 4,000 for months at a time. The capital backing prices like $3 or $300,000 does nothing — it's inventory for a day that never comes. Measured against v2, over 99% of typical pool capital is idle.

v3's move: let an LP say "my capital is only for prices between Pa and Pb." Within [Pa, Pb], their position behaves exactly like a (bigger) v2 position; outside it, it converts fully into one asset and goes dormant. Many overlapping ranges from many LPs stack into the pool's total *liquidity profile* — deep where LPs expect trading, thin at the extremes.

Same capital, concentrated where it's used = deeper effective liquidity = better prices for traders and more fee share for the concentrated LP. That's the whole pitch. The price is complexity — and a new obligation: **when price exits your range you earn nothing and hold 100% of the "wrong" asset.** Concentration amplifies fees *and* impermanent loss (*connect the dot:* Chapter 2's short-gamma framing — a narrower range is a shorter option, higher premium, higher risk; this tradeoff is what LP-management hooks like Bunni tried to automate, Chapters 11–12).

## The three variables that run everything: L, √P, and ticks

v3 rewrites the constant product in new coordinates. Define **liquidity** `L` and work with the *square root* of price:

```
L = √(x·y)          √P = √(y/x)
```

Invert these and you get the two identities that make the whole system tick:

```
x = L / √P          y = L · √P
```

Why bother? Because trades become *linear*. For a swap at constant liquidity, the deltas are:

```
Δy = L · Δ√P                Δx = L · Δ(1/√P)
```

Sell Y into the pool and √P rises proportionally to `Δy/L`; no quadratic solving, no products. The swap loop becomes: "how much does √P move for this input, given current L?" — one multiplication. This substitution (due to the v3 whitepaper) is the reason on-chain concentrated liquidity is affordable at all.

**Virtual reserves.** A position on [Pa, Pb] only needs to hold the tokens that could actually be demanded while price is inside its range. The pool *behaves* as if it had big v2-style reserves (`x_virtual = L/√P`, `y_virtual = L·√P`) but only *holds* the difference between the current point and the range edges:

```
x_real = L · (1/√P − 1/√Pb)      (the X you'd pay out as price rises to Pb)
y_real = L · (√P − √Pa)          (the Y you'd pay out as price falls to Pa)
```

At `P = Pa` the position is all X; at `P = Pb` it's all Y (it sold its X on the way up). The efficiency multiple versus v2 for a symmetric range is roughly `1 / (1 − (Pa/Pb)^(1/4))` — for a ±10% range that's ~20×; for a stablecoin range of ±0.01% it reaches the famous ~4000×.

**Ticks.** Ranges can't be arbitrary reals; the price line is discretized into **ticks**, where tick `i` corresponds to price:

```
P(i) = 1.0001^i
```

Each tick is one basis point (0.01%) away from its neighbors — a musically even grid in log-price. Tick indices run from −887272 to +887272 (spanning prices ~2^−128 to 2^128, enough for any token pair ever). Fee tiers impose a `tickSpacing` (e.g. 60 for the 0.3% tier) so only every 60th tick can be a range boundary — fewer possible boundaries means cheaper swaps (fewer ticks to cross). Positions are defined by `(tickLower, tickUpper, L)`.

Each *initialized* tick stores one crucial number: `liquidityNet` — how much `L` turns on or off when price crosses it (positive crossing left-to-right for a range's lower tick, negative for its upper). The pool's current in-range liquidity is the running sum of all `liquidityNet` below the current tick.

## sqrtPriceX96: prices as Q64.96 integers

The EVM has no floats. v3 stores √P as **sqrtPriceX96**: the real value multiplied by 2^96 and kept as a uint160 — "Q64.96" fixed point (64 integer bits, 96 fractional bits). To convert:

```
sqrtPrice = sqrtPriceX96 / 2^96
P         = (sqrtPriceX96 / 2^96)^2
tick      = floor( log_{1.0001}(P) )
```

Real-world reflex you'll need constantly when reading pool state: token amounts have decimals. For USDC(6)/WETH(18), the raw `P` is off by 10^12 from the human price. Every v3/v4 debugging session eventually involves someone forgetting this.

Why √P rather than P in storage: (1) the linear swap algebra above; (2) precision — squaring at the end rather than square-rooting on the fly keeps error tiny; (3) one canonical monotonic value from which tick, price, and both token amounts derive. The library `TickMath` converts tick↔sqrtPriceX96 in a few hundred gas using bit tricks; `SqrtPriceMath` and `SwapMath` do the delta algebra. These exact libraries are imported by v4 core — when your hook misbehaves in Chapter 10's tests, the stack trace will land in them.

## Anatomy of a swap: walking the ticks

A v3 swap is a loop:

1. Given input remaining and current `L`, compute where √P would end up.
2. If that overshoots the next initialized tick, trade only *up to* that tick's √P, consume the corresponding input, and **cross the tick**: add its `liquidityNet` to `L` (ranges begin/end here).
3. Repeat with the new `L` until the input is exhausted or price hits the user's limit (`sqrtPriceLimitX96`).

So a large swap experiences a *piecewise* constant-product curve: deep and gentle through the liquid middle, steeper as it pushes into thin ranges. Gas scales with ticks crossed — why tickSpacing exists, and why crossing many ticks in one swap is the expensive path. (*Connect the dot:* in v4 this loop is the code your `beforeSwap` hook runs in front of, and that a custom-curve hook *replaces entirely*, Chapter 8.)

## Fee accounting: feeGrowthInside

v2 could compound fees into `k` because everyone shared one position. v3 positions are all different, so fees are tracked with a classic accumulator trick:

- The pool keeps `feeGrowthGlobal` — total fees per unit of `L`, ever.
- Each tick stores `feeGrowthOutside` — fees accrued while price was on the *other* side of it, maintained by flipping the value on every crossing.
- Fees earned *inside* a range = global minus the two outside portions:

```
feeGrowthInside = feeGrowthGlobal − feeGrowthBelow(tickLower) − feeGrowthAbove(tickUpper)
```

- A position remembers `feeGrowthInsideLast` from its previous touch; owed fees = `(inside_now − inside_last) · L`.

O(1) per swap, O(1) per collect, arbitrary numbers of positions. This accumulate-and-diff pattern is one of the great reusable tricks of DeFi — staking rewards, dividend tokens, and several of your future hooks will use it. Note the consequence: v3 fees **do not compound** (they sit as owed tokens, not as more L), unlike v2 where fees compound into the pool automatically.

## What else changed

- **Positions are NFTs** (via the periphery `NonfungiblePositionManager`): ranges make positions non-fungible. Losing fungibility broke the "LP token as money lego" pattern — an entire industry (Arrakis, Gamma, Bunni v1) sprang up to wrap v3 positions back into fungible tokens. Hold that thought for the ecosystem chapter.
- **Three fee tiers** (0.05%, 0.3%, 1%) per pair, later extensible by governance — a coarse admission that one fee can't fit all pairs. Dynamic fees remained impossible until v4 (Chapter 9).
- **The oracle got better**: a ring buffer of up to 65,535 observations storing cumulative *tick* (i.e., log price — so the TWAP is a geometric mean, harder to skew with brief spikes than v2's arithmetic mean). v4 deleted even this; oracles became hook business (Chapter 9).
- **Active management became mandatory.** The moment price leaves your range, you're out of the game. Studies through 2021–2023 repeatedly found a large fraction of retail v3 LPs lost money versus holding — concentration without a rebalancing strategy is just leveraged IL (*connect the dot:* Chapter 5 makes the loss mechanism precise; Chapter 12 shows the hooks trying to fix it).

## The mental model to carry forward

Compress v3 to five sentences you'll reuse constantly:

1. Price lives on a log grid of ticks; the pool's state is (current √P as Q64.96, current tick, current L).
2. L is the pool's local depth; it changes only when price crosses an initialized tick.
3. Swaps move √P linearly per unit input at constant L, walking tick to tick.
4. A position = (tickLower, tickUpper, L): a slice of hyperbola with virtual reserves behind it.
5. Fees accrue per-unit-L through accumulators diffed at position boundaries.

v4 keeps every word of this. What v4 changes is *where pools live* (one singleton), *how tokens settle* (flash accounting), and *who's allowed to interfere* (hooks). That's the next act — and the reason this book exists.
