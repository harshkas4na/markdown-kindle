# v4 — The Singleton and Flash Accounting

**Fast overview:** v4 (January 2025) keeps v3's math and rebuilds everything around it. All pools move into one contract (`PoolManager`); token movements are replaced by a transaction-long ledger of signed deltas settled once at the end (flash accounting, powered by EIP-1153 transient storage); pool creation becomes a cheap state write; native ETH returns; and balances can be held inside the protocol as ERC-6909 claims. This chapter is the architecture; hooks — the reason for the architecture — get the two chapters after.

## From N contracts to one: the singleton

v2/v3 deploy a contract per pool. That means: expensive pool creation (deploying bytecode), and multi-hop swaps that physically transfer tokens contract-to-contract at every hop (ERC-20 transfers are storage writes — the dominant gas cost of routing).

v4's `PoolManager` holds *every pool* as entries in internal mappings. A pool is identified by its **PoolKey**:

```solidity
struct PoolKey {
    Currency currency0;   // lower-sorted token address (or address(0) for native ETH)
    Currency currency1;
    uint24 fee;           // static fee, or 0x800000 flag = dynamic (hook-set)
    int24 tickSpacing;
    IHooks hooks;         // the hook contract address — part of identity!
}
poolId = keccak256(abi.encode(poolKey))
```

Two consequences worth pausing on:

- **Creating a pool ≈ 10–50× cheaper** (initialize storage, no deployment). Combined with hooks, this enabled 2025–2026's explosion of specialized pools (a launchpad like Flaunch casually creates a pool per token — Chapter 12).
- **The hook address is part of the pool's identity.** ETH/USDC-0.3% with hook A and ETH/USDC-0.3% with hook B are *different pools* with separate liquidity. Liquidity fragmentation across hooks is real and intentional — the market, not the protocol, picks winning hooks. (*Connect the dot:* Chapter 2's depth-begets-depth loop now runs *per hook* — a hook must offer LPs enough edge to overcome starting shallow.)

Also revived: **native ETH pairs** (v2/v3 forced WETH), and **`donate()`** — push tokens to in-range LPs of a pool directly, useful for external reward schemes (and an attack surface, Chapter 11).

## Flash accounting: the protocol becomes a tab

Here's the mental model that makes v4 click: **the PoolManager is a bar that runs a tab.**

In v2/v3, every operation pays immediately — swap in pool 1, receive tokens, send them to pool 2, swap again. In v4, you *open a tab* (`unlock`), do arbitrary operations that only update *numbers*, and settle the net once at closing time. The mechanic:

1. Anyone calls `poolManager.unlock(data)`.
2. The manager calls back your contract's `unlockCallback(data)`.
3. Inside the callback you invoke the core operations — `swap`, `modifyLiquidity`, `donate`, `take`, `settle` — as many as you like, across any pools.
4. Each operation adjusts your **currency deltas**: signed numbers per (address, currency). Negative = you owe the PoolManager; positive = it owes you.
5. Before `unlock` returns, **every delta must be zero** — enforced by a counter of nonzero deltas (`NonzeroDeltaCount`). Otherwise: revert, nothing happened.

To move real tokens you use exactly two verbs:

- **`take(currency, to, amount)`** — pull tokens out (makes your delta more negative).
- **`settle(currency)`** — pay tokens in: transfer them to the manager, then call `settle` (or send `msg.value` for native ETH) to credit your delta.

A three-hop swap thus becomes: swap A→B (numbers), swap B→C (numbers), swap C→D (numbers), then *one* `settle` of A and *one* `take` of D. Two token transfers total, regardless of path length. (*Connect the dot:* this is v2's flash-swap "take now, pay by end of transaction" — Chapter 3 — promoted from a per-pool trick to the *only* way the protocol works. And it inherits the same power: inside `unlock`, you always have a free flash loan of anything the manager holds, as long as your tab closes.)

### EIP-1153: why this is affordable

Deltas must be written and rewritten constantly — in regular storage (`SSTORE` ~5k–20k gas per write plus refund complexity) the tab would cost more than it saves. **EIP-1153 (Cancun, March 2024)** added `TSTORE`/`TLOAD`: *transient storage* that lives only for the current transaction and auto-clears — ~100 gas per access, ~20× cheaper. v4 keeps deltas, the unlock flag, and the nonzero-delta counter in transient storage. This is also why v4 shipped in January 2025: it literally could not be deployed as designed before Cancun.

Note the security inversion, worth a highlight: **v2/v3 forbid reentrancy with mutexes; v4 *embraces* reentrancy inside `unlock` and makes it safe with accounting.** Any contract can be called mid-tab (hooks! routers! your code!), can even recursively operate on pools — and none of it matters as long as all deltas hit zero at the end. Solvency is checked at one choke point instead of guarded at every door. (Chapter 11 explores what this does and doesn't protect — the ledger balancing does not mean every *hook's internal* state is consistent. Conservation ≠ correctness.)

## ERC-6909: balances that never leave

Second gas trick: the PoolManager is itself a multi-token vault implementing **ERC-6909** (a minimal multi-token standard — think ERC-1155 without the ceremony). Instead of `take`-ing real ERC-20s out, you can `mint` claim tokens inside the manager; instead of `settle`-ing real tokens in, you can `burn` claims.

Who cares: anyone who touches the protocol repeatedly. An MEV searcher or an active rebalancing hook that would otherwise pay two ERC-20 transfers per round trip keeps working balances as 6909 claims and pays ~a tenth of that. Routers use it for intermediate hop tokens. (*Connect the dot:* your MEV-tax and rebalancing hook designs from the earlier books on this shelf all want 6909 balances for their treasuries.)

## What moved out of core

v4 core is *smaller* than v3 core. Deliberately gone:

- **The oracle.** v3's observation buffer cost every swapper gas to maintain. v4 ships none; oracles are now hooks (Chapter 9), paid for only by pools that want them.
- **Fee tiers as governance decisions.** Any static fee value at pool creation, or the dynamic-fee flag delegating per-swap fees to the hook (Chapter 9).
- **Position management.** Core tracks raw positions; the NFT wrapper, permit2 integration, batching — all periphery (`PositionManager`, `UniversalRouter`, `V4Router`).

The philosophy compounds Chapter 3's core/periphery lesson: **core owns invariants (custody, tick math, delta conservation); everything with an opinion — pricing opinions, fee opinions, oracle opinions — is pushed to the edges** where it can compete and fail without taking custody down with it. Hooks are that edge, made pluggable.

## The lock's fine print (things that bite in Chapter 10)

- **You can't call `swap`/`modifyLiquidity` directly** from an EOA or outside `unlock` — everything routes through an unlock callback. For users this is invisible (routers do it); for you as a hook/integration author it defines your test harness.
- **`unlock` is global, not per-pool.** One tab covers all pools — that's what makes cross-pool netting work.
- **Deltas are per-address.** Hooks can accrue their *own* deltas (taking fees, taking the swap input for themselves...) — the mechanism behind custom accounting in Chapter 8. A hook with unsettled deltas reverts the whole transaction, which is a classic beginner bug.
- **`sync()` before settling ERC-20s.** The manager snapshots its balance, you transfer, `settle` diffs the balances. Fee-on-transfer tokens settle short and revert — v4 core does not support them (their "fee" would break exact delta math).

## The scoreboard, eighteen months in

As of mid-2026: v4 runs on 15+ networks (Ethereum, Unichain, Base, Arbitrum, BNB, Polygon, Monad, Tempo, ...), with roughly **$355B cumulative volume** (~$190B on mainnet, ~$70B on Unichain) and on the order of **2,500+ distinct hooks** deployed. Routing gas savings materialized (~30–40% on multi-hop paths); the singleton has held custody without incident; the failures that did happen (Chapter 11) were all in hook-land — exactly where the architecture said risk should pool.

The stage is set. One field of `PoolKey` has been suspiciously underexplained: `IHooks hooks`. Next chapter: what the PoolManager is willing to let that address do — and why the *address itself* is the permission slip.
