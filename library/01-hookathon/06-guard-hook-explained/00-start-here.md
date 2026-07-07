# 00 — Start Here: What the Guard Hook Is and Why It Exists

Goal: understand the trust crisis this project answers, why the answer is *meta-infrastructure* rather than another clever pool, and the six invariants that form the product.

## The problem: Bunni died with two audits

In Uniswap v3, using a pool meant trusting one thing: Uniswap. In v4, every pool carries an arbitrary hook contract, and the pool's safety is exactly the hook's safety. The ecosystem's growth now hangs on one question nobody can answer: **"how can I trust this hook?"**

September 2025 made the question concrete. **Bunni** — the most celebrated hook project in the ecosystem, audited by *both* Trail of Bits and Cyfrin — was exploited for **$8.4M** through a math rounding bug and shut down permanently. Weeks later, Stream Finance's opaque-manager model torched $93M and froze hundreds of millions more across DeFi. The lesson the market internalized: *audits reduce the probability of a bug; they do nothing about the blast radius when one fires.*

Meanwhile over 1,300 hooks sit deployed on v4 with real volume concentrated in a tiny handful — because LPs, frontends, and aggregators have no standard way to bound their risk when touching a hooked pool. And of the 556 UHI hooks in the directory, the 63 "security" ones all defend against bad *tokens* (rugs, scam coins). Nobody built defenses against bad *hooks*. Meta-infrastructure — tooling whose customer is other builders — is what hackathons chronically underbuild.

## The reframe: bound the blast radius

You cannot make an arbitrary hook bug-free. You *can* make its worst case boring. Traditional finance figured this out too: exchanges don't certify that no trader will ever go crazy — they install **circuit breakers** so that when someone does, the damage per unit time is capped and trading halts before the hole deepens.

The Guard Hook is that idea applied to hooks themselves: a **wrapper** that sits between the PoolManager and any "inner" hook. The pool registers the *guard* as its hook; the guard forwards every callback to the inner hook and enforces hard limits on what can happen — limits the inner hook cannot see, influence, or override.

## The six invariants (the product, in one table)

| # | Invariant | The attack it neutralizes |
|---|---|---|
| 1 | **Fee firewall** — inner fee overrides capped | A hook that suddenly returns a 100% fee |
| 2 | **Delta firewall** — inner return deltas rejected | Token theft through hook return values |
| 3 | **Outflow limits** — per-token per-block caps: soft cap trips an automatic cooldown, hard cap reverts | Bunni-style drains — *whatever* the bug, tokens can't leave faster than X per block |
| 4 | **Price band** — max price move per block | Single-block price manipulation |
| 5 | **Pause switch** — guardian-manual plus automatic | The gap between "exploit detected" and "multisig wakes up" |
| 6 | **LPs can always exit** — removals never blocked, by anything | The nightmare: a hook (or the guard itself) holding LP funds hostage |

Rule 6 is the philosophical center. A circuit breaker that could freeze LP funds would just relocate the trust problem into the guard. So the exit path is *structurally* unblockable: no pause check, inner-hook failures ignored, inner exit-deltas discarded. **The guard can freeze trading; it can never lock funds.** That asymmetry is what makes "wrapped in Guard" a badge worth trusting.

## Who the customer is (different from the other two projects)

The market-hours and MEV-tax hooks serve traders and LPs directly. The guard's customer is **hook developers**: wrapping their hook buys them (a) a safety story LPs can verify on-chain, (b) freedom from address mining (only the guard's address needs flag bits — inner hooks deploy with plain `new`), and (c) a base contract (`GuardedHook`) to inherit. Downstream, LPs get bounded risk, aggregators get a routability signal, and insurance protocols get something they can actually price. Picks and shovels: the guard wins whenever anyone else's hook succeeds *or fails*.

## The shape of the solution

```
PoolManager ──callbacks──► GuardHook ──forwarded calls──► InnerHook (any contract)
                              │
                    checks before forwarding: paused?
                    checks after returning: fee cap? delta zero?
                    checks after the swap: outflow caps? price band?
```

- The guard's mined address carries **all 14 hook permission flags** — it's a universal wrapper; which callbacks actually get forwarded is per-pool configuration (`innerFlags`).
- Per-pool registration happens **before pool initialization** (`configurePool`); the registrant becomes that pool's **guardian** (pause/unpause/limits).
- Inner hook failures are handled by a **fail-open / fail-closed** dial: skip the broken hook and keep the pool alive, or halt everything — except on the exit path, which is always fail-open (rule 6).
- `innerHook = address(0)` is legal: the guard as a **pure circuit breaker** for vanilla pools.

## Map of the codebase

```
src/
├── GuardHook.sol            ~500 lines — forwarding plumbing + all six invariants
└── base/
    └── GuardedHook.sol      ~130 lines — the base contract inner hooks inherit
test/
├── GuardHook.t.sol          21 tests — forwarding, firewalls, breaker, rule 6,
│                            fail-open/closed, fuzzed invariants
└── mocks/MockInnerHooks.sol four characters: a counter, an honest fee hook,
                             a delta thief, a bricked hook
script/                      deploy (mines ALL 14 flags), register+pool, swap
demo/index.html              rogue-hook simulator, drain-the-breaker button,
                             guardian panel
```

## Reading order for this book

1. `01` — concepts: the flags system, the wrapper pattern, raw calls vs try/catch, circuit-breaker mechanics
2. `02` — `GuardHook.sol` line by line
3. `03` — `GuardedHook.sol` and the four mock inner hooks
4. `04` — the tests and what each proves
5. `05` — deployment and the demo

## The one sentence to keep

**After Bunni proved that two audits don't bound a blast radius, the missing primitive is a wrapper that does — the guard forwards every callback to any inner hook while enforcing six invariants it cannot override (capped fees, no return-value theft, rate-limited outflows with an automatic cooldown, banded prices, a pause switch, and exits that nothing can block), so the worst case of any wrapped hook becomes "trading pauses and everyone walks out," never "the pool is empty."**
