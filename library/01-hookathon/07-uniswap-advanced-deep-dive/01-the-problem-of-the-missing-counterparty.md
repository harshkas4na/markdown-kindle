# The Problem of the Missing Counterparty

**Fast overview:** every trade needs someone on the other side. Traditional markets solve this with professional market makers running order books. On early Ethereum that job was impossible, so Uniswap replaced the market maker with a formula and a pot of tokens. This chapter builds the intuition for *why* that works, by first understanding what a market maker actually does — because every later concept (fees, slippage, impermanent loss, LVR, hooks that fight LVR) is a re-appearance of some classic market-making idea in mathematical clothing.

## What a market maker actually does

Suppose you want to sell 10 ETH *right now*. Who buys it? Almost never another person who coincidentally wants exactly 10 ETH at exactly this second. Instead, a **market maker** buys it from you — not because they want ETH, but because their business is to *always* stand ready to trade.

A market maker quotes two prices:

- a **bid** — the price at which they'll buy from you (say $2,995)
- an **ask** — the price at which they'll sell to you (say $3,005)

The gap is the **spread**, and it is their paycheck. Buy at 2,995, sell at 3,005, pocket $10 per ETH — *if* they can do both sides quickly. That "if" hides the two risks that define the whole profession:

1. **Inventory risk.** After buying your 10 ETH, the market maker *holds* 10 ETH. If ETH drops before they offload it, the spread income is wiped out. So they manage inventory constantly, adjusting quotes to shed whatever they have too much of. A market maker overloaded with ETH will lower both bid and ask — discouraging more sellers, attracting buyers — until inventory rebalances. **Remember this reflex: price moves against the side that's piling up.** The constant-product formula will turn out to be exactly this reflex, hard-coded.

2. **Adverse selection.** The scarier risk. Some counterparties know something. If a trader has just seen news that hasn't hit the price yet, they will happily lift the market maker's stale quote, and the market maker loses the full difference. Professionals call flow from informed traders **toxic flow**. Every market maker in history has faced the same dilemma: quote tight spreads and get picked off by the informed, or quote wide spreads and lose the uninformed customers to competitors. **This exact dilemma, translated into DeFi, is called LVR — and fighting it is what half of the advanced hooks in this book do.** We meet it properly in Chapter 5.

The classic result that makes this precise is the Glosten–Milgrom model (1985): the spread exists *because* of adverse selection — spread income from uninformed traders must cover losses to informed ones. Hold that thought for four chapters.

## Why this job didn't work on-chain in 2017

An order book is a list of resting bids and asks with price-time priority. Running one requires the market maker to:

- post, cancel, and re-post quotes constantly (hundreds of times a second on active markets),
- react to external price moves in milliseconds,
- pay nothing (or nearly nothing) per action.

Now put that on 2017 Ethereum: ~15-second blocks, every cancel and re-quote a gas-costing transaction, ordering within a block decided by miners. A quote you can't cancel for 15 seconds is a free option handed to everyone who watches the mempool. On-chain order books (EtherDelta and friends) existed and were dreadful: thin, stale, clunky. The professional market maker simply could not exist in that environment.

So the question became: *can you get the economic function of a market maker — continuous two-sided quotes, inventory that self-manages — without anyone actively doing anything?*

## The formula as market maker

Vitalik Buterin sketched the answer in a 2016 forum post; Hayden Adams, a laid-off mechanical engineer learning Solidity, built it and shipped Uniswap v1 in November 2018. The design:

- A pool holds reserves of two assets: `x` units of one token, `y` of the other.
- Anyone may trade against the pool, but the trade must preserve the invariant `x · y = k` (v1 paired ETH with one ERC-20; v2 generalized to any pair — Chapter 3).
- Anyone may become a **liquidity provider (LP)** by depositing both tokens in the current ratio, receiving shares of the pool.

Check it against the market maker's job description:

- **Always quotes.** The price is just the reserve ratio, `P = y / x` (we derive why in Chapter 2). Reserves always exist, so a quote always exists — for any trade size, at any hour, with zero human attention.
- **Manages inventory by reflex.** Buy ETH from the pool and ETH reserves fall, so ETH's price *rises* — exactly the professional's inventory reflex, enforced by algebra rather than judgment. The more one-sided the flow, the more the price moves against it.
- **Earns a spread.** A fee (0.3% in early versions) is taken on every trade and left in the pool, accruing to LPs. That's the spread income.
- **Suffers adverse selection.** And here the formula inherits the profession's curse too, in aggravated form: the formula *never updates on news*. It only moves when someone trades. Whoever trades first after news moves the market picks off the stale quote — and unlike the human, the formula can't widen its spread when it smells danger. Filing this away is the single most important setup for Chapter 5.

The philosophical shift is worth savoring. An order book *discovers* price from the stream of human quotes. A constant-product pool *dictates* execution price from its own inventory and relies on arbitrageurs to drag it toward the wider market's truth. Uniswap outsourced price discovery — and paid for the outsourcing in LP losses. Nearly a decade of AMM research, and most of the hook designs in Chapters 9 and 12, are attempts to renegotiate that deal.

## Why "lazy liquidity" won anyway

Given that flaw, why did Uniswap crush the on-chain order books? Because it matched the medium:

- **Passive by design.** LPs deposit and walk away. No servers, no quoting engine, no reaction time. The formula *is* the strategy. This unlocked a workforce no order book could touch: ordinary token holders.
- **O(1) state.** A trade updates two reserve numbers. No book to store or match — a few storage slots, ideal where storage is the dominant cost.
- **Permissionless listing.** Any ERC-20 pair could have a market in one transaction, no exchange listing committee. The long tail of tokens — the majority of all trading pairs in existence — got liquid for the first time.
- **Composability.** One `swap()` call, callable by any contract. Aggregators, lending liquidations, and yield protocols could all treat Uniswap as a money lego. Order books offer no such single-call guarantee.

By 2020's "DeFi summer," the AMM was the default venue for the long tail, and increasingly for majors. The costs — slippage on size, impermanent loss, MEV — were real, growing, and are precisely the plot tension the rest of this book resolves.

## Connect the dots forward

Three ideas from this chapter run through everything that follows.

1. **Price moves against inventory** → that is literally the curve. Chapter 2 turns the reflex into calculus.
2. **Adverse selection / toxic flow** → becomes LVR in Chapter 5, and motivates dynamic-fee hooks (Chapter 9), the am-AMM and Angstrom (Chapter 12).
3. **Passivity as a feature** → v3 (Chapter 4) partially walks it back, demanding active range management from LPs. Hooks (Chapters 7–8) let pool designers re-automate that activity. The whole arc of AMM history is a negotiation over *how much work liquidity should have to do*.

Next: the two-line formula, and everything hiding inside it.
