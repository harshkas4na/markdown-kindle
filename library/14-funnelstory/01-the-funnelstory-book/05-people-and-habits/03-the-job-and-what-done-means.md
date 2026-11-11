# The job, and what "done" means

> [!STORY] 17 percent with no target
> Seventeen percent of your pay is a performance component with no defined target. You parked asking on purpose, until you understood the business. That was defensible, with one condition: ask before the first quarterly measurement, which lands around 30 November.
> Then something opened up. Arun said, unprompted, that the company cannot currently see the metric you are paid against: how many agents a customer has deployed and what they did. A founder-stated product gap pointed straight at your seat.
> That is why the agent-adoption assignment is both the work and the answer to the pay question.

## The seat

- Arun, introducing you: the company's first forward-deployed engineer. If he fails, it comes back to us as a requirement or enhancement. The FDE is the buffer between a customer's ask and the product roadmap.
- Helen: customers ask for a faster horse; your job is to give them a car.
- Aadarsh: read and validate the SQL, do not just generate it.
- Arun on the actual goal: Harsh's primary goal is to make customers use more agents.
- Shape: five to six concurrent enterprise customer or POC relationships per quarter, not sprint-based.

## What "done" means

Not "the flow runs". Five clauses. Give them without notes.

1. **The output is real and you have read it.** Not a test fixture. The actual deck, the actual numbers, opened.
2. **It reaches the right person**, and you can say who that is and who else should know. Arun's rule is a completion criterion, not advice.
3. **It stays a draft until the customer says yes.** `draft: true`, `trigger_config: null`. Publishing is a separate act on an explicit green light for that specific artifact.
4. **Somebody would notice if it broke.** A scheduled flow that fails at 6am fails quietly. Who notices is answered before publishing.
5. **The write-back happened.** The company folder is updated (NOW, the brief, the glossary), and the report to the team is in Preetam's four headings.

## What you refuse, even when a tool would let you

Any one of these is a correct answer, said plainly.

- **Activate, publish or schedule anything** in a customer workspace without an explicit green light for that artifact.
- **Any non-GET write** to `/api/*` or a `data_connection.request` with a method other than GET.
- **Anything that leaves the building:** an email, a Slack message to a customer channel, a task in the customer's own tracker.
- **Run your own tooling inside a customer workspace.** Arun's reason is commercial.
- **Use a personal account or personal AI tooling on customer data.** Official accounts only, Cursor first.

## The contract clock

Every piece of work is checked against the contract. Working 40 hours against a flat-fee week is not diligence, it is an unpriced gift. Saying so is part of the job. You are a contractor of the US entity paid via Deel. The first quarterly performance measurement is 30 November 2026, which decides INR 60,000.

## The habits worth keeping

- **Read the record before the code.** The repo holds what the code cannot show: what was decided, by whom, and what they asked for next.
- **Mark every claim verified or assumed.** Two days in, a confident wrong number is not recoverable.
- **Print `>> METHOD /path` before every call.** Which workspace, which flow, which method. Before, not after.
- **Read the current month's release notes before every customer call.**
- **Every term you did not understand gets decoded the same session.** Not "look it up later". That is the glossary's job.
- **First sentence commits.** The detail comes after.
- **Copilot, not autopilot.** Nothing is sent, posted, submitted or pushed on your behalf without you pressing the button. Skills draft. You send.

## Understanding is a tracked state

On 11 September the repo held a 247-line explainer, a driver script, four narrated videos and a brief for the harness, and you still said you knew nothing about it. Producing the explanation is the easy half. So every new thing you must work on gets an on-ramp in fixed layers, general before specific, and the on-ramp is not done until you answered its three check questions in your own words. This book is built on the same idea.

## Traps

- Treating "the customer asked for it" as authorisation.
- Confusing "Aadarsh approved the approach" with "the customer approved the artifact".
- Letting a skill's own permissions outrank the draft gate.

## Check yourself

1. Say what "done" means for a deliverable, in five clauses.
2. Name one thing you would refuse to do even if a skill said you could.
3. Why is the agent-adoption assignment both the work and the answer to the pay question?
