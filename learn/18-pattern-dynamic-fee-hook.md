# 18 — Code Pattern: Dynamic Fee Hook

Goal: build the #1 most-repeated idea in the entire directory (218 of 556 hooks touch this) — a hook that charges a different swap fee based on recent volatility. This is the pattern behind every "protect the LP" pitch from articles 1, 2, and 8.

## The one extra setup step dynamic fees require: the dynamic-fee flag

Normally a pool's fee is a fixed number baked into its `PoolKey.fee` field at creation (e.g. `3000` = 0.30%). To let a hook override the fee *per swap*, the pool must instead be initialized with a special sentinel value:

```solidity
import {LPFeeLibrary} from "v4-core/src/libraries/LPFeeLibrary.sol";

// instead of a fixed fee like 3000, pass this flag when initializing the pool:
uint24 dynamicFeeFlag = LPFeeLibrary.DYNAMIC_FEE_FLAG; // = 0x800000
```

This tells the PoolManager "this pool's fee is not fixed — ask the hook, on every swap, what fee to charge." Without this flag, your hook's fee-override return value is simply ignored.

## The hook itself

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {PoolId} from "v4-core/src/types/PoolId.sol";
import {BeforeSwapDelta, BeforeSwapDeltaLibrary} from "v4-core/src/types/BeforeSwapDelta.sol";
import {StateLibrary} from "v4-core/src/libraries/StateLibrary.sol";

contract VolatilityFeeHook is BaseHook {
    using StateLibrary for IPoolManager;

    // fee bounds, expressed in the same units as Uniswap fees (100 = 0.01%, i.e. hundredths of a bip... actually
    // Uniswap fee units are hundredths of a basis point: 3000 = 0.30%, 500 = 0.05%)
    uint24 public constant BASE_FEE = 3000;     // 0.30% during calm markets
    uint24 public constant MAX_FEE = 10000;     // 1.00% cap during high volatility

    // per-pool tracking of the last observed tick and last-seen timestamp,
    // used as our (deliberately simple) volatility proxy
    mapping(PoolId => int24) public lastTick;
    mapping(PoolId => uint32) public lastUpdate;

    constructor(IPoolManager _poolManager) BaseHook(_poolManager) {}

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false, afterInitialize: true,   // <- need this to seed lastTick on pool creation
            beforeAddLiquidity: false, afterAddLiquidity: false,
            beforeRemoveLiquidity: false, afterRemoveLiquidity: false,
            beforeSwap: true,   // <- this is where we override the fee
            afterSwap: true,    // <- this is where we update our volatility tracker
            beforeDonate: false, afterDonate: false,
            beforeSwapReturnDelta: false, afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false, afterRemoveLiquidityReturnDelta: false
        });
    }

    function _afterInitialize(address, PoolKey calldata key, uint160, int24 tick)
        internal override returns (bytes4)
    {
        lastTick[key.toId()] = tick;
        lastUpdate[key.toId()] = uint32(block.timestamp);
        return this.afterInitialize.selector;
    }

    function _beforeSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, bytes calldata)
        internal override returns (bytes4, BeforeSwapDelta, uint24)
    {
        PoolId id = key.toId();

        // how far has the price moved (in ticks) since our last check?
        (, int24 currentTick, , ) = poolManager.getSlot0(id);
        int24 tickDelta = currentTick - lastTick[id];
        if (tickDelta < 0) tickDelta = -tickDelta;

        // simple linear scaling: more tick movement -> higher fee, capped at MAX_FEE
        uint24 fee = BASE_FEE + uint24(uint256(int256(tickDelta)) * 50);
        if (fee > MAX_FEE) fee = MAX_FEE;

        // this is the actual "override the fee for this swap" mechanism:
        return (this.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, fee | LPFeeLibrary.OVERRIDE_FEE_FLAG);
    }

    function _afterSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, /* delta */ , bytes calldata)
        internal override returns (bytes4, int128)
    {
        PoolId id = key.toId();
        (, int24 currentTick, , ) = poolManager.getSlot0(id);
        lastTick[id] = currentTick;
        lastUpdate[id] = uint32(block.timestamp);
        return (this.afterSwap.selector, 0);
    }
}
```

## Walking through the actual logic decisions

**Why track ticks instead of raw price?** Ticks (article 4) are already a log-scaled representation of price — a fixed tick movement represents a roughly fixed *percentage* price movement, regardless of whether the price is currently $2,000 or $200,000. That makes tick-delta a naturally reasonable, cheap-to-compute proxy for "how much did the price move," without needing floating-point-style percentage math.

**Why `afterInitialize` and `afterSwap` both update `lastTick`?** Because our fee formula in `_beforeSwap` needs a "previous" reference point to compare against — without seeding it at pool creation and updating it after every swap, `lastTick` would either be uninitialized or stale.

**The `OVERRIDE_FEE_FLAG` bitwise-OR is the actual mechanism, not decoration.** The `uint24` return from `beforeSwap` isn't just "the fee" — the PoolManager needs to distinguish "the hook wants to override the fee to X" from "the hook has no opinion, use the pool's default." That distinction is encoded by OR-ing a specific flag bit into the returned value, defined in `LPFeeLibrary`. Forgetting this flag is a common bug — you compute a perfectly reasonable fee value, return it, and the PoolManager silently ignores it because the override bit wasn't set.

**This is deliberately the simplest possible volatility measure.** A real production hook (matching the "Nezlobin directional fee" pattern from articles 1 and 8) would likely also check *direction* — charging more specifically for trades that push the price further from a reference/oracle price (lesson 19), not just any movement — because undirected volatility-based fees tax honest traders exactly as much as arbitrageurs, whereas directional fees target arbitrage more precisely. Starting simple like this, and understanding exactly why it's simple, is a completely reasonable place to begin before adding that directional refinement.

## The one sentence to keep

**A dynamic-fee hook needs the pool initialized with `LPFeeLibrary.DYNAMIC_FEE_FLAG`, computes its own fee inside `_beforeSwap` using some volatility proxy (tick movement is the cheapest reasonable one), returns that fee OR'd with `LPFeeLibrary.OVERRIDE_FEE_FLAG` to actually make it take effect, and updates its own tracking state in `_afterSwap` so the next swap has a fresh reference point to compare against.**
