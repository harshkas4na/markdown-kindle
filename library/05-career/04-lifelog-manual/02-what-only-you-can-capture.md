# What Only You Can Capture

Commits prove you wrote code. They cannot prove why, what you decided against, what you learned, what you think, or what you posted. That half of the record has exactly one source, and it's you hitting ⇧⌘J.

This chapter is about doing that well, which is mostly about doing it *less* than you'd think.

## The window

⇧⌘J, from anywhere, over whatever you're in. Five fields, one of them required:

| Field | What it's for |
| --- | --- |
| **type** | `Auto`, or pick. The menu order is fixed on purpose so it stays muscle memory |
| **tags** | `#lifelog` — a tag naming a known project files the event under that project |
| **title** | the one line every digest will show you three months from now |
| **body** | multi-line: the rough script, the announcement, the actual argument |
| **link** | the X post, the video, the article |

Return saves. Escape cancels. **⌘↩ saves from inside the body**, where Return is a newline. If a URL is already on your clipboard it pre-fills the link field, because that's usually why you hit the hotkey.

The whole point of the window is that it's not a text box any more. A rough video script goes in the body. A post goes in with its URL. An announcement goes in whole.

`me capture` opens the same window from a terminal, and works even when the hotkey doesn't.

## The title is the only line that survives

Everything else is detail a digest shows underneath. The title is what appears in `me week`, in `me events`, and in the line an AI reads while deciding whether to touch `skills.md`.

So write it as the line you'd want to read in three months, not the line that's fastest to type now.

- "fixed the thing" → useless in a week
- "core.hooksPath overrides .git/hooks entirely, not merged with it" → still useful in a year

You're not writing for now-you, who has all the context. You're writing for the version of you who has forgotten, or for a model reconciling `facts.yaml`.

## Prefixes still beat the menu

Typing a prefix is faster than reaching for the popup, and it wins over it:

```
idea: decay curve so skills.md stops lying about me
learned: core.hooksPath overrides .git/hooks entirely
post: shipped my own lifelog in Go today
ship: lifelog v1 #lifelog
decision: no model in the commit path — a guessed summary is worse than none
just a plain thought          → logged as a thought
```

`idea` `learned`/`til` `post`/`x`/`tweet` `opinion`/`take` `ship` `decision` `question`/`q` `bug` `read` `blocked` `win` `note` `article`. Unknown prefix? Kept verbatim, typed as a thought. Capture never rejects input — a box that argues with you is a box you stop using.

## What's actually worth capturing

The test: **would a commit already prove this?** If yes, don't type it.

Worth capturing:

- **Decisions and the reason.** "Chose cursors over timestamps because a clock-based query silently skips backfilled events." Six months from now the code shows *what*; only this shows *why*, and the why is what makes an interview answer.
- **Learnings.** The thing that cost you two hours. `learned: an ad-hoc signature pins the TCC grant to the cdhash, so every rebuild silently revokes Accessibility.`
- **Opinions and takes**, especially ones you'd defend. These are the raw material for posts, and they're what `Personality & Voice` and `voice.md` are built from.
- **Posts and videos, with the link.** The log is the only place your own output gets recorded — X is deliberately not polled, because you should log the ones worth logging and nothing else.
- **Blockers and wins.** Both are invisible in git. A blocker that lasted three days is a story; a win nobody wrote down is gone.
- **Ships.** The moment something is actually usable, which is never obvious from the commit graph.

Not worth capturing:

- What you just committed. It's already there, with file counts and dependency diffs.
- Status updates for yourself. That's what `me status` is for.
- Anything you'd have to invent. An empty log is honest; a padded one poisons every sink downstream.

## Tags do real work

A `#tag` naming a known project attributes the event to that project, which is how a stray thought ends up in the right note in the vault instead of a general pile. The mapping is `project_names` in `~/.lifelog/config.json` — repo directory to canonical name, so one project reads as one project everywhere.

Bare words in the tags field count too. Nobody types the `#` when the box is already labelled "tags".

## From a terminal

```sh
me jot "shipped the capture panel #lifelog"
me jot --type post --link "https://x.com/0xkasana/status/..." "the thread on decay"
me jot --type learned "flock before append, or two repos interleave a line"
```

Useful mid-session when your hands are already on the keyboard and the window would break flow. Same parsing, same fields.

## The honest bit about frequency

You will capture a lot in week one and then taper. That's fine and expected — the commit half keeps running regardless, so a quiet week still produces a real record.

The failure mode isn't capturing too little. It's capturing *noise*: reflexively logging every small thing until the digest is mostly filler and the sync starts writing filler into `skills.md`. Two good captures a week beats twenty thin ones, because everything you type here eventually argues for a change to a file that describes you.
