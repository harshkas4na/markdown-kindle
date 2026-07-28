# When It Breaks

Everything here has bitten this system at least once.

## me doctor first, always

```
✓ log: 443 events (387.8 KB, mode -rw-------)
✓ git hooks: /Users/harshkasana/.lifelog/githooks
✓ capture daemon (⇧⌘J) running
✓ nightly collector scheduled
✓ ⇧⌘J registered
✓ signed with "Lifelog Local Signing" — the grant survives rebuilds
✓ gh CLI available
✓ sync-me skill installed
```

Note that the hotkey line is read from **the daemon's own log**, not from this process. Your terminal's permissions say nothing about the app's, and a check that asked the wrong process would cheerfully report everything fine while the hotkey was dead.

## The hotkey doesn't fire

The tap requires Accessibility permission, granted to an *application identity* — which is why the daemon runs from `~/Applications/Lifelog.app` and not a bare binary.

The failure worth knowing about: **the toggle in System Settings can read "on" while the hotkey is completely dead.** macOS binds the grant to the app's designated requirement. Signed ad-hoc there's no certificate, so the requirement is the literal `cdhash` — and every rebuild produces a new one, silently invalidating the grant with no indication anywhere.

That's why `me install` creates a self-signed certificate, `Lifelog Local Signing`, in your login keychain. With it the requirement becomes `identifier + certificate leaf`, which doesn't move when the code does. Grant once, rebuild forever. `me doctor` tells you which mode you're in, and `me install` shouts if it ever falls back to ad-hoc.

If the grant is genuinely stale: **select Lifelog, press −, then + and re-add `~/Applications/Lifelog.app`.** Toggling off and on does *not* work — it flips a flag on a row that still names the old hash. The row has to be replaced.

While it's broken, `me capture` opens the same window and needs no permission at all.

## The hotkey collides with something

The event tap **consumes whatever it matches**, so the combo lifelog takes is taken from every other app on the machine. That's why it's a setting, and why the default isn't ⌘J:

```sh
me hotkey                  # what is it now
me hotkey ctrl+opt+space   # change it, restarts the daemon
```

The restart matters — the tap is installed once at registration, so without it config and reality disagree.

## The digest is empty but you've been committing

`me doctor` and check the git hooks line. Usual causes: `core.hooksPath` got unset by another tool, the repo has a `.nolifelog` file, or its path matches something in `ignore_repos`.

## A project shows the wrong name, or splits in two

`~/.lifelog/config.json`, `project_names` — it maps a repo directory to the canonical name used across every sink. Two directories can map to the same name, which is how work spread over several repos reads as one project.

## You captured something wrong

```sh
me events --limit 5 --json     # find the id
me retract <id> --reason "..."  # or: me amend <id> "the corrected text"
```

Not a rollback — an appended correction, honoured in every window from then on, including ones covering dates before you wrote it.

## The privacy invariants

These are not preferences. They're the reason the log can hold anything you'd actually want to write down:

- **The log never leaves this machine.** No event contents in web requests. Nothing from `~/.lifelog` committed to any repo. No digest written to a file inside a git repo — read it from stdout.
- The store is mode `0700`, and `me install` adds it to your global gitignore so it can't be committed by accident even if it ends up somewhere odd.
- Commit events carry **stats, never diff content**. File names and counts, not your code.

This book lives in a public repo, which is exactly why the examples in Chapter 4 are written rather than copied.

## Known rough edges

- **"Languages used here for the first time" is noisy on a full-history replay.** It treats every file extension as a language, so a first sync of a large backfill lists `.bak`, `.o`, `.zip`, `.woff2` alongside Go and Solidity. Harmless — the real languages are in there — but don't let a sync treat `.dylib` as a skill.
- **`me events` doesn't rank.** Only the digest does.
- **The nudge is once a day at most**, over 30 pending events. If the sinks are drifting and you want to be told sooner, lower `nudgeThreshold` in `internal/hotkey`.

## If you change the daemon

Rebuilding is now safe for the Accessibility grant, but two things in `internal/hotkey/panel_darwin.m` are load-bearing and easy to break:

- **`mainthread.Call` does not wait**, despite its doc comment. The panel closes a channel from inside and blocks on it. Remove that and `me capture` exits before the window draws.
- **The Edit menu is required, not decorative.** An LSUIElement app starts with no menu bar, and macOS routes ⌘V/⌘C/⌘A through menu key equivalents — without it you cannot paste a link into the capture box.

Both are documented in the repo's CLAUDE.md, which is the first thing to read before touching that file.
