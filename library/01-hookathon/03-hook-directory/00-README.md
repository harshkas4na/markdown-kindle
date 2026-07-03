# UHI Hook Directory — Explained

## What this is

This is a plain-language, organized explainer of the **Uniswap Hook Incubator (UHI) Hook Directory** — a public showcase of **556 projects** built by developers across 8 cohorts (UHI1 through UHI8, roughly mid-2024 through mid-2026) at [Atrium Academy](https://atrium.academy)'s Uniswap Hook Incubator program.

If you don't know what a "hook" is: **Uniswap v4 lets developers attach custom code to a liquidity pool's core actions** (before/after a swap, before/after adding or removing liquidity, before/after initializing a pool). That custom code is called a "hook." It's a plugin system for a decentralized exchange (DEX). Before v4, if you wanted an AMM (Automated Market Maker — the algorithm that sets prices and lets people trade against a pool of tokens instead of an order book) to behave differently — say, charge fees that change with volatility, or block a specific class of trader — you had to fork the entire Uniswap codebase. Hooks mean you can now write a small, focused smart contract that plugs into the standard pool and only overrides the behavior you care about.

This directory is essentially a giant "what did people try to build with this plugin system" showcase. Reading through it, you see the same handful of real, hard problems in decentralized exchanges being attacked over and over by different teams with different tools. That repetition is the interesting part — it tells you what actually hurts in DeFi trading today.

## Source of truth

- Original Notion directory: https://atriumacademy.notion.site/hook-directory
- Raw data export (CSV + Markdown, updated periodically by Atrium Academy): https://github.com/AtriumAcademy/UHI-Hook-Data
- This folder was generated from that export on 2026-07-02. The export contains 556 structured rows (name, cohort, description, tags, integrations, prize track) and a companion Markdown file with fuller subpage content (problem statements, demo links, etc.) for ~562 entries.

## How this folder is organized

- **`00-README.md`** — this file.
- **`01-TRACKER.md`** — the "big picture" dashboard: which problems get attacked the most, cohort-over-cohort trends, and where the genuinely novel ideas are hiding versus where everyone converges on the same pattern.
- **`categories/*.md`** — one file per problem-space (not per hook — see note below). Each file explains: what the underlying problem is, why it's a real problem (in plain language, with the mechanics), what prior art / whitepapers / concepts the solutions in this space typically draw on, and then a table of every hook project in the dataset tagged into that space (name, cohort, one-line description, other tags).

### Why grouped by problem-space instead of one file per hook

The original ask was one file per hook. With 556 entries, most of which are single-paragraph hackathon submissions, that would produce hundreds of near-duplicate files (e.g. dozens of "dynamic fee based on volatility" hooks that differ only in which oracle or ML model they plug in) and no real whitepaper trail — most of these are student/hackathon projects, not published research, so inventing a "reference paper" per project would be fabrication, not documentation.

Grouping by problem gives you the same information with real signal: you can see instantly that ~40% of all submissions touch "dynamic fees," which tells you that's the single most obvious pain point people perceive in AMM design, while things like on-chain options or governance hooks are rare (niche, harder, or just less understood).

A hook can appear in more than one category file if it's tagged with multiple concerns (e.g. a hook that does both dynamic fees AND cross-chain settlement appears in both).

## Categories

| File | Problem space | # Hooks |
|---|---|---|
| `categories/dynamic-fees-lp-optimization.md` | Dynamic/adaptive swap fees, LP fee optimization | 218 |
| `categories/liquidity-management-incentives.md` | Idle capital, JIT liquidity, liquidity mining | 153 |
| `categories/cross-chain-hooks.md` | Cross-chain liquidity & settlement | 150 |
| `categories/mev-lvr-protection.md` | MEV, sandwich attacks, Loss-Versus-Rebalancing | 126 |
| `categories/trading-rewards-gamification.md` | Trading incentives, points, gamification | 131 |
| `categories/stablecoins-rwa-tokenized-assets.md` | Stablecoins, RWA, tokenized assets | 102 |
| `categories/misc-other.md` | Doesn't fit cleanly elsewhere / generic tooling | 75 |
| `categories/oracles-price-discovery.md` | Price oracles & price discovery | 75 |
| `categories/order-types-routing-auctions.md` | Limit orders, custom routing, on-chain auctions | 74 |
| `categories/security-hooks.md` | Rug-pull/exploit protection, circuit breakers | 63 |
| `categories/compliance-kyc-identity.md` | KYC/AML, regulation, identity | 60 |
| `categories/amm-curve-design.md` | Alternative AMM curve math (CFMM/CPMM/CSMM) | 35 |
| `categories/staking-restaking.md` | LST/LRT liquidity, EigenLayer restaking | 33 |
| `categories/privacy-zk-hooks.md` | Trade privacy via ZK / FHE | 24 |
| `categories/governance-hooks.md` | Pool/protocol governance | 21 |
| `categories/ai-ml-hooks.md` | Machine-learning-driven hook logic | 21 |
| `categories/options-derivatives-structured-products.md` | On-chain options, futures, structured yield | 21 |

(Totals sum to more than 556 because most hooks carry multiple tags and appear in multiple categories.)

## A note on the "whitepaper reference" ask

Where a category draws on real, citable prior art (e.g. the Loss-Versus-Rebalancing paper, am-AMM, TWAMM, Nezlobin's directional fee formula, CoW Protocol, EigenLayer's restaking model), that's named at the top of the category file with enough description to look it up. Individual student hooks are **not** each attributed a specific whitepaper unless their own description explicitly names one — most don't, and guessing would be misleading.
