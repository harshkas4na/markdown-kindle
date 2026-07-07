# 03 — The Tests, Explained: Simulating an Arms Race in Foundry

Goal: understand how you *test* a mechanism whose input is a gas-market signal — and then walk all 14 tests, each with the exact claim it proves.

## The special problem: faking a priority fee

Most hook tests manipulate amounts and times. This one must manipulate the **gas market**. Foundry provides exactly the two cheatcodes needed:

```solidity
function _setPriority(uint256 baseFee, uint256 priorityFee) internal {
    vm.fee(baseFee);                        // sets block.basefee
    vm.txGasPrice(baseFee + priorityFee);   // sets tx.gasprice
}
```

`priorityFeePerGas()` inside the hook then reads exactly `priorityFee`. The fixture opens with `_setPriority`-equivalent zeroing (`vm.fee(0); vm.txGasPrice(0)`) so that *setup operations* (liquidity minting) and any test that doesn't opt in run untaxed — a test suite where the fixture accidentally pays tax is a test suite lying to you.

The rest of the fixture is the standard v4-template pattern (see the market-hours book, chapter 05, for the full anatomy): `deployCodeTo` onto a flags-encoded address — here `AFTER_INITIALIZE | BEFORE_SWAP | BEFORE_SWAP_RETURNS_DELTA` — a plain **static-fee** pool (`fee: 3000`; deliberately, to prove the hook needs no dynamic-fee flag), 100e18 full-range liquidity at 1:1, and constructor config chosen for clean arithmetic: **exemption 0, k = 5000 ppm/gwei, cap 100000 ppm**. With those numbers, gwei-of-priority → percent-of-tax is mental math: 2 gwei → 1%, 20 gwei → 10% (capped).

## The core-promise tests

**`test_noPriorityFee_noTax`** — the control group. Zero tip: output ≈ 0.987 for 1e18 in (that's the pool's own 0.30% fee plus ~1% price impact at this depth — the hook contributed nothing), and both `totalDonated` counters are exactly 0. Every other test's numbers are read against this baseline.

**`test_priorityFee_taxedAndDonated`** — the headline. `_setPriority(1 gwei, 2 gwei)` — note base fee 1 gwei, tip 2 gwei, proving the *subtraction* works, not just raw gasprice. Then three layers of assertion, from quote to cash:
1. `priorityFeePerGas() == 2 gwei` — the signal reads right;
2. `taxPpmFor(poolId, 2 gwei) == 10_000` — the curve quotes 1%;
3. after the swap: `totalDonated0 == 0.01 ether` **exactly** (assertEq — the donation is `amount × ppm / 1e6` to the wei), and the swapper's output ≈ 0.977 — one percent worse than the control. The bot paid; the number matches; the money moved.

**`test_priorityFee_belowExemption_payNothing`** — reconfigures the pool with a 1-gwei exemption via `setTaxConfig`, swaps with a 0.5-gwei tip: zero donated. The "normal users pay literally nothing" guarantee, tested at a value that *would* be taxed under the fixture default — so it's the exemption doing the work, not the zero-tip path.

**`test_taxIsCapped`** — a 1000-gwei tip (raw curve: 500%!) quotes exactly `MAX_TAX_PPM` and donates exactly 0.1 ether on a 1-ether swap. The cap is both an economic bound and — remember `HookDeltaExceedsSwapAmount` — the reason the swap *executes at all*.

**`test_exactOutput_taxedOnOutputCurrency`** — the direction nobody thinks about. `swapTokensForExactTokens` for exactly 1 token1 out, 2-gwei tip. Assertions: the user's token1 balance grows by **exactly 1 ether** (the tax did not shave the requested output — the pool over-produces and the hook takes from the overage, per the `amountToSwap += delta` mechanics), `totalDonated1 == 0.01 ether` (the tax landed in the *output* currency — specified-token logic ✓), and `totalDonated0 == 0`. No swap shape dodges the tax.

## The where-does-the-money-go tests

**`test_donationRaisesFeeGrowth`** — reads `getFeeGrowthGlobals` before/after a taxed swap and asserts growth ≥ `taxAmount × 2¹²⁸ / liquidity` — the donation entered the pool's fee-growth accumulator (the Q128 fixed-point per-liquidity units are the same ones LP fee accounting uses). This is the accounting-level receipt.

**`test_lpCanCollectTheDonation`** — the cash-level receipt: after a taxed swap, the sole LP calls `positionManager.collect(...)` and receives ≥ 0.01 token0 (donation + the swap's own fee). This closes the loop the pitch draws: bot's tip → hook's tax → fee growth → **tokens in the LP's wallet**.

**`test_hookNeverHoldsTokens`** — after a heavily-taxed swap (50 gwei), the hook's balance in both tokens is exactly 0. The flash-accounting cancellation isn't just theory; the contract's token balance sheet stays empty under fire.

## The property tests (fuzzed)

**`testFuzz_taxRate_monotonicAndCapped`** — for any two priorities p1 ≤ p2 (up to 10,000 gwei): `taxPpmFor(p1) ≤ taxPpmFor(p2) ≤ cap`. Bid more, never pay a lower *rate*; and the quote never exceeds the cap anywhere on the curve — including around the exemption kink and the cap knee, which is where an off-by-one would hide.

**`testFuzz_donationMatchesFormula`** — the strongest test in the file: fuzz both the swap size (1e6 wei…10 ether) and the tip (0…100 gwei), swap, and assert `totalDonated0 == amountIn × expectedPpm / 1e6` **exactly**, with `expectedPpm` recomputed independently in the test. Not "some tax was taken" — the *implementation matches the specification* across the whole 2-D input space, 256 samples per run. Rounding, capping, exemption: all pinned.

## The governance tests

**`test_disablingPoolStopsTax`** — `setTaxConfig(id, false, ...)` then a 50-gwei swap donates nothing. The kill switch works.

**`test_onlyOwnerCanConfigure`** — mallory hits `NotOwner` on both `setTaxConfig` and `setDefaults` (exact selectors — these calls go straight to the hook, so no PoolManager error-wrapping).

**`test_capBoundedBelowHundredPercent`** — both setters revert `TaxTooHigh` at exactly 1,000,000 ppm. The brick-proof bound holds at every door.

**`test_newPoolsGetDefaults`** — a second pool (same tokens, different fee tier — a distinct PoolId) initialized against the hook comes out enrolled with the constructor defaults. One hook, many pools, no manual enrollment.

## What's deliberately NOT tested, and why that's honest

There is no test that Flashblocks order by priority — that's a *chain* property, not a contract property; the contract's promise is conditional ("if the tip is an honest bid, the tax is fair") and the tests verify the conditional's consequent. There's also no test of batched-swap double-taxing — it's documented behavior, not a bug; a test would just restate the limitation.

## Patterns worth stealing

1. **Zero out ambient signals in the fixture** (`vm.fee(0)`/`vm.txGasPrice(0)`) so only explicit opt-ins are measured.
2. **Assert quote → mechanism → cash as separate layers** (`taxPpmFor` == X, then donated == Y, then LP collects ≥ Z). When one layer breaks you know *which*.
3. **Fuzz against an independently recomputed formula**, not against "> 0". Exact-match fuzzing is what turns a demo into a specification.
4. **Choose constructor numbers for mental math** (k = 5000 → "gwei × 0.5%"). Reviewers check arithmetic they can do in their head; they skip arithmetic they can't.

## The one sentence to keep

**Two cheatcodes (`vm.fee`, `vm.txGasPrice`) turn Foundry into a gas-market simulator, and on top of them the suite proves the full causal chain — signal read correctly, curve quoted correctly (monotone, exempt, capped, fuzz-matched to the formula), swapper charged in the right currency for both swap shapes, donation landed in fee-growth and collected as real LP tokens, hook balance still zero — plus the governance rails and the one bound that keeps every pool alive.**
