# One Application, Start to Finish

The best way to trust a pipeline is to watch one unit go through it. Here's a single A-grade lead, from phone buzz to submitted, with what's happening at each stage and what it costs you in minutes.

## Tuesday, 9:40 — the buzz

Your phone shows a GitHub notification: `[lead] Orbit | Product Engineer | REMOTE (EU) — AI-first logistics OS`. That issue was opened by the scout workflow, which ran on GitHub's servers at 6:23 while you slept, pulled the HN thread, and matched the posting against your keyword tiers. You read it in the GitHub app in bed. It looks real. You comment "grade this" and get on with your morning.

## At the laptop — grading and the go decision

`cd ~/PROJECTS/Me/job-ops && claude`, then: *"check the lead issues, grade the Orbit one, and if it's A or B run the full pipeline."* Claude runs `/job-scout` grading: stack fit (TypeScript, agents — strong), stage fit (early, founder-led — strong), story fit (rc-agents is literally agents doing logistics-shaped work — strong), practicals (remote EU, might be India-flexible — check). Grade: A. **Touchpoint ①: you say go.** Two minutes.

## Research — the part that makes everything else non-generic

`/company-research` fetches their site, blog, founder's X, funding news, and runs `gh-tools/recon.mjs` on their org: their monorepo is 80% TypeScript (JD said Go — worth knowing before you claim Go love), pushed daily, and the #2 committer's GitHub bio says "ex-Flexport, building order intake." That name goes in the dossier as the likely hiring manager. The dossier also captures their vocabulary — they call carrier integrations "the messy middle" on their blog, a phrase no competitor uses — plus two initiatives you could plausibly ship in week one. **Touchpoint ②: you skim the dossier for anything marked GUESS or just wrong.** Three minutes.

## The resume loop — where the 80+ score comes from

`/tailor-resume` picks the AI-agent framing (per the dossier), rebuilds bullets What/How/Impact, then plays two roles against itself: drafter writes, a skeptical-recruiter reviewer tears it apart on an 8-second pass, `/ats-score` scores it against the JD's actual keywords. Round one: 71 — missing "webhooks" (true for you, absent), Hashtro bullet leads with astrology instead of the 3-service architecture. Round two: 86, reviewer has nothing left. `scripts/resume-pdf.mjs` makes the PDF. **Touchpoint ③: you read it once — is it true, is it you?** Two minutes.

## Outreach and the letter

`/outreach` drafts the founder email: opens with a specific observation about their carrier-integration approach, one proof point (rc-agents — agents paying for services autonomously, live URL), one ask, 96 words, "the messy middle" mirrored once, naturally. `/cover-letter` writes the long-form version for the form using the same dossier. **Touchpoint ④, part one: you edit the email in your own words — this is the ten minutes that decides everything — and send it from your inbox.**

## The form

`/apply-pack` compiles `pack.json`: identity fields, knockout answers from facts.yaml (visa: honest; start date: June 2026), the "why Orbit" answer, the cover letter. You open their Ashby form, click the JobOps extension, paste, Fill. It fills what it can match, lists what it couldn't, never touches Submit. **Touchpoint ④, part two: you review every field, attach the PDF, click Submit yourself.**

## Closing the loop

*"/outcome Orbit: applied via form + founder email sent, follow-up Friday+7."* One tracker row, follow-up date set. If Friday+7 passes silently, the workflow opens a `[follow-up]` issue and your phone buzzes again — the system remembers so you don't have to.

Total: about 25 minutes of your attention, most of it on the one part that must be human. Everything else happened while you did something better.
