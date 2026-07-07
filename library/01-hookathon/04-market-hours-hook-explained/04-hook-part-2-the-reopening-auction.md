# 04 — MarketHoursHook.sol, Part 2: The Reopening Auction

Goal: understand the auction subsystem completely — order escrow, epoch targeting, the internal-crossing settlement (the most intricate code in all three projects), pro-rata claims, and the cancellation escape hatch. By the end you should be able to re-derive the settlement math on paper.

## The lifecycle at a glance

```
CLOSED (weekend)        AUCTION (09:30–09:40)      OPEN (09:40+)
     │                        │                        │
placeAuctionOrder ──────► placeAuctionOrder      settleAuction (anyone)
(tokens escrowed,         (still allowed)             │
 epoch = Monday 09:30)        │                   claim / claim / claim
     │                   swaps REVERT             (pro-rata outputs)
cancelOrder allowed           │                        │
(before the open)        swaps STILL revert       continuous trading
                         until settled                resumes
```

## Epoch targeting: `upcomingEpoch`

```solidity
function upcomingEpoch(uint256 ts) public view returns (uint256) {
    uint256 etDay = NYSECalendar.etDayNumber(ts);
    if (isTradingDay(etDay)) {
        uint256 openTs = NYSECalendar.sessionOpen(etDay);
        if (ts < openTs + auctionDuration) return openTs;
    }
    for (uint256 i = 1; i <= 30; i++) {
        if (isTradingDay(etDay + i)) return NYSECalendar.sessionOpen(etDay + i);
    }
    revert NoUpcomingSession();
}
```

"Which auction does an order placed *now* belong to?" Walk the cases: Saturday → Monday's open. Tuesday 3am (pre-market) → Tuesday's own open (`ts < openTs` and today is a trading day). Tuesday 09:35, *inside* the window → still Tuesday's open — latecomers may join the live auction (`ts < openTs + auctionDuration`). Tuesday 2pm, mid-session → tomorrow's open (falls through to the loop). The forward loop mirrors `lastSessionClose`'s backward loop, same 30-day griefing bound.

And the companion used by settlement and the `beforeSwap` gate:

```solidity
function _currentSessionOpen(uint256 ts) internal view returns (uint256) {
    uint256 etDay = NYSECalendar.etDayNumber(ts);
    if (!isTradingDay(etDay)) return 0;
    uint256 openTs = NYSECalendar.sessionOpen(etDay);
    if (ts < openTs || ts >= NYSECalendar.sessionClose(etDay)) return 0;
    return openTs;
}
```

Returns today's open **only while inside a live session**, else 0. The zero return is used as "no session" — safe as a sentinel because a real session-open timestamp can never be 0.

## Placing an order: escrow into the hook

```solidity
function placeAuctionOrder(PoolKey calldata key, bool zeroForOne, uint128 amountIn)
    external returns (uint256 epoch, uint256 orderIndex)
{
    if (amountIn == 0) revert ZeroAmount();
    PoolId id = key.toId();
    if (!poolConfig[id].enabled) revert PoolNotEnabled();
    if (phaseAt(block.timestamp) == Phase.OPEN) revert MarketIsOpen();

    epoch = upcomingEpoch(block.timestamp);

    Currency currencyIn = zeroForOne ? key.currency0 : key.currency1;
    IERC20(Currency.unwrap(currencyIn)).safeTransferFrom(msg.sender, address(this), amountIn);

    Epoch storage e = epochs[id][epoch];
    if (zeroForOne) e.totalIn0 += amountIn;
    else e.totalIn1 += amountIn;

    orderIndex = _orders[id][epoch].length;
    _orders[id][epoch].push(Order({owner: msg.sender, zeroForOne: zeroForOne, amountIn: amountIn, closed: false}));

    emit AuctionOrderPlaced(id, epoch, orderIndex, msg.sender, zeroForOne, amountIn);
}
```

Points worth dwelling on:

- **`MarketIsOpen` guard:** while the market trades continuously there's no reason to queue — just swap. Orders are only for CLOSED and AUCTION phases.
- **Real escrow, not approval-based promises.** `safeTransferFrom` pulls the tokens into the hook immediately. When settlement runs at 9:40 Monday, it must not depend on whether order-placers still have balances or allowances — the batch's inputs are already sitting in the contract. (`safeTransferFrom` rather than `transferFrom` handles the USDT-style tokens that don't return a bool.)
- **Effects order:** tokens in first, then totals, then the order record. Even under a re-entrant token (an ERC-777-style callback), the state the attacker could re-enter into is never *ahead* of the tokens actually received.
- **`orderIndex` is the array position** — the claim ticket. Returned to the caller and emitted, so wallets/UIs can track it.

## Settlement, step 1: `settleAuction` — the choreography

```solidity
function settleAuction(PoolKey calldata key) external {
    PoolId id = key.toId();
    uint256 epoch = _currentSessionOpen(block.timestamp);
    if (epoch == 0 || block.timestamp < epoch + auctionDuration) revert AuctionWindowNotOver();

    Epoch storage e = epochs[id][epoch];
    if (e.settled) revert AlreadySettled();
    if (e.totalIn0 == 0 && e.totalIn1 == 0) revert NothingToSettle();

    e.settled = true;
    _inSettlement = true;
    bytes memory result = poolManager.unlock(abi.encode(key, e.totalIn0, e.totalIn1));
    _inSettlement = false;

    (uint128 out1, uint128 out0) = abi.decode(result, (uint128, uint128));
    e.totalOut1 = out1;
    e.totalOut0 = out0;

    emit AuctionSettled(id, epoch, out1, out0);
}
```

- **Who may call: anyone.** A keeper, the issuer, a participant, or a frustrated trader whose swaps are frozen behind the unsettled auction — every one of them has an incentive, and none of them can influence the outcome (the function takes no pricing parameters; everything is derived from escrowed state and the pool).
- **When:** only inside the session (`epoch != 0`) and only after the window (`>= epoch + auctionDuration`). Settling *during* the window would let a well-timed settlement exclude late orders.
- **`e.settled = true` before the external call** — the checks-effects-interactions pattern. If anything inside the unlock re-entered `settleAuction`, it would hit `AlreadySettled`. And if the unlock reverts, the flag reverts with it — no stuck state.
- **The `_inSettlement` bracket** around `unlock` is what lets our own swaps through the `beforeSwap` freeze (Part 1). It's process-wide, not per-pool — fine, because it's only true within this one call frame.
- **`unlock(data)`:** the PoolManager opens a flash-accounting context and calls our `unlockCallback` with the same bytes. Whatever the callback returns comes back here as `result`. We pass the epoch's totals *in* through the encoding and receive the two output totals *back* — the callback itself stays stateless.

## Settlement, step 2: `unlockCallback` — the opening cross

This is the intellectual center of the project. Real exchanges cross matched buy/sell interest at one price and only route the *imbalance* into the continuous market. Here's the on-chain version:

```solidity
function unlockCallback(bytes calldata data) external returns (bytes memory) {
    if (msg.sender != address(poolManager)) revert NotPoolManager();
    (PoolKey memory key, uint128 in0, uint128 in1) = abi.decode(data, (PoolKey, uint128, uint128));

    // value of the committed token0 in token1 terms, at the pre-open spot price
    (uint160 sqrtPriceX96,,,) = poolManager.getSlot0(key.toId());
    uint256 value0In1 =
        FullMath.mulDiv(FullMath.mulDiv(in0, sqrtPriceX96, FixedPoint96.Q96), sqrtPriceX96, FixedPoint96.Q96);
```

The caller check matters: `unlockCallback` is an external function, and without the check anyone could invoke it directly (it would fail later at settle/take, but fail-fast is cheaper and cleaner). Then: value all committed token0 at the **pre-open spot price** — the price the pool closed at, still untouched because swaps have been frozen since. Call it P. Now three regimes:

```solidity
    uint256 sellersGet1; // total token1 distributed to the zeroForOne (sell) side
    uint256 buyersGet0;  // total token0 distributed to the oneForZero (buy) side

    if (value0In1 > in1) {
        // sellers dominate: all buy interest crosses against sellers at spot;
        // the residual token0 is sold through the pool
        uint256 matched0 =
            FullMath.mulDiv(FullMath.mulDiv(in1, FixedPoint96.Q96, sqrtPriceX96), FixedPoint96.Q96, sqrtPriceX96);
        if (matched0 > in0) matched0 = in0; // guard rounding
        uint128 out1Net = _swapLeg(key, true, in0 - SafeCast.toUint128(matched0));
        sellersGet1 = uint256(out1Net) + in1;
        buyersGet0 = matched0;
    }
```

**Sellers dominate** (more token0 value committed than token1). Every unit of buyer money can be matched against seller inventory at price P: `matched0 = in1 / P` is how much token0 the buyers' token1 purchases at spot (division by price = the two `mulDiv`s with Q96 flipped). The rounding clamp handles the one-wei edge where integer division makes `matched0` fractionally exceed `in0`.

Then the **conservation trick**, the reason this batch cannot go insolvent. Look at what the hook physically holds: `in0` token0 + `in1` token1. It sells the *residual* token0 (`in0 − matched0`) through the pool, receiving `out1Net` token1. Final inventory: token0 = `matched0`, token1 = `in1 + out1Net`. And the distribution is defined as **exactly that inventory**: buyers share all the token0 (`buyersGet0 = matched0`), sellers share all the token1 (`sellersGet1 = in1 + out1Net`). Nothing is computed that could exceed what exists; nothing is left stranded. The fuzz test that drains the escrow to within a few wei of dust across arbitrary order mixes is checking precisely this identity.

Price properties: buyers pay exactly P (they put in `in1` and receive `in1/P` of token0). Sellers receive a *blend* — the matched portion at P, the residual at the pool's execution price for the net swap. Everyone on the same side gets the same per-unit price (pro-rata of one pot). The matched portion pays **zero pool fee and causes zero price impact** — that's the efficiency gain over "everyone swaps individually", and the balanced-auction test shows it exactly: 1 vs 1 at a 1:1 price returns both sides their full 1.0, fee-free.

```solidity
    } else if (in1 > value0In1) {
        // buyers dominate: mirror image
        uint128 matched1 = SafeCast.toUint128(value0In1);
        uint128 out0Net = _swapLeg(key, false, in1 - matched1);
        buyersGet0 = uint256(out0Net) + in0;
        sellersGet1 = matched1;
    } else {
        // perfectly balanced: a pure cross, the pool is never touched
        sellersGet1 = in1;
        buyersGet0 = in0;
    }
    return abi.encode(SafeCast.toUint128(sellersGet1), SafeCast.toUint128(buyersGet0));
```

The mirror case (all seller inventory absorbed at P, residual token1 buys token0 through the pool), and the exact-balance case where the AMM is never touched at all. `SafeCast` on the way out because the struct fields are `uint128` — an overflowing total should revert loudly, not truncate silently.

## Settlement, step 3: `_swapLeg` — the hook as its own trader

```solidity
function _swapLeg(PoolKey memory key, bool zeroForOne, uint128 amountIn) internal returns (uint128 amountOut) {
    if (amountIn == 0) return 0;
    BalanceDelta delta = poolManager.swap(
        key,
        SwapParams({
            zeroForOne: zeroForOne,
            amountSpecified: -int256(uint256(amountIn)),   // negative = exact input
            sqrtPriceLimitX96: zeroForOne ? TickMath.MIN_SQRT_PRICE + 1 : TickMath.MAX_SQRT_PRICE - 1
        }),
        ""
    );
    if (zeroForOne) {
        amountOut = uint128(uint256(int256(delta.amount1())));
        key.currency0.settle(poolManager, address(this), amountIn, false);
        key.currency1.take(poolManager, address(this), amountOut, false);
    } else { /* mirror */ }
}
```

Anatomy of a raw pool swap (no router — we're already inside the unlock):

- **`amountSpecified` negative** = exact-input, matching the escrowed amounts we hold.
- **`sqrtPriceLimitX96`** is mandatory; `MIN_SQRT_PRICE + 1` / `MAX_SQRT_PRICE − 1` means "no limit, take whatever impact" — acceptable here because the batch as a whole *is* the price discovery, and LPs are protected by it happening as one visible cross rather than a bot race.
- **The returned `BalanceDelta`** is from the swapper's perspective: for zeroForOne exact-in, `amount0` is negative (we owe token0), `amount1` positive (we're owed token1). We then resolve both deltas immediately: `settle` pushes our escrowed token0 into the PoolManager; `take` pulls the token1 out to the hook (where it waits for `claim`s). The trailing `false` arguments mean "real ERC20 transfers, not ERC-6909 claim tokens."
- The double cast `uint128(uint256(int256(...)))` is the idiomatic way to move a known-positive `int128` into `uint128` — each step is checked or trivially safe.

Note the re-entrancy shape: `poolManager.swap` → PoolManager calls our `beforeSwap` (the `_inSettlement` branch answers instantly with the base fee) → swap math runs → our `afterSwap` (band check skipped for `_inSettlement`) → back here. Our own hook wraps our own swap. It's turtles, but well-behaved turtles.

## Claiming: pro-rata of one pot

```solidity
function claim(PoolKey calldata key, uint256 epoch, uint256 orderIndex) external returns (uint256 amountOut) {
    ...
    if (!e.settled) revert NotSettled();
    Order storage o = _orders[id][epoch][orderIndex];
    if (o.closed) revert OrderClosed();
    if (o.owner != msg.sender) revert NotOrderOwner();
    o.closed = true;

    if (o.zeroForOne) {
        amountOut = FullMath.mulDiv(e.totalOut1, o.amountIn, e.totalIn0);
        IERC20(Currency.unwrap(key.currency1)).safeTransfer(msg.sender, amountOut);
    } else {
        amountOut = FullMath.mulDiv(e.totalOut0, o.amountIn, e.totalIn1);
        IERC20(Currency.unwrap(key.currency0)).safeTransfer(msg.sender, amountOut);
    }
    ...
}
```

Your share = side's total output × (your input ÷ side's total input), floor-rounded by `mulDiv`. Floor rounding is the safe direction: the sum of all claims can undershoot the pot by at most one wei per order (dust stays in the hook), but can never overshoot it — combined with conservation-based outputs, `claim` can never fail for lack of funds. `o.closed = true` before the transfer is checks-effects-interactions again: a re-entrant `claim` on the same order hits `OrderClosed`.

Design note: claims are **pull, not push**. Settlement doesn't loop over orders transferring tokens — that loop would be unbounded gas (one whale-count auction could brick settlement) and would let one weird recipient (a reverting contract) block everyone. Each owner pulls their own.

## Cancelling: the no-stranded-funds guarantee

```solidity
uint256 sessionEnd = NYSECalendar.sessionClose(NYSECalendar.etDayNumber(epoch));
if (block.timestamp >= epoch && block.timestamp < sessionEnd) revert CancelWindowClosed();
```

An unsettled order can be withdrawn in exactly two windows: **before its session opens** (changed your mind over the weekend — fine, the batch hasn't run) and — the escape hatch — **after the session closed without anyone settling** (a whole day passed, nobody called the permissionless `settleAuction`; your escrow must not be a roach motel). The forbidden middle (`epoch ≤ now < sessionEnd`) is the session itself: once the open has happened your order is committed to the batch, because cancellable-during-settlement-window orders would let someone yank liquidity out of the cross after seeing which way it leans. Note the totals are decremented on cancel — a fully-cancelled epoch settles as `NothingToSettle`, and the `beforeSwap` gate (which checks `totalIn0 > 0 || totalIn1 > 0`) unfreezes automatically.

## What a v2 would sharpen (so you can answer the question before a judge asks)

The crossing price is the *pre-open pool spot* — sound when the pool closed in line with the market, but after a huge weekend news event the "fair" cross price is Monday's, not Friday's. The residual leg does discover the new price, and sellers' blended price partially reflects it, yet a true fixed-point clearing price (where the crossed portion also clears at the *post*-discovery price) requires solving price-vs-net-size against the AMM curve — a research-grade refinement, honestly documented in the README. Similarly, an oracle-fed official close could replace the pool-spot reference both here and in the band.

## The one sentence to keep

**The auction is escrow → freeze → cross → distribute: orders are physically escrowed against a timestamp-named epoch, the open is frozen until a permissionless settlement runs, settlement values both sides at the pre-open spot, crosses the matched portion internally (no fee, no impact), swaps only the net imbalance through the pool via `unlock`/`swap`/`settle`/`take`, and then defines each side's payout as *everything the hook holds in that token* — a conservation identity that makes insolvency structurally impossible and lets `claim` be a simple floor-rounded pro-rata pull.**
