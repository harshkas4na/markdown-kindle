# The GitHub Layer

The original weakness of JobOps was honest but fatal: hits only arrived when you remembered to run a script. A day-one-application strategy that depends on daily willpower isn't a strategy. The GitHub layer fixes that, and then adds three research weapons on top. Setup instructions with exact commands live in `gh-tools/README.md` — this chapter is what each piece is *for*.

## The always-on scout

Once `job-ops` is pushed to a private GitHub repo, a workflow (`.github/workflows/scout.yml`) runs the HN scout every six hours on GitHub's servers. Laptop closed, asleep, in an exam — doesn't matter. Every strong match becomes a GitHub Issue labeled `lead`, with the full posting text, the matched keywords, and the HN link in the body. Overdue follow-ups from your tracker become `follow-up` issues the same way.

Issues, not a log file, because issues come with an entire free workflow: the GitHub mobile app pushes them to your phone the minute they open; labels are triage; comments are notes-to-self that Claude reads later ("grade this one"); closing an issue is a satisfying, trackable act. You wanted reminders to Telegram — that's wired too (bot token + chat id as repo secrets, instructions in the README), but honestly the GitHub app alone covers it with zero infrastructure.

## Recon: sound like you read their code, because you did

`gh-tools/recon.mjs {org}` answers four questions about a target in thirty seconds: What do they *actually* build with? (Their repos' language bytes — when the JD says Go but the org is 97% Rust, that's a dossier finding either way.) Is the code alive? (Repos pushed in the last 90 days — a quiet org is a signal about engineering culture.) **Who are the engineers?** Top committers in the last 90 days are disproportionately the people who'll interview you, findable without LinkedIn. And is there a wedge — open `good first issue` labels waiting for someone like you? This now runs automatically inside `/company-research`, so every dossier carries it.

## The PR wedge: the strongest application that exists

For the two or three companies you actually dream about, `gh-tools/pr-wedge.mjs {org}` scans their open issues and ranks them by stack match, freshness, and low competition — looking for the one issue you could genuinely fix this week. Zed documented this as a real hiring channel ("Hired Through GitHub"): contributor shows up, ships real fixes, and the eventual "interview" is a chat about a codebase they're already inside. A merged PR is unity demonstrated, not claimed — you're not asking to enter their world, you're already in it. The discipline: pick ONE issue, comment before you start, fix it properly. This is reserved for motivation-3 targets because it's real work, and real work is exactly why it converts.

## The mirror: your own GitHub is a landing page

Every recruiter and founder clicks your GitHub link before replying. `gh-tools/profile-audit.mjs` checks what they'll find: are the flagships your resume leads with actually pinned? Does each have a description, a live URL in the header, a README that shows What/How/Impact in the first screen? Anything stale enough to smell abandoned? The system can write you a perfect application, but if the click-through lands on an unpinned profile and a README-less FocuClone, the specificity you paid for evaporates on arrival. Run it monthly; treat the fix list as real tasks.

## One rule for the whole layer

The dedupe state (`.seen.json`, `.issued.json`) is committed to the repo by the workflow. If you also run the scout locally, pull first and push after — otherwise your laptop and the Action will each think they found the lead first, and you'll get double notifications arguing about who saw it.
