# A Day in the Log

Everything so far has been the model. This chapter is the thing itself: an ordinary day, what you do, what lands in the log, and which system downstream ends up changed by it.

> The events below are written as examples, not copied out of your log. The log never leaves the machine — it doesn't get pasted into a repo, and this book lives in a public one.

## An ordinary Tuesday

**09:40 — you fix a bug in the MEV Tax hook and commit.** You do nothing. The global hook fires.

```json
{"type":"commit","source":"git","project":"MEV Tax Hook",
 "title":"fix(hook): donate to in-range LPs only",
 "meta":{"shape":"3 modified · +48/-31 · langs: sol · areas: src, test · tests touched"},
 "key":"<sha>"}
```

Note what's there and what isn't: file counts, languages, that tests moved. No prose about what the fix *means* — nothing guessed it, because nothing was asked to.

**11:15 — you decide something.** You'd been planning to let the hook read a price oracle, and you drop it. No commit will ever show this; the code that isn't there leaves no trace. ⇧⌘J:

```
decision: no oracle in the MEV tax path — priority fee is already on-chain
and free. An oracle adds a trust assumption to save nothing #mevtaxhook
```

```json
{"type":"decision","source":"hotkey","project":"MEV Tax Hook",
 "title":"no oracle in the MEV tax path — priority fee is already on-chain and free",
 "body":"An oracle adds a trust assumption to save nothing","tags":["mevtaxhook"]}
```

Six months from now this is an interview answer about trust assumptions. Without the capture it's gone by Friday.

**13:00 — something costs you two hours.** ⇧⌘J:

```
learned: an ad-hoc code signature pins the TCC grant to the cdhash, so every
rebuild silently revokes Accessibility while the toggle still reads on
```

Type `learning`. This is the highest-value shape in the whole log: a fact that cost you real time, written down once. It ends up in `learnings.md` and, when it's the kind of thing that shows depth, in the story bank.

**16:30 — you publish a video and post about it.** Copy the URL first; the panel pre-fills the link field from your clipboard. Then type a title, paste the script into the body:

```json
{"type":"post","source":"hotkey","project":"Lifelog",
 "title":"why my profile used to lie about me, and the log that fixed it",
 "body":"open on the drift problem\nshow skills.md claiming a dead project\ncut to the digest",
 "link":"https://x.com/0xkasana/status/...","tags":["lifelog"]}
```

The link is a first-class field, not text inside the body, so a digest can cite it and `skills.md` can carry it as a real link.

**23:50 — the collector runs.** You're asleep. It adds a `pulse` row for the day, any new GitHub activity, and any Medium article that went live.

**Later that week — you sync.** Say *"sync it with current me"*. The decision from Tuesday reaches `stories.md`. The learning reaches `learnings.md`. The post reaches `skills.md` and the vault's writing notes. The commit contributes to MEV Tax Hook still reading `active`.

## Every type, and where it lands

| You do / type | Example capture | Ends up affecting |
| --- | --- | --- |
| **thought** | *"the whole 'build your own tools' thing is getting out of hand in a good way"* | Vault voice notes, `Personality & Voice` |
| **idea** | `idea: an article on why cursors beat timestamps` | `05 Writing/Article Ideas.md` |
| **learning** | `learned: core.hooksPath overrides .git/hooks entirely` | `job-ops/profile/learnings.md`, `02 Areas/*` |
| **post** | `post: the thread on decay` + link | `skills.md` §Writing, `Medium Articles`, voice material |
| **opinion** | `take: a guessed commit summary is worse than none` | `voice.md`, `skills.md` §Worldview |
| **ship** | `ship: lifelog v1 #lifelog` | Project note status, `Timeline`, `Achievements & Proof` |
| **decision** | `decision: no model in the commit path` | `stories.md`, the project's vault note |
| **question** | `q: does TCC key on cert leaf for self-signed?` | Nothing automatically — it's a note to future you |
| **bug** | `bug: mainthread.Call doesn't block despite the doc comment` | `learnings.md` if it generalises |
| **read** | `read: DDIA ch.11 — stream processing is this exact design` | `Reading Library`, `Learning System` |
| **blocked** | `blocked: waiting on Accessibility grant, 3 days` | Honest week notes; explains a quiet stretch |
| **win** | `win: hook V1 deployed and verified on testnet` | `Achievements & Proof`, `hack-ops/prior-art.md` |
| **article** | *(automatic, from your Medium RSS)* | `Medium Articles`, `skills.md` §Writing |
| **commit** | *(automatic, every repo)* | Project status, decay, `prior-art.md`, `velocity.md` |
| **gh** | *(automatic — PRs, releases, new repos)* | Upstream-contribution evidence |
| **pulse** | *(automatic, nightly rollup)* | Proof a day was real work |
| **sync** | *(automatic, written on every ack)* | Answers "when did `skills.md` last reflect reality?" |
| **retraction / amendment** | `me retract <id>` / `me amend <id> "..."` | Resolved on read, in every window, forever |

## Which sink takes what

The same event usually lands in more than one place, framed differently for each reader.

You ship the capture panel. One `ship` event plus the commits behind it, and:

- **secondbrain** updates `01 Projects/Lifelog.md` and adds a line to `00 Me/Timeline.md` — narrative, wikilinked, dated.
- **jobops** may add it to `facts.yaml: projects` and, if there's a story in it, to `stories.md`. Structured truth only; nothing goes in that a form field couldn't quote.
- **portfolio** writes it first-person into `skills.md` — §4.2 if it's a tool you built for yourself, §9 if it's breadth. `app/data.ts` only if it has a public link, because every entry there renders as one.
- **hackops** asks a narrower question: is this reusable in a hackathon? A native macOS panel driven from Go is a Tier-3 asset in `prior-art.md`, because desktop entries usually die on packaging.

Four different readings of one event, and none of them had to be written four times.

## What a quiet week looks like

Three small commits, one `blocked`, nothing else. The digest says so plainly — it collapses the commits into `Also: 3 smaller commits, +40/-12 — chore×2, fix×1` and shows the blocker in full.

That's the system working. A quiet week that reads as quiet is worth more than a padded one, because the alternative is a `skills.md` that describes someone who ships constantly and an interview where you can't back it up.

## What it can't see

Worth being honest about the edges:

- **Work in someone else's repo under a different email** — unless the author regex covers that identity.
- **Anything you didn't commit.** A day of reading, a day of debugging that ended in a revert, three hours on a call. If it mattered, capture it — `blocked` and `learned` exist for exactly this.
- **Whether a deployed thing is still alive.** "No commits in 184 days" means no commits. It does not mean the site is down, and sinks are told so explicitly.
- **Anything that isn't code or a capture.** Design work, a conversation that changed your mind, a decision made in the shower. The hotkey is the only door.
