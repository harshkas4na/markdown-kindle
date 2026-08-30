# The Floor

**Fast overview:** Everything so far depends on a session choosing to write something down. That is the same dependency the built-in memory directory had, and it is why that directory is empty. This chapter is about the part that runs whether anyone remembers or not, what it is allowed to record, and the three things the first run got wrong.

## Why a floor is needed at all

A store that only knows about sessions which chose to write to it cannot tell noise from disuse. If the digest is empty, is that because nothing happened, or because everything happened and nobody recorded it? Those need completely different responses and they look identical.

So the floor records **coverage, not content**: a session ran here, for this long, and left this many memories behind, including and especially zero.

## What it is forbidden to record

This is the part that took discipline. The temptation with a mechanical capture is to record everything mechanical: files changed, commits made, tools invoked, a summary of what happened.

All of that is banned, and by the system's own admission rule. Files changed are git's. Commits are lifelog's. And a summary would need a model, which brings back the invariant: a guessed summary is worse than none.

So it records that a session happened, how long it actually ran, how many prompts it received, and how many memories it produced. Nothing interpretive. No title, no topic, no "what this session was about".

## Why it runs after the fact rather than at session end

The obvious design is a session-end hook. It was rejected for two reasons.

First, it needs no hook, so a harness change cannot silently disable it. The hook surface could not even be confirmed on this machine: the Claude bundle sitting in the homebrew path turned out to be a stale copy from over a year earlier with no hook names in it at all, and the binary that actually runs could not be resolved. Building the read path on top of something that could not be verified would have been building on sand. Every ops repo on this machine already opens its `CLAUDE.md` with a session-start line, which is a convention that demonstrably works and needs no API.

Second, and more importantly: reading transcripts after the fact **catches sessions that crashed or were killed**. Those are precisely the sessions most likely to have left something half-finished, and a session-end hook is exactly what does not fire for them.

## Three things the first run got wrong

**553 transcripts, and 308 of them were not sessions.** They were `claude` launched in a directory to type a slash command like `/usage`: six lines, two user records, no reply at all. Unfiltered, they would have been the majority of the store.

The filter is on **content, not path**: a transcript with no assistant turn did no work. That distinction is the entire point. The tempting version of this filter was on location, since most of them lived under `/private/tmp`. There is a standing finding on this machine about exactly that mistake: a cleanup rule written from a path pattern, on the assumption that a temp directory means throwaway content, which would have suppressed seventeen genuine open-source commits made from scratchpad directories. **A cleanup task is still a claim about the data and it needs the same evidence as any other claim.** So the transcripts were opened and read before the rule was written.

**Scope was the most-used working directory, which is wrong.** A session that was launched in `builder-ops` and spent most of its time in `ops-center` got filed under `ops-center`. Worse in the other direction: a `builder-ops` session reading `job-ops` for an analysis would file its memories under `job-ops`, where they are simply incorrect.

The fix came from noticing that Claude Code names a project directory by replacing every non-alphanumeric character of the launch path with a dash. That is lossy going backwards, so the directory name cannot be parsed into a path. But it is **exact going forwards**: slugify each working directory the transcript mentions, look for the one that matches the directory name, and the launch directory falls out unambiguously. Fifteen of 246 sessions were wrong before this.

**One session reported 12,543 minutes.** That is eight and a half days, and it is technically correct: the transcript had been resumed with `--continue` over that span. It is also a useless fact.

The fix is to sum only the gaps a person could plausibly have been present for, under thirty minutes. That session's true figure is 35 minutes of active work across a nine-day span, and both numbers are now recorded separately.

## One rule that is easy to get backwards

Session records are **last-write-wins**. Entries are **not**.

A session record is derived from a transcript that does not change, so re-measuring one is a *correction* and the newest measurement is the right one. An entry is an observation, so a second sighting is *evidence* and accumulates.

Getting this backwards in either direction is a silent bug: corrections that pile up as though they were independent confirmations, or confirmations that overwrite each other and lose the count the entire ranking depends on.

## The schedule

The capture runs nightly through launchd rather than a scheduled cloud runner or cron.

The test for which to use, in this portfolio, is: does the job read anything under the home directory or anything gitignored? This one reads both Claude profile directories and writes to a dot-directory in home. A hosted runner has neither, so it would run green and do nothing.

And cron on macOS silently skips a job whose time passed while the laptop was shut, which for a once-a-day sweep means it never runs on the days the lid closed early. launchd fires it on wake instead, which is the behaviour a habit actually needs.

Verified end to end by forcing a run: exit code zero, real work done, and the correct node binary found, which matters because launchd hands a job a `PATH` of four system directories and nothing else. Every version manager, every homebrew binary, and every user-installed tool is invisible to it unless the path is spelled out.
