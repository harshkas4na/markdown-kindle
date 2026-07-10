# The Hidden Taxes — MEV, Sandwiches, and LVR

**Fast overview:** two invisible taxes drain AMM participants. Traders get taxed by **MEV** — bots that see pending transactions and trade around them (sandwiches). LPs get taxed by **LVR** — arbitrageurs who pick off the pool's stale prices every time the real market moves. This chapter makes both precise, quantifies them, and sets up the design space of defenses — because *the majority of economically interesting hooks are anti-MEV or anti-LVR devices*, and you can't evaluate them without this chapter.

## Part 1: MEV — the tax on traders

**MEV (maximal extractable value)** is profit extractable by whoever controls transaction *ordering* — originally miners, now validators and the builders they outsource to. Ethereum's mempool is public: your swap sits visible for seconds before inclusion, and its exact price impact is computable in advance (Chapter 2 gave you the formula — so it gives it to the bots too).

The canonical AMM attack is the **sandwich**:

1. Bot sees your pending buy of ETH with, say, 1% slippage tolerance.
2. Bot buys ETH first (front-run), pushing the price up your allowed 1%.
3. Your swap executes at the worse price — you buy the top.
4. Bot sells right after you (back-run), pocketing roughly your slippage tolerance minus fees.

Notes that matter for design work later:

- **Your slippage tolerance is the bot's budget.** Tight tolerance = smaller attack surface but more failed transactions; loose tolerance = smooth UX and guaranteed extraction. This dial has no good setting — the fix has to be structural.
- **Back-running alone is "benign" MEV**: arbitraging a pool back into line after a big trade doesn't hurt the trader who already executed — it hurts *LPs* (that's LVR, below). Front-running and sandwiching hurt the trader directly.
- **The supply chain professionalized.** Since Flashbots and MEV-Boost, most Ethereum blocks are assembled by specialized *builders* running sealed order-flow auctions; searchers bid priority fees for position within the block. MEV didn't disappear — it became an orderly market that redistributes extraction toward validators and (increasingly, via private order flow deals) back to users' wallets and front-ends.

Defenses a trader (or a hook designer) can reach for today: private transaction submission (skip the public mempool), batch auctions that give everyone in a block one uniform price (CoW Protocol, and Angstrom as a v4 hook — Chapter 12), or making the pool itself hostile to sandwich geometry (MEV-tax hooks; and note **your own MEV-tax hook book earlier on this shelf** — after this chapter, its design will read differently).

## Part 2: LVR — the tax on LPs

Now the subtler villain, the one from Chapter 1's adverse-selection cliffhanger.

An AMM's price moves only when someone trades against it. When ETH jumps on Binance from 3000 to 3100, the pool still quotes ~3000 until an arbitrageur pushes it to 3100 — buying from the pool below market all the way up. The arbitrageur's profit is the LP's loss: the pool sold ETH at an average of ~3050 that was worth 3100.

**LVR (loss-versus-rebalancing)**, from Milionis, Moallemi, Roughgarden, and Zhang (2022), names and prices this precisely. The trick is the right benchmark. Compare the LP not against HODLing (that comparison gives impermanent loss, Chapter 2) but against a **rebalancing portfolio**: a trader who holds *exactly the same inventory path* as the pool (x(t), y(t)) but executes every rebalance at the *true market price* instead of against the curve. The pool and this twin hold identical assets at every instant — the only difference is execution quality. The value gap is pure adverse selection:

```
LVR(t) = value of rebalancing twin − value of LP position ≥ 0, always growing
```

For constant-product pools the paper derives the famous closed form — instantaneous LVR as a fraction of pool value:

```
lvr = σ² / 8
```

where σ is the (log-)volatility of the price. Read it out loud: **an LP bleeds an eighth of variance per unit time, continuously, regardless of direction.** At 80% annualized vol (an ordinary year for ETH), σ²/8 = 0.64/8 = **8% of the pool per year**, before fees. Empirical studies during 2022–2023 put realized LVR for major ETH pairs around 5–7% of liquidity annually — often *exceeding* fee income, meaning passive LPs in those pools were net losers who felt fine because fees were visible and LVR wasn't.

Three properties to internalize:

- **LVR is IL's cleaner sibling.** IL mixes adverse selection with plain inventory drift and vanishes on round trips. LVR isolates the adverse-selection component: monotonic, non-recoverable, proportional to σ². (Chapter 2's `IL ≈ −(1/8)(Δln P)²` is the same 1/8 wearing a different benchmark — a satisfying dot to connect.)
- **LVR scales with staleness.** The loss accrues between the market moving and the pool being corrected. Faster correction (shorter blocks) = smaller mispricings captured by arbs = less LVR per unit time; this is why Unichain's 250ms flashblocks (Chapter 12) are an LVR intervention disguised as a UX feature.
- **Concentration multiplies it.** A v3 range position has more L per dollar (Chapter 4), so it trades more against every arb. Concentrated LPs earn more fees *and* pay more LVR — leverage on both sides of the same bet.

## Part 3: fees are a no-arbitrage moat

Where does the fee fit? An arbitrageur only corrects the pool when the mispricing exceeds the fee. So a fee `f` creates a **no-trade band** of width ±f around the true price: inside the band, arbs stay away and the pool drifts stale; outside, they snap it back to the band's edge. Consequences:

- Higher fee → wider band → fewer, larger arb events → less LVR, but also worse prices for real traders and less volume. The optimal fee *rises with volatility* and falls with how price-elastic your genuine flow is.
- One static number cannot be right for a stablecoin pair (σ ≈ 0) and an ETH pair (σ ≈ 80%) — v3's three tiers were a crude patch. **A fee that adapts to realized volatility in real time is one of the most natural hooks in existence** — Chapter 9 builds exactly that.
- Research from 2025–2026 formalizes this as a stochastic-control problem (optimal dynamic fees against LVR); the qualitative answer — raise fees when vol spikes, when flow turns toxic, or asymmetrically against the toxic direction — is implementable in ~200 lines of hook code today.

## Part 4: the defense design space (map for Chapters 9 and 12)

Every serious anti-LVR/anti-MEV mechanism in production or research falls in one of four families. Learn the taxonomy and you can classify any new hook in seconds:

| Family | Idea | Examples |
|---|---|---|
| **Reprice the option** | Charge more when being picked off is likelier: dynamic/volatility-scaled fees, asymmetric fees on the arb direction | dynamic-fee hooks (Ch. 9); Bunni v2's surge fees |
| **Sell the right to snipe** | If arbitrage profit is inevitable, auction it and pay the proceeds to LPs | am-AMM (auction the first-swap right per block), MEV taxes on priority fee, Arrakis diamond designs |
| **Remove the stale quote** | Update the pool's price from an oracle before arbs can hit it, or batch everyone at one uniform clearing price | oracle-priced pools, CoW AMM, Angstrom (Ch. 12) |
| **Shrink the window** | Faster blocks / ordering rules so quotes are less stale | Unichain flashblocks + priority ordering (Ch. 12) |

Notice what every row needs: the ability to *change the fee per swap*, *intervene before a swap executes*, or *replace pricing logic entirely*. v2 offered none of these. v3 offered none of these. **This is the demand side of the story — v4's hook system, next chapter, is the supply.**

One paragraph of honesty before we go there: none of these defenses is free. Auctions add latency and centralization surface; oracle pricing imports oracle risk; dynamic fees mis-tuned tax honest flow; batching fragments composability. The 2026 ecosystem (Chapter 12) is a live experiment over which costs users actually tolerate. Your job as a hook designer is not to eliminate the taxes — it's to choose better ones.
