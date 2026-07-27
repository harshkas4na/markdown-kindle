# 08 — Six Ways to Make It Stronger, Explained One at a Time

Each of these came directly out of a weakness found in chapters 06/07: something a critical judge, a competing
team, or a real LP would poke at. For each one: **what it is, why it exists, exactly how it would work, and what
it fixes** — with worked numbers, not just concepts.

---

## Suggestion 1 — Make the "who's a bot" threshold relative, not fixed

**The current setup.** The hook has a number, `exemptPriorityFee`, set once by whoever deploys the pool. If your
priority fee is below that number, you pay zero tax. Above it, you start paying.

**Why that's a problem.** A fixed number is only correct for the network conditions that existed the day it was
set. Gas markets move — sometimes the entire network gets busy (a popular NFT mint, a big news event) and *every
transaction's* priority fee rises, including completely ordinary users who just want their trade to go through
reasonably fast. If your threshold was tuned for a calm day, on a busy day it starts taxing regular people who
aren't racing anyone — they're just paying what the whole network happens to be paying that hour. Conversely, on
an unusually calm day, a bot could get away with a priority fee that used to look aggressive but now sails under
the old threshold untaxed.

**What we'd build instead.** Instead of one fixed number, the hook keeps a running average (a "rolling EMA" —
exponential moving average, a fancy way of saying "the recent average, weighted so newer numbers matter more") of
the priority fees it's *actually seen* on that specific pool recently. Every time a swap happens, the hook quietly
updates this average by a tiny bit. Then, instead of "tax anything above 2 gwei," the rule becomes "tax anything
paying, say, 3x more than the pool's own recent average priority fee." No owner has to log in and manually adjust a
setting when gas prices change across the network — the exemption line moves by itself, automatically, because it's
defined *relative to* what's normal right now, not to a number someone guessed months ago.

**Worked example.** Say the recent average priority fee on this pool has been 1 gwei for the last hour (calm
network). A bot racing to arbitrage a price move bids 8 gwei to guarantee it wins — that's 8x the recent average,
way above the 3x line, so it gets taxed hard. Now imagine a viral NFT mint happens and the *whole network's*
average priority fee jumps to 10 gwei for an hour. Under the old fixed-threshold design, an ordinary user paying 10
gwei just to get included at all would suddenly look identical to a bot and get taxed. Under the new relative
design, the pool's own rolling average also rises to roughly 10 gwei during that busy hour, so a normal user paying
10 gwei is now *at* the average, not 3x above it — untaxed. Only someone still paying wildly more than everyone
else *during that same busy hour* — a real racer — crosses the line.

**What it fixes.** Directly answers the weakness "the tax can't tell a genuinely urgent normal user from a bot" —
by defining "suspicious" relative to right-now conditions instead of a stale, manually-set guess.

---

## Suggestion 2 — Add a second, absolute cap on the tax (not just a percentage cap)

**The current setup.** The tax is `min(k × (priorityFee − exemption), maxTaxPpm)` — a percentage of the trade, capped
at a maximum *percentage* (`maxTaxPpm`, e.g. never more than 3% of the trade no matter what).

**Why that's a problem.** A percentage cap still scales with trade size. If a huge, completely legitimate trade
(say a fund moving $2,000,000 through the pool because they have a real, non-MEV reason to do it quickly, e.g. a
market-moving event they need to react to) happens to be paying a high priority fee for entirely honest reasons —
maybe they just want certainty of execution — a 3% cap still means a $60,000 tax bill. That's not proportional to
any MEV they're actually capturing; it's proportional to the size of their trade, which isn't the same thing. A
percentage-only cap can turn "please definitely include my trade" into an accidental tax on being big.

**What we'd build instead.** Add a *second*, independent ceiling: no matter what percentage math says, the tax
can never exceed some fixed absolute amount per swap (e.g., "never more than 500 USDC-equivalent in a single
swap," set per pool). The final tax is whichever is *smaller* — the percentage-based number, or this hard dollar
ceiling.

**Worked example.** Trade A: $500 swap, aggressive priority fee, percentage math says tax = $15 (3%). The absolute
cap (say $500) is way above that, so nothing changes — $15 tax, as before. Trade B: $2,000,000 swap, same
aggressive priority fee, percentage math says tax = $60,000 (3%). But the absolute cap says "never more than $500
per swap," so the actual tax charged is $500, not $60,000. The whale's tax bill stops scaling linearly into
absurdity just because their trade was large.

**What it fixes.** Prevents the mechanism from accidentally punishing "big and honest" the same way it punishes
"small and predatory" — a fairness gap a competitor or a real institutional LP would call out immediately.

---

## Suggestion 3 — Wrap MevTaxHook inside your own Guard Hook

**First: what even is Guard Hook, in one sentence?** It's the third project you built this hackathon — a
"supervisor" hook that sits between the pool and any *other* hook, and after every action, double-checks that
nothing crazy happened (fees didn't exceed some safe maximum, the pool's balance didn't drain faster than a safe
limit, the price didn't move further than allowed in one block) — and if something did, it can pause the pool
instead of letting the damage happen. Think of it as a circuit breaker or a seatbelt that doesn't care *which*
hook is driving — it just makes sure nothing goes past a hard safety line, no matter what the inner hook's logic
does or gets wrong.

**Why put MevTaxHook inside it specifically?** Right now, MevTaxHook trusts its own owner completely. Whoever
deploys the pool sets `taxPpmPerGwei`, `exemptPriorityFee`, and `maxTaxPpm` — and if that owner makes a mistake (or
turns malicious, or their private key gets stolen), they could, in theory, set an absurd tax rate and start
draining ordinary users' trades. There is currently *nothing on-chain* stopping that except "trust the owner
key holder." That's exactly the kind of single point of failure that killed real hook-based protocols this year
(Bunni lost $8.4M despite professional audits, because the audits checked the code but nothing forced a *runtime*
ceiling on what the code was allowed to do once deployed).

**What it fixes, concretely.** If MevTaxHook is wrapped by Guard Hook, Guard Hook enforces an outer, independent
"fees can never exceed X%" rule that MevTaxHook's own owner *cannot override*, no matter what they set inside
MevTaxHook itself. Even a fully compromised or malicious MevTaxHook owner can now only ever tax up to the ceiling
Guard Hook allows — a second, independent lock on the same door. It turns "trust us, we'd never set the tax too
high" into "even if we wanted to, we mathematically can't."

**Why it's easy for us specifically.** You already built the base contract (`GuardedHook.sol`) that inner hooks
inherit to work with Guard Hook — there's no research needed, just wiring MevTaxHook to inherit from it and adding
a demo showing the safety rail in action (e.g., try to configure an absurd 90% tax, watch Guard Hook reject the
transaction). It also turns three separate hackathon projects into one coherent, cross-referencing portfolio
instead of three unrelated repos — a stronger story for judges evaluating "does this person understand the whole
hook ecosystem, or did they just build three disconnected things."

---

## Suggestion 4 — Add a price-band check as a second layer, on top of the tax

**What this actually is, simply.** Right now, MevTaxHook only asks one question: "is this transaction paying an
unusually high priority fee?" It never looks at *what the trade actually does to the price*. Suggestion 4 adds a
second, independent check, reusing logic you already wrote for your Market Hours Hook project: "did this trade
also move the pool's price by more than some safe amount in one go?"

**Why add it.** A high priority fee alone doesn't necessarily mean damage was done — someone might pay a lot just
to be fast without moving the price much. The trades that actually hurt LPs and ordinary traders the most are the
ones that are *both* racing (high priority fee) *and* moving the price a lot in one shot (the kind of trade a
sandwich attacker or a large arbitrage bot makes). By only reacting when *both* conditions are true, we can be
more targeted: don't touch trades that are fast but harmless, only intervene on trades that are fast *and*
damaging.

**How it would work.** In `beforeSwap`, alongside the existing tax calculation, check: would this trade move the
pool's price by more than, say, 2% in this single block? If yes, *and* the priority fee is also elevated, apply a
stricter response — either a higher tax specifically for that combination, or (borrowing directly from Market
Hours Hook's existing price-band code) temporarily reject trades that would blow through the band entirely, the
same way that hook already protects against runaway price moves during closed-market hours.

**What it fixes.** Answers the honest weakness that "MevTaxHook only taxes racing, it doesn't look at harm" — this
adds a harm-aware layer without needing to build anything new from scratch, since the price-band logic already
exists in a sibling project.

---

## Suggestion 5 — Backrunning: let the hook capture value *for the victim*, not just tax the bot

**What is "backrunning," in plain terms?** When a trade moves a pool's price, it briefly creates a small,
free arbitrage opportunity right afterward — the pool is now slightly "wrong" compared to the rest of the market,
for a moment, until someone corrects it. A "backrun" is a trade placed *immediately after* another trade,
specifically to capture that leftover correction opportunity. Normally, a bot does this — they watch the mempool,
see your trade about to land, and place their own trade right after yours to scoop up the little bit of value your
trade just created. This is a real, constant source of income for MEV bots, and today, none of it goes to you, the
person whose trade actually created the opportunity in the first place.

**The idea.** Paradigm's own research paper (the one that invented the "MEV tax" concept we're already using) also
describes a second half of the idea that we haven't built yet: instead of just taxing the *bot* that backruns you,
what if the hook itself executed the backrun *on your behalf*, atomically, right after your trade, and gave that
captured value back to *you* (or split it with the LPs) instead of letting an external bot get there first?

**Worked example.** You swap $10,000 of USDC for ETH. This slightly moves the pool's price. Normally, within the
same block or the very next one, an arb bot notices the tiny price gap this created and trades against it for,
say, $8 of profit — money that came from a price movement *you* caused, that you'll never see. With backrun
capture, the hook itself (or an authorized process it triggers) executes that same corrective trade automatically,
in the same transaction as your swap, and routes that $8 to you or to the LPs instead of to an anonymous bot who
was simply watching and waiting.

**Why it's a bigger swing than the others.** This is meaningfully more complex to build correctly (you have to be
careful the hook's own backrun doesn't create new exploitable behavior, and correctly calculating the "right" size
of a backrun on-chain has real edge cases). It's suggestion #5 for a reason — it's the most ambitious, most novel,
and most work, not a quick fix. But nothing in the 126-project dataset or the current UHI9/UHI10 chatter does this;
today, every priority-fee-tax project (including our current version) only implements the "tax the racer" half of
Paradigm's idea, never the "give the leftover value back to the person who created it" half.

---

## Suggestion 6 — Explicitly handle coexisting with Uniswap's PFDA

**The situation.** Uniswap's own protocol-level mechanism (PFDA, described in chapter 07) and our hook are both
trying to capture the same pool of value — the MEV that would otherwise leak to outside bots. If both are active
on the same pool at the same time, it's not currently clear whether they interfere with each other: does PFDA's
mechanism already reduce the amount of MEV available for our hook to tax, effectively taking a cut before we ever
see it? Could the two together over-tax a single trade, taking *more* combined value than either would alone,
which would just push traders to a different pool entirely?

**What we'd build.** A small check inside `beforeSwap`: read the pool's current protocol fee (which reflects
whether PFDA-driven mechanisms are already active on it) and, if it's nonzero, automatically scale our own tax
down proportionally — so the *combined* bite (protocol-level + our hook) never exceeds a sensible total ceiling,
regardless of how the two mechanisms happen to interact underneath.

**Why this matters even though it's "just" a defensive feature.** Right now this is an open question the research
flagged as unresolved — and an unresolved question is exactly the kind of thing a sharp judge, or a real pool
deployer deciding whether to turn this hook on, will ask about first. Having a concrete, tested answer ("here's how
we behave when PFDA is also active, here's the math, here's the test") turns a weakness into a demonstrated,
deliberate design decision — which reads completely differently in a demo or an audit than silence on the topic.
