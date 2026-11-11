# Trellix: the account that audits the score

> [!STORY] The first account in the report
> On 1 September the Trellix team sat down to look at the new dossier and the renewal report. Brent, their champion, opened the first account in the report. It had a score of 22. Its renewal was already confirmed.
> The meeting never got past it. Four product screens disagreed about the same account, and nobody could say why the number was 22. Everything else that had been prepared that day stayed unopened.
> Two months later, in late October, the same account was audited the other way round. Brent had a Trellix person go through the predictions account by account, with a sheet carrying what FunnelStory predicts, what Trellix believes, and a reason wherever the answer is no. Trellix became the team's first priority.
> That arc, from "I do not trust this number" to "I will check every number", is the Trellix story.

## Who they are

Trellix is enterprise cybersecurity, formed from McAfee Enterprise and FireEye. It is the **most operationally involved account**. It has its own cloud projects, its own runbook design doc, its own deployment channel, and its own release train deployed separately from production.

Products heard: HX, DX, ePO (unverified against Trellix's public naming). The original proof of concept covered two or three products. The account now covers everything.

## The people

- **Brent** (heard; surname unknown). The champion. His feedback drives the work. Verify the name before using it with anyone: it is attested only by one audio recording.
- **Shoaib** (heard). Controls data access. Two FunnelStory workstreams were blocked on him at once, and nobody at FunnelStory visibly owned the relationship.
- **Ajay.** Their infrastructure. Owns the release process and Vivek's database access.
- **Manny** raises issues. **Manisha Phulwani** noticed the needle mover reset within a day.

## The renewal-watch report

The live artifact, and you are tagged on it. `Renewal watch, next 90 days`, a 55-page PDF printed from Chrome, so it is an HTML page rendered to PDF, not a designed document. Changing it is a template change.

Its scope: about 1,400 open renewal opportunities worth about $37.8M, across about 596 parent accounts, renewals through 28 November 2026. Buckets: healthy 365, at risk 57, renewal-mention 3, not scored 171.

Arun's three criticisms of the first version were the work:

1. It read as all-negative because it only covers risky accounts and did not say so loudly at the top. His fix: three or four summary boxes (healthy, at risk, not scored) before the detail. "Visualize whatever you say in the text."
2. A set of accounts have a confirmed renewal but score 0 or near 0, with no explanation. Same defect as the dossier problem, one level up.
3. "Deployments are shrinking" was asserted without scope: no numbers, no way to size the shrink.

## Known data gaps (as of 31 August)

- Page-views data ends 27 March: three to four months missing.
- SecOps usage appears against accounts that do not have SecOps.
- The services product line has zero usage data, and that is correct. Services is sold without a product attached. Do not raise it as a bug.

## Almost zero complete churn

Trellix customers hold many products. An account only fully churns by dropping all of them. The real shape is partial churn and partial expansion, so accuracy is measured on quarterly ARR drops (chapter 1.2).

## The recall argument

Alok on why the Trellix accuracy work matters: this is an exercise not only for Trellix but for DocuSign. When we hit DocuSign, we have solved it. In the recall experiment the team ran in early September, a first pass gave 12 percent recall on a wrongly defined set (the record does not pin it to one customer), and Preetam said to set up the experiment properly. The false-positive argument followed: the model flags accounts that did not drop. Accuracy is a long argument, and it is the thing the customer is auditing now.

## The evaluation, late October

In the 30 October standup: Brent had a Trellix person evaluate "where we are meeting the mark and where things can be improved". The sheet has what FunnelStory predicts, what Trellix believes, and a reason wherever it is no. Two reasons Arun read out:

- "Unable to engage with this customer, so I have no idea of their intent." That means no communication, so the prediction is usage-only.
- "A customer is clearly unhappy with certain things in the product." Did we catch it?

Engagement recency is disputed: FunnelStory says last contact was August, Trellix says as recent as October. FunnelStory keeps an internal copy of the sheet, Aadarsh analyses it with his agent, and the order is common cause first: missing data type, then weighting, then health scoring.

## Operations

Trellix gets its own separate deploy, currently by hand into their cloud console. Preetam has asked for it to be automated with Ajay and Shoaib. Trellix is also the first priority for the **product knowledge map** feature, with no go yet for a test in their workspace.

## What Trellix teaches

**Explainability.** A score nobody can explain is a trust event (chapter 1.2). Everything about the dossier's "why this score" panel came from this account.

## Traps

- Calling the services line's empty usage a bug.
- Naming Trellix's end customers outside the private notes.
- Treating a recall number as meaningful without its target set.

> [!PROJECT] Where you see this in your week
> The Trellix renewal report, the recall re-run, and now the evaluation sheet. Each time, the question is the same: can the number explain itself?

## Check yourself

1. What happened on the first account the Trellix team opened, and what did it teach?
2. Why does accuracy at Trellix use quarterly ARR drops?
3. What are the three known data gaps, and which one is not a bug?
