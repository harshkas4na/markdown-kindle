# 01 — The Concepts You Need Before Reading the Code

Goal: every mechanism this hook uses, explained once, slowly, so that the line-by-line chapters never have to stop and define anything. If you've read the learn-the-basics series, some of this is revision — but each concept here is explained in terms of *how this specific project uses it*.

## 1. Dynamic fees and the two magic flags

A normal v4 pool bakes its fee into the `PoolKey` at creation (`3000` = 0.30%, in units of hundredths of a basis point — so 1,000,000 would be 100%). Our hook needs a *different fee depending on the phase*, so the pool must be created with a sentinel value instead:

```solidity
uint24 fee = LPFeeLibrary.DYNAMIC_FEE_FLAG; // = 0x800000
```

This tells the PoolManager: "this pool has no fixed fee — ask the hook on every swap." The hook then answers through the third return value of `beforeSwap`. But there's a subtlety that bites everyone once: returning a fee number alone is **ignored**. The PoolManager needs to distinguish "override the fee to X" from "no opinion", and that's encoded by OR-ing a flag bit into the returned value:

```solidity
return (selector, ZERO_DELTA, myFee | LPFeeLibrary.OVERRIDE_FEE_FLAG);
```

Our hook enforces the dynamic-fee requirement at pool creation: `_afterInitialize` reverts with `MustUseDynamicFee` if someone attaches the hook to a static-fee pool. Better an impossible-to-misconfigure pool than a silent no-op.

## 2. LVR, and why a *ramping* closed-hours fee

**LVR (loss-versus-rebalancing)** is the formal name for the money LPs lose to traders who know the "true" price when the pool doesn't. The key insight for this project: LVR risk is not constant — it *accumulates with time since the last trustworthy price*. One hour after the close, Tesla's true value has barely had time to drift. Sixty hours later (Sunday night), an entire weekend of news is priced into everyone's head except the pool's.

So the closed-hours fee is not one number but a **ramp**: `closedFeeStart + hoursClosed × closedFeeRampPerHour`, capped at `closedFeeMax`. With the defaults (1.00% start, +0.03%/hour, 3.00% cap): a Saturday-noon trade (16 dark hours) pays 1.48%; a Sunday-night trade (55 dark hours) pays 2.65%. The fee is exactly the compensation for the option the LP is implicitly writing.

## 3. Circuit breakers as *value* caps, not token caps

The second closed-hours defense is trade-size limits: a cap per swap and a cap per block. The subtle design decision is the *denomination*. A naive cap on `amountSpecified` (the raw token amount) has two holes: (a) a swap can be exact-input or exact-output, so the specified amount is sometimes token0 and sometimes token1 — capping raw amounts means the two directions face different real limits; (b) if the price moves, a fixed token0 cap changes its economic meaning.

Our caps are denominated in **token1 value at the pool's current price**: whatever amount the swap specifies, in whichever token, gets valued through the pool's `sqrtPriceX96` before the check. One cap, one meaning, no direction games.

## 4. sqrtPriceX96 and Q96 fixed-point — the 30-second version

Uniswap stores price as `sqrtPriceX96`: the **square root** of the price (token1 per token0), multiplied by 2⁹⁶. Two facts are enough for this codebase:

- To get a *value in token1* of `x` token0: multiply by the price = multiply by (sqrtP)² and divide by (2⁹⁶)². In code, done in two steps to avoid overflow: `mulDiv(mulDiv(x, sqrtP, Q96), sqrtP, Q96)`.
- To compare two prices in bps: take the ratio of the *sqrt* prices in bps, then **square it** (and re-scale). A ±1% price band is roughly a ±0.5% sqrt-price band — squaring is what converts between them exactly. Our band check computes `sqrtRatioBps²/10000` and compares against `10000 ± bandBps`.

`FullMath.mulDiv(a, b, c)` computes `a*b/c` with a 512-bit intermediate — it cannot overflow even when `a*b` exceeds 2²⁵⁶. Every price computation in the hook goes through it.

## 5. Opening auctions — how real exchanges reopen, and our on-chain translation

At the NYSE, the open is not "first order wins." During pre-market, orders accumulate in a book. At 9:30, the exchange computes a single **clearing price** that best matches accumulated buys against sells, everyone in the cross trades at that one price, and only then does continuous trading start. Nobody gains anything by being 3 milliseconds faster — which is the entire point.

Our translation, given that an AMM has no order book:

1. While the market is closed, anyone can **escrow** an exact-input order into the hook: "sell 5 tSTOCK at the open" or "spend 1,000 mUSD at the open." Orders target an **epoch** — the timestamp of the next session's 09:30.
2. During the first `auctionDuration` (10 min) after the open, continuous swaps **revert**. The auction *is* the open.
3. Settlement (permissionless — anyone can ring the bell): the two sides are **crossed internally** at the pre-open pool price. If sellers committed 10 tSTOCK and buyers committed enough mUSD to absorb 4 of them, those 4 change hands directly inside the hook at the spot price — paying **no pool fee and moving no price**. Only the **net imbalance** (6 tSTOCK) is executed as one swap through the pool.
4. Distribution is **conservation-based**: the hook hands out *everything* it holds — sellers pro-rata share all the token1 (internal cross + net swap output), buyers pro-rata share all the token0. Because outputs are defined as "everything that came in, redistributed", the batch is insolvency-proof by construction. This is the property the fuzz tests hammer on.

Note what this does to the Monday-morning arbitrageur: there is no stale price to snipe. The first trade *is* the batch, everyone in it gets the same price, and the price impact of the repricing accrues as one clean move rather than one bot's profit.

## 6. Flash accounting, `unlock`, `settle`/`take` — how the hook trades with the pool

v4's PoolManager uses **flash accounting** (learn-the-basics lesson 05): nobody transfers tokens during operations; the PoolManager just tracks signed **deltas** per address, and at the end of a `unlock()` context every delta must net to zero, settled by real token movements.

When our hook settles an auction, *the hook itself* becomes a trader:

- `settleAuction` calls `poolManager.unlock(data)` — asking the PoolManager to open an accounting context and call us back.
- The PoolManager calls our `unlockCallback(data)`. Inside it we may call `poolManager.swap(...)` directly (no router needed — routers exist to do exactly this dance for end users).
- Each swap leaves us with deltas: negative in the token we owe, positive in the token we're owed. We resolve them with two primitives: `currency.settle(poolManager, us, amount, false)` — *pay* tokens we owe (transfers ERC20 from the hook into the PoolManager) — and `currency.take(poolManager, us, amount, false)` — *collect* tokens we're owed.
- When `unlockCallback` returns, the PoolManager verifies all deltas are zero, or the whole transaction reverts. Atomicity for free.

One more subtlety: during those settlement swaps, the PoolManager calls the pool's hook — which is *us*, re-entering our own `beforeSwap` while the auction phase would normally freeze swaps. The `_inSettlement` flag (a transient boolean set only inside `settleAuction`) is how `beforeSwap` recognizes its own settlement swaps and lets them through at the base fee.

## 7. Why on-chain date math is genuinely hard (and how we make it tractable)

"Is the NYSE open at timestamp T?" requires knowing, on-chain, with no libraries and no OS:

- **The weekday.** Easy: Unix day 0 (1970-01-01) was a Thursday, so `weekday = (daysSinceEpoch + 4) % 7` with 0 = Sunday.
- **The wall-clock time in New York.** Hard, because New York moves its clocks twice a year. ET is UTC-5 in winter (EST) and UTC-4 in summer (EDT). US law defines the switch as: **DST starts the second Sunday of March at 2am local, ends the first Sunday of November at 2am local.** To evaluate "second Sunday of March of year Y" you need to convert year/month/day → day-number and back. We use **Howard Hinnant's civil-date algorithms** (`civil_from_days` / `days_from_civil`) — the same branchless integer algorithms inside every serious datetime library, about 15 lines each, exact over ±millions of years.
- **Holidays.** Impossible to compute — they're announced by humans every year (and change: Juneteenth was added in 2021). So holidays are the *one* thing the owner updates, as a mapping of ET-day-numbers, with a batch setter to load a whole year at once. Everything computable is computed; only the genuinely human-decided part is configured.

The payoff for this pain: the phase machine needs no oracle, no keeper, and works identically on any chain at any time — and our tests pin it down to the exact DST switch minutes of 2026.

## 8. The pool's spot price without a helper: `getSlot0`

The hook frequently needs the pool's current `sqrtPriceX96`. In v4, pool state lives inside the singleton PoolManager and is read via `extsload` (raw storage reads), wrapped by `StateLibrary`:

```solidity
using StateLibrary for IPoolManager;
(uint160 sqrtPriceX96, , , ) = poolManager.getSlot0(poolId);
```

`slot0` packs the price, current tick, and fee info into one storage slot; we only ever use the price. (The demo UI reads the same slot from JavaScript by hashing `poolId . 6` — the pools mapping is at storage slot 6 — and calling `extsload` directly. Same data, no ABI needed.)

## The one sentence to keep

**Five ideas power this whole codebase — a dynamic fee is only honored when OR-ed with `OVERRIDE_FEE_FLAG`; LVR risk grows with hours-since-close so the fee ramps; caps and bands are computed in price terms via `sqrtPriceX96` and `FullMath`; the reopening auction escrows orders, crosses the matched portion internally, swaps only the net through `unlock`/`settle`/`take` flash accounting, and distributes by conservation; and the calendar is pure math (Hinnant's algorithms + the US DST rule) with only holidays left to configure.**
