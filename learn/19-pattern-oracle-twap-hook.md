# 19 — Code Pattern: Oracle / TWAP Accumulator Hook

Goal: build the pattern behind the 75 "Oracle & Price Discovery" hooks — a hook that maintains its own on-chain time-weighted average price, and a second version that reads an external oracle (Chainlink-style) instead. This is the building block almost every depeg-detection, directional-fee, and options-pricing hook depends on.

## Pattern A: rolling your own TWAP inside a hook

Recall article 9: a TWAP averages price over a time window specifically because it's expensive to manipulate versus a raw spot-price read. Here's the actual accumulator pattern:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {PoolId} from "v4-core/src/types/PoolId.sol";
import {StateLibrary} from "v4-core/src/libraries/StateLibrary.sol";

contract TwapOracleHook is BaseHook {
    using StateLibrary for IPoolManager;

    struct Observation {
        uint32 timestamp;
        int56 tickCumulative;   // running sum of (tick * time-since-last-observation)
    }

    mapping(PoolId => Observation) public lastObservation;

    constructor(IPoolManager _poolManager) BaseHook(_poolManager) {}

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false, afterInitialize: true,
            beforeAddLiquidity: false, afterAddLiquidity: false,
            beforeRemoveLiquidity: false, afterRemoveLiquidity: false,
            beforeSwap: false, afterSwap: true,   // <- we only need to observe AFTER price changes
            beforeDonate: false, afterDonate: false,
            beforeSwapReturnDelta: false, afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false, afterRemoveLiquidityReturnDelta: false
        });
    }

    function _afterInitialize(address, PoolKey calldata key, uint160, int24 tick)
        internal override returns (bytes4)
    {
        lastObservation[key.toId()] = Observation({
            timestamp: uint32(block.timestamp),
            tickCumulative: 0
        });
        return this.afterInitialize.selector;
    }

    function _afterSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, /* delta */ , bytes calldata)
        internal override returns (bytes4, int128)
    {
        PoolId id = key.toId();
        Observation memory last = lastObservation[id];

        (, int24 currentTick, , ) = poolManager.getSlot0(id);
        uint32 elapsed = uint32(block.timestamp) - last.timestamp;

        // this is the core TWAP-accumulator trick: instead of storing every historical
        // price point, we store a running SUM of (tick * time it was active for).
        // any two snapshots of this running sum can reconstruct the average tick
        // over that interval, without ever storing per-block history.
        int56 newCumulative = last.tickCumulative + int56(currentTick) * int56(uint56(elapsed));

        lastObservation[id] = Observation({
            timestamp: uint32(block.timestamp),
            tickCumulative: newCumulative
        });

        return (this.afterSwap.selector, 0);
    }

    // this is what another contract (or another hook) actually calls to GET a TWAP
    function consultTwap(PoolKey calldata key, uint32 secondsAgoStart, uint32 secondsAgoEnd)
        external view returns (int24 averageTick)
    {
        // in a real implementation you'd store a ring buffer of historical Observations
        // and interpolate between the two snapshots bracketing your requested window;
        // this simplified version illustrates the underlying math using only the latest one
        Observation memory last = lastObservation[key.toId()];
        // (production code: look up two Observations at the requested times, then)
        // averageTick = (cumulativeAtEnd - cumulativeAtStart) / (secondsAgoEnd - secondsAgoStart)
    }
}
```

**Why a "cumulative sum" instead of just storing the last N prices?** Because storing and iterating over N historical data points on-chain is expensive (every stored value is a real, gas-costing storage slot). The cumulative-sum trick lets you compute the average over *any* window using just two snapshots — the value right now, and the value from however far back you want to average over — subtract them and divide by elapsed time. This is exactly the technique Uniswap v2/v3's own built-in oracle uses internally; you're not inventing a new idea here, you're reimplementing a well-established pattern by hand inside your own hook.

## Pattern B: reading an external oracle instead (Chainlink-style)

For cases where you don't trust even a TWAP of this specific pool (maybe it's thin/new/easily manipulated), pull a price from outside entirely:

```solidity
import {AggregatorV3Interface} from "chainlink/interfaces/AggregatorV3Interface.sol";

contract ExternalOracleHook is BaseHook {
    AggregatorV3Interface public immutable priceFeed;

    constructor(IPoolManager _poolManager, address _priceFeed) BaseHook(_poolManager) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    function getExternalPrice() public view returns (int256 price, uint256 updatedAt) {
        (, price, , updatedAt, ) = priceFeed.latestRoundData();

        // ALWAYS check staleness — a feed that hasn't updated recently might be
        // broken, and trusting a stale price is exactly the "wrong reference price"
        // failure mode that makes a hook's logic dangerously wrong
        require(block.timestamp - updatedAt < 1 hours, "stale price feed");
        require(price > 0, "invalid price");
    }

    function _beforeSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, bytes calldata)
        internal override returns (bytes4, BeforeSwapDelta, uint24)
    {
        (int256 externalPrice, ) = getExternalPrice();
        // ... compare externalPrice against the pool's own current price,
        // and use the deviation to drive a directional fee (article 8),
        // or block/adjust the trade if it looks like a depeg (article 13)
    }
}
```

**The staleness check is not optional boilerplate — it's the whole point.** An oracle that silently returns a six-hour-old price during a network outage is worse than no oracle at all, because your hook will confidently act on wrong information instead of visibly failing. Every real integration of an external oracle needs this kind of "is this data actually fresh" guard.

## When to use which pattern

Rolling your own TWAP (Pattern A) is cheap, requires no external dependency, and works for any pool — but it can only ever reflect *this specific pool's* trading activity, which is a weaker signal for a thin/new/low-volume pool. Reading an external oracle (Pattern B) gives you a signal aggregated across many venues, which is stronger for detecting things like stablecoin depegs — but it adds a dependency on that oracle network's own uptime and security, and it costs an external call (more gas) on every use.

## The one sentence to keep

**A self-rolled TWAP hook stores a running cumulative sum of `tick * time-elapsed` (not raw historical prices) so any two snapshots can reconstruct an average over any window cheaply, while an external-oracle hook instead calls out to a feed like Chainlink and must always check the returned data's staleness before trusting it — and most serious hooks that need "the real price" pick whichever tradeoff (self-contained but weaker vs. external but stronger) fits how thin or manipulable their specific pool is.**
