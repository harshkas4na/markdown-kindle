# v2 — The Workhorse and Its Architecture

**Fast overview:** Uniswap v2 (May 2020) took v1's formula and built the industrial machine around it: any ERC-20 pair, a core/periphery contract split that became DeFi's standard architecture, a manipulation-resistant price oracle, flash swaps, and LP tokens that plugged into everything. v2 has now run for six years without a governance change or a hack of its core. This chapter is about *engineering*: the specific decisions that made a 300-line contract safe to hold billions, because v4's design (Chapter 6) is best understood as a critique of exactly these decisions.

## From v1 to v2: kill the ETH bridge

v1 only supported ETH↔token pools, so trading token A for token B meant two hops through ETH — two fees, two slippages. v2's headline was simply ERC-20↔ERC-20 pairs. Boring, huge.

## Core / periphery: the architecture DeFi copied

v2 is split into two repositories, and the split *is* the design lesson:

- **Core** (`UniswapV2Factory`, `UniswapV2Pair`): the vault. Holds all funds, enforces the invariant, and does *nothing else*. No safety rails for humans: `swap()` doesn't check you got a fair price, `mint()` doesn't compute the right deposit ratio for you. Minimal surface = minimal attack surface, and it's immutable — no admin keys, no upgrades.
- **Periphery** (`UniswapV2Router02`): the friendly front door. Computes amounts, enforces *your* slippage limits (`amountOutMin`, `deadline`), handles multi-hop paths and ETH wrapping. Holds no funds, and is *replaceable* — the router was upgraded once (Router02) without touching a cent of liquidity.

The principle: **put the money where the code never changes; put the convenience where code can be fixed.** You will see it again in v4 — `PoolManager` is core taken to its extreme, and everything user-facing lives in periphery contracts and hooks.

Two supporting details worth knowing:

- **Deterministic pair addresses.** The factory deploys pairs with `CREATE2`, so a pair's address is computable off-chain from the two token addresses. Routers use this to find pools without any registry lookup. (*Connect the dot:* CREATE2-determined addresses return in v4 with a twist — there, the address of a *hook* encodes its permissions, Chapter 7.)
- **The pair is also an ERC-20.** LP shares are themselves tokens, which is why they could become collateral on lending markets and farmable assets in 2020's yield summer. Composability by default.

## Inside a swap: the reserve/balance dance

The core `swap()` is worth reading once in your life. Its logic, compressed:

```solidity
function swap(uint amount0Out, uint amount1Out, address to, bytes data) {
    // 1. optimistically send the requested output tokens to `to`
    // 2. if data.length > 0, call to.uniswapV2Call(...)   <- flash swap hook
    // 3. measure actual balances now held
    // 4. infer amounts *in* from (balance - (reserve - amountOut))
    // 5. require balance0Adj * balance1Adj >= reserve0 * reserve1 * 1e6  (k check, fee-adjusted)
    // 6. update cached reserves
}
```

Three ideas here shaped everything after:

**1. Balances are measured, not trusted.** The contract compares its *actual* token balances against its cached `reserve0/reserve1` to figure out what you paid. This tolerates weird tokens (fee-on-transfer) and is why `sync()`/`skim()` exist — tiny functions that reconcile cache vs. reality when someone transfers tokens in directly.

**2. The invariant is checked at the end, not the price computed at the start.** Core doesn't calculate your output — the router did that. Core only *verifies* that after everything, `k` didn't shrink (with fee adjustment). Verification is cheaper and safer than computation.

**3. Optimistic transfer enables flash swaps.** Because outputs are sent *before* inputs are verified, you can receive tokens, run arbitrary code in the `uniswapV2Call` callback (arbitrage elsewhere, liquidate a loan), and pay by step 5 — all in one atomic transaction, no capital required. If you can't pay, everything reverts. This "take now, settle by end of transaction" pattern is the direct ancestor of v4's flash accounting (Chapter 6), which generalizes it from one pool to the entire protocol.

## The TWAP oracle: making manipulation expensive

DeFi protocols desperately need prices (to know when a loan is undercollateralized, etc.). Reading a pool's *spot* price is trivially manipulable: a whale can swap to shove the price, trigger your protocol's logic, and swap back — within one transaction, cost ≈ fees only. Several 2020-era protocols died exactly this way.

v2's answer: each pair accumulates `price0CumulativeLast += price * secondsElapsed` on the *first* trade of each block. A consumer contract snapshots the accumulator at two times and divides:

```
TWAP = (cum(t2) − cum(t1)) / (t2 − t1)
```

Why this resists manipulation: the accumulator only samples a price that *survived to the next block*. An attacker must push the price and hold it there across blocks — meaning their capital sits mispriced, exposed to every arbitrageur in the world, for the whole window. Cost scales with pool depth × window length, and post-merge (proposer knows it gets consecutive slots occasionally) it's weaker but still costly. The design lesson: **an oracle's security = the cost of keeping it wrong.** v3 rebuilt this with observation arrays and geometric means (Chapter 4); v4 removed the built-in oracle entirely — making "truncated/oracle hooks" one of the canonical hook use cases (Chapter 9).

## The protocol fee switch: a loaded gun, holstered

v2 shipped with a dormant 1/6-of-fees protocol cut, toggleable by governance. It stayed off for years — flipping it risks liquidity migrating to a fork (Sushiswap's 2020 "vampire attack" proved liquidity is mercenary). The economics of *who* should earn AMM revenue — LPs, token holders, or hook developers — remains live: v4 has both protocol-fee and hook-fee machinery (Chapter 8), and "fee switch" debates continued into 2026. The gun stays interesting because it's still mostly holstered.

## Small decisions with long shadows

- **`MINIMUM_LIQUIDITY = 1000`.** The first LP's first 1000 share-units are burned forever. This blocks a nasty attack: donate-then-inflate the share price so the next depositor's shares round to zero. Rounding-direction and first-depositor attacks remain a *top* vulnerability class in 2026 vaults and hooks (Chapter 11 — Bunni died of rounding).
- **Reentrancy lock.** One mutex on the pair. Simple, effective. v4 replaces the mutex with a global `unlock` pattern where reentrancy is *allowed* but accounted (Chapter 6) — a fascinating inversion.
- **Fixed 0.3% fee for everything.** Stables overpay, exotic pairs underprice risk. v3 answered with three fee tiers; v4 with fully dynamic, hook-set fees (Chapter 9). The fee's role as an LVR defense is Chapter 5's punchline.

## What v2 got wrong (on purpose)

With 2026 hindsight, v2's flaws were mostly conscious simplicity:

1. **Capital efficiency.** Liquidity smeared from 0 to ∞; almost all of it never touches a trade. → v3.
2. **Passive-only LPs.** No way to express a view or a strategy. → v3 ranges, v4 hooks.
3. **One deployed contract per pair.** Multi-hop = token transfers between contracts = gas. → v4 singleton.
4. **Nothing pluggable.** Every innovation required forking the whole protocol (hence the 2020–2022 fork zoo: Sushi, Pancake, and hundreds more). → v4 hooks, which turn forks into plugins.

Keep this list; Chapter 6 is its point-by-point resolution.

Next: v3 attacks flaw #1 with the most important idea in modern AMM design — concentrated liquidity — and pays for it with the hardest math in this book.
