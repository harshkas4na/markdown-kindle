# 07 — The Competition, Explained Like You're New to This

Chapters 05 and 06 are the dense, technical version of the research — good for reference, bad for a first read.
This chapter says the same things in plain language, with analogies, so the *meaning* actually lands.

## First, what problem are we even solving?

Imagine a farmers' market with one fruit stall. The stall's price for apples updates slowly — say, once a minute.
Meanwhile, the "real" price of apples (what every other market in town is charging) changes every second.

Now imagine there's a group of professional traders standing at that stall with phones, watching the real price
everywhere else. The instant the real price moves and the stall's price becomes stale — even for two seconds —
one of them buys up the cheap apples and instantly resells them elsewhere for guaranteed profit. This happens
constantly, all day, every day. The stall owner never notices any single theft, but at the end of the year, the
stall's owner (the person who supplied the apples — that's the LP, the liquidity provider) has quietly lost a
meaningful chunk of the money they should have made, to people who did nothing except being fast and paying
attention. That constant, structural leak is called **LVR (loss-versus-rebalancing)**. It's not a hack, not a bug —
it's just built into how automated markets work, and it is the single biggest reason providing liquidity on Uniswap
is less profitable than it looks on paper.

The second, more visible version of the same idea is a **sandwich attack**: a trader sees your trade about to
happen (because pending transactions are public before they're confirmed), buys right before you to push the
price against you, lets you get a worse price, then sells right after and pockets the difference. Same family of
problem (someone profiting off information/speed you don't have), but this one specifically targets *you*, not the
pool in general.

Every project discussed below is trying to solve one or both of these two problems.

## The six "families" of solution — with an analogy for each

Across 126 previous hackathon projects that tackled MEV/LVR, every single one falls into one of six strategies.
Think of them as six different answers to "how do we stop the fast traders from draining the stall":

1. **"Charge more when it smells like a professional trade."** (Dynamic/directional fees) — the stall raises its
   price slightly whenever a trade looks suspicious (moves the price a lot, or disagrees with an outside reference
   price). ~30 projects did some version of this.
2. **"Sell the right to be first."** (Auctions) — instead of letting anyone race to be first, the stall holds a
   quick auction each round: "who wants to be the only one allowed to trade against me right now?" Whoever pays
   the most for that privilege, that money goes back to the stall owner. ~15 projects.
3. **"Hide the trade until it's already happened."** (Encryption/FHE) — the stall can't tell what anyone is buying
   or selling until after the sale is final, so nobody can race to beat anyone else, because there's nothing to
   see. Over 40 projects — the single biggest group — built some version of this using an encryption technology
   called FHE.
4. **"Match buyers and sellers directly, skip the stall entirely."** (CoW / batching) — if someone wants to buy
   apples and someone else wants to sell the exact same amount at the same moment, just let them trade with each
   other directly and skip the stall (and the fast traders) altogether. ~20 projects.
5. **"Notice who's racing, and tax them specifically."** (Priority-fee-aware fees) — **this is our family.** Watch
   how much extra a trader is willing to pay just to go first (their "priority fee" / gas tip), because that number
   is a dead giveaway that someone's racing for a prize. Charge them in proportion to how badly they wanted to be
   first. ~5 projects, including us.
6. **"Break big trades into tiny pieces over time."** (TWAMM) — instead of one big trade that's an obvious, juicy
   target, spread it out into hundreds of tiny trades over hours, so there's nothing worth racing for at any single
   moment. ~5 projects.

## Why "watch who's racing" (family 5) is special right now

Here's the part that makes our timing lucky rather than clever: **families 2, 3, 4, and 6 all require extra
infrastructure** — an auction system, an encryption coprocessor, an off-chain matching engine, a batching
scheduler. **Family 5 requires almost nothing** — just reading a number (`tx.gasprice - block.basefee`, the
priority fee) that's already sitting in every transaction. It's the cheapest, simplest mechanism on the entire
list.

The catch, historically, is that this number used to be a rumor, not a fact. On most blockchains, a trader could
quietly pay a block-builder off the books to jump the queue, while showing a low, innocent-looking priority fee
on-chain — meaning "watch the priority fee" was watching a lie. That's why almost nobody built a serious version of
family 5 before now: the signal wasn't trustworthy.

**Unichain changed that in 2025.** It introduced something called Flashblocks, which orders every transaction
strictly by priority fee, and does so *inside a sealed, tamper-evident piece of hardware* (a "TEE") that
cryptographically proves it followed that rule. There is no longer a back door — the priority fee genuinely is the
only way to buy your place in line. The moment that shipped, the signal became trustworthy, and family 5 stopped
being "probably useful" and became "provably useful." Our hook is built on that exact guarantee.

## Who's closest to us, and how they're actually different

- **"Priority is all you need" (UHI4)** raises the *pool's regular swap fee* when priority fees look high. That
  fee then flows through Uniswap's normal fee-collection path — which today means a slice of it gets skimmed off
  by Uniswap's own protocol fee switch before LPs ever see it. Our hook instead pulls the tax out *separately*
  from the swap and hands it straight to LPs via a special "donation" function that the protocol fee switch can't
  touch. Same idea, different plumbing — and the plumbing difference means 100% reaches LPs instead of a partial
  share.
- **DAMM and "Dynamic Fees for MEV Mitigation"** try to *detect* MEV using pattern-matching or user history, which
  means they need to store data about traders over time and can be fooled or miscategorize people. We use one
  clean, stateless number per transaction — nothing to store, nothing to fool.
- **EvenFlow (from this year's UHI9 cohort)** is the closest philosophical cousin: it also collects a surcharge and
  gives it back to LPs. But EvenFlow's money sits in a holding reserve until *something* triggers its release, and
  the team discovered a real bug in their own design: if the market goes quiet and nobody trades, there's nothing
  to trigger the release, and the money gets stuck. They had to bolt on an entirely separate automation system
  (Reactive Network, a "cron job that lives on the blockchain") just to fix that. Our hook never has this problem,
  because we never hold the money in the first place — the tax and the payout to LPs happen in the *same single
  instant*, inside the same transaction. There's no reserve to get stuck, because there's no reserve at all.
- **Uniswap's own PFDA** (live in 2026, part of a big protocol update called UNIfication) does something
  structurally similar to family 2 (auctions) at the protocol level, and takes the winnings to **buy and burn
  UNI**, the Uniswap governance token. That's good for people who hold UNI. It is *not* money that goes to LPs. Our
  hook is the direct philosophical opposite: same category of "capture value that would otherwise leak to bots,"
  completely different destination for the money — LPs, the people whose capital was actually used, instead of a
  token burn that benefits a different group entirely.

## The one thing nobody else has done

No project in this whole 126-project dataset, and nothing found from this year's UHI9 or UHI10 cohorts, combines
all three of: (1) no oracle, no off-chain infrastructure, (2) the tax and the LP payout happening atomically in one
transaction so nothing ever sits inside the contract, and (3) doing it on a chain where the underlying signal
(priority fee = true race intensity) is cryptographically guaranteed rather than merely likely. That combination —
simple, safe, and provably true — is the actual competitive edge, and it only exists because Unichain's Flashblocks
are new enough that almost nobody has built on top of them yet.
