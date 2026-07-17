# The YC and Startup Channel

Y Combinator is not one company hiring — it's roughly 4,000+ funded startups on [workatastartup.com](https://www.workatastartup.com/), most small enough that the founder is still doing some of the hiring personally. That changes the entire game. You are not trying to beat an ATS. You are trying to get a founder's attention for fifteen minutes, and founders at seed stage are triaging inbound between shipping product, fundraising, and customer calls — hiring is a scarce-time activity for them, not a department.

## The real conversion numbers by channel

Data compiled by Standout, a job-search platform focused specifically on YC-style hiring, puts real numbers on what most people only guess at: a **cold application through the board** converts at roughly 2–5%, with a 1–3 week turnaround (often nothing at all) — founders read only about 5% of the cold inbound that lands in their public queue while they're mid-fundraise or mid-launch. A **sharply targeted cold email straight to the founder** converts at 5–15%, usually with a reply inside 24–72 hours. A **warm intro** from someone the founder already trusts — another YC founder, a YC alum, an investor — converts at 50–70%, often producing a first call within a day, because the intro itself does the vetting. The takeaway isn't "cold outreach doesn't work" — it's that Work at a Startup is best treated as a **directory of targets**, filterable by batch, stage, and stack, and the actual hiring happens through the channels around it, not through the board's own apply button.

## What YC itself tells candidates to do

Ryan Choi, who leads hiring-related work at YC, has published concrete resume advice that's worth following almost verbatim: structure every past role around **What / How / Impact** — what the product or initiative was (assume the reader has zero context on your last project), how you built it (name the actual languages/frameworks/tools inline, in the bullet, not dumped in a skills section at the bottom), and impact in quantified terms (usage, cost, users, revenue). Cap each role at 3–4 bullets and cut anything that doesn't match the specific role you're targeting. For outreach, the same guidance is explicit: personalize every message and lead with 2–3 concrete initiatives you'd actually tackle at their company — "being a genuine user is a huge plus." Founders get dozens of these a day and filter on specificity almost instantly; a generic compliment gets deleted, a demonstrated, specific opinion about their actual product gets a reply.

**A cold-email shape that fits the data above:**

> Subject: [specific thing you noticed] — question
>
> Hi [Name] — saw you just shipped [X]. I built something similar for [Y project] and ran into [specific non-obvious problem]; here's how I solved it: [one sentence]. I've been [doing relevant thing — e.g., "shipping Solidity + Reactive Network automations solo, most recently REACTOR which got a $9K grant from the network"]. Would 15 minutes be useful before you fill your next engineering seat? Happy to send code either way.
>
> [Name] / [one-line portfolio link]

Four sentences, no résumé attached on the first message — a live link does more work than a PDF. This is the same instinct behind "Think Process, Not Product" from *Show Your Work!* elsewhere in this library: the artifact that gets you noticed isn't a summary of your skills, it's a specific, checkable thing you did.

## The volume math, from someone who tested it

Haseeb Qureshi's well-known essay on breaking into tech (written after landing eight offers, including Google, Uber, and Airbnb, from a non-traditional background) puts real math behind the "just apply more" instinct: roughly a 4% offer rate per application sounds discouraging in isolation, but 50 applications gets you to an 87% chance of at least one offer. His tactical advice transfers directly to the YC channel: target smaller, less-prestigious companies first — they take more chances on unconventional resumes and interview a higher fraction of who applies — and treat outreach as a volume-*with*-quality practice, not a one-shot bet on a single dream company. His own path (self-taught, non-CS background, credibility built through referrals and networking rather than pedigree) is structurally close to what a hackathon-built portfolio has to do: substitute demonstrated work for the resume line a CS degree or FAANG stint would otherwise supply.

## Hacker News: the other YC channel

Y Combinator also runs Hacker News, and its monthly **"Who is Hiring?"** thread (posted on the 1st by the `whoishiring` bot) is often higher-signal than the job board itself, because most posts are written and read by the actual hiring manager or founder, not a recruiter. A companion **"Who wants to be hired?"** thread runs the same month for candidates to post their own listing. Looking at how strong listings in that thread are actually written, a consistent format shows up: `Location / Remote / Willing to relocate / Technologies / Résumé / Email`, posted as early in the month as possible since visibility decays fast after the first few hours. The self-presentation patterns that stand out in strong posts: lead with a **quantified outcome, not a title** (one strong listing opens with having prevented "$20M+ exposure" for a client rather than listing a job title); a **portfolio/GitHub link placed first**, letting shipped work substitute for credentials; a **narrow, named specialization** ("systems-oriented ML/LLM engineer") instead of a generic "full-stack developer" label. For someone with REACTOR, Hashtro, and rc-agents already live, this format is close to a direct fit — it rewards exactly the "shipped, named, quantified" material already sitting in a portfolio, and punishes generic self-description.

Practically: check `hn.algolia.com` and search past months' threads for companies that post the same role repeatedly — a company hiring for the same seat every month for a year is a company that's actually growing, a useful filter a static job board doesn't give you.

## Timing

YC runs two funding batches a year, and hiring activity spikes noticeably in the weeks after each Demo Day, when freshly-funded companies convert investor interest into headcount. That's the highest-density window for new postings on Work at a Startup — worth timing a push around, not just working the channel at a constant low simmer year-round.

## Why this channel fits your profile better than it looks

Most general "how to get a YC job" advice assumes a generic SWE candidate competing on LeetCode and pedigree. That's not your gap. Your edge is that you already have exactly the kind of artifact that makes a specific cold email possible: REACTOR is a live product, on Base mainnet, that got an unsolicited $9K grant and four press mentions. That's a stronger opener than almost anything a new-grad candidate can put in a cold email, because it's proof of the two things an early-stage founder actually screens for — can you ship something real alone, and can you get outside validation for it. Filter Work at a Startup by "Crypto/Web3" and by "AI" and cross-reference; a nontrivial number of current YC batches include AI-agent-and-infrastructure startups where "shipped a working agent-to-contract payment flow" (rc-agents / x402) is a far more relevant flex than it would be at a typical fintech. Build the target list first, then go around the board with the direct-founder approach above.
