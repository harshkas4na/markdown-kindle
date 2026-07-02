# 25 — Security Pitfalls Specific to Hooks

Goal: the closing lesson. A list of mistakes that are easy to make specifically *because* of how hooks work (not generic Solidity security 101, though that all still applies too) — each with a concrete failure scenario, so these stay memorable instead of abstract warnings.

## 1. Forgetting `onlyPoolManager` — letting anyone trigger your callbacks

**The mistake**: writing a `beforeSwap` function that anyone can call directly, not just the PoolManager during an actual swap.

**Why it's dangerous**: if `_beforeSwap` updates state assuming it's only ever called in the middle of a real, PoolManager-orchestrated swap (e.g. lesson 18's fee tracker, lesson 21's tick-crossing detector), an attacker calling it directly, out of context, can desynchronize that state from reality — recording fake volatility data, marking limit orders as executed when no real swap happened, or worse.

**The fix**: `BaseHook`'s constructor already sets this up for you correctly (lesson 15) — the public wrapper functions it provides (`beforeSwap`, `afterSwap`, etc.) already check `msg.sender == address(poolManager)` before calling into your `_beforeSwap`/`_afterSwap` internal functions. The mistake shows up specifically when someone bypasses `BaseHook` and implements `IHooks` raw, or adds a *new*, separate public function that touches the same sensitive state without the same guard. Rule of thumb: any function that reads or writes state your swap-callbacks depend on should be `internal`, `private`, or explicitly access-controlled — never assume "only the PoolManager will realistically call this" without actually enforcing it.

## 2. Trusting `hookData` without verifying who actually sent it

**The mistake**: lesson 23's compliance hook reads an "actual trader" address out of `hookData` and checks *that* address against a whitelist — but never verifies the caller genuinely represents that address.

**Why it's dangerous**: `hookData` is just arbitrary bytes passed along by whoever calls the swap. A malicious or buggy router could pass `hookData` claiming to represent a verified, whitelisted wallet, while the trade is actually being executed on behalf of someone who was never verified at all — completely defeating the compliance check's entire purpose while looking, on the surface, like it's working correctly.

**The fix**: for anything security-critical (compliance gating, reward eligibility, anything with real consequences), don't trust a bare address claim in `hookData` — require a signature (`ecrecover`) proving the claimed address actually authorized this specific trade, or restrict which router contracts are allowed to call your pool at all via a trusted-router allowlist.

## 3. Reentrancy through your own external calls, not through the PoolManager

**The mistake**: assuming that because the PoolManager has its own reentrancy protections around the core swap flow, your hook is automatically safe from reentrancy too.

**Why it's dangerous**: the PoolManager's protections cover *its own* state. The instant your hook makes an external call — to an ERC-4626 vault (lesson 20), to an oracle, to *any* other contract — that external contract can, in principle, call back into your hook before your own function finishes executing, potentially re-entering while your hook's own state (not the PoolManager's) is in a partially-updated, inconsistent state. A vault-integrated hook that updates its own `vaultShares` mapping *after* an external `deposit()`/`redeem()` call, rather than before, is a classic version of this bug shape (the "checks-effects-interactions" ordering violation, just inside a hook instead of a typical DeFi contract).

**The fix**: follow checks-effects-interactions rigorously inside your hook too — update your own internal state *before* making external calls, not after — and use `ReentrancyGuard`'s `nonReentrant` modifier on any hook function that both touches sensitive state and makes an external call, as defense in depth.

## 4. Getting the hook address / permission flags out of sync

**The mistake**: changing `getHookPermissions()` (e.g. adding `afterSwap: true` for a new feature) without re-mining and re-deploying to a matching address.

**Why it's dangerous**: this one usually just fails loudly (pool initialization reverts with `HookAddressNotValid`, per lesson 16) rather than silently causing a security issue — but it's worth listing because it's the single most common "why won't this deploy" moment for anyone iterating on a hook, and it's easy to burn real time confused about it before recognizing the actual cause.

**The fix**: any time you change which callbacks your hook uses, re-run the mining step (lesson 16) — there is no way around this, the address and the permissions are cryptographically tied together by design.

## 5. Trusting your own pool's spot/TWAP price for something that needs a stronger guarantee

**The mistake**: using a self-rolled TWAP (lesson 19, Pattern A) of a specific pool as the reference price for something with real financial stakes — e.g. deciding whether a stablecoin has depegged, or pricing an option — for a pool that's thin, new, or low-volume.

**Why it's dangerous**: article 9's flash-loan manipulation risk doesn't disappear just because you're averaging over time instead of reading spot price — it just gets more expensive to pull off. For a thin enough pool, "more expensive" can still be cheap enough to be profitable for an attacker relative to what they can extract by fooling your hook's logic. A TWAP is a real improvement over spot price, not an absolute guarantee, and its manipulation-resistance scales with how deep and actively-traded the underlying pool actually is.

**The fix**: for anything with serious financial consequences riding on the price being correct, prefer an external, independently-aggregated oracle (lesson 19, Pattern B) over a self-rolled TWAP of a single, possibly-thin pool — and even then, always check staleness (pitfall discussed in lesson 19) rather than trusting the last returned value blindly.

## 6. Fee-override math that can exceed 100%, or underflow to something nonsensical

**The mistake**: a dynamic-fee formula (lesson 18) that, under some extreme but reachable input (very large tick delta, a sudden price gap), computes a fee value larger than what the fee-encoding format can represent, or that silently wraps/underflows into a tiny or zero fee instead of a large one.

**Why it's dangerous**: an unbounded or incorrectly-clamped fee formula can, at the extreme, either lock a pool (fee effectively 100%+, nobody can trade) or accidentally zero out your protection exactly during the highest-volatility moment — the one moment your dynamic fee was supposed to matter most.

**The fix**: always explicitly clamp computed fees to a sane `[MIN_FEE, MAX_FEE]` range (as lesson 18's example does with `if (fee > MAX_FEE) fee = MAX_FEE;`) rather than trusting a formula to naturally stay in bounds under every possible market condition — and write a Foundry fuzz test (`forge test --fuzz`) specifically feeding your fee formula extreme tick-delta inputs to confirm the clamp actually holds.

## The one sentence to keep

**Most hook-specific security bugs come from one of three sources — trusting a caller or a piece of passed-in data (`hookData`, an unverified `sender`) that looks legitimate but isn't verified, making an external call without protecting your own hook's state the way `ReentrancyGuard`/checks-effects-interactions would, or trusting a price signal (self-rolled TWAP, an unbounded fee formula) that's a real improvement over the naive version but still has a breaking point under extreme or adversarial conditions — and the fix in every case is the same instinct: verify explicitly, don't assume the PoolManager's own protections automatically extend to your hook's separate state and logic.**

---

## You've now covered the full build stack

Lessons 14-17 got you from zero to a working, tested hook. Lessons 18-23 gave you real code for the six most common problem patterns in the entire 556-hook directory — dynamic fees, oracles/TWAP, idle liquidity/JIT, limit orders, MEV protection, and compliance gating. Lesson 24 turned every unfamiliar import into a recognizable tool, and this lesson gave you the specific ways these patterns break if built carelessly. Between this stack and the conceptual lessons (1-13), you should now be able to read almost any hook in `hook-directory/categories/`, guess roughly how it's implemented before checking, and start sketching your own idea with a real sense of which building blocks it needs.
