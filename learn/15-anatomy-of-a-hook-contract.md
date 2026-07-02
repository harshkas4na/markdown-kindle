# 15 — Anatomy of a Hook Contract

Goal: read a genuinely minimal, real-shaped hook line by line, so every piece of boilerplate you'll see in every other hook (including the complex ones later in this series) is something you've already met and understood once, slowly.

## The simplest possible hook: a swap counter

This hook does nothing clever — it just counts how many times `beforeSwap` and `afterSwap` have been called on it. That's the entire "Counter.sol" example from the v4-template, and it's the right first thing to read because there's zero business logic to distract you from the *shape* every hook shares.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {BalanceDelta} from "v4-core/src/types/BalanceDelta.sol";
import {BeforeSwapDelta, BeforeSwapDeltaLibrary} from "v4-core/src/types/BeforeSwapDelta.sol";

contract Counter is BaseHook {
    // --- state: this is YOUR hook's own storage, separate from the pool's ---
    mapping(PoolId => uint256) public beforeSwapCount;
    mapping(PoolId => uint256) public afterSwapCount;

    // every hook's constructor just needs to know which PoolManager it belongs to
    constructor(IPoolManager _poolManager) BaseHook(_poolManager) {}

    // --- this is the part every hook MUST implement: declare which callbacks you use ---
    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false,
            afterInitialize: false,
            beforeAddLiquidity: false,
            afterAddLiquidity: false,
            beforeRemoveLiquidity: false,
            afterRemoveLiquidity: false,
            beforeSwap: true,          // <- we're turning this ON
            afterSwap: true,           // <- and this ON
            beforeDonate: false,
            afterDonate: false,
            beforeSwapReturnDelta: false,
            afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false,
            afterRemoveLiquidityReturnDelta: false
        });
    }

    // --- the actual callback logic ---
    function _beforeSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, bytes calldata)
        internal
        override
        returns (bytes4, BeforeSwapDelta, uint24)
    {
        beforeSwapCount[key.toId()]++;
        return (this.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }

    function _afterSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, BalanceDelta, bytes calldata)
        internal
        override
        returns (bytes4, int128)
    {
        afterSwapCount[key.toId()]++;
        return (this.afterSwap.selector, 0);
    }
}
```

Now let's take this apart piece by piece — this is the part worth actually understanding, not memorizing.

## `BaseHook` — why you extend it instead of writing raw `IHooks`

Recall article 6: the PoolManager calls specific functions on your contract at specific lifecycle moments. In principle you could implement the raw `IHooks` interface yourself, but `BaseHook` (from v4-periphery) does two useful things for you: (1) it enforces, via the constructor, that only your declared PoolManager can call your callback functions (rejecting calls from anyone else — a real security concern, covered properly in lesson 25), and (2) it splits each public callback (`beforeSwap`) into a public wrapper plus an internal `_beforeSwap` you actually override, which is just a code-organization convenience. Nearly every real hook you'll ever read extends `BaseHook` rather than raw `IHooks`.

## `getHookPermissions()` — this is article 6's "address mining" flags, made concrete

Remember: a hook's deployed *address* has to have specific bits set, matching exactly which callbacks it uses. `getHookPermissions()` is where you, the developer, declare in code which callbacks you intend to use — and this declaration is what a deployment tool (lesson 16) reads to figure out which address bit-pattern to mine for. If you set `beforeSwap: true` here but deploy to an address whose bits don't match, the PoolManager will reject the pool creation outright — the two have to agree.

Notice: even though this Counter hook implements `_beforeAddLiquidity` internally as inherited boilerplate from `BaseHook`, we declared `beforeAddLiquidity: false` here — meaning the PoolManager will simply never call it for this hook. Only flip a permission to `true` for callbacks you actually use; every `true` flag is a real callback the PoolManager will invoke on every relevant pool action, forever, which costs gas even if your logic inside is trivial.

## `PoolKey` and `PoolId` — how a hook knows *which* pool is calling it

A single hook contract can be attached to many different pools simultaneously (e.g. one dynamic-fee hook, reused across a hundred different token pairs). Every callback receives a `PoolKey` — a struct identifying exactly which pool this specific call is about:

```solidity
struct PoolKey {
    Currency currency0;   // the lower-sorted token address
    Currency currency1;   // the higher-sorted token address
    uint24 fee;           // the pool's fee (or a flag meaning "dynamic, ask the hook")
    int24 tickSpacing;    // how fine-grained the pool's ticks are (article 4)
    IHooks hooks;         // this pool's hook address
}
```

`key.toId()` compresses that struct into a single `PoolId` (just a hash), which is the standard way hooks key their own per-pool storage — exactly how `Counter` above uses `mapping(PoolId => uint256)` to track a separate count for every pool that uses it, even though it's one single deployed hook contract.

## The return values: how a hook actually changes behavior, not just observes it

This is the detail that trips people up most: `_beforeSwap` doesn't just run some logic and return — its return values can *actively change what happens next*.

- The `bytes4` return (`this.beforeSwap.selector`) is a required "yes, this call succeeded and was intentional" signature the PoolManager checks — every hook callback must return its own function selector, or the whole transaction reverts. This exists as a safety check against hooks being called by accident or a broken implementation silently doing nothing.
- The `BeforeSwapDelta` return is where a hook can inject its own token adjustments into the trade *before* it executes — this is the exact mechanism a fee-override hook (lesson 18) uses to change how much the trader actually pays, and how a JIT-liquidity hook (lesson 20) can add its own liquidity into the mix for this one swap.
- The `uint24` return (in `_beforeSwap` specifically) is used to override the pool's fee for this specific swap, when the pool was configured for dynamic fees — the exact lever dynamic-fee hooks pull.

The `Counter` hook above returns "zero, do nothing extra" for all of these — it's a pure observer. Every code-pattern lesson from here on is really just "what non-zero values do we return, and why."

## The one sentence to keep

**Every real hook extends `BaseHook` (which enforces that only the PoolManager can call you), declares which callbacks it uses via `getHookPermissions()` (which must match the bits mined into its deployment address), receives a `PoolKey`/`PoolId` on every call to know which specific pool triggered it, and expresses its actual effect on the trade not by changing global state alone but through the specific return values each callback demands — the difference between every "boring" hook and every "clever" hook in this entire directory is almost entirely about what non-zero values it chooses to return.**
