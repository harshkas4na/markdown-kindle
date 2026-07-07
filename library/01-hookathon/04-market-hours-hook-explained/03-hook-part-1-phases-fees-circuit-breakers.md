# 03 — MarketHoursHook.sol, Part 1: Phases, Fees, and Circuit Breakers

Goal: walk the first half of the hook — state, the phase machine, the dynamic fee logic, the value caps, and the price band — until every branch of `_beforeSwap` and `_afterSwap` is obvious. (Part 2 covers the auction.)

## Imports: a checklist of the machinery in play

```solidity
import {BaseHook} from "@openzeppelin/uniswap-hooks/src/base/BaseHook.sol";
import {CurrencySettler} from "@openzeppelin/uniswap-hooks/src/utils/CurrencySettler.sol";
import {IUnlockCallback} from "@uniswap/v4-core/src/interfaces/callback/IUnlockCallback.sol";
import {LPFeeLibrary} from "@uniswap/v4-core/src/libraries/LPFeeLibrary.sol";
import {StateLibrary} from "@uniswap/v4-core/src/libraries/StateLibrary.sol";
import {TickMath} from "@uniswap/v4-core/src/libraries/TickMath.sol";
import {FullMath} from "@uniswap/v4-core/src/libraries/FullMath.sol";
import {FixedPoint96} from "@uniswap/v4-core/src/libraries/FixedPoint96.sol";
import {SafeCast} from "@uniswap/v4-core/src/libraries/SafeCast.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {NYSECalendar} from "./libraries/NYSECalendar.sol";
```

Each import maps to one job: `BaseHook` gives the callback skeleton + only-PoolManager protection; `CurrencySettler` gives `settle`/`take` for the auction's flash accounting; `IUnlockCallback` is the interface the PoolManager calls back during `unlock`; `LPFeeLibrary` holds `DYNAMIC_FEE_FLAG` / `OVERRIDE_FEE_FLAG` / `MAX_LP_FEE`; `StateLibrary` gives `getSlot0`; `TickMath` gives the price limits for the auction's net swap; `FullMath`+`FixedPoint96` do the Q96 price math; `SafeCast` guards narrowing casts; `SafeERC20` handles non-standard ERC20s in the escrow.

```solidity
contract MarketHoursHook is BaseHook, IUnlockCallback {
    using PoolIdLibrary for PoolKey;    // key.toId()
    using StateLibrary for IPoolManager; // poolManager.getSlot0(id)
    using CurrencySettler for Currency;  // currency.settle(...) / take(...)
    using SafeERC20 for IERC20;          // token.safeTransferFrom(...)
```

Note the hook implements **two** interfaces: it's a hook (called by the PoolManager during other people's swaps) *and* an unlock-callback client (it initiates its own swaps at auction settlement). Most hooks are only the former.

## The types: Phase, PoolConfig, Order, Epoch

```solidity
enum Phase { OPEN, CLOSED, AUCTION }
```

The order matters only for the ABI (0/1/2 in the demo UI).

```solidity
struct PoolConfig {
    bool enabled;
    uint128 closedMaxSwapValue;  // max value of a single swap (token1 terms)
    uint128 closedMaxBlockValue; // max summed value per block
}
```

Per-pool because one hook instance serves many pools (a tTSLA pool and a tAAPL pool want different caps). `enabled` doubles as an "was this pool initialized through us" existence check — several functions revert `PoolNotEnabled` if it's false.

```solidity
struct Order {
    address owner;
    bool zeroForOne;   // true: selling token0 into the auction
    uint128 amountIn;
    bool closed;       // claimed after settlement, or cancelled before it
}
```

One flag, `closed`, covers both terminal states — an order is live exactly once, whether it exits via `claim` or via `cancelOrder`.

```solidity
struct Epoch {
    uint128 totalIn0;  // token0 committed by sellers
    uint128 totalIn1;  // token1 committed by buyers
    uint128 totalOut1; // token1 distributed to the sell side at settlement
    uint128 totalOut0; // token0 distributed to the buy side at settlement
    bool settled;
}
```

An epoch is one auction. Its key is not a counter but **the UTC timestamp of the session open it clears at** — self-describing, collision-free, and computable by anyone from the calendar. `totalIn*` accumulate as orders arrive; `totalOut*` are written once at settlement and then only read by `claim` for pro-rata division.

## State variables and their default story

```solidity
uint24 public baseFee = 3000;             // 0.30% while the reference market is open
uint24 public closedFeeStart = 10000;     // 1.00% the moment it closes
uint24 public closedFeeRampPerHour = 300; // +0.03% per closed hour
uint24 public closedFeeMax = 30000;       // 3.00% cap (deep into the weekend)
uint256 public auctionDuration = 10 minutes;
```

All fee units are v4's millionths (3000 = 0.30%). Sanity-check the ramp: Friday 16:00 ET → Monday 09:30 ET is 65.5 hours; 10000 + 65×300 = 29500, just under the 3.00% cap — the ramp is tuned so a *normal* weekend never quite saturates; only holiday-extended closures hit the ceiling (a test proves exactly this with a Monday holiday).

```solidity
uint256 public constant REFERENCE_SNAPSHOT_WINDOW = 10 minutes;
uint16 public closedBandBps = 0; // off by default; owner opts pools in
mapping(uint256 => bool) public isHoliday;                 // key: ET day number
mapping(PoolId => uint160) public referenceSqrtPriceX96;   // last close's price
mapping(PoolId => PoolConfig) public poolConfig;
mapping(PoolId => mapping(uint256 => uint256)) public blockVolume; // per-block used value
mapping(PoolId => mapping(uint256 => Epoch)) public epochs;
mapping(PoolId => mapping(uint256 => Order[])) internal _orders;
bool private _inSettlement;
```

Two things worth pausing on. `blockVolume` is keyed by `block.number` and never cleaned up — old blocks' entries just become dead storage that's never read again; "cleaning" them would cost more gas than it saves. And `_inSettlement` is the re-entrancy *marker* (not a guard): it exists so `_beforeSwap` can distinguish "a user swapping during the auction freeze" (revert) from "our own settlement swaps during the same freeze" (allow). It is only ever true inside the body of `settleAuction`.

## Permissions: the smallest possible footprint

```solidity
beforeSwap: true,   // phase gating + fee override + closed-hours caps
afterSwap: true,    // the price band check (needs the post-swap price)
afterInitialize: true, // pool admission control
// everything else false
```

Every `true` flag costs every swap a callback forever, so each one needs to earn its place: `beforeSwap` is where all gating must happen (before tokens move), `afterSwap` exists *only* because a price band can only be checked after the price moved (and its body short-circuits in one comparison when the band is off), and `afterInitialize` runs once per pool. Note **no** return-delta flags — this hook changes fees and permissions, never balances, which keeps its accounting surface at zero.

## The phase machine — four views, all stateless

```solidity
function isTradingDay(uint256 etDay) public view returns (bool) {
    return !NYSECalendar.isWeekend(etDay) && !isHoliday[etDay];
}

function phaseAt(uint256 ts) public view returns (Phase) {
    uint256 etDay = NYSECalendar.etDayNumber(ts);
    if (!isTradingDay(etDay)) return Phase.CLOSED;
    uint256 openTs = NYSECalendar.sessionOpen(etDay);
    if (ts < openTs || ts >= NYSECalendar.sessionClose(etDay)) return Phase.CLOSED;
    if (ts < openTs + auctionDuration) return Phase.AUCTION;
    return Phase.OPEN;
}
```

Read `phaseAt` as a funnel: weekend/holiday? CLOSED. Outside 09:30–16:00 ET? CLOSED (pre-market and after-hours are "closed" for our purposes — the conservative choice). Inside the first ten minutes? AUCTION. Otherwise OPEN. Note the boundary conventions: the open instant itself (`ts == openTs`) is AUCTION; the close instant (`ts == closeTs`) is already CLOSED (`>=`).

```solidity
function lastSessionClose(uint256 ts) public view returns (uint256) {
    uint256 etDay = NYSECalendar.etDayNumber(ts);
    for (uint256 i = 0; i <= 30; i++) {
        uint256 d = etDay - i;
        if (isTradingDay(d)) {
            uint256 c = NYSECalendar.sessionClose(d);
            if (c <= ts) return c;
        }
    }
    return ts; // >30 straight non-trading days: no ramp rather than revert
}
```

The fee ramp needs "when did the market last close." Walk backwards day by day (today included — if it's 8pm on a trading day, today's own 16:00 close is the answer; the `c <= ts` check is what excludes today's close when we're *before* it). The 30-day bound is a griefing-proof: if an owner marked a month of holidays, the view degrades gracefully (fee ramp restarts) instead of looping forever.

```solidity
function closedFeeAt(uint256 ts) public view returns (uint24) {
    uint256 hoursClosed = (ts - lastSessionClose(ts)) / 1 hours;
    uint256 fee = uint256(closedFeeStart) + hoursClosed * closedFeeRampPerHour;
    if (fee > closedFeeMax) fee = closedFeeMax;
    return uint24(fee);
}
```

Integer hours (a staircase, not a smooth slope — good enough, cheaper). The math is done in `uint256` and clamped before the narrowing cast, so overflow is structurally impossible.

`upcomingEpoch` and `_currentSessionOpen` belong to the auction — covered in Part 2.

## Pool admission: `_afterInitialize`

```solidity
function _afterInitialize(address, PoolKey calldata key, uint160, int24) internal override returns (bytes4) {
    if (!LPFeeLibrary.isDynamicFee(key.fee)) revert MustUseDynamicFee();
    if (Currency.unwrap(key.currency0) == address(0)) revert NativeCurrencyNotSupported();
    poolConfig[key.toId()] = PoolConfig({
        enabled: true,
        closedMaxSwapValue: defaultClosedMaxSwapValue,
        closedMaxBlockValue: defaultClosedMaxBlockValue
    });
    return BaseHook.afterInitialize.selector;
}
```

Three jobs: (1) refuse static-fee pools — without the dynamic flag, every fee we return would be silently ignored, which is worse than failing loudly at creation; (2) refuse native-ETH pools — the auction escrow uses `safeTransferFrom`, which native currency doesn't have, and tokenized stocks are ERC20s anyway (in v4, native currency is always `currency0` with address zero, so one check suffices); (3) enroll the pool with owner-set default caps.

## `_beforeSwap` — the heart of Part 1

```solidity
if (_inSettlement) {
    return (BaseHook.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA,
            baseFee | LPFeeLibrary.OVERRIDE_FEE_FLAG);
}
```

First branch: our own settlement swaps (see Part 2) short-circuit everything and pay the base fee. This must be first — settlement happens moments after the open, when the phase logic below would misroute it.

```solidity
PoolId id = key.toId();
Phase p = phaseAt(block.timestamp);

if (p == Phase.AUCTION) revert ReopeningAuctionInProgress();
```

During the auction window, continuous trading simply does not exist. This is the freeze.

```solidity
if (p == Phase.OPEN) {
    Epoch storage e = epochs[id][_currentSessionOpen(block.timestamp)];
    if (!e.settled && (e.totalIn0 > 0 || e.totalIn1 > 0)) revert AuctionNotSettledYet();
    return (..., baseFee | LPFeeLibrary.OVERRIDE_FEE_FLAG);
}
```

The subtle line of the whole hook. The auction *window* ends after 10 minutes, but what if nobody has called `settleAuction` yet? If we allowed swaps, a bot could trade ahead of the batch — front-running the auction it was supposed to be neutralized by. So: **if this session's epoch holds any unsettled orders, continuous trading stays frozen until someone settles.** The auction IS the open. (And settlement is permissionless, so "nobody settled" is a one-transaction problem that any participant, keeper, or the frozen swapper themselves can fix.) If the epoch is empty — no orders were placed — this check passes vacuously and the open proceeds normally.

```solidity
// CLOSED: the reference market has no price — cap trade size and widen the fee
PoolConfig memory cfg = poolConfig[id];
uint256 value = _swapValueInToken1(id, params);
if (value > cfg.closedMaxSwapValue) revert SwapTooLargeWhileClosed(value, cfg.closedMaxSwapValue);
uint256 volume = blockVolume[id][block.number] + value;
if (volume > cfg.closedMaxBlockValue) revert BlockVolumeCapExceeded(volume, cfg.closedMaxBlockValue);
blockVolume[id][block.number] = volume;

return (..., closedFeeAt(block.timestamp) | LPFeeLibrary.OVERRIDE_FEE_FLAG);
```

The closed-hours path: value the swap, check it against both caps, *record* the consumed volume (so the block cap is cumulative across swaps in the same block — five swaps can't do what one big swap can't), and quote the ramped fee. Order matters: checks before the storage write, so a reverting swap consumes no allowance.

## `_swapValueInToken1` — one line of boolean elegance

```solidity
uint256 amount = params.amountSpecified < 0 ? uint256(-params.amountSpecified) : uint256(params.amountSpecified);
bool specifiedIsToken0 = params.zeroForOne == (params.amountSpecified < 0);
if (!specifiedIsToken0) return amount;
(uint160 sqrtPriceX96,,,) = poolManager.getSlot0(id);
return FullMath.mulDiv(FullMath.mulDiv(amount, sqrtPriceX96, FixedPoint96.Q96), sqrtPriceX96, FixedPoint96.Q96);
```

v4 convention: `amountSpecified < 0` means exact-*input* (you specify what you pay), positive means exact-*output* (you specify what you receive). Which physical token is "the specified one"? Exact-input + zeroForOne → you're paying token0. Exact-output + !zeroForOne → you're receiving token0. Both cases collapse into `zeroForOne == (amountSpecified < 0)` — a truth-table identity worth checking by hand once. If the specified token is already token1, its amount *is* its value; if token0, multiply by price = ×sqrtP÷2⁹⁶, twice, via overflow-proof `mulDiv`.

## `_afterSwap` — the limit-up/limit-down band

```solidity
if (!_inSettlement && closedBandBps != 0 && phaseAt(block.timestamp) == Phase.CLOSED) {
    uint160 ref = referenceSqrtPriceX96[id];
    if (ref != 0) {
        (uint160 current,,,) = poolManager.getSlot0(id);
        uint256 sqrtRatioBps = FullMath.mulDiv(current, 10_000, ref);
        if (sqrtRatioBps == 0 || sqrtRatioBps >= 20_000) revert PriceOutsideClosedBand();
        uint256 priceRatioBps = (sqrtRatioBps * sqrtRatioBps) / 10_000;
        if (priceRatioBps > 10_000 + closedBandBps || priceRatioBps < 10_000 - closedBandBps) {
            revert PriceOutsideClosedBand();
        }
    }
}
return (BaseHook.afterSwap.selector, 0);
```

Why `afterSwap` at all? Because "would this swap push the price out of the band" can't be known in `beforeSwap` without re-implementing the swap math — but it's trivially checkable *after*: read the price, compare, and if it's out of band, **revert the whole transaction** (a hook revert unwinds the swap — nothing has settled yet under flash accounting). The band is *cumulative by construction*: it compares against the fixed close reference, so ten small swaps can't tiptoe past what one big swap can't do.

The math, carefully: `sqrtRatioBps` is the ratio of sqrt-prices ×10000. Price is sqrt² — so square the ratio and rescale: `(sqrtRatioBps)²/10000` is the *price* ratio in bps. The guard `sqrtRatioBps >= 20_000` (sqrt ratio ≥ 2 ⇒ price ratio ≥ 4×) exists to (a) declare an absurd move out-of-band immediately and (b) bound the squaring so it cannot overflow — without it, a pathological `current/ref` ratio could make `sqrtRatioBps²` exceed 2²⁵⁶.

Three exemptions, each deliberate: `_inSettlement` (the reopening auction is exactly where a *new* price is supposed to be discovered — a band that blocked the repricing would defeat the auction); `closedBandBps == 0` (feature off — the default, so the band costs one SLOAD-and-compare when unused); `ref == 0` (no snapshot taken yet — can't compare against nothing).

## `snapshotCloseReference` — a trustless closing price

```solidity
function snapshotCloseReference(PoolKey calldata key) external {
    PoolId id = key.toId();
    if (!poolConfig[id].enabled) revert PoolNotEnabled();
    uint256 ts = block.timestamp;
    if (phaseAt(ts) != Phase.CLOSED || ts - lastSessionClose(ts) > REFERENCE_SNAPSHOT_WINDOW) {
        revert SnapshotWindowClosed();
    }
    (uint160 sqrtPriceX96,,,) = poolManager.getSlot0(id);
    referenceSqrtPriceX96[id] = sqrtPriceX96;
    emit ReferencePriceSnapshotted(id, sqrtPriceX96);
}
```

The band needs a reference: the closing price. Instead of trusting the owner to post it, *anyone* may snapshot the pool's own price — but only during the 10 minutes right after the bell. The time-lock is what makes permissionlessness safe: the recorded price is guaranteed to be an end-of-session price (still fresh from a full day of open-hours arbitrage), not a Saturday-3am price someone nudged first. The honest caveat (in the README too): the pool's close can differ from the official exchange close; a production version feeds this from an oracle.

## Admin functions — the trust surface, enumerated

`setHoliday`/`setHolidays` (the calendar's one human input, batched for yearly loading), `setPoolConfig` (caps, only for enrolled pools), `setFees` (all four fee params, each clamped to `MAX_LP_FEE` so even the owner cannot set a >100% fee), `setClosedBandBps` (must be < 100%), `setAuctionDuration` (≤ 1 hour — an owner can't freeze trading all day by "configuring" a 24-hour auction), `setOwner`. Every mutation is `onlyOwner`, and every bound is there to limit what a *compromised owner key* could do — the parameters can be tuned, but not weaponized.

## The one sentence to keep

**Part 1 is a stateless funnel: `phaseAt(block.timestamp)` classifies every swap, OPEN pays `baseFee`, AUCTION reverts (and OPEN-with-unsettled-orders also reverts, so nobody ever trades ahead of the batch), CLOSED pays a time-ramped fee and must fit under value caps measured in token1 at spot — and after the swap, an optional band check against the permissionlessly-snapshotted closing price reverts anything that left the corridor, with the auction itself exempt because repricing is its job.**
