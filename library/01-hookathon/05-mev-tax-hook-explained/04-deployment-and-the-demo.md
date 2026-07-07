# 04 — Deployment and the Demo: Two Personas, One Slider

Goal: how the hook gets onto a chain, how the verified local run proved the pitch in two numbers, and exactly how the demo page works — including the parts of the gas market that leak into a "simple" demo.

## Deployment: the short version

The pipeline is the same as the sibling market-hours project (whose deployment chapter covers the two hard-won lessons — optimizer on, and pinning real V4 artifact addresses instead of simulation ghosts). What's specific to this hook:

- **Flags to mine:** `AFTER_INITIALIZE | BEFORE_SWAP | BEFORE_SWAP_RETURNS_DELTA`. The deploy script also carries the economic defaults as constructor args, spelled out for tuning:

```solidity
uint64 exemptPriorityFee = 0.001 gwei; // swaps tipping less are fully exempt
uint32 taxPpmPerGwei = 5_000;          // 0.5% of the swap per gwei above that
uint32 maxTaxPpm = 100_000;            // hard cap: 10%
```

- **The pool is a plain static-fee pool** (`fee: 3000`) — deliberately, to demonstrate the hook composes with vanilla pools. No dynamic-fee flag, no special pool setup at all.
- **Size is a non-issue**: the hook compiles to ~6.5KB — a quarter of the EIP-170 limit (the optimizer stays on anyway, for parity across the three projects).

## The verified run: the pitch in two numbers

After deploying and seeding the pool, the money demo is two swaps through the standard swap script, differing only in gas price:

```bash
BF=$(cast block latest --field baseFeePerGas --rpc-url $RPC)
forge script script/03_Swap.s.sol ... --legacy --with-gas-price $BF       # "normal user"
forge script script/03_Swap.s.sol ... --legacy --with-gas-price 30gwei   # "arb bot"
```

`--legacy` sends a type-0 transaction where `--with-gas-price` sets `tx.gasprice` directly — the cleanest way to control the tip from a script. Then one view call tells the story:

| Swap (1e18 in) | Priority fee | `totalDonated0` delta |
|---|---|---|
| normal user | ~0.01 gwei (incidental) | 0.000048 tokens |
| arb bot | ~30 gwei | **0.100000 tokens** (the 10% cap) |

Same swap, same pool, 2000× difference in what they paid LPs — decided entirely by their own bids.

And that 0.000048 is itself a lesson rather than a rounding error: the "normal" swap was sent at the *current* basefee, but anvil's basefee decays each block, so by inclusion the transaction carried ~0.01 gwei of accidental tip — above our demo exemption of 0.001 gwei, hence a hair of tax. **This is exactly what the exemption threshold is for**, and why the DEPLOYMENT.md calibration note says a real deployment should set the exemption comfortably above the chain's ambient priority-fee noise. The demo run discovered the deployment guidance.

## Unichain: where it actually means something

The scripts work unchanged on Unichain (130) and Unichain Sepolia (1301) — hookmate's `AddressConstants` resolves the canonical PoolManager/router per chain; you supply a funded key. Calibration for real deployment: measure the ambient tip distribution (set `exemptPriorityFee` above the noise floor) and fit `taxPpmPerGwei` to observed arb tips. Both are per-pool hot-tunable via `setTaxConfig` — no redeploy to retune.

## The demo page: architecture

Same single-file pattern as the siblings (`demo/index.html`, ethers v6 from CDN, anvil's unlocked account #0 as signer, addresses as constants at the top). What's unique here is that the page must **manufacture priority fees from JavaScript** — the browser equivalent of `--with-gas-price`:

```javascript
const block = await provider.getBlock("latest");
const gasPrice = BigInt(block.baseFeePerGas) + ethers.parseUnits(slider.value, "gwei");
await router.swapExactTokensForTokens(amt, 0, true, KEY, "0x", me, deadline,
                                      { gasPrice, type: 0 });
```

The `{ gasPrice, type: 0 }` overrides force a legacy transaction at exactly `basefee + chosen tip`. (Same caveat as the script run: the basefee moves one block later, so realized tip ≥ slider tip — the page comments this so a demo-watcher isn't confused by an extra 0.01 gwei.)

## The panels, one by one

**Lifetime-donated card.** The headline: `totalDonated0/1(poolId)` rendered big, plus the current basefee (`block.baseFeePerGas`) and the pool's tax curve, read live from `taxConfig(poolId)` and rendered as a sentence: *"0.5%/gwei over 0.001 gwei, cap 10%"*. Refreshes every 8 seconds.

**The slider — the centerpiece.** A range input from 0 to 40 gwei. On every movement, two things update *without any transaction*:
- the **live tax quote**: the page calls the on-chain view `taxPpmFor(poolId, sliderGwei)` — the same function the hook itself will use — so the preview can never drift from reality;
- the **persona label**, mapping tip ranges to characters: 😊 *normal user — pays nothing extra* (0), 🙂 *slightly impatient* (<3), 🤖 *fast bot* (<15), 🦈 *top-of-block arb — pays the capped maximum*. It's UI sugar, but it's the mental model of the whole mechanism, made visible.

Then **Swap** sends the real transaction at that tip and the log line prints the measured result: `totalDonated0` before vs after — *"swap 1 mWETH @ 12 gwei priority → tax donated: 0.060000 mWETH."*

**The event feed.** The page subscribes to the hook's event with ethers:

```javascript
hook.on("MevTaxCharged", (pid, sender, prio, tax, is0) => { ...log line... });
```

Every taxed swap — from this page or from any other terminal hitting the same anvil — appears as *"⚡ MevTaxCharged: 12.0 gwei priority → 0.06 mWETH to LPs."* This is the observability story: the event carries the entire economic record, no indexer needed.

**Approvals, once.** First swap triggers the Permit2 two-step for both tokens (`token.approve(Permit2)` then `permit2.approve(token, router, ...)`), cached with a flag so subsequent swaps are single-transaction.

## The demo script — what to do in front of someone

1. **Slider at 0, swap 1.** Log: tax donated 0.000000. *"A normal user. The hook is free."*
2. **Slider to 2 gwei.** Quote flips to 1.00% before you even swap. Swap — log shows 0.01 donated, the feed prints the event. *"The hook read the tip out of my transaction and handed 1% to the LPs."*
3. **Slider to 40 gwei** (persona: 🦈). Quote pins at 10.00%. Swap — 0.1 donated. *"A top-of-block arb pays the cap. On Unichain, it can't fake this number down — the tip is the only way to win the race."*
4. Point at the **lifetime counter**, now visibly grown. *"That's LP income that used to be bot profit. And the fee switch can't touch it — donations aren't fees."*
5. Closer: *"The contract has no ERC20 code. It never holds a token. Credit and debit cancel inside the lock."* (If pressed, prove it: `cast call token0 "balanceOf(address)" $HOOK` → 0.)

## The one sentence to keep

**Deployment is the standard pipeline plus three economic constructor args, the verified run compressed the pitch into two numbers (0.000048 vs 0.100000 donated for the same swap at different tips — and the small one taught us where to set the exemption), and the demo is a slider wired to the on-chain `taxPpmFor` view for honest previews, a `{gasPrice, type: 0}` override to manufacture tips from the browser, and a live `MevTaxCharged` feed that turns every taxed swap into a one-line receipt.**
