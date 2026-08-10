# The Rules That Never Bend

Everything else in this manual is a judgment call the system makes with evidence behind it. These four aren't. They're absolute, they don't get weighed against anything, and every skill in the repo is written to check them before it produces a single word.

## Never disclose the tool

No draft, ever, mentions x-ops, a reply assistant, or any of this machinery — not as a joke, not as an aside, and especially not on a post about AI writing, which is exactly where the instinct to mention it is strongest and the cost of giving in is highest. You said the reasoning yourself, and it's the whole argument:

> we can't tell people on X like we are creating a X replier, that's devalue the trust in a person. We are trying to sound humane and sound like me so that in future no one could tell. but if you tell them we are creating something like this then they will judge your future replies like that only.

One reply saying "I'm building a thing that writes my replies" reframes every reply you've ever sent and every one you send after. It can't be walked back the way a bad draft can. Whether to talk about x-ops publicly is entirely your call, made deliberately, whenever you decide to make it — never something a draft slips in on your behalf.

This rule is narrow. It is not a ban on talking about what you build. Lifelog, job-ops, learn-ops, the Uniswap hooks, git-in-Go — all fair game, all mentioned constantly in the posts this system helps assemble. The silence is specific to x-ops alone, and that specificity is the point.

## Never fabricate a belief

Conviction-mode replies and the conviction post series fire only on positions already written down somewhere real — the lifelog, the harvested reply corpus, or `job-ops/profile/writing-samples.md`. If a belief isn't already on record, the honest output is no draft at all, not a plausible-sounding guess.

Putting a stance in your mouth in public, on your real account, with roughly a thousand real followers watching, is the single worst failure this system could produce — worse than a bad voice, worse than a missed post, worse than anything reversible. A bad draft costs you a moment of editing. A fabricated conviction, once sent, cannot be taken back in any way that matters.

## Never post

Every skill in this repository fills a composer or writes to a draft cache, and stops there. That includes the panel that used to exist inside the extension — it could send directly from an in-page list, at your explicit request, on a draft you were looking at, one deliberate click at a time — and it's gone now, replaced by tabs you open and act on yourself, because even a click that felt supervised was still a click the system made instead of you.

The deeper reason isn't caution about automating the account, real as that concern is. It's that **the edit you make between draft and send is the entire training signal.** A draft sent unchanged and a draft cut in half are completely different pieces of evidence about your voice. Automate the send and that evidence stops existing — not gets worse, stops existing, permanently, because there's no way to recover an edit that was never made.

## Never a cron, never open search by default

Three surfaces are allowed to go find posts on their own: the extension, watching the timeline you're already scrolling; `/x-hunt`, which reads your feeds and Lists before it ever searches, and searches last and least; and `/x-engage`, which visits only named people from an active cohort or your quiet circle members. All three run only when you invoke them. `/x-reply` never fills its own queue — an empty queue is a good day, not a gap to close. Nothing in this repository is wired to a schedule, because X is your identity and your real followers, not a feed to be polled while you're not looking.

## One more, not absolute but close: the budget stays off

`state/config.json` sets `budget.enforce: false`, and that was your call, made directly, with reasoning that still holds: a taste model with nothing in the log needs volume before it can learn anything at all, and a cap on a cold-start system throttles the learning rather than the habit it's supposedly protecting. The counters keep running regardless, because `/x-taste` needs the real numbers to work from. Turning enforcement back on is a one-word change in a JSON file, whenever you decide the habit needs managing by something other than you.

## What's still unproven, said plainly

The pulse log from Chapter 2 starts at zero. Every reciprocity number, every cohort verdict, every per-series post number is only as good as the `/x-pulse` habit — skip it for a month and the relational half of this system is a guess wearing a query's clothes. No cohort experiment has actually finished yet; `probe-1` is seeded and waiting on a hand-picked list, which means "people engage back if you engage with them" is still a hypothesis, not a finding. And wave-riding, the `/x-hunt --now` mode, says its own limit out loud every time it runs: velocity at twenty minutes is a weak predictor, most fast posts stall, and the ones that reliably go viral are usually the engagement bait the rest of this system exists to reject. When it comes back with one post, or none, that's the system working correctly, not underperforming.
