# The Thin-Track Theory

Every scoring decision in HackOps descends from one idea, and your own record is the entire evidence base for it. It also corrects something you likely still half-believe.

## The two events that prove it

**ETHIndia, December 2024.** 750+ hackers, 275 projects. You didn't win the main prize. You won the **Walrus track — $1,000**, and the SDK later went to npm.

**ETHGlobal Delhi, 2025.** You targeted the **Uniswap and 1inch tracks**. You placed nowhere.

The naive reading of the first event is "target sponsor tracks." Delhi kills that reading, because you *did* target sponsor tracks — you just picked the two marquee DeFi sponsors that every strong team in the room goes for. Uniswap's track at an ETHGlobal is not a side door. It's the front door with a different sign.

The correct rule is narrower and much more useful:

> **Target thin tracks, not sponsor tracks.** Walrus was a newer, less-known storage protocol. Its track was a thin field. That's the whole difference.

So the scorer actively **discounts fame**. Uniswap, 1inch, Chainlink, the major L2s — a marquee sponsor draws the crowd, and sometimes concentrates it worse than the main pool. Prefer the unglamorous one: the newer protocol, the odd niche, the track that needs something the room can't do.

## The corollary that stings

Delhi teaches a second thing, and it's the more valuable one:

> **Rarity is relative to the room, not to the world.**

Your Uniswap v4 hooks depth is genuinely rare. You have three fully scaffolded hook projects built on a directory of all 556 prior UHI hooks. In a random room of 200 hackers, almost nobody can do that.

But the Uniswap track at an ETHGlobal is not a random room. It is the one room that self-selects for other hook specialists. You brought your rarest skill into the exact place where it was least rare.

This is why `profile/edge.md` ranks skills by **rarity in a hackathon field** rather than by how good you are at them, and why the scorer discounts any edge in a track that advertises for it. A Tier-1 skill is worth most where it is *unexpected* — a niche sponsor whose problem your skill happens to solve.

## The denominator nobody computes

Almost every hackathon decision in the wild is made on the prize pool. The prize pool is the numerator. The number that decides anything is:

```
best track prize  ÷  realistic submissions in that track  ×  your edge fit
```

Nobody publishes the denominator, so the pipeline works hard to estimate it — and where a source publishes a real one, it replaces every estimate. Superteam does: a live submission count, before the deadline. On the first run that single field turned a bounty that looked like the best cash-per-day on the board from $1,250 per submission into **$81**. It went from a B to a C on one number.

Two related traps the scorer now encodes:

- **Registrations are not submissions.** Devpost gives registrations; divide by eight to ten. Devfolio's count for an upcoming event is closer to hype than field size.
- **The name lies.** One event on the first run was called a "Hacker House" — normally the thinnest field in the space and worth a bonus. It had **10,869 registrations**.

## Three more rules from the record

**The prize is not the return.** November 2024 paid $4,000 across two placements and then produced a $9,000 grant, four press features, ReacDEFI, and the job. Compounding return is weighted 25% in the scorer, and chapter 6 is entirely about it.

**"Won" is not a number.** Citrea × AKINDO is on the record as a win. It paid **$20**. So there's a trust axis that checks payout reality, prize distribution, and whether the organizer has ever actually finished an event — VNIT Nagpur was cancelled before judging, after the work was done.

**Eligibility kills more entries than bad code.** On the first live run, four of six Superteam bounties were country-locked: Vietnam, Brazil, Poland, Canada. One of them was the highest-EV thing on the board and simply wasn't enterable from India. The scout filters region now; recon still has to check student-only, age, KYC, and team minimums.

## What this means when you're standing in the room

Ignore the headline prize. Find the sponsor nobody is excited about whose problem you can actually solve. Build the thing their *developers* need rather than an app that uses their tech — that's what the Walrus win actually was, and sponsors rarely get it. Then finish: deploy it, put a live URL on it, record the video. A large share of every field submits a repo and a slide deck, which is why the finish is listed in `edge.md` as a Tier-3 edge and treated as non-negotiable everywhere in the pipeline.
