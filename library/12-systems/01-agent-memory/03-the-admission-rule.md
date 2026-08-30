# The Admission Rule

**Fast overview:** The mechanism is the easy half. What decides whether a memory store is worth anything is what it refuses to hold, and that rule has to be written before the first entry, not after the first thousand. One sentence does most of the work.

## The rule

> **If a session could learn it by reading the repo for sixty seconds, do not write it.**

That is the whole test. It is deliberately harsh, and applying it honestly rejects most of what a session is tempted to record.

## What is worth writing

Six kinds, and each one exists because something specific goes wrong without it.

**lesson.** Something that behaved differently than it looked. Needs an anchor and a statement of what actually happens. This is the highest-value kind, because it is the one that costs real time to rediscover.

**decision.** A fork taken, with the why. *The why is the entry.* A recorded decision without its reasoning cannot be re-evaluated later, only obeyed, which makes it worse than useless when the circumstances change. This is the one clause of the admission rule that a machine can check, so it is enforced in code: a decision without a reason is refused at write time.

**map.** Where a non-obvious thing lives, when finding it cost real time. Not a directory listing. The thing that took twenty minutes of grep.

**state.** An open loop and its next step. This is the kind that expires by design and decays fastest, and it is also the single most valuable line in a session-start digest, because nothing else on the machine records what someone was in the middle of.

**pref.** A correction the human gave about how to work in this repo.

**artifact.** A branch, a draft, a scratch file that a later session needs to know exists.

## What is never written

Narration. Files changed, because git has them. What a commit did, because lifelog has it. A summary of the conversation. Anything already in the `CLAUDE.md`.

That last one is worth dwelling on. A memory that duplicates the contract is not neutral, it is harmful: it makes the store longer without making it more useful, and if the contract later changes, there are now two versions of a rule and the reader trusts the wrong one.

## The rule in action, which is mostly rejection

The best evidence that the rule works is what happened the first time the system went looking for memories in its own history.

Run against `builder-ops`, mining a 141-minute session produced almost nothing worth keeping. The reason is instructive: that session's learnings had already been written by hand into a findings register, so a session reading the repo would find them in well under sixty seconds. The rule correctly threw them all out.

Run against `job-ops`, which has 84 sessions, 90 hours, and no register of any kind, a single session yielded three real traps in one pass.

**A memory system that accepts most of what it is offered is a transcript with extra steps.** The interesting number is the rejection rate, and it should be high.

## Sensitivity, which is not a judgement call

One property is set by code rather than by rule: any entry written from a client repo is marked as client-sensitive by path, automatically, with no flag to pass and no way to forget.

The reasoning is that a guard which depends on the writer noticing is not a guard. The rest of the sensitivity story is in a later chapter, including the one place where no code check can help.
