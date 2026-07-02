# 07 — MEV & Sandwich Attacks

Goal: understand exactly, mechanically, how a sandwich attack works — not just "bots are bad" — because half the hooks in the MEV category are built to break one specific step in this sequence.

## Where a transaction lives before it's confirmed

When you submit a transaction (say, "swap 1 ETH for USDC"), it doesn't instantly happen. It first sits in a public waiting area called the **mempool** ("memory pool") — a holding area of pending transactions that every node on the network can see, waiting for a block producer to pick them up and include them in the next block.

**Analogy: the mempool is like a glass box sitting in the middle of a room where everyone has dropped their sealed envelopes containing "I want to make this trade," except the box is made of glass — anyone can read what's inside every envelope before it's opened.** Your trade intent is completely public for the (typically) 12-ish seconds before it's actually confirmed.

## The sandwich, step by step

Say the ETH/USDC pool currently sits at a price of $2,000/ETH. You submit a transaction to buy 5 ETH — a big enough trade that, per article 1's slippage logic, it'll noticeably move the pool's price upward as it executes (since you're pulling meaningful ETH out of the box).

A bot watching the mempool sees your pending transaction before it's confirmed and does exactly three things, packaged so they all land in the same block, in this exact order:

1. **Front-run**: the bot submits its own "buy ETH" transaction, paying a higher priority fee so it gets included *right before* yours in the same block. This buys ETH at the current $2,000 price, and — because it's also a real trade against the box — it pushes the price up a bit, say to $2,010.
2. **Your trade executes**: your original "buy 5 ETH" transaction now executes against this bot-inflated price, pushing the price up further still, to maybe $2,050. You get a noticeably worse average price than you would have gotten if the bot hadn't traded first.
3. **Back-run**: the bot immediately submits a "sell ETH" transaction, right after yours, which sells the ETH it just bought at $2,000 back into the now-inflated $2,050 pool — pocketing the difference as pure, essentially risk-free profit.

You are the "meat" and the bot's two trades are the "bread" — hence **sandwich attack**. You never see the bot. You just notice your trade executed at a worse price than the quote you were shown before submitting it, and you have no direct way of knowing whether that was normal slippage or a bot deliberately engineered it.

## Why this is even possible — the two enabling conditions

This attack only works because of two structural facts, both worth naming explicitly since different hooks attack different links in this chain:

1. **Transactions are visible before they're confirmed** (the mempool problem). If your trade's existence and direction were hidden until it was already final, a bot couldn't front-run something it can't see. This is exactly the gap that FHE- and ZK-based "private trading" hooks (see article 12) are aimed at closing.
2. **Block producers/validators choose transaction ordering, and can be paid to prioritize certain transactions.** MEV — Maximal Extractable Value — is the general name for any profit a block producer (or someone paying them) can extract purely from *choosing what order transactions execute in*, beyond normal fees. Sandwich attacks are the most famous specific example, but MEV is a broader category (it also covers things like liquidation-sniping in lending protocols, and the arbitrage described in article 1 — which, notably, is a *benign* form of MEV that keeps prices honest, versus a sandwich attack, which is purely extractive and adds nothing useful).

## How hooks try to fight back

Since a `beforeSwap` hook (article 6) can inspect the incoming trade before it executes, several strategies show up repeatedly in the directory:

- **Detect abnormally high priority fees** as a signal that a transaction is probably a bot racing to be first, and charge it a higher fee specifically (punishing the exact behavior that makes sandwiching profitable).
- **Dynamic fees that widen during high-volatility windows** — since a wider effective spread makes the "buy low inside the sandwich, sell high right after" profit margin thinner or negative.
- **Batch/match trades before they ever touch the pool** (the CoW — Coincidence of Wants — approach) so opposing trades cancel out privately instead of both hitting the public pool where they'd be sandwichable.
- **Encrypt the trade's contents until after commitment** (FHE-based hooks) so there's simply nothing for a bot to read and act on in the mempool.

None of these fully "solve" MEV — it's a much-studied, unsolved-in-general problem across all of Ethereum, not just Uniswap — but each approach closes off a different specific step in the three-step sequence above.

## The one sentence to keep

**A sandwich attack works because your pending trade is publicly visible before it's confirmed and block ordering can be paid for, letting a bot buy right before you (pushing the price against you), let your trade execute at the worse price, then sell right after for a guaranteed profit — and every "MEV protection" hook in this directory is really just trying to break one specific link in that three-step chain: visibility, ordering, or the profitability of racing you.**
