# Governance Hooks

**21 hook projects.**

## The problem, explained simply

A single Uniswap pool is normally governed by nobody — the rules are fixed in the pool's contract code at creation and don't change based on any vote. That's fine for a plain swap pool, but it's a limitation once you introduce things like: a hook that has parameters worth tuning over time (what should the fee-adjustment sensitivity be?), a DAO-owned treasury that trades through a pool and wants its members to get preferential terms, or any situation where "who gets to change the rules of this pool, and how" needs an actual answer instead of "whoever deployed the contract, forever."

## Why fewer teams attack this

Governance is a comparatively unglamorous, structural problem — it doesn't produce an exciting demo the way a gamified rewards system or a slick privacy feature does, so it draws fewer entries, and the ones that exist tend to be a governance *feature bolted onto* a hook whose primary pitch is something else (security, DAO treasury management) rather than governance as the standalone product.

## Common approaches seen in this dataset

1. **DAO treasury-aware pools** — give a DAO's own members preferential fees or access when trading through a pool tied to their treasury, and use governance-controlled rebalancing to keep the pool healthy (DAO Treasury Hook).
2. **Governance-gated insurance/security features** — let token holders or a DAO vote on parameters of a security mechanism (e.g. what counts as a rug-pull trigger) rather than hard-coding it (Safu Hook).
3. **Auction-rights allocation with governance oversight** — combine the am-AMM auction pattern (see `dynamic-fees-lp-optimization.md`) with a governance layer that can intervene or set bounds on the auction (AuctionPool).

## Prior art / reference material

- Standard on-chain DAO governance frameworks (e.g. OpenZeppelin Governor, Compound's Governor Bravo) — the general pattern most "governance hook" entries adapt to a pool-specific context, though few entries specify which exact framework they build on.
- am-AMM (auction-managed AMM) research — relevant where governance and auction-based rights allocation intersect.

## Projects in this category

| Project | Cohort | Description | Other Tags |
|---|---|---|---|
| **Dynamic Governance Liquidator** | UHI2 | Hook is a TWAMM extended with onchain governance that can be used to update or cancel the TWAMM order if a proposal is passed. | DeFi, Governance, delegates |
| **NFT Gated Pools** | UHI2 | Exclusive Pools only for the holders of certain NFTs | Compliance, DEX, DeFi, Governance, KYC, Security, Trading Volume Rewards, delegates |
| **Steelo.io** | UHI2 | Steelo is a web3 social media mobile app helping creators turn fans into investors through self-tokenisation, token-gated experiences and value-redistributing tokenomics. | Coincidence of Wants, DEX, DeFi, Dynamic Fee, ETH Staking, Governance, KYC, Order Type, Security, Tokenized Stocks, Trading Rewards, Trading Volume Rewards, base interest rate, zk-SNARK |
| **Nevo.network** | UHI3 | Decentralized p2p fiat exchange on hooks | AML, Custom Routers, Custom hooks, DEX, DeFi, Donation, Donations, Dynamic Fee, Governance, KYC, LP Fees, LP Liquidity, Liquidity Mining, Oracle, Security, Tokenized Stocks, Trading Rewards, Trading Volume Rewards |
| **UniGuard** | UHI3 | Risk management and Insurance mechanisms for Uniswap hooks | Compliance, EigenLayer, Governance, Reputation, Security |
| **VotingHook** | UHI3 | VotingHook allows LP holders to cast votes using the underlying governance tokens held by the pool | Custom Routers, Custom hooks, DeFi, Governance, delegates |
| **Safu Hook** | UHI4 | Safu Hook is a  decentralized insurance solution designed to protect liquidity providers (LPs) from rug pulls and malicious activities. | Governance, LP Fees, Security |
| **Uniroid - Uniswap Pools on Steroids** | UHI4 | Uniroid is an advanced security and utility hook framework for Uniswap V4 | Custom hooks, DEX, Dynamic Fee, Governance, KYC, LP Fees, LP Liquidity, Security, Trading Rewards, Trading Volume Rewards |
| **Cross-Chain Gas Price Optimization Hook** | UHI5 | A sophisticated Uniswap V4 hook that automatically routes swaps to the most cost-effective blockchain using Across Protocol, maximizing user savings through intelligent gas price optimization and cross-chain execution. | Bridge Aggregation, Chainlink Integration, Cost Analysis, Cross-Chain Optimization, Emergency Controls, Gas Price Oracle, Governance, MEV Protection, Multi-Chain Routing, Oracle, Price Discovery, USD Savings Display |
| **InfraFund** | UHI5 | InfraFund bridges the NetZero investment gap by tokenizing real-world renewable energy assets, creating liquid, transparent markets for developers and investors. We are building a custom Uniswap v4 hook to create the first regulatory-compliant liquidity pools for these RWA tokens, enabling features like on-chain identity verification and dynamic fees to accelerate green capital formation. | CCIP, DEX, Donation, Governance, ICO, KYC, LP Fees, LP Liquidity, Machine Learning, Oracle, RWA, Regulation, Security, Tokenized Stocks, Trading Rewards |
| **LiquiDAO** | UHI5 | LiquiDAO helps DAO’s maximize their ecosystem liquidity and contributor retention with permissioned pools exclusively reserved to their core contributors. | Compliance, Custom hooks, DEX, Governance, Illiquid Assets, LP Fees, MEV |
| **PPR Hook** | UHI6 | Building a Portfolio Rebalancing Hook Enables confidential multi-asset rebalancing on Uniswap v4 | Custom hooks, Governance, Security |
| **AuctionPool** | UHI7 | AuctionPool is the first auction-managed AMM on Uniswap v4 where professional operators bid ETH/block for pool management rights, dynamically optimize fees, capture MEV at zero cost, and pay rent directly to LPs increasing LP yields 7-20x while maintaining permissionless access. | Auctions, Dynamic Fee, Governance, LP Fees, LVR, MEV |
| **DAO Treasury Hook** | UHI7 | A DAO Treasury Hook that reduces fees for DAO members when they swap with rebalancing mechanism to keep the pool active and within range irrespective of market condition | Dynamic Fee, Governance, LP Liquidity, Oracle |
| **Arc Hook** | UHI8 | Private, compliance-ready whitelisting for Uniswap v4 pools using multilinear KZG commitments, unichain and the Reactive Network. | DEX, Governance, Security, Unichain, zk-SNARK |
| **DeLi Protocol** | UHI8 | Decentralized patent licensing infrastructure that transforms intellectual property into a programmable, liquid asset class using tokenized rights and Uniswap V4 markets. It enables transparent pricing, permissionless access to licenses, and verifiable on-chain usage while maintaining real-world legal enforceability. | AMM Pricing, Compliance, DEX, Dynamic Pricing, Governance, KYC, LP Liquidity, Licensing Markets, Liquidity Mining, Machine Learning, Oracle, Permit2, RWA, Real World Assets, Reputation, Security, Smart Contract Infrastructure, Specialized Markets, Stablecoins, Tokenized IP, Tokenized Stocks, Uniswap v4 Hooks, Yield Farming |
| **Invariant** | UHI8 | Invariant is a Uniswap v4 hook-native protocol that dynamically optimizes liquidity, fees, and risk using AI-driven strategies while enforcing onchain AMM invariants such as TWAP-based regimes, range constraints, and liquidity safety guards. | CoW, Compliance, Cross-Chain, Custom hooks, DEX, Governance, KYC, LP Fees, Pool Native Incentivization, Reputation, zk-SNARK |
| **The Citadel Hook** | UHI8 | The Citadel is a hub-and-spoke security layer designed to bring institutional RWA compliance to decentralized finance. Built natively as a Uniswap v4 Hook, it enforces strict legal and identity requirements before any swap or liquidity addition can execute. | Compliance, DEX, ERC-3643, Governance, KYC, RWA |
| **Vedyx Network** | UHI8 | **Vedyx Protocol** is a decentralized security infrastructure built on Unichain that protects Uniswap v4 pools from exploits by using reactive smart contracts to detect suspicious on-chain activity in real-time (large transfers, mixer interactions, trace peel chains). Through a community-driven voting system and Uniswap v4 hooks integration, the protocol enables stakers to collectively flag malicious addresses and automatically restrict their access to protected liquidity pools, creating a trustless defense layer for DeFi. | Cross-Chain, Dynamic Fee, Gamefi, Governance, Security |
| **Velo Hooks** | UHI8 | VeloHooks is a dynamic Uniswap v4 loyalty engine that automates point-based rewards and tiered multipliers for traders and liquidity providers directly through pool hooks. Integrated with the Reactive Network, it enables cross-chain reward triggers, allowing external ecosystem milestones to dynamically boost on-chain incentives in real-time. | Governance, LP Fees, Trading Rewards, Trading Volume Rewards, Unichain |
| **Voltaire** | UHI8 | Voltaire is a Uniswap V4 hook that turns any ETH/USDC liquidity pool into a fully on-chain European options market. | Compliance, Constant Product Market Maker (CPMM), Constant Sum Market Maker (CSMM), Copy Trading, Custom hooks, DEX, Dynamic Fee, Governance, Illiquid Assets, KYC, LP Fees, LP Liquidity, Liquidity Mining, MEV, Order Type, Price Discovery, Proof Of Humanity, Stablecoins, Trading Rewards, Trading Volume Rewards, Unichain, Yield Farming |