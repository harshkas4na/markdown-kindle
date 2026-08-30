# Mining the Past

**Fast overview:** Two hundred and forty-six sessions of history were sitting in transcripts, unread. Getting memories out of them requires judgement, and judgement requires a model, which the write path forbids. The resolution is to split the work at exactly that seam, and the seam is the most interesting design decision in the system.

## The seam

**Selection is mechanical. Judgement is not.**

- **The tool selects and quotes.** It finds the passages where a memory is most likely to be hiding and prints them verbatim, with a hard cap. It never interprets, never summarises, never proposes.
- **A session reads that and applies the admission rule**, writing candidates.
- **A human keeps or drops them.** Candidates live outside the store entirely, in their own file, until reviewed.

That last step is not ceremony. A backfilled memory is a guess about the past, and the entire value of the store is that a session can trust what it is told. One unreviewed guess in there devalues everything next to it.

A candidate enters at the lowest confidence level no matter how convincing the passage looked. Promoting one to verified is a separate act that happens after the claim has been re-checked at source.

## What is worth quoting

Two kinds of passage, and both are recognisable without understanding them, which is what makes the extraction deterministic.

**Prompts.** What the human actually typed. There are six of them in a 1,150-line session. They carry the intent and, more valuably, the corrections: the moments where the work was going one way and got redirected. Slash commands and harness plumbing are filtered out, because those are not something a person said.

**Stumbles.** A tool call that errored, followed by a different call to the same tool that worked. That pairing is the literal shape of a trap being discovered, and it is the single richest source of durable lessons in the whole corpus.

Finding the second half of that pair required two passes over the file. The recovery is a call that happens *later* than the error, so an index built while walking forward is always missing exactly the thing being looked for. The first version returned a null fix for every stumble, which does not read as a bug. It reads as "nothing was learned here", which is the most dangerous kind of wrong output: it is indistinguishable from a true negative.

## What it actually found

Mining one `job-ops` session, 539 minutes long, with nothing recorded:

- **`timeout(1)` does not exist on macOS.** A command wrapped in it dies with exit 127. Re-checked directly on the machine before it was accepted: neither `timeout` nor `gtimeout` is present, exit code 127 confirmed.
- **A Chrome tab id goes stale between sessions.** Closing one from an earlier session fails with a message saying the tab group no longer exists.
- **A subagent type takes an agent name, not a tool name.** Passing the latter returns a list of the real ones.

All three are cross-cutting. None of them is written down anywhere else on the machine. Every one of them would have cost time again.

## The rejection rate is the point

Mining `builder-ops` produced almost nothing worth keeping, and that is the system working rather than failing. That repo's session had already written its learnings into a findings register by hand, so the sixty-second test correctly rejected all of them as things a session would find by reading the repo.

The value is concentrated in the repos with no register at all. That is a useful thing to know in itself: it tells you where to point the tool.

## The rule that no code can enforce

Mining `job-ops` printed a client's name to the terminal.

Not because of a bug, and not because the client's repo was being read. Contract work gets discussed in the repo where the opportunities are tracked, not only in the repo where the client's code lives. A conversation about a role, a call, a scope of work, all of it lands in the job pipeline's transcripts.

The path-based sensitivity marking is therefore a **floor, not a ceiling**. It correctly and automatically marks anything written from a client repo. It cannot mark what a transcript from an unrelated repo happens to contain.

So every candidate written from mined material is de-identified by the session writing it: the technical substance is kept, the client is not. This is the one place in the system where a human rule is doing work no code check can do, which is exactly why it is written down explicitly rather than assumed.
