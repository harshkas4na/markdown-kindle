# Your Own Posts

Replies react to other people. Posts are the other half — the ones on your own timeline — and until this layer existed, nothing in the system touched them at all. The idea for it came out of a raw thinking session you wrote yourself: *"maybe JobOps ki day 14 of applying to this this company... ek daily ka learn-ops article... next video updates what's I am reading watching for this rn."* You already had the material scattered across three pipelines. What was missing was the assembly step, so your attention could go to the parts only you can write.

## What a skeleton owes you, and what it doesn't

`/x-post` produces skeletons, not finished posts, and the distinction is load-bearing. The fact assembly — counts, dates, what shipped, what broke — is the tool's half. The reaction is yours. A skeleton leaves marked gaps exactly where the post needs the thing only you have: `[your take]`, `[ss]`. It never fills those in for you, because the draft/final pairs in Chapter 1 already proved the rule that governs this: beliefs sourced from your own writing survive your edits, beliefs composed for you don't. There's no reason posts would work differently from replies on that point, so the skill doesn't try.

## The seven series

**Job-ops day-N** pulls real counts from `applications/` and lifelog `win`/`blocked`/`learning` events tagged JobOps — the funnel, the process, what a stage felt like. Company names in active processes never appear; a company is only nameable once its outcome is final, and even then it's flagged for your call rather than assumed. Numbers are never rounded up. A build-in-public series with an inflated number in it is worse than no series at all.

**Today's learning** is deliberately unfinished. It names the concept and why it grabbed you, then stops — the explanation is your job, with a `[ss]` slot for the screenshot. If the skill explained the concept fully, the post would be homework with your name signed to it, which is precisely what your own feed position argues against.

**Behind the scenes** takes one moment from the last few days of lifelog `ship` or `decision` events — the "so I built it" arc that's your single strongest signature as a writer: friction stated as a small story, "so I built...", one-line result, wry aside in parentheses. Other projects are fair game here — lifelog, job-ops, learn-ops, the Uniswap hooks, git-in-Go, all of it. One project is never mentioned, and Chapter 7 explains exactly why.

**Project update** is the arc rather than the moment — everything that happened on one project since the last update, checked first against `xo posts` so it continues instead of repeating.

**Bug story** only fires on lifelog `bug` events that have a real cause recorded. Your register for this already exists — flat failure, no "learnings" dressed up as growth, then the fix — and this series is arguably the most valuable one you can post, because it's the one genre nobody can fake without actually having done the work.

**The system post** explains how one of your systems — job-ops, learn-ops, the lifelog itself — actually works, in the teaching voice you already use: `>` step lists, "see it like this." It has to quote the system's real numbers, never a flattering version of them.

**Conviction** only fires on beliefs already written down somewhere real — a lifelog `opinion` event, or something already in `job-ops/profile/writing-samples.md`. If the belief isn't already on record, this series produces nothing rather than guessing, for the same reason conviction-mode replies work the same way.

## Closing the loop

Every skeleton handed over gets logged: `node bin/xo post <series> "<text>"`. That single line is what turns posting from something that happens into something that can be learned from — `/x-pulse` matches incoming engagement against these logged skeletons and reports per-series numbers, the same way it reports per-person reciprocity. Without that log, the post side would produce forever and never find out which series is actually worth the effort. With it, the question "which kind of post should I write more of" has an answer instead of a hunch.
