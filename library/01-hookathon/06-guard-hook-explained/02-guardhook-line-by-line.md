# 02 — GuardHook.sol, Line by Line

Goal: walk the guard from configuration to every callback. The contract is long (~500 lines) but rhythmic — ten callbacks share one skeleton, so once you've read the swap path deeply, the rest read themselves.

## The configuration struct — one pool's whole safety policy

```solidity
struct GuardConfig {
    address innerHook;   // address(0) = no inner hook: a pure circuit breaker
    uint160 innerFlags;  // which callbacks the inner hook implements (Hooks flag bits)
    address guardian;    // can pause/unpause and update limits
    bool failOpen;       // inner hook failure: true = skip it, false = revert
    bool paused;         // manual switch
    uint64 pausedUntil;  // auto circuit-breaker cooldown deadline
    uint24 maxFee;       // cap on the inner hook's dynamic-fee override (1e6 = 100%)
    uint16 maxPriceMoveBps; // max pool price move within one block (0 = disabled)
    uint32 cooldown;     // seconds of auto-pause when the soft cap trips
    uint128 blockOutflowSoftCap; // per-token outflow per block that trips the breaker (0 = disabled)
    uint128 blockOutflowHardCap; // per-token outflow per block that reverts (0 = disabled)
}
```

Read it as three groups: *identity* (innerHook, innerFlags, guardian), *failure policy* (failOpen, paused, pausedUntil), *limits* (the five numbers). Every limit has a 0-disables convention, so a pool can adopt exactly the subset of protections it wants. `innerFlags` is stored as raw `uint160` flag bits — the same constants (`Hooks.BEFORE_SWAP_FLAG` etc.) the PoolManager uses on addresses, reused as a plain bitmap for "what should I forward."

```solidity
mapping(PoolId => GuardConfig) internal _config;

mapping(PoolId => uint256) internal _baselineBlock;
mapping(PoolId => uint160) internal _baselineSqrtPrice;

mapping(PoolId => mapping(uint256 => uint256)) public blockOutflow0;
mapping(PoolId => mapping(uint256 => uint256)) public blockOutflow1;
```

The two `_baseline*` mappings implement "the price at this block's first operation"; the two `blockOutflow*` mappings are the per-block drain meters, keyed by `block.number` (old entries become dead storage — never read again, cheaper than cleaning). `_config` is internal with an explicit `config(id)` view returning the whole struct — a deliberate choice, because auto-generated getters for structs flatten them into tuples that are unpleasant for UIs; the explicit view gives named fields to ethers.

## Registration: `configurePool` — the guard's front door

```solidity
function configurePool(
    PoolKey calldata key,
    address innerHook,
    uint160 innerFlags,
    bool failOpen,
    uint24 maxFee,
    uint16 maxPriceMoveBps,
    uint32 cooldown,
    uint128 blockOutflowSoftCap,
    uint128 blockOutflowHardCap
) external {
    if (address(key.hooks) != address(this)) revert WrongHookAddress();
    if (maxFee > LPFeeLibrary.MAX_LP_FEE) revert BadCaps();
    if (blockOutflowHardCap != 0 && blockOutflowSoftCap > blockOutflowHardCap) revert BadCaps();
    PoolId id = key.toId();
    if (_config[id].guardian != address(0)) revert AlreadyConfigured();

    _config[id] = GuardConfig({ ..., guardian: msg.sender,
        innerFlags: innerHook == address(0) ? 0 : innerFlags, ... });
    emit PoolGuarded(id, innerHook, msg.sender);
}
```

Why must this happen **before** `poolManager.initialize`? Because `initialize` takes no hook data in current v4 — there is no way to smuggle a config into the creation call itself. So the flow is: compute the `PoolKey` you intend to create → `configurePool(key, ...)` → `initialize(key, price)`, and the guard's `_beforeInitialize` rejects any pool that skipped step two (`NotConfigured`). The checks in order: the key must actually point at this guard (else you're configuring a pool that will never call us — a footgun); the fee cap must be a legal LP fee; soft ≤ hard when both are set; and **first-come-first-owned** — `guardian != address(0)` doubles as the "exists" sentinel, and `AlreadyConfigured` prevents anyone from re-registering (and thereby hijacking) a pool. The `msg.sender` becomes the guardian: whoever creates the pool owns its safety dials. Forcing `innerFlags = 0` when `innerHook == 0` keeps the pure-circuit-breaker mode from ever attempting a forward to the zero address.

## The guardian's controls

```solidity
modifier onlyGuardian(PoolId id) {
    if (msg.sender != _config[id].guardian) revert NotGuardian();
    _;
}

function pause(PoolId id) external onlyGuardian(id) { _config[id].paused = true; ... }
function unpause(PoolId id) external onlyGuardian(id) {
    _config[id].paused = false;
    _config[id].pausedUntil = 0;   // also lifts an active cooldown early
    ...
}
function setLimits(...) external onlyGuardian(id) { /* re-validates BadCaps bounds */ }
function setFailOpen(...) / transferGuardian(...) ...
```

Per-pool ACL (contrast the other two projects' single global owner — here every pool has its *own* guardian, because the guard is shared infrastructure). `unpause` clearing `pausedUntil` is what makes it double as "lift the auto-cooldown early." And the paired view used everywhere:

```solidity
function isPaused(PoolId id) public view returns (bool) {
    GuardConfig storage cfg = _config[id];
    return cfg.paused || block.timestamp < cfg.pausedUntil;
}
```

Paused = the manual flag **or** a still-running cooldown. Two mechanisms, one question.

## The three internal workhorses

```solidity
function _cfg(PoolId id) internal view returns (GuardConfig storage cfg) {
    cfg = _config[id];
    if (cfg.guardian == address(0)) revert NotConfigured();
}

function _requireLive(GuardConfig storage cfg) internal view {
    if (cfg.paused || block.timestamp < cfg.pausedUntil) revert PoolIsPaused();
}

function _wants(GuardConfig storage cfg, uint160 flag) internal view returns (bool) {
    return cfg.innerHook != address(0) && (cfg.innerFlags & flag) != 0;
}
```

`_cfg` = fetch-or-die (returns a `storage` pointer — one SLOAD, mutations write through). `_requireLive` = the pause gate. `_wants` = "does this pool's inner hook subscribe to this callback." Every callback body opens with some combination of these three.

And the heart of the forwarding machinery:

```solidity
function _callInner(
    GuardConfig storage cfg, PoolId id, bytes memory callData,
    bytes4 expectedSelector, bool forceOpen
) internal returns (bool ok, bytes memory ret) {
    (ok, ret) = cfg.innerHook.call(callData);
    if (ok && ret.length >= 32 && bytes4(ret) == expectedSelector) return (true, ret);
    if (cfg.failOpen || forceOpen) {
        emit InnerHookSkipped(id, expectedSelector);
        return (false, ret);
    }
    revert InnerHookFailed(expectedSelector);
}
```

Concept 3 from the previous chapter, realized. The acceptance test — success AND ≥32 bytes AND selector echo — is the same handshake the PoolManager demands of real hooks. On failure, the `forceOpen` parameter is rule 6's lever: callers pass `true` on the remove-liquidity path, overriding even fail-closed pools. The `InnerHookSkipped` event turns silent degradation into an observable — a monitoring system watching a fail-open pool sees every skip.

## The swap path — where all six invariants live

### `_beforeSwap`

```solidity
PoolId id = key.toId();
GuardConfig storage cfg = _cfg(id);
_requireLive(cfg);              // invariant 5: paused pools don't trade
_snapshotBaseline(id);          // arm invariant 4 for this block

uint24 fee = 0;
if (_wants(cfg, Hooks.BEFORE_SWAP_FLAG)) {
    (bool ok, bytes memory ret) = _callInner(
        cfg, id, abi.encodeCall(IHooks.beforeSwap, (sender, key, params, hookData)),
        IHooks.beforeSwap.selector, false
    );
    if (ok) {
        (, int256 innerDelta, uint24 innerFee) = abi.decode(ret, (bytes4, int256, uint24));
        // DELTA FIREWALL: the inner hook cannot take tokens via return deltas
        if (innerDelta != 0) revert InnerDeltaForbidden();
        // FEE FIREWALL: the inner hook's fee override can never exceed the cap
        if (innerFee != 0) {
            uint24 raw = innerFee & ~uint24(LPFeeLibrary.OVERRIDE_FEE_FLAG);
            if (raw > cfg.maxFee) revert FeeCapExceeded(raw, cfg.maxFee);
            fee = innerFee;
        }
    }
}
return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, fee);
```

Read the checks against their invariants. The **delta firewall** decodes the inner's `BeforeSwapDelta` as a raw `int256` (that's all the type is underneath) and rejects *any* nonzero value — v1's rule is absolute: wrapped hooks may observe and set fees but may not touch balances, because the alternative (mediating inner settlements safely) is a genuinely hard v2 problem, and a firewall that's simple is a firewall that's verifiable. The **fee firewall** strips the `OVERRIDE_FEE_FLAG` bit to get the raw fee number, compares against the cap, and — crucially — forwards the *original flagged value* on success, so an honest dynamic-fee inner hook works transparently through the guard. Note what the guard returns for itself: always `ZERO_DELTA` (its own hands stay clean) and the inner's fee or 0.

And the baseline arm:

```solidity
function _snapshotBaseline(PoolId id) internal {
    if (_baselineBlock[id] != block.number) {
        (uint160 sqrtPriceX96,,,) = poolManager.getSlot0(id);
        _baselineBlock[id] = block.number;
        _baselineSqrtPrice[id] = sqrtPriceX96;
    }
}
```

First swap of a block stores the pre-trade price; later swaps in the same block skip (the `!=` check), so the band always measures against the block's *opening* price — cumulative by construction.

### `_afterSwap`

```solidity
if (_wants(cfg, Hooks.AFTER_SWAP_FLAG)) {
    ... _callInner(afterSwap) ...
    if (ok) {
        (, int128 innerDelta) = abi.decode(ret, (bytes4, int128));
        if (innerDelta != 0) revert InnerDeltaForbidden();   // firewall again
    }
}

_accountOutflow(id, cfg, delta);   // invariant 3

if (cfg.maxPriceMoveBps != 0) {    // invariant 4
    (uint160 current,,,) = poolManager.getSlot0(id);
    uint256 moveBps = _priceMoveBps(_baselineSqrtPrice[id], current);
    if (moveBps > cfg.maxPriceMoveBps) revert PriceMoveExceeded(moveBps, cfg.maxPriceMoveBps);
}
return (BaseHook.afterSwap.selector, 0);
```

Forward-and-firewall first, then the two core-sourced checks. The order (inner first, checks after) doesn't matter for safety — a revert anywhere unwinds everything — but letting the inner hook run first means its state updates are included in what a revert unwinds.

### `_accountOutflow` — hard cap and soft trigger in one pass

```solidity
int128 a0 = delta.amount0();
if (a0 > 0) {
    uint256 v = blockOutflow0[id][block.number] + uint128(a0);
    if (cfg.blockOutflowHardCap != 0 && v > cfg.blockOutflowHardCap) {
        revert OutflowHardCapExceeded(v, cfg.blockOutflowHardCap);
    }
    blockOutflow0[id][block.number] = v;
    if (cfg.blockOutflowSoftCap != 0 && v > cfg.blockOutflowSoftCap) tripped = v;
}
// ... mirror for a1 ...

if (tripped != 0 && cfg.cooldown != 0 && block.timestamp >= cfg.pausedUntil) {
    cfg.pausedUntil = uint64(block.timestamp + cfg.cooldown);
    emit CircuitBreakerTripped(id, tripped, cfg.blockOutflowSoftCap, cfg.pausedUntil);
}
```

Per positive leg (tokens leaving the pool): accumulate → hard-cap check (revert **before** writing, so a rejected swap consumes no allowance... note the check is on the *new* total `v`, so it's cumulative across the block) → store → soft-cap comparison. Then the breaker: the crossing swap *stands* (concept 5 — you can't revert and pause in the same breath), the cooldown deadline is written, the event fires. The `block.timestamp >= cfg.pausedUntil` condition stops repeated trips inside one block from re-extending the deadline — and the very next operation on the pool will hit `_requireLive` and stop.

### `_priceMoveBps` — the band math

```solidity
if (baseline == 0) return 0;
uint256 sqrtRatioBps = FullMath.mulDiv(current, 10_000, baseline);
if (sqrtRatioBps >= 20_000 || sqrtRatioBps == 0) return type(uint16).max; // >4x price move
uint256 priceRatioBps = (sqrtRatioBps * sqrtRatioBps) / 10_000;
return priceRatioBps >= 10_000 ? priceRatioBps - 10_000 : 10_000 - priceRatioBps;
```

Same square-the-sqrt-ratio construction as the market-hours band (see that book for the derivation), returned as an absolute deviation in bps. The `type(uint16).max` return on extreme ratios both avoids overflow in the squaring and guarantees any configured band rejects a >4× move.

## The other callbacks — the skeleton with different muscles

**Initialize:** `_beforeInitialize` runs `_cfg` — this is where an unconfigured pool dies at creation — then forwards if wanted; `_afterInitialize` just forwards. No pause check (you can't pause a pool that doesn't exist yet).

**Add liquidity:** `_beforeAddLiquidity` checks `_requireLive` — **deposits into a paused pool are blocked**, deliberately: a pause usually means "something may be compromised," and the guard shouldn't let newcomers walk into it. Then forwards. `_afterAddLiquidity` forwards and firewalls the inner's returned `BalanceDelta` (decoded as `int256`, rejected if nonzero), returning `ZERO_DELTA` for itself.

**Remove liquidity — rule 6, in code:**

```solidity
function _beforeRemoveLiquidity(...) internal override returns (bytes4) {
    PoolId id = key.toId();
    GuardConfig storage cfg = _cfg(id);
    if (_wants(cfg, Hooks.BEFORE_REMOVE_LIQUIDITY_FLAG)) {
        _callInner(cfg, id, abi.encodeCall(IHooks.beforeRemoveLiquidity, (...)),
                   IHooks.beforeRemoveLiquidity.selector, true /* forceOpen */);
    }
    return BaseHook.beforeRemoveLiquidity.selector;
}
```

Spot the two absences: **no `_requireLive`** (a paused pool still lets LPs leave) and **`forceOpen = true`** (a reverting inner hook is skipped even on fail-closed pools). `_afterRemoveLiquidity` goes further: it doesn't even *look* at the inner's returned delta — comment in source: *"inner delta is ignored entirely: an inner hook can never skim an exit"* — and returns `ZERO_DELTA` unconditionally. Three code-level decisions, one guarantee: nothing in this system can stand between an LP and their principal.

**Donate:** pause-checked on `before` (donations enter the pool; a paused pool shouldn't accept them), plain forwards otherwise.

## What the guard structurally cannot do (honest edges)

The guard sees only what crosses the PoolManager's callbacks. Bunni's actual bug lived in *vault accounting above the pool* — a guard can't detect wrong math it never sees. What it *does* guarantee is the bound: whatever breaks, tokens cannot leave the pool faster than `hardCap` per block, and a soft-cap trip freezes the flow within one block. Blast radius, not bug-freedom — the honest product.

## The one sentence to keep

**The guard is one struct (a pool's safety policy), three helpers (`_cfg` fetch-or-die, `_requireLive` pause gate, `_wants` forwarding bitmap), one distrusting call primitive (raw `call` + selector handshake + the fail-open/forceOpen dial), and ten callbacks on a shared skeleton — with the swap path enforcing fee cap and delta firewall on the inner's returns, outflow caps and the price band on the core's own numbers, and the remove-liquidity path stripped of every check that could ever hold an LP hostage.**
