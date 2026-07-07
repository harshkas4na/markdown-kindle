# 00 — Start Here: What the Market Hours Hook Is and Why It Exists

Goal: before touching a line of code, understand the *problem* this project attacks, why nobody solved it before, and the exact shape of our solution — so that every file you open afterwards feels inevitable rather than arbitrary.

## The problem, told as a story

Imagine a Uniswap v4 pool holding tokenized Tesla (tTSLA) against a stablecoin. It's Friday, 4:00pm in New York. The NYSE closing bell rings. Every real-world venue where Tesla trades goes dark for 65 and a half hours.

The on-chain pool doesn't ring any bell. It keeps quoting the same price it had at the close, all weekend, to anyone who shows up. Now three bad things happen, in order:

1. **Friday night through Sunday: the pool has no anchor.** During market hours, arbitrageurs keep the pool honest — if the pool's price drifts from the NYSE price, a bot instantly trades against it and pockets the gap, dragging the pool back in line. That mechanism is the *only* reason AMM prices track reality. When the reference market closes, there's no "real" price to arbitrage against. The pool's price is whatever the last trader left it at, and a thin weekend pool is cheap to push around. Regulators reviewing tokenized equities flag exactly this: manipulable off-hours prices and **no circuit breakers**.

2. **All weekend: LPs are selling free options.** Suppose news breaks Saturday — Tesla recalls every Cybertruck. Everyone *knows* the stock will open lower on Monday, but the pool still quotes Friday's price. Anyone who trades against the pool at the stale price is picking money out of LPs' pockets, and the LPs get nothing for bearing that risk. In the literature this loss is called **LVR — loss-versus-rebalancing** (see the learn-the-basics lesson 08): the systematic bleed from trading against better-informed flow at stale prices. A weekend with a closed reference market is LVR in its purest, most brutal form.

3. **Monday, 9:30:00 AM: the massacre.** The real market reopens and instantly discovers the new price — say 8% lower. The pool still quotes Friday's price. Now there is a race: the first transaction to land against the pool captures the entire 8% gap. It will be won by whoever runs the fastest bot and bids the most for block position, and the prize is paid entirely by the pool's LPs. Every single Monday. It's a structural, scheduled transfer from LPs to the fastest arbitrageur.

Traditional markets solved every piece of this **a century ago**: closing bells (don't trade when there's no price discovery), circuit breakers and limit-up/limit-down bands (bound how far a price can move when things are thin or crazy), and **opening auctions** (when the market reopens, don't let the fastest order win — collect all orders and clear everyone at one fair price). On-chain AMMs have none of it. And the wave is arriving *now*: Kraken's xStocks, Robinhood's tokenized equities, the NYSE building its own 24/7 tokenized venue.

## Why 556 previous UHI hooks didn't build this

The hook directory's RWA category (102 hooks) is almost entirely *compliance* — KYC gates, whitelists, transfer restrictions. That's "who may trade." Nobody built the *market microstructure* for assets that have a closing bell — "how trading should behave when the reference market sleeps." The niche was empty not because it's impossible but because tokenized stocks only became a live, funded trend after most cohorts ended.

## The shape of our solution

One hook contract, `MarketHoursHook`, that derives one of **three phases** from `block.timestamp` on every single swap — no keeper, no cron job, no oracle for the schedule (only holidays need updating, because those change every year):

| Phase | When | What the hook does |
|---|---|---|
| **OPEN** | 09:30–16:00 ET, trading days, after the first 10 minutes | Nothing special: swaps run at the base fee (0.30%) |
| **CLOSED** | Nights, weekends, holidays | Three defenses: (a) a **fee that ramps up** the longer the market is dark (1.00% at the bell, +0.03%/hour, capped 3.00%) — the compensation LPs currently don't get; (b) **per-swap and per-block value caps** — you cannot dump through a thin weekend pool; (c) an optional **price band** around the snapshotted closing price — an on-chain limit-up/limit-down |
| **AUCTION** | The first 10 minutes after each open | Continuous swaps are **frozen**. Orders escrowed during the closed period settle in one batch: matched buy/sell interest crosses internally at the pre-open price, only the net imbalance touches the pool, everyone on a side gets one uniform price. The Monday race becomes a fair opening auction |

The single most important design idea: **the phase machine is stateless.** The hook never stores "we are now closed." It recomputes the phase from the timestamp every time, using pure on-chain date math (including US daylight-saving rules). Stateless means nothing to keep in sync, no keeper to bribe or forget, and no state to corrupt.

## Map of the codebase

```
src/
├── MarketHoursHook.sol      612 lines — the hook: phase machine, fees, caps,
│                            price band, and the full reopening auction
└── libraries/
    └── NYSECalendar.sol     ~105 lines — pure date math: civil-date algorithms,
                             US DST rules, ET conversion, session boundaries
test/
├── MarketHoursHook.t.sol    30 tests — every phase, fee, cap, band and the whole
│                            auction lifecycle, plus fuzzed conservation proofs
└── NYSECalendar.t.sol       7 tests — DST switch minutes, weekdays, round-trips
script/
├── 00_DeployHook.s.sol      CREATE2 address mining + deployment
├── 01_CreatePool...s.sol    creates the dynamic-fee pool + liquidity
└── testing/                 local-chain V4 stack + demo tokens
demo/
└── index.html               a single-file control panel: phase clock, time
                             machine, swaps, and the auction lifecycle
```

## Reading order for this book

1. `01` — the concepts: dynamic fees, LVR, batch auctions, flash accounting, and why on-chain date math is harder than it looks
2. `02` — `NYSECalendar.sol` line by line
3. `03` — `MarketHoursHook.sol` part 1: phases, fees, caps, the band
4. `04` — `MarketHoursHook.sol` part 2: the reopening auction (the crown jewel)
5. `05` — every test and what it proves
6. `06` — deployment and the demo UI

## The one sentence to keep

**A tokenized-stock pool without market hours is a scheduled weekly donation from LPs to the fastest bot — this project gives the pool the three things the NYSE spent a century inventing (a calendar, a circuit breaker, and an opening auction), computed statelessly from `block.timestamp` inside one hook.**
