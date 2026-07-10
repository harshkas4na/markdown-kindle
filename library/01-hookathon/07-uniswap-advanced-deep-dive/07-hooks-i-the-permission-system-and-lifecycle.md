# Hooks I — The Permission System and Lifecycle

**Fast overview:** a hook is a contract the PoolManager calls at fixed points in a pool's life: before/after initialize, add/remove liquidity, swap, and donate. Which calls happen is encoded in the *bits of the hook contract's own address* — so deploying a hook means mining a CREATE2 salt until the address matches your permissions. This chapter covers the callback set, the address trick, deployment mechanics, and the basic (non-delta) hook patterns. The delta-returning superpowers wait for Chapter 8.

## The callback map

For each pool operation, the PoolManager consults the pool's `hooks` address (from the PoolKey — Chapter 6) and, if the corresponding permission bit is set, calls:

| Operation | Before | After |
|---|---|---|
| initialize | `beforeInitialize` | `afterInitialize` |
| add liquidity | `beforeAddLiquidity` | `afterAddLiquidity` |
| remove liquidity | `beforeRemoveLiquidity` | `afterRemoveLiquidity` |
| swap | `beforeSwap` | `afterSwap` |
| donate | `beforeDonate` | `afterDonate` |

Ten callbacks. Four more permission bits don't add callbacks but *upgrade* existing ones to return deltas (`beforeSwapReturnDelta`, `afterSwapReturnDelta`, `afterAddLiquidityReturnDelta`, `afterRemoveLiquidityReturnDelta`) — 14 flag bits total. The delta quartet is Chapter 8.

Every callback receives rich context — the caller (`sender`, i.e. the router/position manager that invoked the PoolManager, *not* the end user!), the full `PoolKey`, the operation's params, and an arbitrary `bytes hookData` passed through from the original caller. Every callback must return its own function selector as acknowledgment, or the transaction reverts.

Timing intuition: `before*` callbacks are your chance to *veto or reprice* (revert to block, update a dynamic fee, front-load custom logic); `after*` callbacks see the *result* (actual amounts, new price) and are your chance to *account, rebalance, or take a cut*. A veto is just `revert` — the entire transaction unwinds (flash accounting guarantees no partial state, Chapter 6).

## The address *is* the permission mask

Now the famous trick. The PoolManager must know which callbacks to attempt. Storing a permissions bitmap per pool would cost a storage read on every operation. Asking the hook (`hook.getPermissions()`) would cost an external call. v4 does neither:

**The low 14 bits of the hook's contract address are the permission bitmap.**

```solidity
// from v4-core Hooks.sol
uint160 constant BEFORE_INITIALIZE_FLAG          = 1 << 13;
uint160 constant AFTER_INITIALIZE_FLAG           = 1 << 12;
uint160 constant BEFORE_ADD_LIQUIDITY_FLAG       = 1 << 11;
uint160 constant AFTER_ADD_LIQUIDITY_FLAG        = 1 << 10;
uint160 constant BEFORE_REMOVE_LIQUIDITY_FLAG    = 1 << 9;
uint160 constant AFTER_REMOVE_LIQUIDITY_FLAG     = 1 << 8;
uint160 constant BEFORE_DONATE_FLAG              = 1 << 7;
uint160 constant AFTER_DONATE_FLAG               = 1 << 6;
uint160 constant BEFORE_SWAP_FLAG                = 1 << 5;
uint160 constant AFTER_SWAP_FLAG                 = 1 << 4;
uint160 constant BEFORE_SWAP_RETURNS_DELTA_FLAG  = 1 << 3;
uint160 constant AFTER_SWAP_RETURNS_DELTA_FLAG   = 1 << 2;
uint160 constant AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG    = 1 << 1;
uint160 constant AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG = 1 << 0;
```

Checking a permission is a bitwise AND on an address already in memory — effectively free. Elegant, with two sharp edges:

- **You can't choose your address freely.** You must deploy to an address whose low bits equal your flags — hence **address mining**: iterate CREATE2 salts until `keccak256(0xFF, deployer, salt, keccak256(initcode))` produces a matching address. With 14 constrained bits, ~2^14 ≈ 16k tries on average — seconds of compute. The v4-template ships `HookMiner` for exactly this; deterministic-deployment proxies let you land the same hook address on every chain. (*Connect the dot:* CREATE2-as-namespace is v2's deterministic pair trick, Chapter 3, upgraded from convenience to access control.)
- **Flags and implementation must agree.** Flag set but callback not implemented → PoolManager calls it, gets no selector back, *every such operation reverts* — a bricked pool (DoS). Callback implemented but flag not set → the PoolManager never calls it; your carefully written logic is dead code and whatever it was supposed to enforce silently doesn't exist. Both directions are real audit findings in the wild (Chapter 11's checklist, item one).

`pool.initialize` validates hook addresses: an address with *any* hook bits must pass `isValidHookAddress`, and a hook address of `address(0)` means "no hook, vanilla pool." Note also: **hook code is set forever at pool creation** — but nothing stops the hook from being an upgradeable proxy or having owner-controlled parameters. "Immutable pool, mutable hook" is a trust-model subtlety users routinely miss (Chapter 11).

## BaseHook and the shape of real code

Nobody writes the interface raw; you inherit `BaseHook` from `v4-periphery`, which pins the PoolManager, reverts non-manager callers, declares `getHookPermissions()` (checked against the address at deploy), and gives every callback a virtual default. A minimal, real hook:

```solidity
contract CounterHook is BaseHook {
    mapping(PoolId => uint256) public swapCount;

    constructor(IPoolManager pm) BaseHook(pm) {}

    function getHookPermissions() public pure override returns (Hooks.Permissions memory p) {
        p.afterSwap = true;           // everything else false
    }

    function _afterSwap(
        address, PoolKey calldata key, SwapParams calldata,
        BalanceDelta, bytes calldata
    ) internal override returns (bytes4, int128) {
        swapCount[key.toId()]++;
        return (BaseHook.afterSwap.selector, 0);   // 0 = taking no delta (Ch. 8)
    }
}
```

Three habits visible even in a toy:

1. **Key by `PoolId`.** One hook contract can serve many pools; per-pool state is mandatory hygiene. (A hook serving arbitrary pools must also decide: do I *allow* unknown pools to attach me? `beforeInitialize` is where you whitelist.)
2. **Only request what you use.** Every enabled callback adds gas to every user's every operation on your pool. A `beforeSwap` you don't need is a tax on all your LPs' customers.
3. **The `sender` parameter is the router.** If your hook needs the *end user's* identity (allowlists, per-user limits), it must arrive via `hookData` with proof (e.g. a signature) or via `msgSender()`-forwarding routers — trusting `tx.origin` or the router address blindly are both known footguns.

## What you can build with observation-only hooks

Before any delta magic, the before/after callbacks alone cover a surprising catalog. Patterns, each mapping to a shelf-mate book or a Chapter 12 case study:

- **Gating / compliance:** `beforeSwap` + `beforeAddLiquidity` that check an allowlist, a KYC token, a sanctions oracle — or *market hours* (revert outside NYSE hours — your Market Hours hook is exactly this pattern plus dynamic fees).
- **Limits and circuit breakers:** revert swaps exceeding size caps, or when price moved too far too fast (your Guard hook lives here: observation + veto).
- **Oracles:** `afterSwap` records price observations — a self-funded v3-style TWAP for pools that opt in (Chapter 9 builds it).
- **Liquidity policy:** `beforeAddLiquidity` enforcing range widths (anti-JIT: block just-in-time liquidity that snipes fees from committed LPs), time-locks via `beforeRemoveLiquidity`, LP loyalty programs via `afterAddLiquidity` bookkeeping.
- **Incentives and distribution:** `afterSwap` streaming rewards; `beforeDonate/afterDonate` structuring external yield injection to in-range LPs (Chapter 6's `donate`).
- **Dynamic fees:** technically its own permission-less pattern — the hook calls `poolManager.updateDynamicLPFee` — important enough to own Chapter 9.

The common thread: these hooks *bend* the pool's behavior without touching its money flow. The pool still prices by v3 math (Chapter 4); flash accounting still settles exactly what the curve says (Chapter 6). The moment a hook wants to *take a cut, subsidize a trade, or replace the curve* — to move money — it needs the four delta flags, a genuinely different power class with genuinely different failure modes.

That's Chapter 8: `BeforeSwapDelta`, custom accounting, and hooks that quietly become exchanges of their own.
