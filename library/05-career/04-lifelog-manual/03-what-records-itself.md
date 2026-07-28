# What Records Itself

Most of the log is written while you're doing something else. This chapter is what happens without you touching anything, and — more importantly — what it deliberately refuses to do.

## Every commit on the machine

One line does it:

```sh
git config --global core.hooksPath ~/.lifelog/githooks
```

That's every repo on this machine, including ones you clone tomorrow, with no per-repo setup and nothing to remember. The installed hooks are dispatchers: they run lifelog's capture and then **chain to whatever hook the repo already had**, so taking over `core.hooksPath` can't silently disable someone's pre-commit. Drop a `.nolifelog` file in a repo root to opt it out.

`me commit-hook` is built so it **can never fail a commit**. It swallows every error and exits 0. A logging tool that blocks a commit is a logging tool you rip out within a week.

## No model in the commit path

This is the design decision worth understanding, because it's the one people get wrong.

Nothing summarises your commit with an LLM. `internal/gitcap` extracts structure deterministically:

- conventional-commit type and scope (`feat(panel):` → type `feat`, scope `panel`)
- files added vs modified vs deleted, insertions and deletions
- languages, and which areas of the tree were touched
- whether tests or docs moved
- and the highest-signal part: **dependency diffs** across `package.json`, `go.mod`, `Cargo.toml`, `requirements.txt`, `pyproject.toml` and `Gemfile`

The reason is simple: **a guessed summary is worse than no summary.** A model reading a diff will confidently describe intent it can't see, and that guess flows into `skills.md` as if it were evidence. Counting files is boring and correct. Boring and correct is what a source of truth needs to be.

## Dependencies are evidence, scaffolding isn't

`deps added` is the closest thing to hard proof of new tech. You don't add `@coral-xyz/anchor` to a project by accident.

But dependencies arriving *with a brand-new manifest* are a different thing entirely — that's what a template generated, not something you went and learned. So the log labels them separately: `initial stack (scaffolded, not newly learned)`. FocuClone's first commit shows fourteen npm packages that way; none of them are a claim that you learned Electron that day.

Sinks are told the difference explicitly. It's the single most common way a profile inflates itself, and it's closed off at the source.

## The collectors

A LaunchAgent runs `me collect --all` nightly at 23:50:

- **`gh`** — PRs, issues, releases and new repos via the `gh` CLI
- **`medium`** — published articles from your RSS feed, keyed by guid so re-polling never duplicates
- **`pulse`** — a single rollup row for the day: commits, net lines, languages, projects touched

The pulse is the one that surprises people. It's not detail — it's a heartbeat. `2 commits across 1 project(s), +4182/-7 lines — Lifelog` is enough, months later, to know a day was real work rather than a stray typo fix.

**X is deliberately not polled.** Nothing scrapes your timeline. You log the posts worth logging with ⇧⌘J, which means the log contains your ten real posts rather than four hundred replies.

## Backfill

```sh
me backfill ~ --days 3650 --author 'you@a.com,you@b.com'
```

This is what made the system useful on day one instead of a month later — it walked the whole home directory and pulled 407 commits back to JEUWEI, which is where the vault's timeline gets its spine from.

Three things make it safe to re-run whenever: it's keyed by SHA so re-encountered commits no-op, it accepts several author identities (most people commit under a work email *and* a GitHub noreply, and matching one silently drops half the history), and it applies the scaffolded-stack rule so a decade of `npm init` doesn't read as a decade of learning.

## The daemon

A code-signed LSUIElement bundle at `~/Applications/Lifelog.app`, kept alive by launchd. It owns the hotkey, and it also runs a quiet **nudge loop**: every six hours it checks how far the sinks have drifted, and at most once a day — if more than 30 events are pending — it posts a single notification. A notification you learn to dismiss is worse than none, so it stays rare.

## What this half is good for

The automatic half answers *what did you actually do*, with numbers, without you being involved. That turns out to be the harder half to reconstruct honestly. Memory inflates the interesting weeks and deletes the ordinary ones; 415 commit events don't.
