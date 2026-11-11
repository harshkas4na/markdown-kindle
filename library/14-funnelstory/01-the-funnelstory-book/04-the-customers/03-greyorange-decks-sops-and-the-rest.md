# GreyOrange: the decks, the checklists and the rest

> [!STORY] 24 decks with holes
> Every Friday, every GreyOrange project gets a PowerPoint status deck, emailed to its project manager. On 30 October the Friday run mostly failed. ClickUp refused 42 requests that were made at once. Twenty-four decks went out with empty sections.
> A fix was saved the same day. PMs can re-run their own project from the ClickUp button, and the scheduled Friday run is unaffected by the button problem from chapter 4.1.
> The deck is not the story. The story is that a deck is a promise. Every Friday, someone opens it and believes the numbers.

*These facts come from older repo notes and were not all re-checked on 10 November. Where it matters, check the live flow.*

## The weekly deck agents

Two flows. One lists the live projects (Thursday). One builds each deck. Decks go out by email to the PM, with Dikshant copied for quality checks, and are saved in ClickUp (Weekly Reports, one folder per project, one version per week).

A bit of history. On 4 September Aadarsh handed over his proof-of-concept flow and four local scripts. Dikshant had marked up a Weekly Status Report Template (11 pages, six data-backed changes). You built version 2 in GreyOrange's production workspace as a draft with no trigger, five completed runs, every one emailing only you. Ten decks had been shared the week before.

On 7 September came a one-hour assignment: **provenance**. For every number on the deck, say where it came from. That is the same habit as chapter 3.7: bring the source with the number.

When a customer says a deck is wrong, the routine is the `/work-deck-fix` skill: pin the box and the flow variant, diff the saved flow against the repo before editing, check where the number comes from, fix from the saved version, re-run the week they reviewed on their project plus others, sweep every deck already sent for the same defect, and draft the reply with the old and new number.

## The SOP checklist agents

Each of roughly 27 in-progress projects needs a long SOP checklist, 1,780 items in the full set. Pulkit built agents that create them. A change in September fixed it so each project only gets items for the products it actually has: 300 items instead of 884 for one project.

The date to remember: **10 September**. Dikshant reviewed Luxottica ATL and said "This looks perfect, you may enable the rest". He confirmed once a day was enough. All seven agents were then run manually for Luxottica ATL and every folder matched its expected count exactly (1,228 tasks). On your instruction relaying Pulkit, the limit was removed and all eight flows were set live.

They run themselves since: a collector at 05:00 India time, the agents at 05:30. Roughly 32,000 task creations a day, draining over four to five hours through the platform's 25-worker cap. Rollback is one command. Live since 10 September and used daily by Dikshant's team.

The design question behind it, which is still open in one form: should the agent dedupe (do not make the same task twice) or reconcile (make reality match intent)? Pulkit found a real bug in one design in a single message: a product changed twice never re-triggers, because of the run idempotency key. That is why idempotency is on the study list. "Safe to re-run" is a property you design in, not a guard you bolt on.

## AGT-014, the stakeholder view

A ClickUp page, "Stakeholder Role Matrix", lists who plays which role on every project: 547 rows across 27 projects. Built on 26 October and running hourly since 27 October. Mahima has not reviewed it yet. Her request for colours was refused because of a platform limit.

## The CHI data app

Covered in chapter 4.1: built, deployed, waiting for GreyOrange's validation.

## The go-live report

Mahima asked for a readiness report with four tiles per project. A draft flow was built in August and gated on her approval. Its status since September has not been re-checked.

## The gStore SLA work

Chris's team confirmed their standard SLA and severity definitions and attached four client contracts to start with, in PDF. The data is in Salesforce Service Cloud (tickets and time logs) and in the PDFs. The request: prove the system on those four first, and with the Savage X Fenty account manager agreeing it works. Arun asked for follow-up on 27 October.

## Words you need

- **RCA:** root cause analysis. A document explaining why a milestone slipped.
- **Milestone:** a stage of a project (FSD, UAT, HAT, Go-Live). **Root delay:** the first late milestone in a project.
- **Baseline:** the due date the alert agent first saw. ClickUp keeps no original date, so this is the starting point.
- **FSD:** functional specification document sign-off. **ISD, I&C, SIT, UAT, HAT:** later stages. I&C is installation and commissioning, UAT is user acceptance testing, HAT is hardware acceptance testing.
- **PRJ code:** the project number. Not unique.
- **Slack Channel List:** a ClickUp list saying which Slack channel belongs to which project.
- **Idempotent:** running it twice changes nothing the second time. Our flows aim for this.

## Traps

- Fixing a deck defect only in the deck you were shown.
- Forgetting that the scheduled run and the button path are different paths.
- Assuming status from a September note is still true in November.

## Check yourself

1. Why did 24 decks go out with empty sections on 30 October?
2. What happened on 10 September with the SOP agents, and who said what?
3. Explain idempotent in your own words, with an example from this account.
