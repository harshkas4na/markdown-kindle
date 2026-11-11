# Glossary, in plain English

The long version, with every term you decoded, lives in `glossary.md` in the work folder (more than 3,000 lines). This is the short, useful one. Where a term has its own chapter, it points there.

## The business words

- **ARR / ACV.** Annual recurring revenue / annual contract value. (1.2)
- **Churn.** The customer leaves. **Partial churn:** they drop a product or shrink. (1.2)
- **GRR.** Gross retention: revenue kept, before upsell. Cannot exceed 100 percent.
- **NRR.** Net retention: revenue kept plus expansion. Above 100 percent means growth from the base.
- **Renewal motion.** The 90 to 180 days before a contract ends.
- **CSM.** Customer Success Manager. **CCO:** the head of customer success.
- **QBR.** Quarterly business review.
- **Book of business.** The accounts one CSM owns.
- **Expansion / upsell.** More money from an existing account.
- **Adoption.** Whether they use what they bought.
- **Champion.** The person at a customer who pushes for you. **Single-threaded:** an account that depends on one person.
- **POC.** Proof of concept. **FDE.** Forward-deployed engineer.
- **Precision / recall.** Of flagged, how many were right / of the real ones, how many were flagged. Always state the denominator. (1.2)

## The product words

- **Workspace.** A customer's own space in FunnelStory. `workspace_id` isolates it.
- **Account / child / parent.** The customer company, and the levels under it.
- **Customer Intelligence Graph.** The fused context: usage, CRM, conversations, business intel. (1.3)
- **Get, Set, Go.** Intelligence, automation, delivery layers. (1.3)
- **AX.** Agent experience: reachable from Claude or Cursor over MCP.
- **MCP.** Model Context Protocol. How Claude or Cursor talk to FunnelStory's tools.
- **Renari.** FunnelStory's name for its reasoning platform and agent surface.
- **Felix.** The in-product assistant (and a status page component).
- **Provenance.** Where a fact came from. Kept even for bad data.
- **Content label.** One signal found in a conversation, with type, sentiment and impact. (2.2)
- **Topic types.** pricing, competitor, personnel_change, feature_request, task_issue_bug, action_item.
- **Sentiment / impact.** Tone (-1 to 1) and consequence (-10 to 10). (2.2)
- **Content theme.** A pattern across many labels.
- **Retention tag.** A label on a whole account: churned or retained. Training data. (2.3)
- **Audience.** A saved set of accounts. Churn and Retention are hidden ones.
- **Factor.** One input the model scored.
- **Rollup.** Product to child to parent.
- **Needle mover.** A leading indicator of churn or expansion, with evidence. (2.4)
- **Relationship map.** Who talks to whom at an account.
- **Account Dossier.** The synthesised, source-cited account story. (2.5)
- **Fact / case / STAR-L.** Extracted observation / concluded episode / situation, task, action, result, learning.
- **Action Card.** A drafted suggested action for a needle mover.
- **Outcome-Based Agent.** FunnelStory-built single-job agent. **AI Agent / flow:** one you author. (3.1)
- **Cohort.** A group of accounts defined by criteria.
- **Journey funnel.** The stages a customer moves through.
- **Data app.** A declarative JSON app embedded in a customer's tool. (3.6)
- **Dataset.** A named, saved query result or record set. **Managed dataset:** system-owned.
- **Data model.** A customer-defined mapping from their data into FunnelStory objects.
- **Connection.** A built-in integration with a known provider.
- **Semantic DB.** SQLite virtual tables over Postgres. (2.6)
- **BlocksQuery.** Provider-specific blocks inside SQL for non-warehouse connections.
- **Vtable.** Virtual table.
- **`account_id` / `account_fs_id`.** External id / internal UUID. (2.1)

## The flow words

- **Flow.** Trigger plus a step graph. **Agent:** same thing, customer's word.
- **Draft.** Saved but off. **Active / live:** running.
- **`trigger_config: null`.** No trigger, so it never runs on its own.
- **Op types.** CALL, AGENT, LOOP, BRANCH, CONDITION, TRANSFORM, WAIT, SPAWN, JOIN, REPLAN. (3.2)
- **Local / global (`@.`).** Frame-only variable / run-wide variable. (3.3)
- **Test mode.** Run for real output; refuses non-GET external writes. (3.3)
- **Draft gate.** Nothing live, sent or written without your word. (3.4)
- **Harness.** Custom scripts inside FunnelStory that call external APIs. (3.1)
- **Idempotent.** Running twice changes nothing the second time.
- **Runner.** Background scheduler. **Processor / Store / Handler / Policy / Resolver / Syncer / Engine.** Code roles. (2.7)

## The people-and-process words

- **Standup.** 9:00 IST engineering call.
- **Read-back.** A short message confirming what you understood from a spoken ask. (`/work-readback`)
- **Verified / assumed.** The house register for any claim.
- **Four headings.** Problem, Cause, How it was fixed, What is pending and ETA. (Preetam)

## GreyOrange words

- **PRJ code.** A project number. Not unique. (4.1)
- **Milestone.** A project stage. **Root delay.** The first late milestone. **Baseline.** The date the alert agent first saw.
- **RCA.** Root cause analysis. **FSD, ISD, SIT, I&C, UAT, HAT.** Project stages. (4.3)
- **CHI.** Customer Health Index. Performance 40, Experience 30, Business 30.
- **SOP.** Standard operating procedure checklist.
- **gStore.** GreyOrange's retail side. **SSC.** Salesforce Service Cloud.
- **AGT-013 / AGT-014.** RCA filing agent / stakeholder view agent.

## Money and employment

- **Deel.** The payroll platform that pays you as a contractor of the US entity.
- **The 17 percent.** The performance pay component, first measured around 30 November 2026.
- **Contract clock.** The check every skill makes before work: hours against fee.

## Compliance

- **Vanta.** The compliance tool. **SOC 2, US Data Privacy, ISO 27001.** The standards.
- **CASA.** A security assessment named in a recent standup (heard).
