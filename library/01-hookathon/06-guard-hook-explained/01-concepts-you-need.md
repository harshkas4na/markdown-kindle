# 01 — The Concepts You Need Before Reading the Code

Goal: the guard is architecturally the strangest of the three projects — a hook that *hosts other hooks*. These six concepts make its strangeness systematic.

## 1. The flags system, revisited from the guard's angle

Recall (learn-the-basics 06/16): a hook's *deployed address* must physically encode which callbacks it uses — the low 14 bits of the address are a permission bitmap the PoolManager checks before making each call. `beforeSwap` is bit 7 (`1 << 7 = 128`), `afterSwap` bit 6, and so on; `Hooks.ALL_HOOK_MASK = (1 << 14) - 1 = 0x3FFF` is all of them.

The guard cannot know at deployment which callbacks its future inner hooks will need — so its address carries **all fourteen flags**. The PoolManager therefore calls the guard on *every* lifecycle event of every guarded pool, and the guard decides per-pool, per-callback, whether to forward. Cost of mining: 14 fixed bits → on average ~16,384 CREATE2 salts to try — seconds of CPU, done once, and every wrapped hook afterwards needs **zero mining** (only the guard ever calls them; the PoolManager never sees their addresses).

One subtlety: four of the fourteen flags (`*ReturnDelta`) aren't callbacks but *parsing permissions* — they tell the core "this hook's return values include balance deltas, parse them." The guard has them all set, which obliges it to always return *well-formed* deltas. It returns zeros (and polices the inner hook's deltas — that's invariant #2).

## 2. The wrapper (proxy) pattern, and who calls whom

Normal hook: `PoolManager → Hook`. Guarded: `PoolManager → Guard → InnerHook`. Three identity questions to keep straight:

- **To the PoolManager,** the pool's hook *is the guard* — its address is in the `PoolKey`, its flags gate the callbacks, its returns drive the swap.
- **To the inner hook,** the caller is the guard — so inner hooks guard their functions with `onlyGuard`, not `onlyPoolManager`. This is why *existing deployed hooks can't be wrapped as-is* (their BaseHook rejects any caller but the PoolManager) and why the project ships `GuardedHook`, a base contract built for life behind the guard.
- **The original `sender`** (the router/user who initiated the operation) is passed through untouched as the first argument — the inner hook sees the real actor, not the guard.

## 3. Raw `call` + manual decoding — controlled distrust

The guard cannot type-safely `IHooks(inner).beforeSwap(...)` and let reverts bubble: a broken inner hook would then always brick the pool, and rule 6 (exits always work) would be unenforceable. Instead it uses a **raw low-level call**:

```solidity
(bool ok, bytes memory ret) = cfg.innerHook.call(callData);
```

A raw `call` never throws — failure comes back as `ok = false`, and success with garbage comes back as bytes we can inspect *before* trusting. The guard's acceptance test is threefold: the call succeeded, returned at least 32 bytes, **and** the first four bytes equal the expected selector (every v4 callback must return its own selector as an "I meant to do that" signature — the guard enforces this convention on inner hooks just like the PoolManager enforces it on real hooks). Anything else is a failure, routed to the fail-open/fail-closed dial. `abi.encodeCall(IHooks.beforeSwap, (...))` builds the calldata with **compile-time type checking** — the safety of an interface call, the control of a raw one.

## 4. Fail-open vs fail-closed — a dial, not a dogma

When a dependency fails, systems choose: **fail-open** (skip it, keep serving) or **fail-closed** (halt everything). Neither is universally right for hooks: a *decorative* inner hook (analytics, points) should never brick a pool → fail-open; a *load-bearing* one (KYC gate, oracle guard) failing silently would be worse than downtime → fail-closed. So it's per-pool configuration... with one override: on `removeLiquidity`, the guard forces fail-open regardless — a reverting (or malicious) inner hook must never trap LP funds. The dial covers trading; rule 6 covers exits.

## 5. Circuit breakers: revert-the-trade vs trip-the-breaker

Two different protections hide under "circuit breaker", and the guard implements both because they fail differently:

- **The hard cap reverts the offending trade.** If a swap would push this block's outflow past `blockOutflowHardCap`, it reverts. Protection is immediate but *stateless* — the attacker can try again next block.
- **The soft cap trips a cooldown.** Here's the subtle part: you *cannot* "detect a breach and pause" in the same transaction you revert — a revert unwinds your pause flag along with everything else. So the soft cap works with the grain of the EVM: the crossing swap **succeeds** (it's under the hard cap; it's not provably evil), but the guard *records* `pausedUntil = now + cooldown` in that same successful transaction. Every subsequent operation finds the pool paused. Like the NYSE's breakers: the triggering trade stands; the market halts; trading resumes on a timer (or a guardian's unpause) with no human required to notice at 3am.

Why per-*block* accounting? Because a drain is a rate phenomenon. Any single-transaction limit is dodged by splitting into many transactions; a per-block cap bounds what *all* transactions in a block can jointly extract, which — combined with the cooldown — bounds tokens-per-hour no matter how the attacker slices the calls.

## 6. Where the guard reads "outflow" and "price" from

The guard needs ground truth that the inner hook cannot fake. Both signals come from the core, not from the inner hook:

- **Outflow:** `afterSwap` receives the swap's `BalanceDelta` *from the PoolManager* — signed amounts from the swapper's perspective, positive = tokens the user receives = tokens leaving the pool. The guard accumulates the positive legs per token per block. (Liquidity removals are deliberately *not* counted — withdrawing your own principal isn't a drain, and counting it would let an attacker exhaust the cap to block others' exits, violating rule 6's spirit.)
- **Price:** `poolManager.getSlot0(id)` — the pool's actual `sqrtPriceX96`. The band compares the *current* price against the price at the **block's first operation** (snapshotted in `beforeSwap` when the block number changes), so ten small swaps can't tiptoe where one big swap can't jump. The bps math is the same square-the-sqrt-ratio trick as the market-hours hook's band, with the same ≥2× overflow guard.

## The one sentence to keep

**Six ideas make the guard readable: an all-14-flags address makes one deployment a universal wrapper (and frees inner hooks from mining); the wrapper re-routes identity (PoolManager sees the guard, the inner hook sees the guard, the original sender passes through); raw `call` + selector-checking turns inner-hook failures into data instead of reverts; a per-pool fail-open/fail-closed dial handles those failures — with exits always forced open; the hard cap reverts trades while the soft cap lets the crossing trade stand and pauses the future (because a revert can't persist a pause); and every enforcement signal (deltas, prices) is read from the core, where no inner hook can lie about it.**
