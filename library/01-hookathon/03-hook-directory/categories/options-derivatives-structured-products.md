# Options, Derivatives & Structured Products

**21 hook projects** — one of the smaller, more technically demanding categories.

## The problem, explained simply

In traditional finance, **derivatives** (options, futures, structured products) let you gain exposure to an asset's price movement, hedge risk, or bet on volatility itself, without holding the underlying asset directly. On-chain, building these has historically required an entirely separate protocol (dYdX, GMX, Opyn, and others each built bespoke infrastructure) because a plain spot AMM has no built-in concept of "expiration date," "strike price," or "leverage." Hooks change the economics of this: because a hook can intercept every swap and liquidity event, some derivative-like payoffs can be approximated *using Uniswap's own concentrated liquidity positions as building blocks*, rather than writing an entirely new options-pricing engine from scratch.

A related idea in this bucket is turning impermanent loss itself into a tradeable risk — instead of treating IL purely as something to minimize (see `dynamic-fees-lp-optimization.md`), some projects let one party effectively "short" IL, transforming it into a hedgeable, tradeable exposure.

## Why fewer teams attack this

This is one of the more mathematically demanding categories — correctly pricing an option or building a safe leveraged position requires real quantitative finance knowledge, not just Solidity skill, so it naturally has fewer entries than more "pattern-following" categories like dynamic fees.

## Common approaches seen in this dataset

1. **Perpetual/leveraged trading built on top of AMM liquidity** — let traders "rent" a pool's underlying liquidity to take a leveraged directional position, effectively turning any Uniswap v4 pool into a mini perpetual-futures exchange (PerpDexHook, Swappy, Shinrai).
2. **Options built from concentrated liquidity positions** — since a concentrated liquidity position already has option-like payoff characteristics (it's exposed to price within a range, flat outside it), some hooks formalize this into an actual options product (Gainswap, UniLaas).
3. **Interest-rate benchmarking** — define an on-chain "basic interest rate" or "risk-free rate" (often referencing ETH staking yield) as a pricing input for other structured products.
4. **Stablecoin-adjacent structured yield** — combine stablecoin mechanics with yield-generating structured payoffs (unipeg).

## Prior art / reference material

- Black-Scholes / options-pricing theory (traditional finance) — the classical foundation for any legitimate options-pricing logic, though most hackathon-scale entries use simplified heuristics rather than a full options-pricing model.
- Uniswap v3's concentrated liquidity design — explicitly noted in DeFi research (e.g. by Guillaume Lambert and others) to be mathematically equivalent to a covered-call-like options payoff, which is the direct inspiration for "options from LP positions" hooks.
- GMX v2's architecture — explicitly cited as the inspiration for at least one project (Swappy) building a perpetual-exchange hook.
- Opyn/Squeeth and other on-chain options/power-perpetual protocols — general prior art for the "on-chain derivatives without a centralized order book" design space.

## Projects in this category

| Project | Cohort | Description | Other Tags |
|---|---|---|---|
| **APR LinkHook** | UHI2 | Dynamic fee hook that moves swap fees to outperform the 'risk-free' ETH Staking base interest rate | Dynamic Fee, ETH Staking, base interest rate |
| **Hedgehog ALM** | UHI2 | ALM is a Uniswap V4 NoOp hook that enhances LP performance by holding ETH as collateral on Morpho to earn interest. During price declines, it dynamically borrows USDC to acquire more ETH, offering a passive, "set and forget" strategy that provides enhanced returns compared to Uniswap V2. | DEX, DeFi, LP Fees, Security, base interest rate |
| **Steelo.io** | UHI2 | Steelo is a web3 social media mobile app helping creators turn fans into investors through self-tokenisation, token-gated experiences and value-redistributing tokenomics. | Coincidence of Wants, DEX, DeFi, Dynamic Fee, ETH Staking, Governance, KYC, Order Type, Security, Tokenized Stocks, Trading Rewards, Trading Volume Rewards, base interest rate, zk-SNARK |
| **Issuance and Redemption Hook** | UHI3 | A hook that issues assets in the case it’s a better price execution as compared to swapping.  Assets are temporarily borrowed and then replenished.     Issued assets includes LST/LRTs,index, the 20+ universalassets.xyz such as uSOL, uNEAR,  uXRP, uSUI, and others.   Universal assets are non-ERC20 native tokens issued on ERC20 chains. | Cross-Chain, Custom Routers, Custom hooks, DEX, DeFi, ETH Staking, EigenLayer, Illiquid Assets, Inter-Connected Pools, LP Fees, LP Liquidity, Oracle, Order Type, Price Discovery, base interest rate |
| **Tenor** | UHI3 | Tenor's V4 hook enables users to swap ERC20 tokens for fixed rate tokens (e.g. Pendle PTs) using a custom interest rate AMM. The hook enables creators to deploy fully onchain fixed rate lending pools, allowing users to earn using Uniswap V4. | Custom hooks, DeFi, NoOp, Order Type, base interest rate |
| **TurboStable** | UHI3 | LP vault that boosts stablecoin and pegged asset liquidity up to 20x. | Custom hooks, DEX, DeFi, LP Fees, LP Liquidity, NoOp, Stablecoins, base interest rate |
| **PerpDEX** | UHI4 | Decentralized leveraged trading enabled by v4 hooks | DEX, ETH Staking, LP Liquidity, Options/Futures, Order Type |
| **unipeg** | UHI4 | stablecoin that resides with hooks | Basic Interest Rate, Dynamic Fee, Options/Futures, Stablecoins, Yield Farming |
| **Amply** | UHI5 | Amply is a hook that gamifies trading by implementing a dynamic reward system with tier-based POINTS distribution, milestone bonuses, and referral mechanisms, while integrating with EigenLayer for staking rewards and Ink for NFT milestone rewards.  The hook automatically tracks users' cumulative ETH swap volume, awards POINTS tokens based on their tier level, provides milestone bonuses for reaching specific thresholds, distributes referral rewards, and enables users to stake ETH through EigenLayer and earn NFT rewards via Ink. | Basic Interest Rate, Dynamic Fee, ETH Staking, Trading Rewards, Trading Volume Rewards |
| **Debt Hook** | UHI5 | DebtHook is a DeFi lending protocol that leverages Uniswap v4 hooks to enable, MEV-protected liquidations of collateralized debt positions, with ETH as collateral and USDC as the lending currency. The protocol features automatic liquidations during swaps, EigenLayer-powered batch matching for optimal efficient interest rate discovery, and a seamless interface for lenders and borrowers, paying gas in USDC. | Basic Interest Rate, CoW, Custom hooks, DEX, MEV, Private Debt, Unichain |
| **Vixdex.finance - Decentralized Volatility Trading Protocol** | UHI5 | Vixdex is an implied volatility trading protocol that lets users trade the volatility of any Uniswap V3 pool from memecoins to BTC , making it a degen-friendly way to speculate on market uncertainty. | DEX, Options/Futures |
| **OpSwap - American Options on Unichain** | UHI6 | American Options created Just in Time to defragment liquidity through a hook. Users can swap for tokenized exercisable options! | Constant Product Market Maker (CPMM), Custom hooks, DEX, NoOp, Options/Futures, Unichain |
| **Prisma** | UHI6 | Yield maximizer auto-Compounding for Uniswap | Basic Interest Rate, LP Fees, LP Liquidity, Trading Rewards |
| **StreetRate** | UHI6 | real time currency exchange that agreegates official parallel and p2p market rates in one place | Basic Interest Rate, Custom hooks, LP Fees, Other, Price Discovery |
| **HooLotto** | UHI7 | HooLotto gamifies DeFi participation with lottery multipliers that level the playing field, hybrid rewards that give LPs passive income, and engagement drivers like jackpots and NFT boosts | Basic Interest Rate, Custom hooks, DEX, LP Fees, Trading Rewards, Trading Volume Rewards |
| **YieldLock (PlexusOne)** | UHI7 | Interest rate swap protocol using custom curves and hooks on Uniswap V4 | Basic Interest Rate, LP Liquidity, NoOp, Private Debt, Unichain, Yield Farming |
| **DopeSpreader** | UHI8 | DopeSpreader is institutional spread trading: ONCHAIN | Custom hooks, Options/Futures, Price Discovery |
| **GammaHedge** | UHI8 | An autonomous risk-management sentinel for Uniswap V4 that programmatically eliminates impermanent loss through real-time delta hedging. It leverages Reactive Smart Contracts for decentralized execution and Filecoin for verifiable auditing, turning passive liquidity into an institutional-grade, market-neutral yield strategy. | LP Fees, LP Liquidity, LVR, Options/Futures, Unichain, Yield Farming |
| **ParaDex** | UHI8 | A perpetual futures market implemented inside a Uniswap v4 hook: traders act through the v4 unlock-callback path, and per-pool OI skew drives on-chain fee overrides and exposure limits. Funding settlement and liquidations are automated by Reactive Network reactors subscribed to Unichain events. | Options/Futures, Price Discovery, Unichain |
| **ThaHtay** | UHI8 | A Uniswap v4 Hook that converts liquidity pools into a fully on-chain perpetual trading engine. | DEX, Options/Futures, Unichain |
| **The Multiverse Market** | UHI8 | Multiverse Markets is a prediction market platform built on Uniswap V4 hooks that uses LMSR (Logarithmic Market Scoring Rule) pricing for binary outcome trading. Users can create markets with    yes/no outcomes, trade outcome tokens against TUSD collateral, and redeem winnings after resolution — all powered by custom V4 hook logic on Unichain. | Options/Futures, Prediction Market, Unichain |