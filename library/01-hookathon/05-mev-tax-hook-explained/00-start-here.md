# 00 — Start Here: What the MEV-Tax-for-LPs Hook Is and Why It Exists

Goal: understand the problem, the almost-magical mechanism that solves it, why it only works on one chain, and the political twist that makes this project's positioning write itself.

## The problem: LPs pay for everyone's lunch

Every AMM pool leaks money in one specific direction. When the "true" price of an asset moves on some faster venue (a CEX, another chain), the pool still quotes the old price for a moment — and the first arbitrage bot to trade against it captures the difference. Multiply by every price move, every day, forever: this is **LVR (loss-versus-rebalancing)**, the systematic bleed from passive LPs to arbitrageurs. Research keeps finding that for volatile pairs, swap fees usually don't cover it. LPs subsidize the whole system.

Then it got worse. In December 2025, Uniswap governance passed **UNIfication**: the protocol now takes roughly a quarter to a sixth of LPs' fee income to buy and burn UNI. Great for UNI holders; a straight pay cut for the people who were already the system's least-compensated participants. If anything in 2026 helps LP income, it swims with a strong current.

## The mechanism: the bot's bid is a confession

Here's the beautiful idea, from Paradigm's paper *"Priority Is All You Need"* (the **MEV tax**):

When an arbitrage opportunity appears, *many* bots see it simultaneously. Only the first transaction in the block captures it. So bots compete for position — and on a chain ordered by priority fee, that competition is an **auction**: each bot bids up its priority fee until bidding more would eat the whole profit. Competition forces the winner's bid toward the value of the opportunity itself.

Which means: **`tx.gasprice - block.basefee` — the priority fee — is a truthful, self-reported estimate of how much MEV this transaction is about to extract.** A normal user, who has no race to win, bids approximately zero.

The MEV tax reads that confession and charges accordingly: an extra fee proportional to the priority fee. Bots pay in proportion to their profit; users pay nothing. No oracle, no ML classifier of "toxic flow", no allowlist — the attacker's own bid is the evidence.

## Why now, and why only Unichain

On Ethereum mainnet this doesn't work: block builders don't have to order by priority fee, so a bot could bribe its way to the top through side channels while showing a zero priority fee on-chain. The tax needs **provable priority ordering**.

That's exactly what Unichain shipped in 2025: **Flashblocks** — ~200-250ms sub-blocks built inside TEEs (trusted hardware) that *provably* order transactions by priority fee. The moment that went live, the MEV tax stopped being a paper and became a buildable primitive. Almost nobody has built on it — most UHI cohorts predate it. Freshest mechanism in the ecosystem, nearly empty field.

## The twist: who gets the money

Uniswap Labs' own version of this idea exists — the PFDA in UNIfication — and it uses the captured value to **burn UNI**. This hook is the ideological counter-position: the same mechanism, but the proceeds go to the pool's **LPs** — the people the MEV was extracted *from*. And through a specific technical channel with a political property: `PoolManager.donate` sends value directly to in-range LPs as fee growth, and **donations are not swap fees, so the UNIfication fee switch never touches them**. 100% to LPs, structurally.

"The LP-first MEV tax." One line, complete positioning.

## The shape of the solution

One compact hook, `MevTaxHook` (~90 lines of logic):

1. `beforeSwap` reads `priorityFee = tx.gasprice - block.basefee`.
2. Computes `taxPpm = min(k × (priorityFee − exemption), cap)` — linear above an exemption threshold (so ordinary users with habitual small tips pay *literally zero*), hard-capped (so the tax can never eat a swap).
3. Charges the tax via a **`beforeSwapReturnDelta`** — the swapper pays `taxAmount` extra of the swap's specified token.
4. **Donates the exact same amount to in-range LPs in the same callback.** The delta credit and the donate debit cancel inside the flash-accounting lock — the hook never holds, transfers, or approves a single token. There is **no ERC20 code in the contract at all**.

That last property is a post-Bunni feature worth advertising: a hook that *cannot* hold funds cannot lose them.

## Map of the codebase

```
src/
└── MevTaxHook.sol         ~240 lines total, ~90 of logic — the whole mechanism
test/
└── MevTaxHook.t.sol       14 tests — tax math, donation accounting, LP collection,
                           exact-output, caps, fuzzed formula-matching
script/
├── 00_DeployHook.s.sol    CREATE2 mining + deployment with tax defaults
└── testing/               local V4 stack + mWETH/mUSDC demo tokens
demo/
└── index.html             priority-fee slider, live tax preview, swap simulator,
                           MevTaxCharged event feed
```

## Reading order for this book

1. `01` — concepts: MEV auctions, priority ordering, `donate`, return deltas, flash accounting
2. `02` — the contract line by line
3. `03` — the tests and what each proves
4. `04` — deployment and the demo

## The one sentence to keep

**Under provable priority ordering, an arbitrageur must publicly bid away its profit to win the race — this hook reads that bid in `beforeSwap`, charges a proportional tax through a return delta, and donates every wei to in-range LPs inside the same transaction, turning the exact money that used to be LP loss into LP income, with zero tokens ever passing through the hook itself.**
