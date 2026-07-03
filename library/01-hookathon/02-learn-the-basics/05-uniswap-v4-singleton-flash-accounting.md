# 05 — Uniswap v4: The Singleton + Flash Accounting Rewrite

Goal: understand the plumbing change v4 made *before* it added hooks — because hooks only became cheap and practical to use once this rewrite happened. This is the "why did they even need a new version" article.

## Recall the v2/v3 problem: every pool is its own contract

From article 3: in v2 (and v3 kept this pattern), every single trading pair — ETH/USDC, DAI/USDC, a hundred others — is deployed as its own, entirely separate smart contract. Separate contract means separate storage on the blockchain, and critically, it means every trade that touches that pool has to physically **transfer tokens in and out of that specific contract's balance.**

**Analogy: imagine a mall where every single store is its own separate building, on its own separate plot of land, each with its own loading dock.** If you want to buy a shirt from Store A and then walk next door to buy shoes from Store B, in a normal mall you'd just walk between them. But in this weird version of the mall, every purchase requires a truck to drive your money from your house, into Store A's private loading dock, do the transaction, then a *separate* truck trip carries your remaining money to Store B's separate loading dock. Every hop between stores costs you a full truck trip (gas), even though logically you're just "shopping in the mall."

That's what a multi-hop trade across several v2/v3 pools actually costs: real token transfers, in and out, at every single pool along the route, each one its own gas-costing operation.

## The v4 fix: one giant contract for every pool (the "Singleton")

Uniswap v4 throws out "one contract per pool" entirely. Instead, there is **one single contract — called the PoolManager — that holds every single pool's liquidity inside it**, tracked as internal accounting entries (just numbers in a ledger), not as separate token balances scattered across a hundred different contract addresses.

**Same mall analogy, fixed**: now imagine the mall is one single building. Store A and Store B are just different counters inside the same building, sharing one back-office ledger. When you buy a shirt then shoes, the mall's internal ledger just updates two line items — "customer owes $20 less, has 1 shirt and 1 pair of shoes" — no trucks required until you actually leave the building at the very end, at which point one single settlement happens.

This is the **singleton pattern**: one contract, tracking every pool's state as internal bookkeeping, instead of many separate contracts each managing their own physical token balances.

## Flash accounting: why this saves so much gas

Because everything lives in one ledger, v4 can do something v2/v3 architecturally couldn't: let an entire multi-step trade happen as pure internal number-updates, and only move actual tokens once, right at the very end, to settle the net difference. This is called **flash accounting** (sometimes described via v4's internal concept of a running balance called a "delta").

Concretely: if your trade route touches five different pools inside the PoolManager, v4 doesn't transfer tokens after each of the five hops — it just updates five internal ledger entries, then checks at the very end that everything nets out to zero (you can't walk away owing the contract money, or the transaction reverts), and only then does the *one* real token transfer that settles your final net position. Fewer real token transfers = dramatically less gas for anything that touches multiple pools, which turns out to be almost everything, once hooks are involved.

## Why hooks specifically needed this rewrite

Here's the connection that makes this article matter for the rest of the directory: a hook is code that runs *in addition to* a normal swap — checking a condition, updating some tracking variable, maybe even doing its own mini-trade before or after yours. Under the old "every pool is a separate contract with real token transfers" model, every one of those extra hook operations would mean *more real token transfers*, and gas costs would explode combinatorially with every hook you stacked on. Under the singleton + flash accounting model, a hook's extra logic can just add a few more lines to the same internal ledger and let it all net out in one final settlement — making hooks *actually affordable* to use in practice, not just theoretically possible.

## The one sentence to keep

**Uniswap v4 replaced "one contract per pool, with real token transfers at every hop" with "one giant contract holding every pool as internal ledger entries, settling real tokens only once at the very end" — and this single architectural change (not the hooks themselves) is what made it cheap enough to let arbitrary custom code run on every single swap, which is the precondition the entire hook ecosystem in this directory depends on.**
