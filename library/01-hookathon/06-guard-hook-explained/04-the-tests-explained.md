# 04 — The Tests, Explained: Attacking Your Own Fortress

Goal: how you test a security wrapper (spoiler: you play both sides), the fixture tricks specific to a many-pools contract, and all 21 tests with the exact promise each proves.

## The fixture: one guard, many disposable pools

```solidity
function setUp() public {
    deployArtifactsAndLabel();
    (currency0, currency1) = deployCurrencyPair();

    address flags = address(uint160(Hooks.ALL_HOOK_MASK) ^ (0x4444 << 144));
    deployCodeTo("GuardHook.sol:GuardHook", abi.encode(poolManager), flags);
    guard = GuardHook(flags);
}
```

The address carries **all fourteen flags** (`ALL_HOOK_MASK = 0x3FFF`) — in tests via `deployCodeTo`, on real chains via ~16k iterations of CREATE2 mining. Note what setUp *doesn't* do: create a pool. Because the guard serves many pools with different configs, each test builds its own through the factory helper:

```solidity
int24 nextTickSpacing = 10;

function _newGuardedPool(
    address inner, uint160 innerFlags, bool failOpen,
    uint24 maxFee, uint16 maxMoveBps, uint32 cooldown,
    uint128 softCap, uint128 hardCap
) internal returns (PoolKey memory key, uint256 tokenId) {
    key = PoolKey(currency0, currency1, LPFeeLibrary.DYNAMIC_FEE_FLAG, nextTickSpacing, IHooks(address(guard)));
    nextTickSpacing += 10;
    guard.configurePool(key, inner, innerFlags, failOpen, maxFee, maxMoveBps, cooldown, softCap, hardCap);
    poolManager.initialize(key, Constants.SQRT_PRICE_1_1);
    // ... mint 100e18 full-range liquidity ...
}
```

The `nextTickSpacing += 10` trick deserves a note: a v4 pool's identity is the hash of its whole key (tokens, fee, tickSpacing, hook), so bumping tickSpacing per call mints an endless supply of *distinct* pools over the same two tokens and the same guard — one isolated pool per test, no cross-contamination, no token-deployment overhead. All pools use `DYNAMIC_FEE_FLAG` so fee-override scenarios work; the test contract is `msg.sender` for `configurePool` and therefore every pool's guardian.

Two testing quirks carried over from the sibling books, plus one new one:

- Hook-path reverts arrive wrapped by the PoolManager → bare `vm.expectRevert()` with a comment naming the real error; direct guard calls (`pause`, `configurePool`) match exact selectors.
- `vm.roll(block.number + 1)` — new block — is this suite's time machine (the breaker state is per-block), alongside `vm.warp` for cooldowns.
- **The `expectRevert`-through-a-library trap:** `positionManager.increaseLiquidity` here is an *internal library call* (EasyPosm) whose first external call is a harmless view — which would eat the `expectRevert`. Fix: an external self-call wrapper (`this.increaseLiquidityExternal(tokenId)`) so the cheatcode targets one whole external frame. (This exact test failed for exactly this reason before the wrapper existed — a bug in the test, not the guard, and a pattern worth stealing.)

## Forwarding & registration (the plumbing works)

- **`test_forwardsCallbacksToInnerHook`** — with a `CountingInnerHook` wrapped: the setup's liquidity mint already bumped `beforeAddCount` to 1; a swap bumps both swap counters; `lastSender == address(swapRouter)` — the *original* sender crossed both hops; a `decreaseLiquidity` bumps the remove counter. Four callbacks in, four counters right.
- **`test_innerHookOnlyCallableByGuard`** — calling the inner hook's `beforeSwap` directly reverts `NotGuard`. The wrapped hook's own door is locked.
- **`test_innerHookNeedsNoFlagMining`** — asserts the *guard's* address carries all 14 flags while the inner hooks are plain `new` deployments. The "no mining for wrapped hooks" selling point, stated as an assertion.
- **`test_unconfiguredPoolCannotInitialize`** — initializing a guard-keyed pool without `configurePool` reverts (`NotConfigured` inside `beforeInitialize`). No pool can exist in an unguarded limbo.
- **`test_cannotConfigureTwice`** — second `configurePool` on the same key → `AlreadyConfigured`. Nobody hijacks a live pool's guardianship.
- **`test_configRejectsForeignHookAddress`** — configuring a key whose `hooks` field points elsewhere → `WrongHookAddress`. You can't register a pool the guard will never see.

## Pause & rule 6 (the heart)

- **`test_pauseBlocksTradingButNeverExits`** — the single most important test in the suite, a five-act play: guardian pauses → `isPaused` true → swap reverts → deposit (`increaseLiquidity`, via the external wrapper) reverts → **`decreaseLiquidity` succeeds while paused** → unpause → trading resumes. The exit door stayed open through the whole lockdown.
- **`test_onlyGuardianCanPause`** — mallory gets `NotGuardian`. Per-pool ACL holds.

## The firewalls

- **`test_feeFirewall_compliantFeePassesThrough`** — a 1% `FeeSettingInnerHook` under a 2% cap: swap output ≈ `in × 0.99`. Proves the *positive* path — the guard isn't a fee censor; a lawful override reaches the pool intact (this is also the only place the pass-through of `OVERRIDE_FEE_FLAG` is exercised end-to-end).
- **`test_feeFirewall_blocksGreedyFee`** — the same hook flipped to 50% via `setFee`: swap reverts (`FeeCapExceeded`). Then flipped to **exactly 20000** — exactly the cap — and the swap passes: the boundary belongs to the compliant side (`>` not `>=`). Rogue behavior *acquired after wrapping* is caught, which is the whole point — audits are snapshots, firewalls are continuous.
- **`test_deltaFirewall_blocksTokenTheft`** — the `DeltaStealingInnerHook` tries to skim 10% via a return delta: swap reverts (`InnerDeltaForbidden`). Theft-by-return-value is dead on arrival.

## The failure dial

- **`test_failOpen_brokenInnerHookIsSkipped`** — `RevertingInnerHook`, `failOpen = true`: the swap succeeds with real output. A dead dependency doesn't kill a fail-open pool.
- **`test_failClosed_brokenInnerHookRevertsSwaps`** — same hook, flipped to fail-closed via `setFailOpen`: swaps revert (`InnerHookFailed`)... **and `decreaseLiquidity` still succeeds** — rule 6 tested against its hardest adversary, a hook that reverts *on the exit callback itself*, on a fail-closed pool. (Small fixture note: the pool is created fail-open then flipped, because with a fail-closed reverting hook you couldn't even seed the liquidity.)

## The circuit breaker

- **`test_outflowHardCap_revertsBigDrain`** — cap 1 ether, no inner hook: a 0.5-out swap passes; a second 0.6-out swap in the same block reverts (**cumulative** — 1.1 > 1.0 even though each swap alone fits); `vm.roll(+1)` and 0.6 passes. Per-block allowance, proven at the boundary.
- **`test_outflowSoftCap_tripsAutomaticCooldown`** — soft 0.5 / hard 10 / cooldown 1h: a 0.7-out swap **succeeds** (that's the breaker's defining subtlety — the crossing trade stands) and `isPaused` flips true; next block's swap reverts (`PoolIsPaused`); `vm.warp(+1h+1)` and `isPaused` reads false, trading resumes — *no human touched anything*. The full automatic cycle: trip, halt, self-heal.
- **`test_guardianCanLiftCooldownEarly`** — same trip, then `unpause` clears `pausedUntil` before the timer. The manual override of the automatic system.

## The band, the bare mode, the admin

- **`test_priceMoveCap`** — ±1% band, no inner hook: a 0.2-ether swap (≈0.4% move at this depth) passes; a 1-ether swap that would take the *cumulative* block move past 1% reverts (`PriceMoveExceeded` — against the block-start baseline, so the earlier swap's movement counts); next block, fresh baseline, small swap passes again.
- **`test_pureCircuitBreaker_noInnerHook`** — `innerHook = address(0)` with an outflow cap: swaps work, protection active. The guard as standalone insurance for vanilla pools is a first-class mode, not an accident.
- **`test_setLimits_andGuardianTransfer`** — `setLimits` updates read back correctly; soft > hard reverts `BadCaps`; after `transferGuardian`, the old guardian's `pause` reverts and the new one's succeeds. The dials turn, the bounds hold, the keys hand over.

## The fuzzed invariants — where the security claim becomes a law

- **`testFuzz_outflowNeverExceedsHardCap(uint256[5])`** — five swaps of fuzzed sizes (0.01–2 ether against a 1-ether cap), each wrapped in `try/catch` so reverts don't end the test, and after *every* attempt: `blockOutflow1 ≤ hardCap`. Read what that quantifies over: any prefix of any size-sequence, mixed accepts and rejects — the meter can never read past the cap, because the check precedes the write. This is the "no matter what breaks, tokens can't leave faster than X" pitch, machine-checked 256 sequences per run.
- **`testFuzz_priceNeverMovesPastBandWithinBlock(uint256[4])`** — same shape for the band: four fuzzed swaps under a 1.5% band; every *accepted* swap satisfied the band check (or it wouldn't have been accepted), and a final probe confirms the pool is still functional. The property is enforced by construction — the fuzz hunts for an ordering of sizes that sneaks cumulative movement past the check, and finds none.

## Patterns worth stealing

1. **A pool factory with a uniqueness counter** (`nextTickSpacing += 10`) — cheap isolated worlds for a shared-infrastructure contract.
2. **Test the positive path of every firewall** (compliant fee passes) — a guard that blocks everything trivially "passes" all attack tests; only pass-through tests prove it's a filter, not a wall.
3. **Test boundaries as members of the allowed side** (fee exactly at cap passes; outflow exactly at cap passes).
4. **`try/catch` fuzzing for invariants** — when the property is "holds whether transactions succeed or revert," catch the reverts and assert the invariant after every attempt.
5. **External self-call wrappers** for `expectRevert` through library helpers.

## The one sentence to keep

**The suite plays both sides — honest hooks prove forwarding and pass-through, evil mocks prove each firewall catches its designated attack, a bricked hook proves the failure dial and that exits survive even a fail-closed pool whose inner hook reverts on the exit path — and the two fuzz tests elevate the outflow cap and price band from tested examples to quantified laws over arbitrary swap sequences.**
