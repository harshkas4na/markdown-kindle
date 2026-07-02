# 17 — Testing Hooks With Foundry

Goal: write an actual passing test against the `Counter` hook from lessons 15-16, understand the test routers you're calling through, and learn the assertion patterns you'll reuse for every hook you ever build.

## Why you can't "just call the pool" the way you'd call a normal contract

Recall article 5: the PoolManager is a singleton, and it uses flash accounting — a swap isn't one simple external call, it's a sequence of internal ledger updates that must net out to zero by the end of the transaction, settled via a callback pattern (the caller has to implement an `unlockCallback` that the PoolManager calls back into, to actually perform the settlement). Writing that settlement logic by hand in every single test would be tedious and error-prone, so Uniswap ships **test router contracts** that already implement it correctly — you interact with the pool *through* these routers in tests, not directly against the raw PoolManager.

The two you'll use constantly: `PoolSwapTest` (for performing swaps) and `PoolModifyLiquidityTest` (for adding/removing liquidity) — both provided automatically once you call `deployFreshManagerAndRouters()` from lesson 16.

## A full test: verifying our Counter hook actually counts

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Deployers} from "v4-core/test/utils/Deployers.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolSwapTest} from "v4-core/src/test/PoolSwapTest.sol";
import {Counter} from "../src/Counter.sol";

contract CounterTest is Test, Deployers {
    Counter hook;

    function setUp() public {
        // (same setup as lesson 16: deploy manager, tokens, mine+deploy hook, init pool)
        // ...
    }

    function test_beforeSwapCountIncreases() public {
        // sanity check: count starts at zero for this pool
        assertEq(hook.beforeSwapCount(key.toId()), 0);

        // build the parameters for a swap: sell some of currency0 for currency1
        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({
            zeroForOne: true,              // trading currency0 -> currency1
            amountSpecified: -1e18,        // negative = "exact input": sell exactly 1e18 of currency0
            sqrtPriceLimitX96: MIN_PRICE_LIMIT  // no meaningful slippage guard for this test
        });

        // testSettings just controls how the test router handles native ETH / claim tokens —
        // for a plain ERC20/ERC20 pool, this is boilerplate you'll copy every time
        PoolSwapTest.TestSettings memory testSettings =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});

        swapRouter.swap(key, params, testSettings, ZERO_BYTES);

        // now assert our hook actually got triggered exactly once
        assertEq(hook.beforeSwapCount(key.toId()), 1);
        assertEq(hook.afterSwapCount(key.toId()), 1);
    }
}
```

Run it:

```bash
forge test -vv
```

`-vv` (and `-vvv`, `-vvvv` for more detail) controls verbosity — worth cranking this up whenever a test fails and you need to see exactly what happened, including a full call trace at `-vvvv`.

## Reading the `SwapParams` you'll write in every test

- **`zeroForOne`**: which direction the trade goes. `PoolKey` sorts the two tokens by address (`currency0` is always the numerically lower address) — `true` means you're selling `currency0` for `currency1`.
- **`amountSpecified`**: the trade size, with a sign that changes its meaning. Negative means "exact input" — "I am selling exactly this much." Positive means "exact output" — "I want to receive exactly this much, whatever the input cost turns out to be." This sign convention surprises almost everyone the first time; get used to double-checking it.
- **`sqrtPriceLimitX96`**: a slippage guard — the trade will revert rather than push the price past this limit. In tests, you'll often just use the library's `MIN_PRICE_LIMIT`/`MAX_PRICE_LIMIT` constants to mean "no meaningful limit for this test," but in production code this is exactly where real slippage protection lives.

## Testing liquidity actions, the same pattern

```solidity
function test_addLiquidityTriggersHook() public {
    IPoolManager.ModifyLiquidityParams memory params = IPoolManager.ModifyLiquidityParams({
        tickLower: -600,
        tickUpper: 600,
        liquidityDelta: 1e18,
        salt: 0
    });

    modifyLiquidityRouter.modifyLiquidity(key, params, ZERO_BYTES);
    // then assert whatever your hook was supposed to do on liquidity add
}
```

Notice `tickLower`/`tickUpper` here are article 4's concentrated-liquidity range, expressed directly in tick units — this is the actual low-level interface every "auto-rebalancing" hook you build will eventually call under the hood.

## Reading pool state from inside a test (or from inside a hook)

Sometimes you need to check the pool's actual current state — its current price, current tick, current liquidity — not just your hook's own storage. The `StateLibrary` gives you read access to the PoolManager's internal state:

```solidity
import {StateLibrary} from "v4-core/src/libraries/StateLibrary.sol";

using StateLibrary for IPoolManager;

(uint160 sqrtPriceX96, int24 currentTick, , ) = manager.getSlot0(key.toId());
uint128 currentLiquidity = manager.getLiquidity(key.toId());
```

This is exactly the tool a dynamic-fee hook (lesson 18) or a limit-order hook (lesson 21) uses *inside its own callback* to check "what tick did we just cross" or "what's the current price" as part of its real logic — not just a testing convenience.

## The general shape of every hook test you'll write

1. `setUp()`: deploy manager + routers, mine + deploy your hook, initialize a pool using it.
2. Build a `SwapParams` or `ModifyLiquidityParams` struct describing the action you want to test.
3. Call it through `swapRouter`/`modifyLiquidityRouter`, never directly against the raw PoolManager.
4. Assert on your hook's own state changes (its custom mappings/variables) and/or on the pool's resulting state via `StateLibrary`.

Every single hook lesson from here forward (18-23) will use exactly this test shape — only the business logic inside the hook itself changes.

## The one sentence to keep

**You never call the PoolManager directly in tests — you go through `PoolSwapTest`/`PoolModifyLiquidityTest` routers that correctly implement flash accounting's settlement callback for you, `SwapParams`'s sign-flipping `amountSpecified` (negative = exact input, positive = exact output) is the detail that trips people up first, and `StateLibrary` lets both your tests and your hook's own logic read the pool's real current price/tick/liquidity directly from the PoolManager's storage.**
