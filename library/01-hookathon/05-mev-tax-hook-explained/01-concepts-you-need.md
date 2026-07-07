# 01 — The Concepts You Need Before Reading the Code

Goal: five ideas, each explained from zero, that together make the ~90 lines of `MevTaxHook` fully legible.

## 1. The priority fee, and why it's readable on-chain

Every EIP-1559 transaction pays gas in two parts: the **base fee** (set by the protocol, burned) and the **priority fee** (the tip, chosen by the sender, paid to the block producer). Inside the EVM both ends are visible:

```solidity
uint256 priorityFee = tx.gasprice - block.basefee;
```

`tx.gasprice` is what this transaction actually pays per gas; `block.basefee` is the protocol part; the difference is the tip. One guard needed: theory says `gasprice ≥ basefee` always, but defensive code doesn't trust theory (`tx.gasprice > block.basefee ? ... : 0`).

Normal users tip ~nothing (wallets add cents of priority just to not be last). Arb bots racing for top-of-block tip enormously — because position *is* the product they're buying.

## 2. Why the tax needs *provable* ordering — the honest-signal argument

The tax works only if the priority fee is the *real* auction for position. Two failure modes on ordinary chains:

- **Side-channel bribes.** If a builder accepts payment through a private channel (a direct transfer, an off-chain deal), the winning bot shows a zero priority fee on-chain and the tax reads "innocent user."
- **Non-priority ordering.** If blocks aren't ordered by tip at all, a high tip doesn't buy position, so bots don't bid tips, so the signal is empty.

Unichain's **Flashblocks** close both: blocks are built inside TEEs (trusted execution environments — hardware that proves it ran the published code) that order strictly by priority fee. On that chain, the tip is provably the only way to buy position — so bidding is honest, and taxing the bid is taxing the MEV. Deployed anywhere else, the hook degrades to "a fee on impatience" (still LP-positive, but not the theorem). This is why the README calls it a Unichain hook.

## 3. `donate` — the LP payment rail with a political property

`PoolManager.donate(key, amount0, amount1, hookData)` credits tokens directly to a pool's **currently in-range LPs**, via the same fee-growth accounting that swap fees use (each LP's claimable amount grows pro-rata to their share of active liquidity). Three properties we lean on:

1. **It targets exactly the right people** — the LPs whose liquidity was live when the MEV was extracted.
2. **It is not a swap fee**, so the UNIfication protocol fee switch (which skims LP *fee* income) never touches it. This is the mechanical guarantee behind "100% to LPs."
3. **It reverts on a pool with zero in-range liquidity** (`NoLiquidityToReceiveFees`) — nobody to pay. The hook checks `poolManager.getLiquidity(id) == 0` first and simply skips the tax: no LPs → no victims → no tax.

## 4. `beforeSwapReturnDelta` — how a hook charges a swapper

This is the deepest concept here, worth slowing down for. Recall (learn-the-basics 15) that `beforeSwap` returns three things: a selector, a **`BeforeSwapDelta`**, and a fee override. The delta is how a hook injects its own token adjustment into the swap — but only if the hook's address carries the `BEFORE_SWAP_RETURNS_DELTA_FLAG`.

`BeforeSwapDelta` packs two `int128`s: a delta in the **specified** currency (the one `amountSpecified` denominates — input for exact-input, output for exact-output) and one in the unspecified. Sign convention: **positive = the hook is owed that amount** (takes it); negative = the hook owes.

What the PoolManager does with a positive specified delta (from `Hooks.sol`, the actual core logic):

```solidity
amountToSwap += hookDeltaSpecified;
```

Concretely, exact-input of 1000 token0 (`amountSpecified = -1000`) with a hook delta of +10: `amountToSwap` becomes −990. The pool swaps 990; the user is still debited the full 1000; the 10 difference is credited to the hook's flash-accounting balance. For exact-output of 1000 token1 with delta +10: `amountToSwap` becomes 1010 — the pool produces 1010, the user receives their exact 1000 (paying input for 1010), the hook is credited 10. In both cases: **the swapper pays the tax in the specified token, transparently, atomically.** There's also a built-in safety: if the hook's delta exceeds the swap amount (flipping its sign), the core reverts `HookDeltaExceedsSwapAmount` — one reason our tax needs a hard cap below 100%.

## 5. Flash accounting makes the hook token-free

Now combine 3 and 4. Inside the swap's `unlock` context:

- The return delta gives the hook a **credit** of `taxAmount` in some currency.
- `donate(key, taxAmount, 0, "")`, called by the hook in the same `beforeSwap`, gives the hook a **debit** of exactly `taxAmount` in the same currency.

Credit + debit = zero. At the end of the lock the PoolManager checks every address's deltas net out — the hook's do, arithmetically, every time. **No `transfer`, no `approve`, no `settle`, no `take`, no balance.** The tokens flow user → pool-LPs entirely inside the accounting ledger. Consequences: native-ETH pools work (no ERC20 assumptions anywhere), the attack surface is minimal, and the test `test_hookNeverHoldsTokens` can assert the hook's balances are zero after a taxed swap.

One ordering subtlety: the code calls `donate` *before* returning the delta that funds it. That's fine — flash accounting only requires net-zero **at the end of the unlock**, not at every instant. Transient negative balances are the entire point of the design.

## 6. Fee units and the tax curve's shape (quick reference)

The tax rate is expressed in **ppm** (parts per million — same unit as v4 LP fees: 10,000 ppm = 1%). The curve:

```
taxPpm(priority) = 0                                          if priority ≤ exempt
                 = min((priority − exempt) × kPpmPerGwei / 1 gwei,  maxTaxPpm)
```

- **`exempt`** makes "normal users pay nothing" a hard guarantee, not a tendency.
- **Linear in gwei** because the bid is linear in the MEV (competition drives bid → profit).
- **`maxTaxPpm` (must be < 1,000,000)** exists for two reasons: the `HookDeltaExceedsSwapAmount` revert above, and grief-resistance — without a cap, wrapping someone's swap in a high-priority transaction would burn them at 100%.
- Note the tax *amount* is `swapSize × taxPpm`: a bigger arb needs a bigger swap *and* bids a bigger tip, so its payment grows in both factors — matching how LVR extraction actually scales.

## The one sentence to keep

**Five gears mesh: the EVM exposes the tip as `tx.gasprice − block.basefee`; provable priority ordering (Unichain's TEE-built Flashblocks) makes that tip an honest auction bid for MEV; a positive `beforeSwapReturnDelta` in the specified currency makes the swapper pay `tax = size × min(k·(tip−exempt), cap)`; `donate` hands that exact amount to in-range LPs outside the fee switch's reach; and flash accounting cancels the hook's credit against its donate debit so the contract never touches a token.**
