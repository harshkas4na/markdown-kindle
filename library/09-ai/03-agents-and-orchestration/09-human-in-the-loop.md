# Human-in-the-Loop

**Fast overview:** Every company in the corpus building agents over real operations says some version of "governed", "operator controls" or "human approval". Almost none of them means a checkbox. This chapter treats the human gate as an architectural component with its own design problems: where the gate goes, what the human is actually shown, why approval fatigue destroys the safety property you thought you bought, and how the whole thing gets measured.

## The premise

An agent acting on the world will sometimes be wrong. The question is never "how do we stop that" — it is "what does a wrong action cost, and who catches it before it lands".

Human-in-the-loop is the answer for actions whose cost is high enough. It is not free: it adds latency measured in minutes or hours, it consumes a scarce human, and it introduces its own failure mode in the human who stops reading.

## Where the gate goes

Four placements, and the choice matters more than the implementation:

**Before the plan executes.** The agent proposes a plan; the human approves it whole; then it runs. Good UX — one decision instead of eight — and the human is approving an intention rather than a specific action, which is a weaker guarantee if the execution diverges. Best paired with plan-and-execute (Chapter 5).

**Before each risky action.** The agent proposes `refund_order(ord_77, 4200)`; the human approves that specific call. Strongest guarantee, worst latency, and the highest fatigue risk. Reserve it for the genuinely irreversible.

**After the work, before it lands.** The agent produces a draft, a human reviews and sends. **This is the JobOps model**: the pipeline generates a resume, an email, a pack, and nothing is ever sent or submitted automatically. It is the highest-throughput form of oversight because the human reviews finished work rather than blocking a process.

**On exception only.** The agent acts autonomously and escalates when a confidence signal, a policy rule or an anomaly detector fires. Best throughput, and the whole safety property now rests on the escalation trigger being right, which is a hard problem worth being honest about.

Most real systems mix them: autonomous for reads, draft-and-review for external communication, per-action approval for money.

## The decision rule

Which actions need a gate? Two axes:

|  | **Reversible** | **Irreversible** |
|---|---|---|
| **Low impact** | Autonomous | Autonomous, log it |
| **High impact** | Autonomous with an undo path and an alert | **Gate it** |

The useful move is to **make actions reversible so they do not need a gate.** Soft-delete instead of delete. Draft instead of send. Schedule with a cancellation window instead of executing now. Every action you move from the right column to the left is a gate you do not have to staff.

That reframing — reduce the need for approval rather than adding approval steps — is the senior answer, and it is directly transferable from smart-contract thinking, where the equivalent instinct is bounding what a function can do rather than trusting the caller.

## Designing the approval itself

This is where most implementations are weak, and it is what separates a real answer from a checkbox.

**Show the action in the user's language, not the model's.** Not `refund_order({"order_id":"ord_77","amount_cents":4200})`. Instead:

> **Refund £42.00 to Jane Doe** for order #77 (placed 12 July, annual plan).
> **Why:** the order is within the 30-day window and the customer reported a duplicate charge.
> **Evidence:** [policy §4.2] [order record] [the customer's message]
> **If wrong:** refunds are reversible within 24 hours.

Every line is doing work. The **plain-language action** is what the human is actually deciding. The **reason** lets them evaluate the judgement, not just the operation. The **evidence links** let them verify in seconds instead of switching systems. The **reversibility note** calibrates how much care this decision deserves.

**Offer more than approve/reject.** Real reviewers want to *edit*: same action, different amount; same email, different second paragraph. An approve/reject-only gate forces a reject-and-retry loop that wastes everyone's time and teaches the human to approve marginal cases rather than fight the UI.

**Capture the reason on reject.** This is the highest-value data in the entire system. A rejection with a reason is a labelled failure case: it goes into the eval set, and the pattern across rejections tells you what to fix. `x-ops` already encodes this instinct — dismissing the voice guard requires a reason, and the reason is the payload, because an override is the user stating a rule at the moment it applies. Same principle, and it is worth stealing for any approval UI.

## Approval fatigue, which is the real failure

A human asked to approve forty low-risk actions an hour stops reading by the eighth. The gate is still there; the safety property is gone. And now you have worse than no gate, because everyone believes an action was reviewed.

Defences:

- **Gate less.** Move actions to the reversible column. Raise thresholds so only genuinely risky actions surface.
- **Batch.** Twelve similar actions reviewed as a group with the outliers highlighted, rather than twelve separate prompts.
- **Auto-approve the confidently routine**, with sampled auditing. A random 5% of auto-approved actions goes to a human anyway, which keeps you honest about whether the threshold is right.
- **Measure the approval rate.** If 99% of prompts are approved, the gate is theatre and the threshold is wrong. If 40% are rejected, the agent is not good enough to be proposing.

That last metric deserves emphasis: **approval rate is a measure of your agent, and time-to-decision is a measure of your gate.** Both belong on the dashboard, and neither is usually there.

## Implementing suspend and resume

The technical requirement is that a run can stop for an arbitrary time and continue. Which means state must be durable and the process must not be holding it.

With LangGraph, `interrupt()` plus a checkpointer (Chapter 8). Without a framework, the pattern is:

1. Persist the full run state to a store, keyed by run id.
2. Emit an approval request (a row, a queue message, a Slack action, an email) carrying the run id and the proposed action.
3. Return from the process. Hold nothing.
4. On the human's response, load the state, apply the decision, continue from the next step.

The details that bite: **expiry** (what happens to a request nobody answers in 48 hours — default deny, and say so), **idempotency** (the human clicks approve twice), **authorisation** (is this person allowed to approve this), and **audit** (who approved what, when, and what they were shown — the last part matters legally and is usually missing).

## What to log

An approval event should record the run id, the proposed action and arguments, **the exact rendering the human saw**, the decision, the reason, the approver's identity, and the timestamps. "What they were shown" is the field people omit and the one that matters when a decision is questioned six months later.

## Where this fits the corpus

Several companies in the pipeline describe exactly this surface. Rem Labs' posting names "execution visibility, operator controls, observability UX" as the scope of the role. Railway's framing is "bumpers to keep it on the rails" and "your AI wants to nuke your database". Kontigo has an LLM that can move USDC in a chat window, where the dossier's own recommendation is a confirmation layer.

The through-line worth saying in any of those conversations:

> The interesting problem in an approval flow is not the pause. It is what the human sees, and whether the rate of prompts is low enough that they are still reading by the fortieth one. A gate that gets rubber-stamped is worse than no gate, because everyone downstream believes the action was reviewed.

*Connect the dot:* the JobOps rule that nothing is ever sent or submitted automatically is this chapter's third placement, chosen deliberately. It is worth noticing that the rule is stated as a system property in `CLAUDE.md` rather than as a request in a prompt, which is exactly the enforcement distinction Book 05 is built on.

Next: multi-agent systems, and the cost you always pay.
