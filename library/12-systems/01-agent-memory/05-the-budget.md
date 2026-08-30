# The Budget

**Fast overview:** The most likely way this system fails is not a missing feature. It is succeeding at collection and then dumping two thousand tokens of plausible junk into every session's opening context, where it displaces real work and gets skipped. There was a directly applicable precedent on the same machine, and its lesson was applied to context the way it had been applied to pixels.

## The precedent

A live command centre had been built for these ops repos a few days earlier. Its first version put **229 discrete things, 153 of them clickable, and 2,297 words on one page.**

The reaction to it was the correct one: he could not read it or act on it. The rebuild got the main screen down to twelve things, eight clickable, forty-four words. Same data, same repos.

Four rules produced that, in priority order:

1. **One screen answers one question.**
2. **Rank and cluster; never list.** Thirty-nine overdue rows are one fact with a count and a worst member, not thirty-nine rows.
3. **Never put your schema in the UI.** Fourteen filter chips existed because `type` was a field in the JSONL. Nobody had ever wanted to filter by it.
4. **Show what is active.**

A session-start digest is a screen. The same four rules apply, and there is a reason to take them even more seriously here: a person can visually skip a bad UI in a quarter of a second, whereas injected context is paid for in full whether it is used or not.

## The budget is enforced in code

Thirty-five lines, hard. Not a guideline, not a comment, an actual cap in the renderer with a check that fires if the output ever exceeds it.

The budget is **spent, not filled**. Sections are offered lines in priority order and each one gets what is left over after the ones above it. That is what makes "open loops first" a real guarantee rather than a preference that quietly loses to a chatty section higher up the file.

Tested with sixty extra entries added to a scope: the digest still rendered in sixteen lines, open loops were still the first section, and the hidden entries were counted rather than silently dropped.

## What the digest actually shows

```
  agent-memory · job-ops · 14 live · 3 stale

  OPEN LOOPS
    · resume-tailoring rewrite half-done                              4d
      next: wire scorer into apply-pack
    · ats-score returns 0 for PDF resumes, unfixed                   11d

  TRAPS
    · page-text read after SPA nav returns the PREVIOUS page  [5x]
    · launchd PATH excludes homebrew and nvm node             [3x]

  DECIDED
    · autoapply stays C-lane only                            2026-08-12

  3 entries drifted, their files changed
```

**Open loops first**, because it is the highest-value line on the screen and nothing else on the machine carries it. Git can tell you what changed. Only this can tell you what you were in the middle of.

The reasoning is carried for exactly two kinds: `state`, because an open loop without its next step is just anxiety, and `decision`, because a fork without its reasoning cannot be re-evaluated. For everything else the claim stands alone.

Claims are clipped at 96 characters in the render. That is a backstop rather than a fix. The real fix is short claims, and the write path warns when one runs long: a claim is one sentence, and anything longer is usually two memories that will never be independently confirmable.

## The line that gets shown when there is nothing

There is one more thing the digest can honestly say, and it turned out to be the most useful line in the whole system.

If a repo has no memories but sessions have run there, the digest says so: *84 sessions ran here and left nothing behind, 90h.*

That is real information. It distinguishes a repo nobody has opened from a repo where ninety hours of work evaporated. And it is the honest alternative to the tempting thing, which would be to generate a summary from the transcripts to fill the gap. That would need a model, and the standing invariant on this machine is that a guessed summary is worse than none, because the next session cannot tell it apart from an observed one.
