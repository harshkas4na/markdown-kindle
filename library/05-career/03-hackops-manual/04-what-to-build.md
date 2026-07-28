# What To Build

This is your own method, industrialized. For UHI10 you mined all **556 prior hooks** for structural gaps before designing anything, and that research is why the three hook designs are strong. `/prior-winners` runs that process on any event instead of only the ones big enough to justify a week of manual work.

## The rule that makes it work

**Read the losers too.**

An analysis of winners alone tells you what won. It cannot tell you what everyone *else* submitted — and that's the more useful half, because it's the idea you must not build. A winners-only analysis reliably produces "the crowd's idea, slightly better," which is how you lose to someone with more polish.

So the corpus is every submission from the last one or two editions, not the podium.

## What comes out of the corpus

**Track economics.** Submissions per track, prize per track, and prize divided by submissions. This number is almost never published anywhere, and it feeds straight back into the scorer to replace its estimates with measurements. It's the single biggest accuracy upgrade available to the whole system.

**The selection function.** Comparing winners against non-winners tells you what these judges actually reward: novelty or polish or depth or demo quality. Whether live deployments beat mocks — they usually do. Whether SDK and tooling submissions do disproportionately well — they usually do, because sponsors love the thing their own developers can pick up, and that is precisely what the Walrus SDK was. Whether the sponsor's tech was used *centrally* or incidentally, because centrally is what gets rewarded.

**The crowd.** The default idea everyone submits. Named explicitly so you can avoid it.

**The gaps.** The payoff. Cluster submissions by the *problem* they attacked rather than the tech they used, then ask what obvious adjacent problem nobody touched — and distinguish carefully between "nobody thought of it," which is an opportunity, and "everyone tried and it's infeasible in three days," which is a trap.

The UHI research is the model for all of it. RWA hooks were *all* compliance gating and nobody had built market microstructure. Security hooks all defended against bad *tokens* and nobody defended against bad *hooks*. Each of those is a sentence that only exists because someone read 556 submissions.

## The timing gap is the best kind

The third UHI finding was different in kind: MEV redistribution only became buildable after Unichain Flashblocks shipped provable priority ordering. Nobody had built it because until recently nobody *could*.

That's the highest-value gap there is. When a protocol upgrade, a new primitive, or a new API landed since the last edition, there is a window where the idea is obvious in hindsight and nobody has done it yet. Always ask what became newly possible.

## The human signal nobody reads

`/x-intel` layers this on, and it's the least-mined source in the entire space. Judges and sponsor devrels say out loud what they wish people would build — "surprised nobody built", "what we want to see", "wish someone had". Winner announcement threads from prior editions often explain *why* something won, which the gallery never does. A sponsor's track brief is marketing; their team's timeline is what they're actually excited about.

That distinction is exactly what `Pull ⭐⭐⭐` means in the ratings: they have said out loud that they want this to exist.

## The six idea shapes that have worked

`/idea-forge` generates against these, roughly in order of historical return:

**The structural gap, directly.** "Nobody built X because Y just became possible."

**Prior art re-aimed.** A Tier-1 asset from `prior-art.md` pointed at this sponsor's stack. The cheapest strong idea available, and it has already won twice — Mercado upgraded at IIIT Sricity, and the Walrus SDK shape. Note the discipline: you re-aim the *design*, and let knowing exactly what to write be the speed. Most events require new code written during the event, and `/hack-recon` quotes the exact clause.

**The SDK move.** Build what the sponsor's own developers need rather than an app that uses their tech. Disproportionately effective and rarely attempted under time pressure.

**Cross-layer.** Something needing contracts *and* a real client, where a contract-only hacker can't ship the UI and a frontend hacker can't write the contract. The field thins fastest here, and you span both.

**The adversarial inversion.** Build the attacker to demonstrate the defender — the way the money-laundering simulation suite was written specifically to be caught by your own team's detection backend at SIH. Memorable, and almost nobody does it.

**The defensive wrapper.** Guard Hook's shape: everyone defends against bad inputs, nobody defends against bad *peers*. It generalizes to most ecosystems.

## Rating honestly

Novelty asks whether five other teams will submit this. Pull asks whether the sponsor wants it to exist. Feasibility asks whether it ships, deployed and demoed, in the days available at your real speed after prior art transfers.

**Be pessimistic on Feasibility.** It's the rating that gets inflated, and an inflated Feasibility is how a week produces nothing. `profile/velocity.md` prices an unfamiliar stack at roughly double plus a day of ramp, with a hard gate: never take an unfamiliar-stack event with fewer than five days left.

That gate exists to protect something you actually want. You've changed rooms every six months for three years — frontend to web3 to Reactive to agents to Go — and learning value is a scored axis precisely because those events compound. It just has to be priced instead of wished away, and it gets one slot at a time, never concurrent with a Tier-1-edge event.
