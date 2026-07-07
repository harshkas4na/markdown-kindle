# 05 — Deployment and the Demo: Watching a Hook Go Rogue and Get Caught

Goal: what's different about deploying a universal wrapper, the registration flow that inverts the usual pool-creation order, and the demo page — whose star attraction is flipping the inner hook evil live and watching the guard stop it.

## Deploying the guard: three differences from a normal hook

The pipeline is the shared one (see the market-hours book's deployment chapter for the optimizer and simulation-ghost lessons — both apply; the guard weighs ~12KB *with* the optimizer). What's guard-specific:

**1. Mining all fourteen bits.** The deploy script's flags line is simply:

```solidity
uint160 flags = uint160(Hooks.ALL_HOOK_MASK); // every callback, every delta flag
```

14 fixed bits → ~16,384 CREATE2 iterations on average. `HookMiner.find` grinds through it in seconds; the verified local deployment landed at `0xE7e1...bfFf` — read the tail: `...bfFf` ends in binary `11 1111 1111 1111`, the fourteen flag bits, visible to the naked eye in the address itself.

**2. No constructor economics.** Unlike the siblings, the guard's constructor takes only the PoolManager — all policy is per-pool, set at registration. One deployment serves every pool and every team.

**3. The inverted pool-creation order.** A normal pool: `initialize`, done. A guarded pool: **configure first, then initialize** — because `initialize` carries no hook data, so the config must be waiting when `beforeInitialize` fires. The pool-creation script does the whole dance in one broadcast:

```solidity
FeeSettingInnerHook innerHook = new FeeSettingInnerHook(address(hookContract), 3000); // plain new — no mining!
GuardHook(address(hookContract)).configurePool({
    key: poolKey,
    innerHook: address(innerHook),
    innerFlags: innerHook.guardedPermissions(),  // the hook declares, the script relays
    failOpen: false,
    maxFee: 20000,            // 2.00% fee firewall
    maxPriceMoveBps: 500,     // 5% per block
    cooldown: 5 minutes,
    blockOutflowSoftCap: 2 ether,
    blockOutflowHardCap: 5 ether
});
// ...then positionManager.multicall(initialize + mint) as usual
```

Note `innerFlags: innerHook.guardedPermissions()` — the declaration lives in the hook's own code, the script just relays it; no hand-maintained bitmap to drift out of sync. The verified run deployed the inner hook at a plain unmined address and the on-chain config read back exactly as written: flags = 128 (`BEFORE_SWAP_FLAG` alone), fee cap 2%, band 5%, caps 2/5, guardian = deployer.

The demo's guarded pool uses `DYNAMIC_FEE_FLAG` because its inner hook overrides fees. Pure-circuit-breaker pools (no inner hook) can be static-fee.

## The demo page: architecture

Same single-file recipe as the siblings (ethers v6 CDN, anvil's unlocked account #0, address constants at the top — guard, inner hook, tokens, router, Permit2). The distinctive part is *whose* functions the panels call: this demo drives **three different roles** from one page — a trader (router swaps), the guardian (guard admin), and, mischievously, *the inner hook's own dark controls* (`setFee` is unprotected on the mock, precisely so the demo can play saboteur).

One detail to know when reading the code: in this pool the demo swaps dUSD → gASSET, which is `zeroForOne = false` (address sort put gASSET as currency0), so the asset *leaving* the pool is token0 — which is why the status card watches `blockOutflow0` and the drain button crosses the *token0* soft cap.

## The panels, one by one

**Pool status card.** Every 8 seconds: `isPaused(poolId)` renders the big ✅ LIVE / ⛔ HALTED; `config(poolId)` fills the policy rows (fee cap, band, soft/hard caps, fail mode — all read from the chain, not hardcoded); `inner.fee()` shows the inner hook's *current* fee with a ⚠️ badge when it exceeds the cap (the page compares client-side — a nice touch: you can see the rogue state *before* anyone gets reverted); `blockOutflow0(poolId, currentBlock)` shows the drain meter; and `pausedUntil` renders as a live countdown when a cooldown is running.

**Trader panel.** A plain router swap (Permit2 two-step on first use, then `swapExactTokensForTokens`). Every outcome goes to the log — successes green, guard rejections red *with the revert reason*, because in this demo **reverts are the product**. The panel's second button is pre-loaded ammunition: *"Swap 3.0 (crosses the 2.0 soft cap)"*.

**Rogue-hook simulator — the star.** Two buttons calling the mock's `setFee`:

- *"Make inner hook demand a 50% fee"* → `inner.setFee(500000)`. Nothing visibly breaks — until anyone swaps, and the guard answers `FeeCapExceeded`. The narrative beat: the wrapped hook *turned malicious after deployment, after any audit* — and it didn't matter.
- *"Restore honest 0.30% fee"* → `inner.setFee(3000)`, and swaps flow again.

**Guardian panel.** `pause(poolId)` / `unpause(poolId)` — the manual switch and the early cooldown-lift, with the rule-6 reminder printed right under it.

**Event feed.** ethers subscriptions on the guard's events: `CircuitBreakerTripped` (with outflow, cap, and until-when), `Paused`, `Unpaused` — every safety action, from this page or any terminal against the same anvil, becomes a timestamped log line.

## The demo script — what to do in front of someone

1. **Baseline.** Status: ✅ LIVE, policy rows populated from chain. Swap 0.5 — works; the inner hook's 0.30% fee applied *through* the guard. *"The wrapped hook works normally; the guard is invisible."*
2. **The rogue flip.** Press *"demand 50% fee."* Status shows fee 50.00% ⚠️ over cap. Swap — **red log line: FeeCapExceeded**. *"The hook went greedy after every audit that will ever be run on it. The guard doesn't care when it happened."* Restore, swap, green again.
3. **The drain.** Press the 3.0 drain button. Watch the log: the swap **succeeds** — then `⚡ CircuitBreakerTripped` in the feed, status flips ⛔ HALTED with a countdown. Try a small swap: blocked. *"The crossing trade stood — you can't revert and pause in one breath — but the pool froze itself within the same transaction. Nobody was awake, and it didn't matter."*
4. **The exit that always works.** While halted, mention (or show via `cast`, since the demo page has no LP panel): `decreaseLiquidity` still succeeds. *"Frozen means frozen for trading. LPs can always leave — that invariant is structural, not policy."*
5. **The lift.** Either wait out the countdown (5 minutes on the demo config) or press Unpause. ✅ LIVE.
6. **The meta-point**, gesturing at the top of the page: *"The inner hook's address has no flag bits — it's a plain `new` deployment. Wrapping costs a hook developer one inheritance and one registration call, and buys their LPs everything you just watched."*

## Real-chain notes

Nothing chain-specific here (unlike the MEV-tax hook): the guard works anywhere v4 does — hookmate resolves canonical addresses for mainnet, Base, Arbitrum, Unichain, etc. The one operational difference at scale: the guardian role should be a multisig or DAO per pool, and the README flags the honest v2 wishlist — permissionless unpause after a maximum duration (guardian-griefing bound), value-denominated caps (like the market-hours hook's), and mediated inner deltas for fee-taking hooks.

## The one sentence to keep

**Deploying the guard means mining an address whose last 14 bits are all ones (you can read `...bfFf` off the verified deployment), registering each pool's policy *before* initializing it (with the inner hook — a plain unmined `new` — declaring its own `guardedPermissions()`), and the demo turns the safety argument into theater: flip the wrapped hook to a 50% fee and get `FeeCapExceeded`, press the drain button and watch the breaker trip *after letting the crossing trade stand*, then note the halted pool still lets LPs walk — all narrated by the guard's own event feed.**
