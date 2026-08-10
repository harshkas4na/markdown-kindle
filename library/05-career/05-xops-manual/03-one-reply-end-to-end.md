# One Reply, End to End

Theory is easier to trust once you've watched it run. Here's what actually happens between a post appearing on your timeline and a reply landing in the decision log — with real mechanics at every step, not a summary of them.

## The mark

The extension watches every article that renders on the page. Each one gets parsed for handle, text, age, reply count, and like count, then batched and sent to `POST /score` on the local daemon. The scorer itself is deliberately dumb — no model, just weights over surface features: whether the poster is in your circle, whether the post describes a mechanism, whether it reads like engagement bait. That's on purpose. Getting the *mark* wrong costs you a glance. Getting the *words* wrong costs your account. Only the second is worth spending a model on.

If it marks, the post gets a blue border and a `stash` / `not for me` row. Both record. `not for me` is worth more than `stash`, even though it feels like the less important button — it's the negative signal a morning brief could never have collected, because nobody writes down what they scrolled past on their own.

## The stash

You hit `stash`. That fires a `stash` event into `decisions.jsonl` with the post's href, text, and the scorer's reasoning attached. The href gets validated the instant it's written — the store rejects anything that isn't a real `/handle/status/id` shape, which is the fix for the one bad write this system ever produced.

## The draft

You (or a morning `/x-hunt`) run `/x-reply`. It pulls the queue — everything stashed with no draft yet — and for each post, opens the actual parent thread. Not the flattened snippet the extension captured; the full post, read properly. This step is not optional and skipping it produces the single most common failure mode: generic affirmation, because the draft was written from 600 characters of stash text instead of an actual understanding of what was built.

Then it picks a mode. `learn` is the one you asked for by name — a post you half-understand, where the reply states your read and leaves the door open for correction:

> so the fee ramps off block delta and the LP eats the difference? or does it get donated back

Or, more precisely for how you actually ask things — the pattern the send log surfaced on its own, three separate times with three separate people:

> what got you most of it? move ordering or the eval fn.
> how deep does it go, actual instruction decode or more of an overview?
> is that a bandwidth thing or you want feedback between them?

You don't ask open questions. You name two plausible mechanisms and ask which one's right. That's not a weaker version of curiosity — naming two candidates proves you already have a model of their thing, which is what makes the question worth them answering. If a draft can't name two, the post hasn't been understood well enough yet to draft the ask.

The draft gets pushed with `node bin/xo draft <statusId> "<text>" --mode learn`, which writes it to the draft cache and logs a `draft` event.

## The guard, quietly, the whole time

While you're typing anything into a real composer — not this draft flow specifically, any composer on the page — a guard is watching, 2.2 seconds after you stop typing, never sooner. It checks for em dashes, hype vocabulary ("delve," "leverage," "seamless"), the "not just X, it's Y" cadence that gives away an LLM, and — the one check here that's about consequences rather than taste — any phrase that would disclose the tool itself. It never blocks. It shows a strip above the composer, and if you dismiss it, it asks for one line of why. That line is the single most valuable record the guard produces, because it's you stating a rule about your own voice in the exact moment it applies.

The guard used to also flag short replies with no lexical content. It fired on "I am the guy" — a joke — and on "you doing goo," which was you mid-word, before "you doing good whatever you are doing boii" was even finished. Both were wrong, both were ignored, and ignoring a wrong warning twice on day one is the crying-wolf failure that makes people stop reading warnings at all. That check was removed. The lesson generalized: **the guard only fires on things wrong no matter what the post above says.** Em dashes are context-free. A three-word reply is not — it might be carrying all its meaning from the thread above it, which the guard structurally can't see.

## The tab walk

Once a batch of posts has drafts waiting, ask for the tab walk. Each drafted post opens in its own Chrome tab, oldest stash first. In each one: the draft sits inline under the post with a `use` button. Click it, the text lands in the composer through a synthetic paste event — the only method that actually works against X's React-controlled composer; a plain `execCommand` insert silently does nothing there. Edit if you want to. Send.

## The send

The moment you click X's own send button, the extension reads what's actually in the composer and compares it to what it loaded. That comparison becomes a `sent` event, with both the original `draft` and the `final` text attached, and an `edited: true/false` flag computed from whether they match. If you never loaded a draft at all — you wrote the whole thing yourself — it still gets logged, unaided, flagged as the cleanest kind of voice sample there is: nothing generated, nothing to compare against, just you.

That one event, sitting in `decisions.jsonl`, is what every later `/x-taste` pass reads to find out whether the draft matched the person you actually are.
