# Promotion, and Why It Is the Point

**Fast overview:** A memory that has bitten in more than one repo is not that repo's memory any more. Detecting those is the half that makes the store worth more than the sum of its entries, and it feeds something that could not otherwise be built: a pattern detector that can see things which leave no trace in code.

## The mechanism

An entry's id includes its scope. That is correct: a memory about `job-ops` is genuinely not a memory about `x-ops`, even if the words match, because the anchors and the context differ.

But it means the same claim in two repos produces two different ids, and detecting "this has now bitten twice" needs a second key that deliberately ignores scope. That key is a hash of the kind and the normalised claim alone.

When a claim appears live in two or more scopes, it becomes a promotion candidate. Promoting it creates one entry in a `global` scope, recording which repos it came from, and retires the scoped copies with a note pointing at the promotion. Everything appends. Nothing is edited and nothing is lost.

Global entries appear in every repo's digest, capped hard at three. The cap is the point: a cross-cutting lesson only earns its line if it is one of the very few that genuinely applies everywhere, and a global section that grows is a global section that gets skipped.

The mechanism was proved on a real claim. The same trap about stale page reads after a navigation, worded differently and capitalised differently in two repos, matched on the scope-independent key, promoted cleanly, retired both copies, and now appears at the top of every repo's digest on the machine.

## Why this is the interesting half

There is a tool in this portfolio whose whole job is finding what one repo does that another should copy. It works by matching signatures against **code**: does this repo have a control panel, a scheduled sweep, a notification path.

It has a recorded limitation, found the hard way: prose-based detectors produce false negatives that look like real holes. A pattern present under a different name reads as missing, and someone spends an afternoon transplanting something that is already there.

But there is a deeper limit that no amount of signature-tuning fixes. **Experience leaves no trace in code at all.** A trap that cost two hours in one repo and two more in another is invisible to every grep ever written, because the fix for it is usually a line of code that looks completely ordinary, or no code at all.

Promotion sees exactly that. The moment a second repo records the same trap, it becomes visible as a cross-cutting fact, with a count of how many independent sessions have hit it.

So the honest answer to "what does this do for the intelligence layer" is: that layer could previously only see what is *in* the code. This gives it what was *learned* and never written down.

## What it does not do

The promotion feed **proposes** rows for the findings register. It never writes them.

That register belongs to another repo, which owns it, curates it, and applies its own standards to it. A second writer into it would be precisely the duplication that the portfolio's single-source-of-truth rule exists to prevent, and the rows would drift.

Nothing promotes itself either. Promotion puts a claim in front of every future session in every repo, which makes it the highest-leverage write in the system and the one most worth a human look before it happens.

## The guard that lives in one place

A client-scoped memory can never become a promotion candidate.

The check sits inside the candidate-finding function rather than at each call site, and that placement is deliberate: it means there is exactly **one** place in the codebase where it could be forgotten, rather than one place per caller.

This inherits a ruling made earlier on this machine about the same question in a different system. The conclusion there was that suppressing capture from client repos would cost real signal, because that capture is how the record learns from contract work at all, and that the correct place for the guard is the **export boundary** rather than the capture boundary. Promotion is that boundary. The rule is inherited rather than re-argued.
