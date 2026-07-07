# 02 — MevTaxHook.sol, Line by Line

Goal: read the whole contract — it's short enough to hold in your head at once — and understand why each of its ~90 logic lines earns its place. This is the smallest of the three projects, and its elegance *is* the pitch: judge-legible in one sitting.

## Imports: notice what's missing

```solidity
import {BaseHook} from "@openzeppelin/uniswap-hooks/src/base/BaseHook.sol";
import {Hooks} from "@uniswap/v4-core/src/libraries/Hooks.sol";
import {IPoolManager, SwapParams} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {PoolId, PoolIdLibrary} from "@uniswap/v4-core/src/types/PoolId.sol";
import {
    BeforeSwapDelta, BeforeSwapDeltaLibrary, toBeforeSwapDelta
} from "@uniswap/v4-core/src/types/BeforeSwapDelta.sol";
import {StateLibrary} from "@uniswap/v4-core/src/libraries/StateLibrary.sol";
import {SafeCast} from "@uniswap/v4-core/src/libraries/SafeCast.sol";
```

No `IERC20`. No `SafeERC20`. No `CurrencySettler`. No `IUnlockCallback`. The absence is the design: this hook moves value exclusively through flash-accounting deltas, so the entire family of token-handling imports — and the entire family of token-handling bugs — doesn't exist here. `toBeforeSwapDelta` is the free-function constructor that packs two `int128`s into the delta type; `StateLibrary` is only here for `getLiquidity`; `SafeCast` guards one narrowing cast.

## The tax configuration type

```solidity
struct TaxConfig {
    bool enabled;
    uint64 exemptPriorityFee;  // wei/gas below which a swap pays no tax at all
    uint32 taxPpmPerGwei;      // ppm of the specified amount, per gwei above exemption
    uint32 maxTaxPpm;          // hard cap in ppm (must stay < 1_000_000 = 100%)
}
```

Four fields, one storage slot (1+8+4+4 = 17 bytes packs into 32). Per-pool, because a stable-stable pool and a volatile pool face wildly different arb landscapes and want different `k`. The units are chosen for human tuning: "0.5% per gwei above 0.001 gwei, capped at 10%" reads directly off `(5000, 1e6 wei, 100000)`.

```solidity
address public owner;
uint64 public defaultExemptPriorityFee;
uint32 public defaultTaxPpmPerGwei;
uint32 public defaultMaxTaxPpm;
mapping(PoolId => TaxConfig) public taxConfig;

mapping(PoolId => uint256) public totalDonated0;
mapping(PoolId => uint256) public totalDonated1;
```

The `totalDonated*` counters do no accounting work — claims never read them. They exist purely as **legible receipts**: the demo's headline number, a subgraph-free dashboard, the thing an LP checks to believe the pitch. Cheap (one SSTORE per taxed swap) and worth it.

```solidity
event MevTaxCharged(
    PoolId indexed poolId, address indexed sender, uint256 priorityFee, uint256 taxAmount, bool currencyIs0
);
```

The event carries the whole story of each taxed swap — who, what bid, what tax, which token — which is exactly what the demo's live feed renders.

## Constructor: bounds enforced from birth

```solidity
constructor(
    IPoolManager _poolManager,
    address _owner,
    uint64 _defaultExemptPriorityFee,
    uint32 _defaultTaxPpmPerGwei,
    uint32 _defaultMaxTaxPpm
) BaseHook(_poolManager) {
    if (_defaultMaxTaxPpm >= 1_000_000) revert TaxTooHigh();
    ...
}
```

`maxTaxPpm < 1e6` is a *safety invariant*, not a preference: at 100%+ the return delta could equal or exceed the swap amount, and the core would revert every swap with `HookDeltaExceedsSwapAmount` — a config that bricks the pool. So it's rejected at the constructor and re-checked in both setters. Nobody, including the owner, can configure a broken pool.

## Permissions: three flags, each load-bearing

```solidity
beforeSwap: true,              // read the tip, compute, donate
beforeSwapReturnDelta: true,   // charge the swapper
afterInitialize: true,         // enroll pools with defaults
// all eleven others: false
```

`beforeSwapReturnDelta` is the interesting one — without it the PoolManager ignores the delta we return, silently. (It's a *separate* flag from `beforeSwap` precisely so the core can skip delta-parsing for the vast majority of hooks that never return one.) Note also what's *not* requested: no `afterSwap`. The tax is computed from the specified amount, known before the swap runs — so the entire mechanism fits into the before-phase, and untaxed swaps pay almost no gas overhead.

## The two views: signal and curve

```solidity
function priorityFeePerGas() public view returns (uint256) {
    return tx.gasprice > block.basefee ? tx.gasprice - block.basefee : 0;
}
```

The confession-reader (concept 1). Public so UIs can display "your current tip as the hook sees it."

```solidity
function taxPpmFor(PoolId id, uint256 priorityFee) public view returns (uint256) {
    TaxConfig memory cfg = taxConfig[id];
    if (!cfg.enabled || priorityFee <= cfg.exemptPriorityFee) return 0;
    uint256 ppm = ((priorityFee - cfg.exemptPriorityFee) * cfg.taxPpmPerGwei) / 1 gwei;
    return ppm > cfg.maxTaxPpm ? cfg.maxTaxPpm : ppm;
}
```

The whole economic policy in five lines. Walk the units: `priorityFee` is wei/gas; subtract the exemption; multiply by "ppm per gwei"; divide by `1 gwei` (10⁹) to land back in ppm. A 2-gwei tip with `k = 5000`: `(2e9 × 5000)/1e9 = 10000 ppm = 1%`. Overflow check: priority fees are ≤ ~10⁴ gwei = 10¹³ wei; times a uint32 k ≤ 4×10⁹ → ~10²² — nowhere near 2²⁵⁶, so plain arithmetic is fine. The `<=` on the exemption means "at the threshold" is still free — the exemption is a guarantee, so its boundary belongs to the user. Taking `priorityFee` as a *parameter* (rather than reading the live one) makes the curve unit-testable and lets the demo preview "what would a 7-gwei swap pay" without sending one.

## `_afterInitialize`: enrollment, not gatekeeping

```solidity
function _afterInitialize(address, PoolKey calldata key, uint160, int24) internal override returns (bytes4) {
    taxConfig[key.toId()] = TaxConfig({
        enabled: true,
        exemptPriorityFee: defaultExemptPriorityFee,
        taxPpmPerGwei: defaultTaxPpmPerGwei,
        maxTaxPpm: defaultMaxTaxPpm
    });
    return BaseHook.afterInitialize.selector;
}
```

Contrast with the market-hours hook, which *rejects* pools here (dynamic-fee-only, no native). This hook rejects nothing: static fee, dynamic fee, native ETH — all fine, because the mechanism composes on top of any pool. Enrollment just copies the deployment defaults; the owner tunes per-pool later.

## `_beforeSwap` — the entire mechanism, one screen

```solidity
function _beforeSwap(address sender, PoolKey calldata key, SwapParams calldata params, bytes calldata)
    internal override returns (bytes4, BeforeSwapDelta, uint24)
{
    PoolId id = key.toId();

    uint256 priorityFee = priorityFeePerGas();
    uint256 ppm = taxPpmFor(id, priorityFee);
    if (ppm == 0) {
        return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
```

**Exit ramp #1 — the common case.** Zero tip, tip under exemption, or pool disabled: return the do-nothing triple. `ZERO_DELTA` charges nothing; fee `0` without the override flag means "no fee opinion" (works identically for static- and dynamic-fee pools). A normal user's swap runs two SLOADs heavier than on an unhooked pool, nothing more.

```solidity
    if (poolManager.getLiquidity(id) == 0) {
        return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
```

**Exit ramp #2 — no LPs.** `donate` to an empty pool reverts (`NoLiquidityToReceiveFees`), and taxing with no one to compensate is senseless anyway. Skip, don't revert — the swap itself (which would just move price through empty range) remains the core's business, not ours.

```solidity
    uint256 amount = params.amountSpecified < 0 ? uint256(-params.amountSpecified) : uint256(params.amountSpecified);
    uint256 taxAmount = (amount * ppm) / 1_000_000;
    if (taxAmount == 0) {
        return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
```

The tax base is `|amountSpecified|` — whatever the swapper *specified*, input or output. Exit ramp #3 handles dust: a 50-wei swap at 1% floors to zero tax; returning a zero delta is cleaner (and cheaper) than donating zero.

```solidity
    // the tax is taken in the swap's *specified* currency: the input token for
    // exact-input swaps, the output token for exact-output swaps
    bool specifiedIs0 = params.zeroForOne == (params.amountSpecified < 0);
```

The same truth-table identity as in the market-hours hook, worth re-deriving once: exact-input (`amountSpecified < 0` is true) specifies the *input* token — token0 iff `zeroForOne`. Exact-output specifies the *output* — token0 iff `!zeroForOne`. Both collapse to `zeroForOne == (amountSpecified < 0)`. This bit decides which side of the donate and which delta slot the tax lives in.

```solidity
    if (specifiedIs0) {
        poolManager.donate(key, taxAmount, 0, "");
        totalDonated0[id] += taxAmount;
    } else {
        poolManager.donate(key, 0, taxAmount, "");
        totalDonated1[id] += taxAmount;
    }

    emit MevTaxCharged(id, sender, priorityFee, taxAmount, specifiedIs0);

    return (BaseHook.beforeSwap.selector, toBeforeSwapDelta(SafeCast.toInt128(int256(taxAmount)), 0), 0);
}
```

The finale, and the trick that makes the contract token-free (concept 5): the `donate` **debits** the hook `taxAmount`; the returned delta (`+taxAmount` in the specified slot, `0` in the unspecified) **credits** the hook `taxAmount` — same currency, same lock. Net zero, checked by the PoolManager at unlock-end. The swapper pays; in-range LPs receive; the hook's ledger passes through zero.

Two footnotes on the last line. `SafeCast.toInt128` matters because the delta field is an `int128` — a hypothetical >2¹²⁷ tax must revert, not truncate into a *negative* delta (which would mean the hook *paying the swapper*). And could `donate` re-enter us? It invokes the pool's beforeDonate/afterDonate hooks — which are us — but our permission flags declare both `false`, so the core never makes the call. The permission bitmap is doing double duty as re-entrancy hygiene.

## Admin: three setters, one shared bound

```solidity
function setTaxConfig(PoolId id, bool enabled, uint64 exemptPriorityFee, uint32 taxPpmPerGwei, uint32 maxTaxPpm)
    external onlyOwner
{
    if (maxTaxPpm >= 1_000_000) revert TaxTooHigh();
    taxConfig[id] = TaxConfig(enabled, exemptPriorityFee, taxPpmPerGwei, maxTaxPpm);
    emit TaxConfigSet(id, enabled, exemptPriorityFee, taxPpmPerGwei, maxTaxPpm);
}

function setDefaults(uint64, uint32, uint32) external onlyOwner { ... same bound ... }
function setOwner(address _owner) external onlyOwner { ... }
```

Per-pool tuning (`setTaxConfig`), future-pool defaults (`setDefaults` — existing pools keep their config; the snapshot happens at `afterInitialize`), and ownership transfer for handing the keys to a multisig or LP governance. The `TaxTooHigh` bound appears in all three places money-parameters enter — constructor and both setters — so the brick-the-pool config is unreachable from every direction.

## What the contract deliberately does NOT do (design honesty)

- **No top-of-block detection.** A refinement would tax only each pool's *first* swap of the block (arbs are top-of-block by definition under priority ordering), sparing later swaps entirely. Left out to keep v1 auditable at a glance; noted in the README roadmap.
- **No per-transaction memoization.** A router batching two swaps in one taxed transaction pays the rate twice. Mostly correct (an atomic two-leg arb *should* pay on both legs), occasionally unfair (an innocent swap bundled with an urgent one); the cap bounds the damage.
- **No volatility-adaptive `k`.** Paradigm's analysis suggests the optimal rate depends on pool depth and volatility; v1 keeps `k` a per-pool constant and makes it hot-tunable instead.

## The one sentence to keep

**The contract is three exit ramps and a pincer: bail out at zero rate, zero liquidity, or zero tax; otherwise decide the specified token with `zeroForOne == (amountSpecified < 0)`, `donate` the tax to in-range LPs and simultaneously charge the swapper via a positive `toBeforeSwapDelta` — debit and credit cancelling inside the lock so the hook holds nothing — with the one true safety invariant (`maxTaxPpm < 100%`) enforced at the constructor and every setter because a fee at or above the swap amount would revert every swap in the pool.**
