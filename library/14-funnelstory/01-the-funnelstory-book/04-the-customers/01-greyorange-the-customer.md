# GreyOrange: the customer

![Illustration for this chapter](../img/art-two-ids.jpg "Illustration. Generated for this book, no real data")

> [!STORY] The button that sent the wrong kind of number
> On 26 October Dikshant, a project manager at GreyOrange, sat on a call with you. Their team was about to get a button inside ClickUp that launches a FunnelStory data app. The trouble: the button sends an account ID. But every weekly-deck flow is built on a ClickUp project code, such as PRJ10234.
> At GreyOrange, an account ID is a site. A project code is one live implementation at that site. They are not the same thing, and the data does not carry one to the other.
> You and Dikshant reached the same simple fix independently: have the button send the project identifier along with the email and drop the mapping. A week of confusion came down to two kinds of ID that looked alike.
> This chapter is about the customer. The next two are about the agents you have built, and are building, for them.

## Who they are

GreyOrange builds **warehouse robots**. Each customer installation is a **project**, named like `PRJ10234 ODW Logistics`. Their project managers run every project in **ClickUp** and talk about it in **Slack**, one channel per project.

FunnelStory builds **agents** for them: small automated programs that read ClickUp and Slack and do a job. Everything has to appear where their people already work, because they will not log into FunnelStory.

Their structure, in their own words: one **account** (say Exol) over several **sites**. Each site is its own Salesforce account row with its own id. Each site normally has one live implementation project with a `PRJ` code. And a fourth level, product lines such as RTP and TTP, which is why names and CHI scorecard rows carry those labels.

> [!GOTCHA] PRJ codes are not unique
> Dikshant first said project codes are unique. Their own ClickUp contradicted it: `PRJ10173` is on three projects, two live. On 29 October he reversed himself: more projects like this are coming, and GreyOrange will not clean up the codes. So the mapping has to carry the PRJ code **and** the full project name everywhere. A typed code on the deck generator fans out to every live project under it, one email each.

## The people

**GreyOrange**

- **Mahima Goel**, Project Management. Asked for the alert agent, the filing agent and the stakeholder view. The one who reviews your work.
- **Dikshant Lal**, Project Management. Your day-to-day contact. Gives the rules, tests them, runs them himself. The ClickUp connection is his own account. He acts on rows, not on rules, so send him the actual rows.
- **Neelesh or Nilesh Maheshwari** (spelling unsure), senior. Insists FSD stays part of the alert order.
- **Satish and Deepak**, senior. Tagging both on an RCA document is what makes it final. Deepak also leads the CHI score use case and wants full automation (heard).
- **Jaspreet and Vivian**, who build the CHI scorecards by hand. **Mayank**, Manager-CEM for CHI.
- **Sraboni**, coordinator. **Akhil, Shivdeep, Maruti**, others in the record.
- **Chris**, on the gStore side (retail), in Customer Success in Chicago.
- **Ganesh** (heard), GreyOrange IT.

**FunnelStory**

- **Aadarsh** built most of the GreyOrange agents. On 10 November he said you take over "the GreyOrange side", with no list yet of what that means.
- **Pulkit** did front-end and platform work. He left on 6 November. His fix that makes Slack usable inside flows merged on 2 November.
- **Arun** leads. Vivek, Mamta and Preetam work on other parts.

## The use cases, one line each

- **Go-Live readiness report.** A readiness report with four tiles per project, from the customer's own written Go-Live Dashboard Guide. A draft flow was built on 31 August, gated on Mahima's approval.
- **The CHI score.** Customer Health Index, a score out of 10 per customer site: Performance 40 percent, Experience 30 percent, Business 30 percent. Built daily by hand in a spreadsheet by Jaspreet and Vivian until it was automated. It must show up in ClickUp, because about 950 people use ClickUp.
- **The weekly status deck.** One PowerPoint per project each Friday, emailed to its PM.
- **The SOP checklist.** Each of roughly 27 in-progress projects needs a long SOP checklist, about 1,780 items in the full set.
- **The alert agent, the filing agent and the stakeholder view.** The three covered in the next chapter.
- **gStore customer health.** Chris scoped an agent that emails a uniform customer-health report, twice weekly (Monday and Thursday), with monthly and quarterly roll-ups, the same format for the weekly meeting and the executive review. In late October the gStore team emailed their SLA documents (four client contracts to start with, in PDF), picking up that thread.
- **Jira.** GreyOrange connected Jira to FunnelStory. Their login is Google SSO, which exposes the whole Jira, and they wanted tickets from one project only. From the code: OAuth only, read-only scopes, syncs every project the connecting user can see. So the route without a build was a Jira user who only has access to that one project. The first sync only covers tickets updated in the last 30 days, which will read as "missing" unless said.

## The CHI score and why it is contested

The CHI data app is built and deployed in FunnelStory and ClickUp, structured and unstructured. The blocker is **GreyOrange's own validation**, not the build. Findings so far:

- A defect GreyOrange found: September scores in ClickUp were wrong because the agent ran on 2 to 3 October but the scorecards were not rebuilt afterwards. The agent run and the scorecard rebuild are separate steps.
- A site-scope check against Jaspreet's list of 63 sites: 52 matched and were scored, 11 on their list were not scored (no active Salesforce contract), and 55 scored sites were not on their list. Pending confirmation of the true scope.
- Vivian, the named reviewer, started validating and said the score's input scope is thin and reused across metrics, and that GreyOrange is far from being able to deploy the agent broadly.

Aadarsh's position, argued in the open: the CHI score "just cannot be truly automated", with a concrete split of what FunnelStory should and should not compute. He was asked for a document, not overruled.

## What FunnelStory delivers here

Replaces Mahima's hand-built go or no-go deck. Replaces Jaspreet and Vivian's daily spreadsheet. Blocks 150 calendars without buying 150 ClickUp seats. None of that is "an AI answer". Each is a report, a sync, a dashboard or an alert that reaches a named person.

![GreyOrange's public website](../img/shot-4-1-greyorange-site.jpg "Screenshot, public page, 2026-11-11. GreyOrange's public website")

## Traps

- Assuming a project code identifies one project.
- Assuming an account ID means an account in the way you think of one. At GreyOrange it is a site.
- Treating Jaspreet's objections as a technical problem. They are about who sees a number before it is validated.

> [!PROJECT] Where you see this in your week
> It is the account in your 10 November takeover, so every GreyOrange question lands on you. Chapters 4.2 and 4.3 are the study material. The study plan in the work-ops folder splits it into six sessions.

## Check yourself

1. Explain the difference between an account ID and a project code at GreyOrange, and why the ClickUp button broke on it.
2. What is the CHI score, how is it weighted, and what is the blocker?
3. Name Mahima, Dikshant and Aadarsh, and what each does in this story.
