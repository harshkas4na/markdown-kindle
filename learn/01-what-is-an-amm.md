# 01 — What is an AMM

Goal: understand, in one sitting, why decentralized exchanges don't use an order book, and what problem the "constant product formula" is actually solving. Everything in the Hookathon dataset (dynamic fees, MEV protection, LVR, all of it) is a modification bolted onto this one core idea — so if this doesn't click, nothing after it will either.

## Start with the actual problem, not the formula

On a normal exchange (Binance, NYSE, whatever), when you want to buy something, the exchange matches you with someone who wants to sell it, at a price you both agree to. That's an **order book** — a big list of "I'll sell at this price" and "I'll buy at this price," sorted, matched automatically.

This works great when there are lots of buyers and sellers constantly posting orders. It works terribly on a blockchain, because posting and canceling an order book entry costs gas (real money) every single time, and someone has to be running matching-engine software 24/7 that's fast enough to not get front-run. Nobody wants to be the market maker sitting there manually.

So Uniswap asked a different question: **what if there's no matching at all — what if you just trade against a pool of tokens, and a formula decides the price?**

## The pool, and the formula

Picture a box. Inside the box sits some amount of Token A and some amount of Token B — say, 10 ETH and 20,000 USDC. That's the entire "market." No buyers, no sellers, no order book. Just this box, sitting there, and anyone can trade against it.

Now: what price should the box charge you if you want to buy 1 ETH from it?

Uniswap's answer is the **constant product formula**:

```
x * y = k
```

Where `x` is how much ETH is in the box, `y` is how much USDC is in the box, and `k` is a number that the box insists must never change, no matter what trade happens.

So if you put USDC into the box and take ETH out, the box will let you — but only exactly enough ETH so that `x * y` still equals the same `k` as before. Take out more ETH than that, and the box won't allow it, because `k` would drop.

Walk through the actual numbers: 10 ETH * 20,000 USDC = 200,000 = `k`. You want to buy 1 ETH. The box now has 9 ETH left. For `k` to still be 200,000, `y` must become 200,000 / 9 = 22,222.22 USDC. So the box demands you deposit 2,222.22 USDC to get that 1 ETH out. Notice: that's a *worse* price per ETH (2,222 USDC) than the "starting" implied price (2,000 USDC per ETH). The box automatically charged you more because you're taking a meaningful chunk of its ETH.

That "price gets worse the more you take" behavior is called **slippage**, and it isn't a bug or a fee — it falls directly out of the formula. It's the formula's way of saying "the more scarce something becomes in this box, the more expensive it gets to take more of it," which is a rough digital echo of real supply and demand, without anyone setting a price by hand.

## Why "constant" product, specifically

You could imagine other rules — `x + y = k` (constant *sum*) would mean every trade happens at a perfectly flat 1:1 rate no matter how much you buy, with zero slippage. That sounds nicer, until you realize: it means the box will happily sell you *all* of its ETH for a fixed price, even down to zero ETH left, if you bring enough USDC. That box can be completely drained. (This constant-sum idea isn't useless, by the way — it's exactly what you want for two assets that truly should always be worth the same amount, like two stablecoins. More on that later.)

The constant-*product* curve, by contrast, is a curve that gets steeper and steeper as one side of the box gets thinner — mathematically, it can never fully run out of either token, because taking the last drop would require infinite payment. That self-protecting shape is the entire reason Uniswap chose it as the default: it can't be drained, no manual price-setting is required, and it works for any token pair on day one with zero configuration.

## Where the "market" comes from at all

Here's the part that trips people up: if the box just mechanically follows a formula, how does its price ever match the *real* price of ETH (what it's trading for on Binance, say)?

Answer: it doesn't, automatically — **arbitrageurs make it match**. If the box's formula says ETH is worth 2,100 USDC, but the real world says ETH is worth 2,000 USDC, then anyone can buy ETH for 2,000 USDC elsewhere and sell it into the box for 2,100 USDC, pocketing the 100 USDC difference — and doing that trade pushes the box's ratio back toward 2,000, because you're adding ETH and removing USDC from it. Bots do this within seconds, automatically, every time the box's implied price drifts from the outside world. That's the mechanism that keeps a completely dumb, formula-only box roughly honest.

Hold onto that last idea — it's the seed of almost every "MEV" and "LVR" problem you'll read about later in this directory. Arbitrage keeps the pool honest, but it does so *at the liquidity provider's expense* — every time an arbitrageur profits off the box, that profit came out of the box, which means it came out of whoever deposited tokens into it. That's article #2.

## The one sentence to keep

**An AMM is a box holding two tokens, governed by a formula that decides the exchange rate as a function of what's currently inside it — no order book, no market maker, and the "market price" only stays accurate because outside arbitrageurs are constantly nudging the box back into line, for a profit.**

Everything else — concentrated liquidity, dynamic fees, hooks — is a modification to *how the box decides the rate*, or *what happens right before/after a trade touches the box*. The box itself, underneath it all, is still just holding two numbers and enforcing a formula.
