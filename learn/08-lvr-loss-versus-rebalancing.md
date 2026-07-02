# 08 — LVR (Loss-Versus-Rebalancing)

Goal: separate this cleanly from a sandwich attack (article 7) — LVR is a different, subtler, *structural* loss that happens even when there's no bot specifically targeting you, no malicious actor, nothing "wrong" happening at all. This is the one that has an actual named academic paper behind it, and it's worth being precise about.

## Start from what you already know: arbitrage keeps the box honest

Recall article 1: when the outside "real" price of ETH moves, arbitrageurs trade against the pool until the pool's implied price matches the outside price again. This is good — without it, the pool's price would just be wrong, permanently, and nobody could trust it.

But recall article 2: every one of those arbitrage trades is *profitable for the arbitrageur and a loss for the LP*, because the arbitrageur is, by construction, buying the pool's now-underpriced asset and selling the pool's now-overpriced asset — trading against the pool at a price that's stale relative to the new reality, and pocketing the gap.

**LVR is the name for this specific, structural, unavoidable-by-default loss: the value that leaks from LPs to arbitrageurs, purely because the pool's price always updates a little bit *after* the real world's price already moved, and someone gets to trade in that gap before the LP's price catches up.**

## Why this isn't the same thing as a sandwich attack

A sandwich attack (article 7) requires your specific pending trade to exist and be visible, and a bot deliberately targeting it. LVR requires none of that — it happens purely from the passage of time and price movement in the outside world, even if literally nobody trades against the pool except the one arbitrageur closing the gap. You could be an LP who never trades, whose pool sees only arbitrage flow and zero organic user trades, and you would still bleed LVR every time the external price moves, because the arbitrageur is *always* first-to-react by definition — that's the entire economic function they're performing.

**Analogy: imagine a currency-exchange kiosk at an airport that only updates its posted exchange rate once every hour, but the real global exchange rate is moving continuously.** In the 59 minutes between updates, anyone who happens to know the current real rate can walk up and trade against the kiosk's stale rate for a guaranteed profit — buying whichever currency the kiosk is currently under-pricing. The kiosk owner isn't being "attacked" by any one specific bad actor; they're just structurally always one step behind reality, and *someone* will always be there to collect that gap the instant it opens.

## The formal version (Milionis, Moallemi, Roughgarden, Zhang, 2022)

This intuition was formalized into an actual academic paper — "Automated Market Making and Loss-Versus-Rebalancing" — which proved, mathematically, that an LP in a constant-product pool earns strictly less than they would have earned from simply holding a "rebalancing portfolio" that tracks the same 50/50 value split without ever touching an AMM. The gap between "what the LP actually earned" and "what a hypothetical frictionless rebalancing strategy would have earned" is LVR, and the paper showed the gap grows larger the more volatile the asset is — which is exactly why every dynamic-fee hook wants to charge *more* fee precisely when volatility is high: to try to make the fee income outrun the LVR bleed.

## LVR vs. impermanent loss — aren't these the same thing?

Closely related, easy to conflate, worth being precise about the difference: **impermanent loss (article 2)** is the simple, static comparison — "what I'd have if I held my tokens" vs. "what I actually have in the pool right now," at any single point in time. **LVR** is a more refined, continuous-time framing that specifically isolates the piece of that loss caused by arbitrageurs reacting *faster* than the pool's own pricing can update — it's the "rate at which value leaks to arbitrage" rather than just the total loss snapshot. In practice, most people (including most hook project descriptions in this directory) use the two terms fairly loosely and interchangeably, but if you want to sound precise: IL is the symptom you can observe at withdrawal time, LVR is the mechanism/rate that causes it.

## How the directory's hooks try to address it

The two dominant strategies you'll see, both already previewed in earlier articles:

1. **Directional dynamic fees (Nezlobin-style)** — charge a higher fee specifically on trades that push the pool price *away* from a reference/oracle price (i.e., likely arbitrage trades), and a lower fee on trades that push it back toward the reference price (likely benign trades). This directly taxes the exact behavior that causes LVR, without needing to know in advance who's an arbitrageur and who isn't.
2. **Auction-managed AMMs (am-AMM)** — instead of trying to detect and tax arbitrage trade-by-trade, auction off the *right* to be the one who arbitrages the pool for a fixed time window to a single "manager," who pays rent for that privilege, and that rent gets distributed back to LPs. This effectively converts LVR from "leaked to anonymous bots for free" into "sold to the highest bidder, with the proceeds returned to the people who were losing money in the first place."

## The one sentence to keep

**LVR is the structural, unavoidable-by-default value that leaks from LPs to arbitrageurs purely because a pool's price always updates slightly after the real world's price already moved — distinct from a sandwich attack because it requires no malicious targeting and would exist even with zero organic trading, and it's the specific, formally-proven loss that directional dynamic fees and auction-managed AMMs are both explicitly engineered to claw back for LPs.**
