# Everything Hiding Inside x·y = k

**Fast overview:** this chapter squeezes the constant-product formula until it confesses everything: where the price comes from, what slippage really is, why bigger pools are better, exactly how much LPs make or lose, and the precise formula for impermanent loss. This is the one chapter of pure math in Part One — but every equation returns later wearing v3 or v4 clothes, so the effort compounds.

Notation for the whole book: pool holds `x` units of token X (say ETH) and `y` units of token Y (say USDC). `P` is the price of X in terms of Y. `k = x · y`.

## 1. Spot price: why P = y/x

Trade an infinitesimally small amount `dx` of X into the pool and receive `dy` of Y. The invariant must hold before and after:

```
(x + dx)(y − dy) = xy
xy − x·dy + y·dx − dx·dy = xy
```

The `dx·dy` term is negligibly small (product of two infinitesimals), so:

```
y·dx = x·dy   →   dy/dx = y/x
```

The marginal rate of exchange — the **spot price** — is just the ratio of reserves. A pool with 1,000 ETH and 3,000,000 USDC quotes ETH at 3,000. No oracle, no feed: the inventory *is* the price. (*Connect the dot:* this is Chapter 1's market maker whose quotes are a pure function of inventory.)

Equivalently: the curve `y = k/x` is a hyperbola, and the spot price is the slope of the tangent at the current point. A trade slides the pool along the hyperbola; the slope at the new point is the new price.

## 2. Finite trades: execution price and slippage

Real trades aren't infinitesimal. Sell `Δx` of X into the pool (ignore fees for a moment). The new reserves must satisfy the invariant:

```
(x + Δx)(y − Δy) = xy
Δy = y · Δx / (x + Δx)
```

Your **execution price** is `Δy/Δx = y / (x + Δx)` — strictly worse than the spot price `y/x`, and worse the bigger `Δx` is. That gap is **price impact** (commonly, if loosely, called slippage). Two facts fall out:

- **Impact scales with trade size relative to reserves.** Sell 1% of the pool's X and you move the price ~2% (each reserve shifts ~1% in opposite directions). This is why *depth* is the competitive metric for a trading venue.
- **You can never empty a pool.** As `Δx → ∞`, `Δy → y` but never reaches it. The hyperbola never touches the axes. The last token in a pool costs infinity — elegant built-in bankruptcy protection.

With the fee `f` (0.3% in v2), only `(1−f)·Δx` counts toward the swap; the fee stays in the pool. The actual v2 formula:

```
Δy = y · 0.997·Δx / (x + 0.997·Δx)
```

Note what "fee stays in the pool" implies: `k` *grows* slightly on every trade. LP wealth is proportional to `√k` (next section), so growing `k` is exactly how fees accrue to LPs without any bookkeeping — a beautifully lazy design. (*Connect the dot:* v3 abandons this laziness — fees there are tracked separately per position, Chapter 4 — and v4 hooks can redirect fees anywhere, Chapter 8.)

## 3. What an LP share is worth

LPs own the pool pro-rata. The pool's value in terms of Y at price `P` is `V = x·P + y`. Since `P = y/x` at all times (arbitrage keeps it so — Chapter 5), we get `x·P = y`, so:

```
V = 2y = 2·√(k·P)        (because y = √(k·P) and x = √(k/P))
```

Memorize `V = 2√(kP)`. It says a constant-product LP position is worth the *square root* of the price, times a constant that fees slowly grow. Three consequences:

- **The pool is always 50/50 by value.** The formula self-rebalances: as P rises, the pool sells X into the rally. An LP is running an automated "constant-mix" rebalancing strategy — this exact framing is what makes LVR computable in Chapter 5.
- **Concave payoff.** `√P` is concave: LPs have *less* upside than holding and *more* downside — before fees. The compensation for accepting concavity is fee income. Whether it compensates enough is the empirical question hooks keep trying to fix.
- **Volatility drag = impermanent loss**, made precise next.

## 4. Impermanent loss, derived exactly

Compare an LP against a holder who deposits the same 50/50 portfolio and does nothing. Start at price `P0`, with the pool worth `V0 = 2√(k·P0)`. Let the price move by factor `r` (so `P1 = r·P0`).

Holder: their `x0 = √(k/P0)` of X and `y0 = √(k·P0)` of Y are now worth

```
V_hold = x0·r·P0 + y0 = √(k·P0)·(1 + r)
```

LP: `V_pool = 2√(k·r·P0)= 2√r·√(k·P0)`

The ratio is the **impermanent loss** function:

```
IL(r) = V_pool / V_hold − 1 = 2√r / (1 + r) − 1
```

Tabulated, because these numbers are worth having in your head:

| Price change r | IL |
|---|---|
| 1.0 (no move) | 0% |
| 1.25 | −0.6% |
| 1.5 | −2.0% |
| 2 | −5.7% |
| 3 | −13.4% |
| 5 | −25.5% |
| 0.5 (halves) | −5.7% |

Observations that matter later:

- **Symmetric in log-price**: doubling and halving hurt identically (`IL(r) = IL(1/r)`). IL is a function of *how far* price travels, not which direction.
- **"Impermanent"** because if price returns to `P0`, the loss vanishes — the pool bought low and sold high on the round trip and kept fees. The name is still misleading marketing: for a price move that sticks, the loss is permanent. The honest name, **divergence loss**, never caught on.
- **Second-order for small moves** (a Taylor expansion gives `IL ≈ −(1/8)·(Δln P)²` for small moves). Small daily wiggles cost little; sustained trends are what bleed LPs.

One more reframe, because it unlocks Chapter 4: the LP payoff `2√r/(1+r)` is what an options trader calls a **short-gamma** profile — you lose whenever price moves, in either direction, and you collect a premium (fees) for standing still. LPing *is* selling volatility. v3's ranged positions concentrate the gamma; some hooks (Chapter 12) exist purely to reprice the premium in real time.

## 5. Why depth wins: the aggregation argument

Two pools with the same price but different sizes: the bigger one gives strictly better execution for every trade (impact `∝ Δx/x`). So order flow routes to depth, fees follow flow, and fee yield attracts liquidity — a winner-take-most loop that explains a decade of DEX competition:

- Liquidity mining (2020) was an attempt to *bootstrap* the loop with subsidies.
- v3's efficiency gains (Chapter 4) were an attempt to fake a 4000×-bigger pool with the same capital.
- v4's cheap pool creation and hooks (Chapters 6–8) bet that *specialization* can beat raw depth — a pool tuned for stables or for a launch token can offer better execution than a generic deep pool.

## 6. Generalizations you'll meet in the wild

The constant product is one member of a family. You should recognize the relatives:

- **Constant sum** `x + y = k`: zero slippage, price fixed at 1 — perfect for identical assets, but drainable the instant true price ≠ 1. Not usable alone.
- **StableSwap / Curve (2020)**: a blend of constant-sum (near balance) and constant-product (far from balance), controlled by an amplification parameter `A`. This is *the* design for stablecoin pairs, and re-implementing StableSwap-like curves as v4 hooks is a standard exercise in Chapter 8.
- **Weighted product** (Balancer): `x^w · y^(1−w) = k` gives an 80/20 or any-ratio pool; the weight sets the value split.
- **Concentrated liquidity** (v3): not a new formula but the same hyperbola *cut into slices* — each price range gets its own little constant-product segment with virtual reserves. That construction is the entire next-but-one chapter.

The meta-lesson, and the thesis of v4: **the curve is a design parameter.** Different asset pairs want different curves, fees, and defenses. v1–v3 hard-coded one answer per protocol version; v4 makes the answer programmable per pool. Everything in this chapter is the raw material those programs manipulate.

Next chapter: the formula grows an architecture — v2, the contract design that half of DeFi copied.
