# 02 — Liquidity, LP Tokens, Fees & Impermanent Loss

Goal: understand what it actually feels like, financially, to be the person who fills the box from article 1. This is the article that explains why "protect the LP" is the single most repeated phrase in the entire hook directory.

## Who fills the box, and why would they

Nobody trades against an empty box. Someone has to deposit the first ETH and the first USDC. That person (or, in practice, thousands of different people over time) is a **Liquidity Provider (LP)**. They aren't trading — they're not trying to buy or sell ETH. They're providing the *inventory* that lets other people trade, and in exchange, the protocol pays them a cut of every trade that touches the box. On Uniswap that cut is the swap fee — historically a flat 0.30% of every trade, handed to the LPs in proportion to how much of the box they own.

Think of it like being the person who owns the vending machine, not the person buying the snack. You don't care whether people buy Coke or Sprite today — you just want lots of purchases happening, because you get a slice of every purchase regardless of direction.

## LP tokens: your receipt for "I own X% of this box"

When you deposit into a pool, you don't get ETH-shaped or USDC-shaped tokens back — you get a completely different token, an **LP token**, which just represents "I own this fraction of the box." If you deposited 10% of the box's total value, you get an LP token representing 10% ownership. As trading fees accumulate inside the box, the box grows, and your 10% is now worth more (in v2-style pools; v3/v4 track fees a bit differently, but the ownership-receipt idea is the same). When you're done, you burn your LP token and the contract hands you back your proportional share of *whatever is currently in the box* — which is the part that gets interesting.

## Why "whatever is currently in the box" is the whole problem

Here's the trap: you deposited 10 ETH and 20,000 USDC (50/50 in value, ETH at $2,000). Now imagine ETH's real-world price doubles to $4,000 while you're sitting in the pool, doing nothing.

Arbitrageurs (from article 1) will have already pushed the box's ratio to match — they buy the now-underpriced ETH out of the box until the box's implied price also says $4,000. Because the box always rebalances to keep `x * y = k` constant, and the price is now double, the math works out to the box holding *less ETH and more USDC* than it started with — roughly 7.07 ETH and 28,284 USDC in this example (still worth the same `k`, but a different mix).

So when you withdraw, you don't get your original 10 ETH + 20,000 USDC back. You get roughly 7.07 ETH + 28,284 USDC — total value about $56,568.

Now compare: if you had just held the original 10 ETH + 20,000 USDC in your wallet and done absolutely nothing, that'd be worth 10 * $4,000 + $20,000 = $60,000.

You have less money than if you'd just held. That gap — $60,000 vs $56,568 — is called **impermanent loss (IL)**. It's called "impermanent" because if the price goes back down to where it started, the gap closes again (that's the "rebalancing" the arbitrageur did in reverse) — but if you withdraw while the price is still moved, the loss is very much permanent for you.

**The vending machine analogy again**: imagine your vending machine automatically re-stocks itself by always selling off whichever snack becomes suddenly more popular, and buying more of whichever snack becomes unpopular. If Coke suddenly becomes twice as valuable on the outside market, your machine will have quietly sold off most of its Coke for Sprite by the time you check on it — even though you, the owner, never asked it to make that trade. You didn't choose to sell your Coke. The formula chose for you, automatically, because that's the only way it knows how to keep quoting a fair price to walk-up customers.

## So why would anyone ever be an LP, then?

Because the fees you earn from all that trading volume can outweigh the impermanent loss — that's the entire bet an LP is making. If the pool sees enough trading volume, the 0.30% fee income adds up faster than the IL erodes your position. If the pool is quiet and the price is volatile, IL wins and you'd genuinely have been better off just holding the tokens.

This is the exact tension that almost every "dynamic fee" hook in the directory is trying to fix: **make the fee higher precisely when the price is moving a lot (when IL risk is highest), so LPs get compensated more exactly when they need it most, instead of a flat fee that doesn't know the difference between a calm day and a violent one.**

## The one sentence to keep

**Being an LP means constantly, automatically buying high and selling low relative to the outside market (because that's mechanically what keeping `x*y=k` requires as prices move), and you're betting that the fees you collect from traders outweigh that structural bleed — which is why almost every clever hook idea in this dataset is, underneath the branding, an attempt to tilt that bet back in the LP's favor.**
