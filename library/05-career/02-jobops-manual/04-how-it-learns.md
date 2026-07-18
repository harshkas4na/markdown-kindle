# How It Learns

"Self-improving system" is usually a slide, not a mechanism. Here's the actual mechanism, so you know exactly what to feed it and what it does with the food.

## The loop is a file

`profile/learnings.md` is the entire learning system. It has five sections: what converts, what didn't, form questions seen in the wild, phrases and stories that landed in real conversations, and profile updates pending. Two rules give it power:

1. **`/outcome` writes to it.** Every logged result — a reply to a founder email, a rejection at resume screen, a form question pack.json didn't anticipate — becomes an entry with a date and an honest count.
2. **Every generating skill reads it first.** Tailor-resume, outreach, cover-letter, and apply-pack all consult it before producing anything. A lesson logged Tuesday changes Wednesday's resume. That's the whole trick — there is no model being fine-tuned, just evidence sitting where the generators can't miss it.

## Promote or prune

An append-only lessons file rots into noise, so the weekly review enforces a lifecycle. A learning confirmed three or more times gets **promoted**: it stops being a note and becomes a permanent rule, edited directly into the relevant skill file or `voice.md` (with your OK — recalibrations never apply themselves). A learning contradicted by new evidence gets **deleted**, not argued with. The file should stay short enough to read in a minute; if it can't be, it's overdue for a pruning pass.

This mirrors how you already learn, which is why it'll feel natural: inputs from many directions, outputs tested against reality, and the survivors compressed into intuition — except here the intuition is written down where the next generation run inherits it.

## What counts as signal (small-numbers honesty)

You will not have statistically significant data — you'll have eleven applications and four replies. The review reports counts, never percentages dressed up as insight. Two rejections at the same stage with the same framing is a pattern worth acting on; one is weather. The skills are told to treat it that way, and you should too — recalibrate on repetition, not on single stings.

## The second loop: your public profile

There's a slower loop running underneath. Every new thing the system learns about you — an answer you wrote for a form that said something `stories.md` didn't have, a framing that kept winning — lands in "profile updates pending," and periodically that becomes an edit to the portfolio's public `skills.md`, the file recruiter-side AI agents actually read. Applications sharpen the profile; the profile sharpens applications. You said you want to keep answering questions about yourself and condensing them — this is where those answers become compounding infrastructure instead of scattered notes.

## What starves the loop

One thing only: unlogged outcomes. Silence is data ("ghosted, 14 days" is a channel finding). A rejection is data. An interviewer lighting up at the Terraform-in-Go story is *premium* data — that goes in "phrases that landed" and starts appearing in future letters to similar companies. Thirty seconds of logging per event is the entire tax. Pay it every time, especially when the news is bad, because "what didn't work" is the section that saves you the most hours.
