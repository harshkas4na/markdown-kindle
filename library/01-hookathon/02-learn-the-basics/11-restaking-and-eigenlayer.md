# 11 — Restaking & EigenLayer AVS

Goal: understand staking first, then why "restaking" is a genuinely clever idea, then what an AVS actually is — because "EigenLayer AVS" shows up as a black-box buzzword in a huge number of hooks, and it's worth actually knowing what it means.

## Staking, in one paragraph

Ethereum today runs on **Proof of Stake**: instead of miners burning electricity to propose blocks (the old Proof of Work model), **validators** lock up ("stake") 32 ETH as collateral and are chosen to propose/verify blocks. If a validator behaves honestly, they earn rewards. If they behave dishonestly (e.g. try to approve two conflicting versions of history), a portion of their staked ETH is destroyed — this is called **slashing**. The entire security of the network rests on this simple idea: it's economically painful to misbehave, because you have real money locked up that gets taken away if you do.

## Liquid staking: the token version of "staked ETH"

Normally, staked ETH is locked and illiquid — you can't spend it or trade it while it's securing the network. **Liquid staking** protocols (Lido being the largest) solve this by pooling many people's ETH, staking it on their behalf, and giving each depositor a tradeable receipt token — **stETH**, in Lido's case — representing their staked ETH plus accumulating rewards. Now you can hold "staked ETH" and also use it elsewhere in DeFi (as collateral, in a liquidity pool, etc.) at the same time. This receipt-token category is called an **LST (Liquid Staking Token)**.

## Restaking: the actual new idea EigenLayer introduced

Here's the genuinely novel part. Ethereum's staking security only protects *Ethereum itself*. But there are lots of *other* systems in the crypto ecosystem that also need strong economic security — oracles, bridges, data availability layers, and other infrastructure — and historically, each of these had to bootstrap its *own*, entirely separate pool of staked collateral and validators from scratch, which is slow, expensive, and fragments security across dozens of smaller, individually-weaker networks.

**EigenLayer's idea: let ETH that's already staked (or LSTs representing it) be "re-pledged" as collateral for one or more of these *other* systems too**, opting in voluntarily, earning *additional* yield on top of normal staking rewards — in exchange for taking on the additional risk that misbehaving in that other system can now also get your original stake slashed.

**Analogy: imagine a security guard who's already been vetted, bonded, and posted collateral to guard Building A.** Instead of Building B down the street having to recruit, vet, and bond a completely separate set of guards from zero, the same guard can say "I'll also guard Building B during my shift, using my *same* posted collateral as the guarantee — if I mess up at either building, I lose my bond." Building B gets instant access to a pool of already-trustworthy, already-collateralized guards, instead of bootstrapping trust from nothing.

This is why restaking is such a big deal: it lets brand-new infrastructure projects "rent" Ethereum's existing, deeply battle-tested economic security instead of building their own weaker version from scratch.

## AVS: what these "other systems" are actually called

An **AVS (Actively Validated Service)** is the general name for any of these external systems that EigenLayer's restaked collateral can be used to secure. An AVS defines its own rules for what counts as "good behavior" and "bad behavior" (which gets slashed), and restakers who opt in to that specific AVS run software (an "operator" node) that actively participates in whatever that service does — validating data, signing off on computations, attesting to outcomes — earning extra yield for the work, at the risk of slashing if they cheat or go offline.

## Why so many hooks in the directory namedrop "EigenLayer AVS"

Once you see it this way, the pattern in the directory clicks: **an AVS is a general-purpose way to get a decentralized network of economically-accountable operators to do some computation and report a trustworthy result on-chain** — which is exactly the primitive several hook categories need:

- **Oracles (article 9)**: instead of trusting a fixed set of Chainlink nodes, some hooks spin up their own AVS specifically to attest to a volatility measurement or price feed, with EigenLayer-backed slashing as the trust mechanism.
- **MEV auctions (article 8)**: EigenLVR and similar hooks use an AVS to run a sealed-bid auction off-chain (hiding bids from front-runners) and have operators attest to the honest winner on-chain, with slashing if they lie about the result.
- **ML inference (learn category `ai-ml-hooks`)**: since running a real machine-learning model on-chain is expensive/impractical, several hooks have an AVS run the model off-chain and attest to the prediction on-chain instead.

In every one of these cases, the actual pattern is the same: *do the expensive or sensitive computation off-chain, and use a slashing-backed network of operators to make the on-chain-reported result trustworthy without a centralized single point of failure.* "EigenLayer AVS" is just the specific, currently-popular brand name for that pattern, not a fundamentally different idea each time it's mentioned.

## The one sentence to keep

**Restaking lets ETH that's already staked (and already has real, slashable collateral behind it) be re-pledged to secure additional external systems called AVSs, which is why "EigenLayer AVS" shows up constantly across totally different hook categories — it's not one specific product, it's a general-purpose way to get a decentralized, economically-accountable network to do off-chain computation (an oracle reading, an auction result, an ML prediction) and report it on-chain in a way you don't have to blindly trust.**
