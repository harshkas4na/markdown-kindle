# 21 — Code Pattern: On-Chain Limit Order Hook

Goal: build the pattern behind the "place a limit order, no external bot required" idea from article `order-types-routing-auctions.md` — a hook that lets a user say "execute my trade only once the price reaches tick X," implemented as single-sided liquidity that gets automatically consumed when the price crosses that tick.

## The core trick: a limit order IS a single-sided liquidity position

Recall article 4: a concentrated liquidity position only needs to hold *both* tokens if its range straddles the current price. If you place a position entirely *above* or entirely *below* the current price, it only needs to hold one of the two tokens — and here's the key insight: **as the price moves through that position's range, the position mechanically converts entirely from one token into the other.** That conversion, happening automatically as a side effect of normal AMM math, *is* the limit order executing. You don't need special "order" logic distinct from liquidity provision — you need a hook that (1) tracks which narrow ranges have pending single-sided positions, and (2) notices, after each swap, when the price has crossed through one, so it can let the user claim their now-converted tokens.

## The hook

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {PoolId} from "v4-core/src/types/PoolId.sol";
import {StateLibrary} from "v4-core/src/libraries/StateLibrary.sol";

contract LimitOrderHook is BaseHook {
    using StateLibrary for IPoolManager;

    struct Order {
        address owner;
        int24 tick;
        bool zeroForOne;   // which direction this order is selling
        uint256 amount;
        bool executed;
    }

    mapping(PoolId => mapping(int24 => Order[])) public ordersAtTick;
    mapping(PoolId => int24) public lastCheckedTick;

    constructor(IPoolManager _poolManager) BaseHook(_poolManager) {}

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false, afterInitialize: true,
            beforeAddLiquidity: false, afterAddLiquidity: false,
            beforeRemoveLiquidity: false, afterRemoveLiquidity: false,
            beforeSwap: false,
            afterSwap: true,   // <- this is where we detect a crossed order and execute it
            beforeDonate: false, afterDonate: false,
            beforeSwapReturnDelta: false, afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false, afterRemoveLiquidityReturnDelta: false
        });
    }

    // user-facing function: place a limit order at a specific tick
    function placeOrder(PoolKey calldata key, int24 tick, bool zeroForOne, uint256 amount) external {
        // (real implementation: pull `amount` of the correct token from msg.sender,
        // then deposit it as single-sided liquidity via poolManager.modifyLiquidity()
        // at [tick, tick + tickSpacing], recording it below for tracking)

        ordersAtTick[key.toId()][tick].push(Order({
            owner: msg.sender,
            tick: tick,
            zeroForOne: zeroForOne,
            amount: amount,
            executed: false
        }));
    }

    function _afterInitialize(address, PoolKey calldata key, uint160, int24 tick)
        internal override returns (bytes4)
    {
        lastCheckedTick[key.toId()] = tick;
        return this.afterInitialize.selector;
    }

    function _afterSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, /* delta */ , bytes calldata)
        internal override returns (bytes4, int128)
    {
        PoolId id = key.toId();
        (, int24 currentTick, , ) = poolManager.getSlot0(id);
        int24 previousTick = lastCheckedTick[id];

        // walk every tick between where we were and where we are now,
        // checking for any pending orders that just got crossed
        if (currentTick > previousTick) {
            for (int24 t = previousTick; t <= currentTick; t++) {
                _tryExecuteOrdersAtTick(key, id, t);
            }
        } else if (currentTick < previousTick) {
            for (int24 t = previousTick; t >= currentTick; t--) {
                _tryExecuteOrdersAtTick(key, id, t);
            }
        }

        lastCheckedTick[id] = currentTick;
        return (this.afterSwap.selector, 0);
    }

    function _tryExecuteOrdersAtTick(PoolKey calldata key, PoolId id, int24 tick) internal {
        Order[] storage orders = ordersAtTick[id][tick];
        for (uint256 i = 0; i < orders.length; i++) {
            if (!orders[i].executed) {
                orders[i].executed = true;
                // (real implementation: call poolManager.modifyLiquidity() to remove
                // this single-sided position, which by now holds the OTHER token,
                // and credit it to orders[i].owner's claimable balance)
            }
        }
    }

    // user-facing function: withdraw tokens from a filled order
    function claimOrder(PoolKey calldata key, int24 tick, uint256 orderIndex) external {
        Order storage order = ordersAtTick[key.toId()][tick][orderIndex];
        require(order.executed, "not filled yet");
        require(order.owner == msg.sender, "not your order");
        // (transfer the converted tokens to msg.sender, mark as claimed)
    }
}
```

## The part worth sitting with: why we loop over ticks, not just check "did we cross"

Notice `_afterSwap` walks tick-by-tick between `previousTick` and `currentTick`, rather than just comparing the two endpoints. This matters because a single large swap can cross *many* ticks in one transaction — if three different users placed limit orders at three different ticks and one big trade blows through all three at once, all three need to be detected and executed within that same `afterSwap` call, not just the final resting tick. This is a real gas consideration in production: if `currentTick - previousTick` can be very large (a huge single swap), looping over every tick in between can get expensive — real implementations often use a more efficient bitmap-based structure (similar to how Uniswap's own core tracks "which ticks have liquidity" via a `TickBitmap`) to jump directly to only the ticks that actually have pending orders, rather than iterating over every possible tick number.

## Why `claimOrder` is a separate function instead of auto-sending funds

Deliberately splitting "detect and execute" (`afterSwap`) from "claim your filled order" (`claimOrder`) rather than automatically pushing tokens to the user the moment their order fills is a common, deliberate pattern: pushing tokens to an arbitrary external address as a side effect of *someone else's* swap transaction adds gas cost to that unrelated swap, and — more importantly — opens a reentrancy surface (sending tokens can trigger arbitrary code in the recipient) at a moment when the PoolManager's own accounting is still mid-settlement. Letting the order-filler claim their own tokens later, in their own separate transaction, is simpler and safer.

## The one sentence to keep

**An on-chain limit order is really just a single-sided liquidity position placed at a specific tick, which mechanically converts into the other token as the price crosses through it — the hook's real job is watching `afterSwap` for which ticks got crossed (potentially many in one swap) and marking those positions executed, while actually handing tokens back to the user happens in a separate, user-initiated `claimOrder` call rather than automatically, to avoid loading unrelated gas cost and reentrancy risk onto someone else's swap transaction.**
