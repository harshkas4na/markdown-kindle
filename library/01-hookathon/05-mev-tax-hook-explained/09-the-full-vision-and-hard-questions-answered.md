# 09 — If We Build All of This: The Full Story, and Every Hard Question Answered

## Part 1 — The narrative, if all six suggestions ship

Picture the finished pitch, walking through it top to bottom:

**"MevTaxHook turns Uniswap's biggest structural leak — the money LPs quietly lose to arbitrage bots every single
day — into LP income, automatically, with no oracle, no off-chain infrastructure, and no possibility of the funds
ever getting stuck."**

Every swap on a pool using this hook passes through `beforeSwap`. The hook reads the transaction's priority fee —
how much extra the trader paid to jump the queue — and compares it not to some number a human guessed months ago,
but to a **live rolling average of what this specific pool has actually seen recently** (Suggestion 1). If the fee
is unusually high *relative to right now*, the hook knows this trader is probably racing someone, because on
Unichain, priority fee is the *only* way to buy your place in line — there's no side door, because Flashblocks
enforce that ordering rule inside sealed, tamper-evident hardware.

The tax charged scales with how aggressively they're racing, but it's capped two different ways at once — a
percentage ceiling so no single trade can ever be taxed away entirely, and an **absolute dollar ceiling**
(Suggestion 2) so a legitimately huge, honest trade never gets punished just for being large. The exact tax amount
is pulled out of the swap and, in the very same transaction, **donated straight to the pool's LPs** — never sitting
in the contract even for one block, so there's no reserve that can ever get orphaned or stuck.

Layered on top, a **price-band check** (Suggestion 4) means the hook doesn't just react to speed — it specifically
watches for trades that are *both* racing *and* moving the price hard, the exact signature of the trades that do
real damage, borrowing logic already proven in the sibling Market Hours Hook project. And where today's version
only taxes the winner of the race, the upgraded version can go further and **capture the small leftover arbitrage
opportunity a trade creates and route it back to the trader or the LPs instead of an outside bot** (Suggestion 5,
"backrunning") — turning a purely defensive mechanism into one that actively returns value nobody currently
collects on your behalf.

The whole thing is wrapped inside **Guard Hook** (Suggestion 3), an independent safety supervisor from the same
project portfolio, so even a compromised or careless MevTaxHook owner is mathematically incapable of setting a tax
rate above a hard, externally-enforced ceiling — a real answer to "how do I know this hook won't be misused,"
instead of just "trust us." And it knows how to behave politely next to Uniswap's own protocol-level PFDA
mechanism (Suggestion 6), automatically backing off its own tax when the protocol is already capturing value on
that pool, so the two mechanisms complement rather than compete.

The result: a single, compact hook that (1) is provably, not probabilistically, correct about who's racing; (2)
can never hold or lose user funds; (3) can't be pushed past a safety ceiling even by its own operator; (4) targets
actual harm, not just speed; (5) actively returns value to the people who create it, not just the people who tax
it; and (6) plays well with the protocol's own competing mechanism instead of ignoring it. That's the pitch.

---

## Part 2 — Every hard question, answered directly

### "How do you *force* MEV bots to actually pay this tax? Can't they just avoid it?"

We don't force anyone in the sense of a penalty or a punishment — there's nothing to "escape." Here's the actual
mechanics: to win an arbitrage opportunity, a bot has to beat every *other* bot that also sees the same
opportunity. On a chain where transactions are ordered strictly by priority fee (which Unichain's Flashblocks
cryptographically guarantee, no exceptions, no side channel), the *only* way to be first is to pay the highest
priority fee. That competition already exists with or without our hook — bots have always had to bid against each
other to win. All our hook does is sit in the middle of a race that was already happening, and take a cut of the
bid that the winner *already had to pay to win in the first place*. The bot isn't choosing to pay us instead of
something else; they're paying to win the race exactly like before, and we intercept part of that payment before
it disappears to the validator/builder instead. There is no version of "just avoid the tax and still win the race"
available on Unichain specifically, because the TEE enforces that priority fee is the *only* lever that determines
who goes first — no bribes, no private deals, no back door. That's why this mechanism is described as "provable"
rather than "probable": it isn't relying on bots being honest, it's relying on the chain's hardware-enforced rule
that there is only one door, and we're standing at that door.

### "You're not actually stopping sandwich attacks — so how do you protect me as a trader?"

Honestly: **this hook does not protect your execution price.** That needs to be said plainly, because it's true,
and pretending otherwise would fall apart under any real scrutiny. If someone sandwiches your trade, you still get
a worse price than you would have without the attack — this hook doesn't change that outcome for you personally.
What it changes is *where the attacker's profit ends up*. Today, when someone sandwiches a trade or arbitrages a
stale price, 100% of their profit leaves the system into their own wallet. With this hook, a meaningful chunk of
that same profit gets redirected to the pool's LPs instead — the same LPs whose capital made the sandwich or the
arbitrage possible in the first place. So the honest positioning is: **this is an LP-compensation mechanism, not a
trader-protection mechanism.** If someone wants a hook that actually prevents or blocks sandwich attacks from
happening at all (rather than taxing them after the fact), that's a different mechanism family entirely —
encryption-based hiding, or execution delays, or batch matching (families 3, 4, and part of 5/6 in chapter 07) —
and those exist as separate, valid projects with a different goal. We could, if we wanted, layer Suggestion 4 (the
price-band check) to specifically make the *most* damaging sandwich-style trades more expensive or blocked — but
even then, the honest framing stays "we make it less profitable and compensate the victims of the pool broadly,"
not "we make it impossible."

### "Uniswap already has PFDA doing something similar. Why do we need this too? Are we competing with Uniswap?"

Yes, in a real sense, we are — and that's actually the point, not a problem to hide from. PFDA and MevTaxHook both
try to capture value that would otherwise leak to outside MEV bots, but they send that captured value to two
completely different groups of people. **PFDA burns UNI — it benefits people who hold the UNI token.** MevTaxHook
donates directly to **LPs — the people who actually supplied the capital that made the trade possible in the first
place.** Those are not the same group, and reasonable people can disagree about which one deserves the money more.
Our position, stated openly, is: the LPs earned it, because it was their capital being arbitraged against; a token
burn helps a different constituency (governance token holders) who didn't take on any of the risk in that specific
pool. We're not trying to replace PFDA or argue it shouldn't exist — we're offering pool deployers a second,
alternative lever they can choose instead, or (with Suggestion 6) even run *alongside* PFDA in a way that doesn't
double-tax the same trade. The honest way to describe this in a demo: "Uniswap built one answer to 'who should get
this money.' We built a different, LP-first answer, and we made the two mechanisms aware of each other instead of
pretending the other doesn't exist."

### "What exactly does Guard Hook do, and why is it there?"

Guard Hook is a separate hook you built this same hackathon, and its entire job is to be a safety supervisor for
*other* hooks — not just this one. Think of it like this: MevTaxHook's owner sets numbers (how much tax, at what
threshold, capped how high). Right now, those numbers are only as trustworthy as the person or key controlling
them. If that key were ever compromised, or the owner made a careless mistake, MevTaxHook itself has no *internal*
mechanism stopping the tax from being set absurdly high and effectively draining trades. Guard Hook sits
*outside* MevTaxHook, watches every action it takes, and independently enforces a hard ceiling ("fees can never
exceed X%, no matter what the inner hook's own settings say") that MevTaxHook's own owner cannot override, because
the rule lives in a completely separate contract that MevTaxHook doesn't control. It's the difference between "the
babysitter promises not to eat all the candy" and "the candy jar is physically bolted so nobody, including the
babysitter, can take more than three pieces." We're putting MevTaxHook inside Guard Hook specifically because it's
the one project in our portfolio explicitly designed to answer "how do I know a hook won't misbehave, even if its
owner does" — which is one of the single most common objections raised against any hook that has admin-configurable
parameters (and MevTaxHook does have those).

### "What's Suggestion 4 again — the price-band idea — in plain terms?"

Right now, MevTaxHook only asks one question about a trade: "is the priority fee unusually high?" It never asks
"did this trade actually move the price a lot?" Suggestion 4 adds that second question. A trade can pay a high
priority fee without doing much damage (someone just wants speed), and a trade can move the price a lot without
racing anyone (a big, slow, honest trade). The trades that really hurt people are the ones doing *both at once* —
racing *and* moving the price hard. By checking both signals together, instead of just one, the hook gets better at
telling "this trader just wants to be fast" apart from "this trader is exploiting a price gap aggressively" — and
we get to reuse code you already wrote and tested for a different project (Market Hours Hook's price-band logic),
so it's cheap to add.

### "What is 'backrunning' — Suggestion 5?"

When your trade goes through, it nudges the pool's price slightly. For a brief moment afterward, the pool is
priced a tiny bit "off" compared to the rest of the market — and whoever trades against that gap first pockets a
small, essentially free profit. That's a backrun: a trade placed right after yours specifically to grab the small
leftover opportunity your trade created. Today, an outside bot does this constantly and keeps 100% of that profit,
and you'll never see a cent of it, even though your trade is what created the opportunity. Suggestion 5 is: what if
the hook did that corrective trade itself, automatically, in the same transaction as your swap, and gave that
small profit to you or the LPs instead of an anonymous bot who was simply watching and waiting to pounce? It's the
most ambitious of the six suggestions because doing this safely and correctly on-chain is genuinely harder than the
others — which is exactly why it's positioned as the "bigger swing," not a quick fix.

### "What's Suggestion 2 again — the absolute cap?"

The tax today is calculated as a *percentage* of your trade. A percentage always scales with size — so a giant,
completely honest trade that happens to pay a high priority fee (maybe the trader just wants certainty, nothing
shady) could get hit with a huge dollar tax purely because the trade itself was huge, even though the *behavior*
wasn't necessarily any more predatory than a small trade doing the exact same thing. Suggestion 2 adds a second
rule on top: no matter what the percentage math says, the tax can never go above some fixed dollar amount per
swap. Whichever number is smaller — the percentage-based one or the fixed dollar ceiling — is what actually gets
charged. It stops the mechanism from accidentally being harshest against the people doing nothing wrong except
being large.

### "What happens if the exemption threshold or tax rate gets set wrong?"

Today: nothing stops it except human judgment, which is exactly the gap Suggestion 3 (Guard Hook) and Suggestion 1
(relative, self-adjusting threshold instead of a fixed guess) are built to close. Suggestion 1 means the threshold
mostly can't go "stale" because it moves with real, observed network conditions instead of staying frozen at
whatever number someone typed in once. Suggestion 3 means even if a human still sets something wrong (or
maliciously), there's a hard outer ceiling enforced by a separate contract that can't be talked out of its rule.
Together, they turn "we hope the owner tunes this correctly forever" into "the system self-corrects most of the
time, and can't be pushed past a safe limit even when it doesn't."

### "Is this only useful on Unichain? What happens if Unichain doesn't take off?"

Yes — today, the mechanism's core promise ("the priority fee is a truthful signal") is only *provably* true on
Unichain specifically, because that's the one chain currently offering hardware-enforced priority ordering via
Flashblocks. On a chain without that guarantee (including Ethereum mainnet today), the same code would still run,
but the assumption underneath it gets weaker — a sophisticated bot could theoretically find other ways to secure
priority that don't show up as a public priority fee, meaning the tax would only catch less-sophisticated actors,
not all of them. This is a real, stated limitation, not a hidden one — chapter 06 calls it out directly as the
single biggest structural risk of the whole design. The honest mitigation: this isn't a bet on "Unichain succeeds
as a brand," it's a bet on "provable priority ordering inside a TEE is a good idea that other chains will likely
copy" — and if that happens, this same mechanism becomes valid wherever else it's adopted, without needing to be
rebuilt.

### "Does this actually reduce total MEV in the world, or just move money around?"

Just moves money around — and that's worth being upfront about. This hook does not make the underlying arbitrage
opportunity disappear; the price gap that gets exploited was always going to get closed by *someone*. What changes
is who ends up holding the profit from closing it: today, 100% goes to an outside bot's wallet; with this hook, a
meaningful share instead goes to the LPs whose capital was exposed to that opportunity in the first place. Compare
that honestly to families 3, 4, and 6 from chapter 07 (encryption, batching, TWAMM) — those *do* genuinely reduce
the total amount of MEV available to extract, by removing the information or the atomic-trade window bots need in
the first place. This hook is a redistribution mechanism, not a reduction mechanism, and that's a legitimate,
useful thing to be — it's just a different claim than "we made MEV smaller," and the pitch should never blur that
line.
