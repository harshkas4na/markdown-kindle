# The Big Picture: What Problems Are People Actually Working On

This is the "zoom out" view across all 556 hooks in the directory (cohorts UHI1–UHI8, roughly mid-2024 to mid-2026). It's meant to answer: *which problems get attacked over and over, which ideas are one-offs, and how has the focus shifted over time?*

## 1. Category size — the repetition ranking

Ranked by how many of the 556 hooks touch each problem space (a hook can be tagged into more than one):

| Rank | Category | # Hooks | Share of all submissions |
|---|---|---|---|
| 1 | Dynamic Fees & LP Fee Optimization | 218 | ~39% |
| 2 | Liquidity Management & Incentives | 153 | ~28% |
| 3 | Cross-Chain Hooks | 150 | ~27% |
| 4 | MEV & LVR Protection | 126 | ~23% |
| 5 | Trading Rewards & Gamification | 131 | ~24% |
| 6 | Stablecoins, RWA & Tokenized Assets | 102 | ~18% |
| 7 | Misc / Other (generic or long-tail) | 75 | ~13% |
| 7 | Oracles & Price Discovery | 75 | ~13% |
| 9 | Order Types, Routing & Auctions | 74 | ~13% |
| 10 | Security Hooks | 63 | ~11% |
| 11 | Compliance, KYC & Identity | 60 | ~11% |
| 12 | AMM Curve Design | 35 | ~6% |
| 13 | Staking & Restaking | 33 | ~6% |
| 14 | Privacy & ZK Hooks | 24 | ~4% |
| 15 | Governance Hooks | 21 | ~4% |
| 15 | AI/ML Hooks | 21 | ~4% |
| 15 | Options, Derivatives & Structured Products | 21 | ~4% |

**Reading this:** the top four categories (dynamic fees, liquidity management, cross-chain, MEV/LVR) are all attacking essentially the same underlying complaint from different angles — *"AMM design, as Uniswap ships it out of the box, leaves money on the table for LPs and is easy to exploit for value extraction."* If you collapse "dynamic fees" + "MEV/LVR protection" + "liquidity management" into one meta-category ("make LPs whole"), it covers a clear majority of all 556 submissions. That is the single dominant theme of the entire UHI hook ecosystem: **hooks are overwhelmingly about protecting and better-compensating liquidity providers**, not about novel trading products for end users. Options/derivatives, governance, and AI/ML are all rare — these require either niche quant skill (derivatives) or don't produce an exciting demo (governance), or make claims that are hard to substantiate in a hackathon timeframe (AI/ML).

## 2. Cohort-over-cohort trend — is a topic growing or fading?

Each cell shows count and % of that cohort's submissions tagged into the category. Cohort sizes: UHI1=36, UHI2=61, UHI3=61, UHI4=54, UHI5=57, UHI6=71, UHI7=76, UHI8=139.

| Category | UHI1 | UHI2 | UHI3 | UHI4 | UHI5 | UHI6 | UHI7 | UHI8 | Trend |
|---|---|---|---|---|---|---|---|---|---|
| Dynamic Fees & LP Optimization | 0% | 41% | 46% | 46% | 49% | 32% | 40% | 42% | Consistently the #1 topic every cohort since UHI2 |
| Liquidity Mgmt & Incentives | 3% | 2% | 33% | 50% | 30% | 30% | 28% | 32% | Rising — jumped hard from UHI2→UHI3, now a permanent fixture |
| Cross-Chain | 0% | 7% | 13% | 20% | 32% | 18% | 15% | **60%** | Sharp, sudden rise in UHI8 |
| MEV & LVR Protection | 0% | 21% | 16% | 19% | 32% | 30% | **38%** | 18% | Peaked UHI7, dipped UHI8 (crowded out by cross-chain surge) |
| Trading Rewards/Gamification | 3% | 28% | 31% | 22% | 35% | 23% | 32% | 16% | Was a steady ~25-35%, fell off sharply in UHI8 |
| Stablecoins/RWA/Tokenized | 0% | 3% | 15% | 17% | 23% | 14% | 22% | 30% | Rising — RWA narrative gaining share cohort over cohort |
| Staking/Restaking | 0% | 7% | 18% | 7% | 5% | 6% | 9% | **0%** | Fell to zero in UHI8 — EigenLayer restaking hype has cooled |
| AI/ML | 0% | 0% | 8% | 7% | 4% | 1% | 3% | 5% | Small and inconsistent — no sustained trend |
| Oracles & Price Discovery | 0% | 0% | 10% | 20% | 23% | 11% | 18% | 17% | Rising then plateaued |

**What this tells you:** UHI1 (36 hooks) predates most of these tags entirely — it looks like an early, exploratory cohort before dynamic fees became the "obvious" hook idea. From UHI2 onward, dynamic fees is essentially the baseline everyone starts from. The most dramatic single-cohort shift in the whole dataset is **cross-chain jumping to 60% of UHI8** — almost certainly tracking Unichain's growing prominence as a sponsor/integration target (see integrations below) as it matured. Staking/restaking dropping to 0% in UHI8 is the clearest sign of a narrative that has fully faded — EigenLayer restaking was a big theme UHI2–UHI7 and essentially disappeared by UHI8.

## 3. What sponsor technology actually got used

Counting the `Integrations` field across all 556 rows (a hook can integrate more than one):

| Integration | # Hooks using it |
|---|---|
| EigenLayer | 111 |
| Unichain | 100 |
| Reactive Network | 76 |
| Fhenix | 59 |
| Chainlink | 45 |
| Brevis | 23 |
| Arbitrum (Stylus) | 19 |
| Circle | 14 |
| Flaunch | 10 |
| Ink | 10 |
| Across | 11 |

**Reading this:** these numbers roughly explain the category-trend spikes above. EigenLayer's dominance (111 integrations) explains why "AVS-secured X" shows up across oracles, MEV auctions, and staking categories simultaneously — it's infrastructure, not a single product category. Fhenix's 59 integrations mostly map onto the Privacy/ZK and MEV-protection categories (encrypted order flow). Reactive Network (76 integrations, a cross-chain automation/event-driven execution protocol) is a major, easy-to-miss driver of the "cross-chain" category surge — it doesn't show up as its own tag/category above because tags didn't consistently include it, but the raw integration count says it was heavily used, especially in later cohorts.

## 4. Prize tracks (what sponsors explicitly incentivized)

| Prize track | # entries targeting it |
|---|---|
| Uniswap Prize (general) | 54 |
| EigenLayer Prize | 16 (+4 combined with Uniswap) |
| Brevis Prize | 10 (+2 combined) |
| Fhenix Prize | 5 |
| Reactive Network Prize | 5 |
| Arbitrum Prize | 4 |
| Flaunch Prize | 4 (+2 combined) |
| Unichain Prize | 4 |
| Across Prize | 3 |
| Chainlink Prize | 2 (+3 combined) |
| Circle Prize | 1 (+2 combined) |

This mostly confirms the integrations data: prize-track participation is a direct incentive for using a particular sponsor's technology, and it correlates cleanly with which categories are inflated by infrastructure availability (EigenLayer, Fhenix, Brevis) rather than pure organic demand.

## 5. The overall picture, in one paragraph

The UHI Hook Directory is best read not as 556 independent ideas but as **iterative attempts at solving roughly six real, recurring problems**: (1) static AMM fees are inefficient and unfair to LPs, (2) MEV/LVR structurally taxes LPs and traders, (3) concentrated liquidity often sits idle out-of-range, (4) liquidity is fragmented across chains, (5) bringing regulated/real-world assets on-chain needs compliance tooling a plain pool can't provide, and (6) new pools/tokens need a cold-start incentive mechanism. Everything else — governance, AI-driven fees, options, privacy tech — is either an enabling technology applied to one of those six problems, or a genuinely niche, less-repeated idea. Cohort-over-cohort, the *problems* people care about have stayed remarkably stable (fees, MEV, liquidity efficiency are constants from UHI2 onward); what changes fastest is *which sponsor infrastructure* is fashionable to build the solution with — EigenLayer and Fhenix dominated the middle cohorts, while Unichain and cross-chain tooling dominate the most recent one (UHI8).

## 6. Data caveats

- Tags in the source data are free-text and inconsistent (e.g. "Donation" vs "Donations", "base interest rate" vs "Basic Interest Rate" appear as separate tags for the same concept) — counts above are best-effort de-duplication at the category level, not exact.
- Cohort field is missing/blank for a small number of rows (1 row had no cohort at all) and is excluded from the cohort trend table.
- "Active?" field is blank for 546/556 rows and marked "Active" for only 10 — most of these are historical hackathon submissions, not maintained production protocols. Treat descriptions as a snapshot of intent at submission time, not a claim that the project is live today.
