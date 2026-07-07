# 03 — GuardedHook.sol and the Four Mock Inner Hooks

Goal: read the base contract that inner-hook developers inherit (the "publish it as a base contract others inherit" bonus from the original build sketch), then meet the four characters the test suite uses to attack the guard from every direction.

## GuardedHook: BaseHook's cousin, rewired for life behind the guard

A normal hook inherits `BaseHook`, which does two big things: restricts callers to the PoolManager, and reverts `HookNotImplemented` for any callback you didn't override (safe, because the flags in your mined address mean unimplemented callbacks are never called). Behind the guard, both assumptions flip — so `GuardedHook` is a fresh base with three deliberate differences:

```solidity
abstract contract GuardedHook is IHooks {
    address public immutable guard;

    error NotGuard();

    modifier onlyGuard() {
        if (msg.sender != guard) revert NotGuard();
        _;
    }

    constructor(address _guard) {
        guard = _guard;
    }

    /// @notice The Hooks flag bits this hook implements — pass to configurePool
    function guardedPermissions() public pure virtual returns (uint160);
```

**Difference 1 — the caller is the guard.** `onlyGuard` replaces `onlyPoolManager`. Without it, anyone could call your callbacks directly and corrupt whatever state they keep; with it, only the guard's forwarded calls (which themselves only happen inside real PoolManager callbacks) get through. `immutable` means the binding is set at deployment and unchangeable — a wrapped hook belongs to one guard for life.

**Difference 2 — permissions are a declaration, not an address.** There is no mined address to read flags from, so the hook *states* its callbacks in `guardedPermissions()` — returning the same `Hooks.*_FLAG` constants OR-ed together — and the pool creator passes that value as `innerFlags` to `configurePool`. It's abstract (`virtual` with no body): the one thing every inheritor MUST answer is "which callbacks do you actually use." (Nothing on-chain forces the declaration to be honest — declare too much and the guard forwards calls your no-op defaults absorb; declare too little and your overrides never run. Either way you only hurt yourself.)

**Difference 3 — defaults are accepting no-ops, not reverts.** Every one of the ten callbacks has a default body returning its own selector (and zero deltas where the signature has them):

```solidity
function beforeSwap(address, PoolKey calldata, SwapParams calldata, bytes calldata)
    external virtual onlyGuard returns (bytes4, BeforeSwapDelta, uint24)
{
    return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
}
```

Why accepting instead of BaseHook's reverting? Defense in depth around the fail-closed dial: if a pool misdeclares `innerFlags` and the guard forwards a callback you didn't override, a reverting default would (on a fail-closed pool) freeze trading over a paperwork error. An accepting no-op keeps the pool alive and correct. Note the selectors are `IHooks.*` — the guard's handshake checks against the canonical interface selectors, and returning the right one is the entire "yes, I meant that" protocol.

The doc-comment on the contract states the house rules a wrapped hook lives under — return deltas must be zero (the delta firewall *will* revert your swaps otherwise), fee overrides get capped, and nothing you do can block an LP exit. Inheriting the base doesn't grant trust; it makes the rules ergonomic to follow.

## The four mocks: a cast of characters

Test suites for security systems need adversaries. `MockInnerHooks.sol` supplies four, each isolating one behavior. Notice they're all deployed with plain `new` — no address mining — which is itself the feature under test.

### CountingInnerHook — the honest observer

```solidity
contract CountingInnerHook is GuardedHook {
    uint256 public beforeSwapCount;
    uint256 public afterSwapCount;
    uint256 public beforeAddCount;
    uint256 public beforeRemoveCount;
    address public lastSender;

    function guardedPermissions() public pure override returns (uint160) {
        return uint160(Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG
             | Hooks.BEFORE_ADD_LIQUIDITY_FLAG | Hooks.BEFORE_REMOVE_LIQUIDITY_FLAG);
    }

    function beforeSwap(address sender, ...) external override onlyGuard returns (...) {
        beforeSwapCount++;
        lastSender = sender;
        return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
    // afterSwap / beforeAddLiquidity / beforeRemoveLiquidity: same pattern
}
```

The v4-template's classic `Counter.sol`, reborn behind the guard. Its counters prove *forwarding fidelity* — the guard called the right callbacks the right number of times — and `lastSender` proves the **original sender** (the router, not the guard, not the PoolManager) survives the extra hop. It subscribes to four callbacks; the guard must forward exactly those and skip the rest.

### FeeSettingInnerHook — the legitimate dynamic-fee hook (with a dark side)

```solidity
contract FeeSettingInnerHook is GuardedHook {
    uint24 public fee;

    constructor(address _guard, uint24 _fee) GuardedHook(_guard) { fee = _fee; }
    function setFee(uint24 _fee) external { fee = _fee; }

    function guardedPermissions() public pure override returns (uint160) {
        return uint160(Hooks.BEFORE_SWAP_FLAG);
    }

    function beforeSwap(...) external view override onlyGuard returns (...) {
        return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA,
                fee | LPFeeLibrary.OVERRIDE_FEE_FLAG);
    }
}
```

A perfectly normal fee-override hook (lesson-18 pattern: fee OR-ed with `OVERRIDE_FEE_FLAG`)... whose fee is **mutable by anyone** (`setFee` has no access control — deliberately, in a *mock*, so tests and the demo can flip it evil in one call). At 1% it demonstrates the pass-through path: the guard lets a compliant override reach the pool untouched. At 50% it *is* the rogue-hook scenario — "the audited hook turned greedy overnight" — and the fee firewall's `FeeCapExceeded` is the answer. This same contract, at 0.3%, is what the live demo deploys as its inner hook.

### DeltaStealingInnerHook — the thief

```solidity
function beforeSwap(address, PoolKey calldata, SwapParams calldata params, bytes calldata)
    external view override onlyGuard returns (bytes4, BeforeSwapDelta, uint24)
{
    // try to skim 10% of the swap
    int256 amt = params.amountSpecified < 0 ? -params.amountSpecified : params.amountSpecified;
    return (IHooks.beforeSwap.selector, toBeforeSwapDelta(int128(amt / 10), 0), 0);
}
```

This is a *real attack shape*, not a strawman: a positive specified delta is exactly how legitimate fee-taking hooks charge swappers (the MEV-tax project does precisely this, honestly). An inner hook returning one through an unguarded wrapper would siphon 10% of every swap. The guard's delta firewall reads the returned delta before the PoolManager ever sees it and reverts `InnerDeltaForbidden` — theft by return value is a compile-time-shaped hole closed at runtime.

### RevertingInnerHook — the bricked dependency

```solidity
function beforeSwap(...) external view override onlyGuard returns (...) {
    revert("inner hook is broken");
}
// beforeAddLiquidity, beforeRemoveLiquidity: same revert
```

Not malicious — *dead*. An upgrade gone wrong, a dependency that renounced, an oracle it calls that vanished. It subscribes to three callbacks and reverts all of them, which lets the tests exercise the whole failure matrix: fail-open pool → swaps work anyway (guard skips it, emits `InnerHookSkipped`); fail-closed pool → swaps revert `InnerHookFailed`; and on *both*, `removeLiquidity` succeeds — because the exit path passes `forceOpen = true` no matter what. One mock, three verdicts, rule 6 proven against the worst case: a hook that reverts *specifically* on the exit callback.

## What the cast teaches about the design

Line the four up against the invariant table: Counting proves the *plumbing* (forward the right calls, preserve the sender), FeeSetting proves the *fee firewall* (pass compliant, block greedy), DeltaStealing proves the *delta firewall*, Reverting proves the *failure dial and rule 6*. The outflow caps and price band need no evil inner hook at all — they're tested with `innerHook = address(0)` (pure circuit-breaker mode), because those invariants police the *market*, not the hook. Every invariant has a dedicated adversary or a dedicated bare-mode test; nothing is proven by vibes.

## The one sentence to keep

**`GuardedHook` is BaseHook re-derived for a different trust root — `onlyGuard` instead of `onlyPoolManager`, a `guardedPermissions()` declaration instead of a mined address, accepting no-op defaults instead of reverts — and the four mocks are a complete adversary cast (an honest counter, a fee hook that can turn greedy, a return-delta thief, and a bricked reverter) that map one-to-one onto the guard's invariants, so every protection is proven against the specific attack it was built for.**
