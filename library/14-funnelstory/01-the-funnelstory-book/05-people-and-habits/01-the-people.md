# The people

> [!STORY] The table that was wrong
> The first version of "who is who at FunnelStory" came from the company's public repos. It named Preetam as the largest contributor and did not contain Vivek Kairi at all. Then somebody ran a measurement across every branch of all 16 repos, and the shape of the team changed.
> Pulkit turned out to be the largest contributor in the whole organisation, with 3,535 commits. Vivek was the most active engineer right now. Preetam was the one writing most of the design docs.
> The lesson is about method: when a claim about the team can be checked, check it. And a second one, which is why this chapter has a table: people are what matters when you want to get something done.

## Who is who

- **Alok Shukla**, co-founder and CEO. The commercial and category voice. Chases customer status in the customers-and-POCs channel constantly. Hosts the company's podcast.
- **Arun Balakrishnan**, co-founder and Head of Product. **Your manager.** Customer-facing. His only committing surface is the public skills repo.
- **Preetam Jinka**, co-founder and Chief Architect. Writes the most back-end code and most of the internal design docs. Runs the artifact loop.
- **Aadarsh S**, Sales Engineer, about 3.5 years. **Your daily pair.** Owns customer workspace configuration. Wrote the twelve FunnelStory skills.
- **Pulkit Banta**, the largest contributor, 3,535 commits. Front-end history, the marketing site, prediction and rollup work, and customer calls. **Left on 6 November.**
- **Vivek Kairi**, Principal Engineer. Most active engineer. Back-end and ops, including the AWS to GCP migration.
- **Mamta Harris**, Senior Engineer. The outcome model, precision and recall, Trellix reprocessing.
- **Avadhut Thorat**, Senior UI Engineer. The marketing site day to day, plus front-end.
- **Nitin Chauhan**, back-end. Recently graduated, now full time. Stress-testing at 150,000 accounts.
- **Priyam Mitra**, Principal Architect. Named in the Trellix runbook as a holder of production database credentials.
- **Rajesh**, IT and security compliance. Vanta device onboarding. SOC 2 and US Data Privacy done, ISO 27001 in progress.
- **Helen**, operations and hiring. Ran your hiring process. Gave the clearest statement of the role anyone has ("a handful of large enterprise customers, not volume" and the faster-horse-versus-car line). Surname unknown.
- **Sanskar and Snehal**, design and marketing. Deliberately not in the engineering standup.

## How the work flows

- **Standup at 9:00 IST**, engineering. Optional for you going forward, because your work runs through Arun and Aadarsh. On 2 September Arun told both of you to drop off and focus on GreyOrange.
- **A rotating on-call**, announced daily by a Zapier bot in the dev channel. Preetam takes the late slot, Mamta, Vivek and Pulkit the morning.
- **Releases** are a PR in `funnelstory/ops` that bumps production image tags. The dev channel is subscribed to the `release` label. Trellix gets its own separate deploy, currently by hand.
- **Issues** live in `funnelstory/product`, and the four-digit numbers in branch names resolve there.
- **The customers-and-POCs channel** is the account channel. Alok chases status there, and every customer problem surfaces there first. **Read it before any customer conversation.**
- **The security channel** is Vanta-driven compliance, not incidents. SOC 2 and US Data Privacy are live. It is the backdrop to "only use official accounts": an audit surface, not a preference.

## Where decisions actually happen

Not in the standup. In Slack and in the artifact loop. The standup is where status is said out loud. Where a decision is made is where you will find a message beginning "decided".

## The register for disagreeing

- **Aadarsh argued back at Arun in the open** about the CHI score, with a specific alternative and examples. He was asked for a doc, not overruled. That is the register: a specific alternative, plus examples, on paper.
- **Vivek asks the reuse question**: "how is it different from the Play?", "why not add the missing features to Plays?". He makes people give the house answer: build the product concept from existing primitives.
- **Vivek says "I have never worked on this precision recall stuff"** in front of the founders. Not knowing something is sayable here.
- **Mamta reported a bad number honestly**: "it's terrible, that's why I am not confident with that value at all", and then proposed the verification step herself.
- **Pulkit does the read-back** before committing to a decision, and declines to decide architecture in the room: not something we can decide in two minutes.

## Traps

- Treating the standup as the place decisions happen.
- Reporting a ticket as progress to Arun.
- Merging `arun` with `@arunmecheri`, a GitHub handle reviewing release PRs, without checking.

## Check yourself

1. Who is your manager, who is your daily pair, and who left on 6 November?
2. Where do decisions actually happen?
3. Which person asks the reuse question, and what answer does he want?
