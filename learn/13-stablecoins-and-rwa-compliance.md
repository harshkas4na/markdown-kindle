# 13 — Stablecoins & RWA Compliance Basics

Goal: the last article in the stack — tie together everything from articles 1-12 (curves, oracles, compliance-gating via hooks) into the two problem spaces (stablecoins, and real-world assets) that most directly determine whether DeFi ever connects to serious institutional money.

## Stablecoins: what "stable" actually means, and how it's enforced

A stablecoin is a token engineered to always be worth approximately $1.00 (or whatever it's pegged to). There are, broadly, three different ways this peg gets enforced, and it matters which one you're dealing with because they fail differently:

- **Fiat-collateralized (USDC, USDT)**: a company holds $1 in a real bank account (or short-term treasury bonds) for every token in circulation, and promises to redeem 1 token for $1 on demand. The peg holds as long as people trust that redemption promise. This is the type that depegged briefly in March 2023, when USDC's issuer Circle had a portion of its reserves stuck at the failing Silicon Valley Bank — not a flaw in the token's code, a real-world counterparty risk showing up.
- **Crypto-collateralized (DAI)**: backed by a surplus of *other* crypto assets locked in a smart contract (e.g. $150 of ETH locked to mint $100 of DAI), with automatic liquidation if the collateral value drops too close to the debt. The peg holds as long as the collateral liquidation mechanism works fast enough during a crash.
- **Algorithmic (mostly discredited after Terra/UST's 2022 collapse)**: attempts to maintain the peg purely through supply-and-demand incentive mechanisms, without full collateral backing. Worth knowing this category exists and why it's viewed with much more skepticism today — UST's collapse wiped out tens of billions of dollars and is the canonical cautionary tale anytime someone pitches a new algorithmic stablecoin design.

## Why a plain AMM pool is bad at stablecoin pairs

Recall article 1: a plain constant-product pool applies the same slippage curve regardless of what the two assets are — it doesn't "know" that USDC and USDT are supposed to always be worth the same amount, so it gives you the same amount of slippage on a USDC/USDT trade as it would on a genuinely volatile pair, which is unnecessarily bad for traders and unnecessarily inefficient for LPs. This is exactly why specialized curves exist (article-adjacent to `amm-curve-design.md` in the category files) — a Constant Sum or StableSwap-style curve gives near-zero slippage specifically *because* it assumes the two assets should trade near 1:1, right up until a real depeg happens, at which point that assumption needs a safety valve (dynamic, depeg-aware fees, as covered in the stablecoin category file).

## Real-World Assets (RWA): the other half of this category

Separately from stablecoins, **RWA tokenization** is the broader effort to represent things that exist outside crypto entirely — government bonds, private credit, real estate, company equity, carbon credits — as on-chain tokens, so they can be transferred, traded, and composed with other DeFi protocols the same way a crypto-native token can.

The appeal: real-world assets like government bonds already exist in enormous size (many trillions of dollars) compared to the crypto-native market, and getting even a small fraction on-chain means DeFi's tools (instant settlement, composability, 24/7 markets) become available for assets that have historically settled slowly, only during business hours, through many layers of intermediaries.

## Why RWAs can't just plug into a normal, permissionless pool

Here's the part where everything from article 6 (hooks) and this article's own compliance discussion connects: a tokenized government bond or company share is, legally, still the *same regulated instrument* it always was — securities law generally requires knowing who's allowed to buy/sell it (accredited investors only, in many jurisdictions, for certain instruments), tracking ownership for tax and reporting purposes, and sometimes restricting transfers entirely for a holding period. A standard, fully permissionless Uniswap pool has no way to enforce any of that — anyone with a wallet can trade in it, which is precisely the feature that makes it illegal to list an unrestricted security token on, in most jurisdictions.

This is exactly why RWA hooks in the directory are almost always paired with compliance mechanisms: a `beforeSwap` or `beforeAddLiquidity` hook (article 6) that checks the trading wallet against a whitelist, a KYC attestation, or a compliant-token-standard's own built-in transfer restrictions (like **ERC-3643**, a real, production token standard purpose-built for regulated/permissioned securities, referenced explicitly by several hooks in this dataset) before allowing the trade to proceed at all. Without that compliance layer bolted on, tokenizing a real security on a permissionless AMM isn't actually legally usable for its stated purpose — it's just a demo.

## The one sentence to keep

**Stablecoins need specialized, near-zero-slippage AMM curves (because they're supposed to always trade near 1:1, unlike genuinely volatile assets) plus depeg-aware safety mechanisms for when that assumption breaks; RWAs need the exact same specialized curve thinking plus a hard compliance layer bolted directly into the swap/liquidity hooks (whitelist checks, permissioned token standards like ERC-3643), because the legal reality of the underlying asset doesn't disappear just because it's now represented as a token on a permissionless exchange.**

---

## You've now covered the full stack

Articles 1-6 gave you the core AMM/Uniswap architecture (box → LP economics → v2 contracts → v3 ranges → v4 rewrite → hooks themselves). Articles 7-13 gave you the seven problem-domains hooks are built to solve (MEV, LVR, oracles, cross-chain, restaking, privacy, stablecoins/RWA). Every one of the 17 category files in `hook-directory/categories/` should now read as "a specific combination of these ideas," rather than a wall of unfamiliar jargon. That's the point where you're actually equipped to judge which hook ideas are genuinely interesting versus which ones are a familiar pattern with a new sponsor's logo slapped on — which is exactly the next step in your plan.
