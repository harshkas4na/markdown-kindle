# 03 — Uniswap v2 Architecture

Goal: go from "the box" as a concept to the actual three-contract system Uniswap v2 shipped, so that when v3 and v4 change things, you know exactly what changed and why.

## Three contracts, three jobs

Uniswap v2 is built from three kinds of smart contracts, each with one job:

**1. The Pair contract — this is literally "the box" from article 1.** Every single token combination (ETH/USDC, DAI/USDC, whatever) gets its own, separate Pair contract deployed. Each Pair holds exactly two tokens, enforces `x*y=k`, mints/burns LP tokens, and takes the 0.30% fee. It has no idea any other pair exists. It's a dumb, self-contained box.

**2. The Factory contract — the box-maker.** When someone wants to create a brand-new trading pair that doesn't exist yet (say, the first ever DOGE/SHIB pool), they call the Factory, which deploys a new Pair contract for that combination and keeps a registry — a lookup table — of "which address is the DOGE/SHIB Pair contract." Think of the Factory as a landlord who builds a new vending machine on demand whenever someone asks for a snack combination that doesn't have one yet, and keeps the master list of "machine #4 sells DOGE for SHIB, machine #7 sells ETH for USDC."

**3. The Router contract — the front desk.** You, as a regular user, are not supposed to talk to a Pair contract directly — it's a low-level, minimal contract, and using it wrong can lose you money (e.g. it won't stop you from getting terrible slippage if you don't set limits yourself). The Router is a helper contract that does the safe, ergonomic version of "swap my ETH for USDC": it calculates the expected output, lets you set a minimum-acceptable-output as slippage protection, and — crucially — it can **chain multiple Pairs together**. If there's no direct DOGE/SHIB pool but there is a DOGE/ETH pool and an ETH/SHIB pool, the Router can silently route your trade through ETH as an intermediate hop, so it still looks to you like one simple swap.

## Why this three-way split matters

Notice what this buys Uniswap: the Pair contracts are as simple and minimal as possible (fewer lines of code = fewer bugs = safer to trust with your money), while all the user-friendly complexity (routing, slippage math, multi-hop paths) lives in the replaceable Router layer. If Uniswap wants to ship a smarter Router later with better routing logic, they can, *without touching a single already-deployed Pair contract holding real money.* Separation of "the vault" from "the front desk" is a recurring pattern you'll see reused, in spirit, all the way through v4's hook system.

## A concrete walk-through

Say you want to swap 1 ETH for USDC:

1. You call the Router's `swapExactETHForTokens` function, specifying "at least 1,950 USDC or revert the whole transaction" (your slippage protection).
2. The Router asks the Factory "what's the address of the ETH/USDC Pair?"
3. The Router sends your ETH into that Pair contract.
4. The Pair contract runs the `x*y=k` math, calculates your USDC output, and sends it back — not to the Router, but directly to your wallet.
5. If the calculated output would have been less than 1,950 USDC, the entire transaction reverts (undoes itself) before any money moves, and you just lose a bit of gas, not your funds.

## What v2 is missing (setting up v3 and v4)

Two real limitations of this design become the whole story of what comes next:

- **Every Pair holds liquidity across the *entire* possible price range**, from 0 to infinity, even though realistically ETH/USDC is never going to trade near $0 or near $1,000,000. That means most of the capital sitting in the box is doing basically nothing, because trades only ever happen in a narrow price band anyway. This "wasted capital" problem is exactly what Uniswap v3's concentrated liquidity fixes (article 4).
- **Every single Pair is a fully separate contract deployment.** A hundred different pools means a hundred different contract addresses, each with its own storage, each needing its own token transfers in and out for every trade — which is expensive in gas, and makes it structurally impossible to customize *how* an individual pool behaves beyond the one fixed formula every Pair shares. There's no way to say "this one pool should have a custom fee rule" — the code is identical for every pool. Fixing *that* limitation, years later, is the entire reason hooks (article 6) needed a rewritten core (article 5) to exist at all.

## The one sentence to keep

**Uniswap v2 is three contracts with clean separation of concerns — dumb, minimal Pair boxes holding the money; a Factory that deploys new boxes on demand; and a Router that gives users a friendly, safe, multi-hop interface — and its two big blind spots (capital spread across the whole price range, and identical unchangeable logic in every pool) are precisely the two problems v3 and v4 were each built, respectively, to solve.**
