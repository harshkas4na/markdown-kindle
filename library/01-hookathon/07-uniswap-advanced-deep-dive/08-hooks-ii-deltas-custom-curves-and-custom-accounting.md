# Hooks II — Deltas, Custom Curves, and Custom Accounting

**Fast overview:** the four `*ReturnsDelta` permissions let a hook move money: charge its own fees, subsidize trades, fill orders from its own inventory, or replace the constant-product curve entirely (including "no-op" swaps the hook settles by other means). The instrument is a packed return value — `BeforeSwapDelta` — that plugs the hook into flash accounting as a first-class debtor/creditor. This is the most powerful and most dangerous chapter in the book: everything Bunni was, and everything that killed it, lives here.

## Deltas refresher, one level deeper

Recall Chapter 6: inside `unlock`, every address has signed per-currency deltas, all of which must be zero by the end. **The convention: positive delta = the PoolManager owes you; negative delta = you owe it.** When a hook has a delta-returning permission, the amounts it returns from callbacks are *applied to the hook's own tab* — and the swapper's tab is adjusted to match. The hook then clears its tab like anyone else: `take` what it's owed, `settle` what it owes, or hold it as ERC-6909 claims (the efficient choice for recurring fee income — Chapter 6).

The sign discipline is the number-one source of bugs, so say it twice: **from the swapper's perspective, `amountSpecified < 0` means "exact input"** (I will pay exactly this much) and `> 0` means "exact output" (I want to receive exactly this much). All hook deltas compose against that orientation.

## BeforeSwapDelta: intercepting the swap before the curve

With `BEFORE_SWAP_RETURNS_DELTA`, `beforeSwap` returns a `BeforeSwapDelta`: two int128s packed in an int256:

```
[ upper 128 bits: delta in the SPECIFIED currency ]
[ lower 128 bits: delta in the UNSPECIFIED currency ]
```

Crucial subtlety: the axes are **specified/unspecified**, not token0/token1. "Specified" is whichever currency the trader fixed (input for exact-input, output for exact-output); "unspecified" is the other. A hook that hardcodes token0/token1 works in tests and breaks the first time someone sends an exact-output swap — a classic audit finding.

What the PoolManager does with it: the specified-side delta is *subtracted from what reaches the core swap*. The hook consumed (or contributed) part of the trade; the AMM curve (Chapter 4's tick walk) only processes the remainder. The unspecified-side delta adjusts what the swapper receives/pays on the other side. Three regimes:

**1. Partial consumption — hook fees.** Trader sends exact-input 100 USDC. Hook returns +1 on the specified side (taking 1 USDC for itself as a fee); the curve swaps 99. The hook's tab is +1 USDC, which it later `take`s or mints as 6909. Note this is a *hook fee* — separate from the LP fee (Chapter 9) and the protocol fee; v4 has three distinct fee layers, and hooks choosing their cut is pure market competition (greedy hook = pools nobody routes to).

**2. Full consumption — the no-op swap.** Hook returns a delta that consumes the *entire* specified amount: nothing reaches the curve; the pool's price never moves. The hook now owes the trader the unspecified side, which it can source however it likes:

- from its own inventory (held as 6909 claims),
- from a *different* pool,
- from an off-curve pricing model (an oracle quote, a StableSwap formula, an RFQ fill),
- or asynchronously — take the input now, deliver output later (**async swaps**: the hook takes custody and completes the trade in a future transaction — the basis of on-chain limit orders that fill when price crosses a level).

**3. Subsidy — negative hook delta.** The hook *adds* value to the trade (rebates, incentivized routes): its tab goes negative and it must settle from its own funds by the end of the unlock.

`afterSwap`'s return-delta variant is the tamer sibling: it can only skim/add on the **unspecified** side after the curve has run — the natural place for volume-based fees or rewards computed from the actual executed amounts.

The liquidity twins — `afterAddLiquidityReturnDelta` / `afterRemoveLiquidityReturnDelta` — let a hook tax or top-up liquidity operations: deposit fees, withdrawal penalties (a time-lock hook that *fines* early exits rather than reverting them), or auto-compounding schemes that intercept owed fees and reinvest them.

## Custom curves: the hook as its own AMM

Combine the pieces and you reach the endgame: a hook with `beforeSwap + beforeSwapReturnsDelta` that no-ops *every* swap and prices trades with its own math. The v4 pool becomes a shell — settlement rails, flash accounting, router integration — around a foreign pricing engine. The vanilla concentrated liquidity is bypassed entirely (such pools typically also block `modifyLiquidity` and manage deposits through their own vault; the hook *is* the pool).

Why would you? Because Chapter 2's punchline — *the curve is a design parameter* — becomes deployable reality:

- **StableSwap-style curves** for pegged pairs, inside v4's routing universe instead of on a separate protocol.
- **Oracle-anchored curves** that quote around an external price and never go stale (an anti-LVR family from Chapter 5's taxonomy — "remove the stale quote").
- **Shared/rehypothecated liquidity**: EulerSwap (Chapter 12) prices swaps against lending-market inventory, so the same dollar backs a loan *and* fills your trade.
- **Wholly new instruments**: prediction-market curves, bonding curves for launches (Flaunch), auction-settled batches (Angstrom fills trades at a uniform clearing price and uses the pool only as fallback settlement).

The cost is that you inherit the *entire* responsibility the v3 math used to carry. Uniswap's core guarantees conservation of deltas — it does **not** guarantee your curve is arbitrage-free, your rounding favors the pool, or your inventory can't be drained by a carefully shaped sequence of trades. Conservation ≠ correctness (Chapter 6's warning, now with teeth — and Chapter 11's body count).

## Worked example: skeleton of a fixed-price no-op hook

Compressed to essentials (error handling and exact-output branch omitted — see Chapter 10 for the tested version):

```solidity
function _beforeSwap(
    address, PoolKey calldata key, SwapParams calldata params, bytes calldata
) internal override returns (bytes4, BeforeSwapDelta, uint24) {
    require(params.amountSpecified < 0, "exact-input only");
    uint256 amtIn = uint256(-params.amountSpecified);
    uint256 amtOut = quote(amtIn);                    // your pricing model

    (Currency cIn, Currency cOut) = params.zeroForOne
        ? (key.currency0, key.currency1) : (key.currency1, key.currency0);

    poolManager.mint(address(this), cIn.toId(), amtIn);   // claim the input as 6909
    poolManager.burn(address(this), cOut.toId(), amtOut); // pay output from our 6909 stash

    // consume ALL of the specified (input) side; owe the unspecified side
    BeforeSwapDelta d = toBeforeSwapDelta(int128(int256(amtIn)), -int128(int256(amtOut)));
    return (BaseHook.beforeSwap.selector, d, 0);
}
```

Read the flow twice: the hook takes the trader's input into its own 6909 balance, pays the output from its 6909 balance, and reports deltas so the PoolManager can reconcile everyone's tabs. The curve is never touched. Congratulations — those fifteen lines are a DEX.

## The gas and MEV fine print

- Every delta-returning hook adds calls, arithmetic, and usually storage to the hot path. The rule of thumb from live 2026 hooks: simple observation hooks add ~10–30k gas per swap; full custom-accounting hooks 60–150k+. On L2s this is trivia; on mainnet it's a real routing disadvantage — aggregators *will* route around expensive pools for small trades.
- Hooks see swaps *before execution* — a privileged position. A malicious or compromised hook is a perfectly-placed sandwich bot (it literally runs inside your trade). "Who controls the hook and what can they change?" is now part of every pool's due diligence (Chapter 11).
- Multi-hop routes compose hooks: a route through three hooked pools runs all three hooks' logic in one unlock. Mis-accounted deltas in one hook can revert — or worse, misprice — the whole route. Test composed paths, not just single swaps (Chapter 10).

## Where we stand in the story

Look how far the plot has traveled: Chapter 2 said the curve is a formula; Chapter 5 said the formula leaks value in specific, measurable ways; Chapters 6–7 built rails where the formula is replaceable; this chapter replaced it. What remains is craft (building and testing — Chapter 10), humility (how this power kills protocols — Chapter 11), and taste (what's actually worth building — Chapters 9 and 12).

Next, the gentlest of the money-touching patterns and the most requested real-world feature: **dynamic fees** — the pool that reprices its own spread.
