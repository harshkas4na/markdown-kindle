# 05 — The Tests, Explained: What 37 Green Checkmarks Actually Prove

Goal: understand the test architecture (fixtures, time control, revert-matching quirks) and then walk every test in `MarketHoursHook.t.sol` and `NYSECalendar.t.sol`, stating precisely which claim about the system each one proves. A test suite is a list of promises; this chapter is the list, annotated.

## The fixture: how a hook test world gets built

```solidity
function setUp() public {
    // start every test during regular Monday trading hours (11:30 ET)
    vm.warp(MONDAY_OPEN + 2 hours);

    deployArtifactsAndLabel();                      // PoolManager, PositionManager, router, Permit2
    (currency0, currency1) = deployCurrencyPair();  // two fresh mock ERC20s, sorted

    address flags = address(
        uint160(Hooks.AFTER_INITIALIZE_FLAG | Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG) ^ (0x4444 << 144)
    );
    deployCodeTo("MarketHoursHook.sol:MarketHoursHook", constructorArgs, flags);
    hook = MarketHoursHook(flags);

    poolKey = PoolKey(currency0, currency1, LPFeeLibrary.DYNAMIC_FEE_FLAG, 60, IHooks(hook));
    poolManager.initialize(poolKey, Constants.SQRT_PRICE_1_1);
    // ... mint full-range liquidity of 100e18, fund alice/bob/carol
}
```

Four things to internalize:

1. **`deployCodeTo` is the testing cheat for address mining.** Real deployments must CREATE2-mine an address whose low bits match the hook's permission flags (lesson 16). Tests skip the mining: compute a valid address by OR-ing the flags (the `0x4444 << 144` namespace just avoids collisions between test suites), then *etch* the compiled bytecode there. Consequence worth remembering: `deployCodeTo` also bypasses the 24KB contract-size limit — which is exactly why the size bug only surfaced at real deployment (see the deployment chapter).
2. **Time is fully ours.** `vm.warp(t)` sets `block.timestamp`. Every test starts at a hardcoded real instant — Monday 2026-07-06, 11:30 ET — chosen so the phase is OPEN and no auction/window logic interferes with setup. The constants at the top (`MONDAY_OPEN = 1783296000 + 13h30m`, `SATURDAY_NOON`, `FRIDAY_CLOSE`) were hand-derived from the epoch and double-checked against the weekday formula; the calendar tests re-verify them independently.
3. **The pool must carry `DYNAMIC_FEE_FLAG`** or the hook's `_afterInitialize` rejects it — the fixture is itself a test of the happy path.
4. **100e18 of full-range liquidity at price 1:1** makes mental math possible everywhere: a swap of size `x` has price impact ≈ `2x/100e18` ≈ 2% per 1e18, and fees are read directly off outputs.

**The revert-matching quirk:** when a *hook* reverts, v4's PoolManager wraps the error (`WrappedError`) before it reaches the test, so `vm.expectRevert(SpecificError.selector)` fails to match. Convention in this suite: hook-path reverts use bare `vm.expectRevert()` with a comment naming the real error; directly-called hook functions (like `settleAuction`) match exact selectors.

## The calendar suite (7 tests) — pinning the math to the real world

| Test | The promise it proves |
|---|---|
| `test_civilRoundTrip` | day 20640 ↔ (2026, 7, 6) both directions — the Hinnant algorithms agree with reality on a known date |
| `test_weekday` | day 0 = Thursday; 2026-07-06 = Monday — the `+4 % 7` shift is right |
| `test_dstOffsets` | July timestamp → 4h offset, January → 5h — the coarse seasons work |
| `test_dstBoundaries2026` | **the minutes on both sides of both switches**: 06:59 vs 07:01 UTC on March 8 (start), 05:59 vs 06:01 UTC on Nov 1 (end) — the exact-hour constants encode the law correctly |
| `test_sessionTimes` | Monday's open is exactly 13:30 UTC and close 20:00 UTC in July (EDT) |
| `test_weekend` | Sat/Sun true, Fri/Mon false around the reference week |
| `testFuzz_civilRoundTrip` | for **any** day in [0, 200000] (~year 2517): `daysFromCivil(civilFromDays(d)) == d`, months in 1–12, days in 1–31 — the algorithms are inverses everywhere, not just on cherry-picked dates |

The fuzz round-trip deserves emphasis: it turns "trust these fifteen lines of black magic" into "the property holds on 256 random days per run, forever."

## The hook suite (30 tests), grouped by the promise

### Phase machine

- **`test_phases`** — one test, five assertions: 11:30 ET Monday = OPEN, 09:35 = AUCTION, 08:30 = CLOSED (pre-market), 16:00:00 sharp = CLOSED (close boundary is exclusive), Saturday = CLOSED. This is the truth table of `phaseAt`.
- **`test_holidayClosesMarket`** — Tuesday 11am ET reads OPEN; owner marks Tuesday's ET-day a holiday; same instant now reads CLOSED. Proves the holiday mapping participates in the phase funnel.
- **`test_dstTransition_sessionShiftsWithTheClocks`** — the showpiece: Friday 2026-03-06 (EST) has its auction window at 14:30–14:40 **UTC**, while Monday 2026-03-09 (first trading day after the spring switch) has it at 13:30–13:40 UTC. Same New York wall clock, one hour of UTC difference, zero configuration. If either `isDST` hour-constant were wrong, this test is where it dies.

### Fees

- **`test_openHours_baseFee`** — a 0.01e18 swap during OPEN returns ≈ 0.00997 (0.30% fee + negligible impact), asserted with `assertApproxEqRel` at 0.2% tolerance.
- **`test_closedHours_widerFee`** — first asserts the *quote*: `closedFeeAt(SATURDAY_NOON) == 14800` — exactly 1.00% + 16 dark hours × 0.03%. Then proves the quote is *charged*: the same swap now returns ≈ 0.009852.
- **`test_closedFee_rampsAndCaps`** — Sunday night (55h) = 26500; then a Monday *holiday* is set and Tuesday pre-market (89 dark hours, raw 36700) reads exactly 30000 — the cap engages only in holiday-stretched closures, as designed. (Fun fact from building it: the first version of this test naively did `closedFeeAt(FRIDAY_CLOSE + 200 hours)` and failed — because 200 hours later there were *trading days in between*, so `lastSessionClose` had reset the ramp. The fix — forcing a genuinely long closure with a holiday — is itself documentation of how `lastSessionClose` really behaves.)
- **`testFuzz_closedFee_monotonicOverTheWeekend`** — for any two instants t1 ≤ t2 inside the Friday-close→Monday-open window: fee(t1) ≤ fee(t2) ≤ max, and ≥ start. The ramp never dips — a property, not an example.

### Closed-hours circuit breakers

- **`test_closedHours_swapSizeCapReverts`** — a swap one wei over `closedMaxSwapValue` (1 ether in the fixture) reverts on Saturday.
- **`test_closedHours_blockVolumeCapReverts`** — three 1-ether swaps fill the 3-ether block cap exactly; the fourth reverts; `vm.roll(+1)` (new block) and it clears. Proves the cap is *cumulative within a block* and resets by block, not by time.
- **`test_openHours_noCaps`** — the same 2-ether swap that dies on Saturday sails through on Monday. Caps are a closed-hours phenomenon only.
- **`test_closedHours_exactOutputAlsoCapped`** — exact-*output* swaps (via `swapTokensForExactTokens`) face the same value cap: 1.5-out reverts, 0.5-out passes. Proves `_swapValueInToken1`'s specified-token logic covers both swap kinds — no direction dodges the breaker.

### The price band

- **`test_priceBand_limitUpLimitDown`** — the full story in one test: owner enables a ±1% band; a random keeper address snapshots the close reference in the 5th minute after Friday's bell (permissionless ✓); Saturday: a 0.05-ether swap (≈0.1% move) passes, then a 0.95-ether swap that would push the *cumulative* move ≈2% reverts; finally the same big swap succeeds Monday — the band binds only while CLOSED.
- **`test_snapshot_onlyRightAfterTheBell`** — snapshotting at Saturday noon (16h late) reverts; snapshotting while OPEN reverts. The 10-minute time-lock is what makes the permissionless snapshot manipulation-resistant, so it gets its own test.

### The auction — the largest group, one test per lifecycle stage

- **`test_auction_ordersTargetMondayOpen`** — weekend orders land in the epoch keyed exactly `MONDAY_OPEN`; totals record 1 ether in0 / 0.5 ether in1; `orderCount` is 2.
- **`test_auction_swapsFrozenDuringWindow`** — 09:31 Monday: continuous swap reverts (`ReopeningAuctionInProgress`).
- **`test_auction_swapsBlockedUntilSettled`** — 09:41, window over but nobody settled: swap still reverts (`AuctionNotSettledYet`). *The auction is the open* — this test is that sentence.
- **`test_auction_settleTooEarlyReverts`** — settling at 09:35 hits `AuctionWindowNotOver` (exact selector — this call goes straight to the hook, no PoolManager wrapping).
- **`test_auction_fullLifecycle`** — the end-to-end: place both sides over the weekend, settle at 09:41, assert `settled` + nonzero outputs, alice (sold 1 token0) claims ≈0.99 token1, bob (sold 0.5 token1) claims ≈0.5 token0 *with balances checked against actual ERC20 transfers*, double-claim reverts `OrderClosed`, and a continuous swap finally succeeds. One test, seven promises.
- **`test_auction_settleIsPermissionless_afterWindow`** — a fresh `keeper` address (no orders, no roles) settles successfully.
- **`test_auction_balancedOrdersCrossWithoutPool`** — 1 token0 vs 1 token1 at a 1:1 pool: both sides claim **exactly** 1.0 (assertEq, not approx). The pure-cross branch pays no fee and touches no pool — the efficiency claim, proven to the wei.
- **`test_auction_singleSided`** — an auction with only sellers degrades gracefully into one batch pool-swap at the base fee (≈0.99 out).
- **`testFuzz_auction_conservationAndSolvency`** — the crown: three participants with fuzzed sizes (two sellers 0–4 ether each, one buyer 0–8 ether — the bound crosses all three regimes of the settlement branch), settle, everyone claims, then assert **the hook's remaining balance in both tokens is ≤ 3 wei**. Escrow in, escrow out, dust bounded by one wei per floor-rounded claim. This is the conservation identity from chapter 04, machine-checked 256 random ways per run.
- **`test_auction_multiEpoch`** — Saturday's auction settles Monday; Monday-night orders target **Tuesday's** open (`epoch2 == MONDAY_OPEN + 1 days` — same 13:30 UTC because July stays EDT); both epochs claim independently. Epoch isolation.
- **`test_auction_cancelBeforeOpenRefunds`** — cancel on Saturday returns the exact escrow and zeroes the epoch total.
- **`test_auction_cannotCancelDuringSession`** — cancelling at 09:35 Monday reverts `CancelWindowClosed` — committed means committed.
- **`test_auction_escapeHatch_cancelAfterUnsettledSession`** — nobody settles all Monday; after the close, alice cancels and recovers her full 10-ether balance. The no-stranded-funds guarantee.
- **`test_auction_cannotPlaceWhileOpen`** — placing an order at 13:30 ET reverts `MarketIsOpen` — just swap.

### Admission & admin

- **`test_staticFeePoolRejected`** — initializing a static-fee (3000) pool against the hook reverts. Misconfiguration is impossible, not just discouraged.
- **`test_onlyOwnerCanAdministrate`** — alice calling `setHoliday` hits `NotOwner`.
- **`test_setHolidaysBatch`** — the batch setter marks two days and the phase machine immediately reflects it.

## Patterns worth stealing for your own hook tests

1. **Anchor time to real dates** and verify them twice (hand math + calendar tests). Symbolic "day 1, day 2" tests can't catch DST bugs.
2. **Test the quote and the charge separately** (`closedFeeAt` returns 14800; the swap output reflects 14800). A fee can be computed right and applied never (the forgotten `OVERRIDE_FEE_FLAG` bug) — only the pair of assertions catches it.
3. **Fuzz the invariants, example-test the flows.** Lifecycles are stories (example tests); solvency and monotonicity are laws (fuzz).
4. **Let the failed test teach.** The ramp-cap test failing on "200 hours later" exposed a real subtlety of `lastSessionClose` that's now documented behavior.

## The one sentence to keep

**The suite proves four kinds of promise — the calendar matches the real 2026 (down to the DST switch minutes), each phase charges exactly the fee it quotes, every breaker (size, block volume, band) binds when CLOSED and vanishes when OPEN, and the auction's whole lifecycle works with a fuzz-checked conservation law showing the escrow always drains to dust — with `deployCodeTo` faking the mined address and bare `expectRevert` absorbing the PoolManager's error-wrapping.**
