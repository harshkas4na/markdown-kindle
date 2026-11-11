# The world the customer lives in

![Illustration for this chapter](../img/art-six-products.jpg "Illustration. Generated for this book, no real data")

> [!STORY] The account that never churned
> Trellix sells many security products, and its customers hold several at once. Imagine, as an illustration and not a real account, a customer who holds six of them and renews five while dropping one. Did they churn?
> If your answer is yes or no, you have a problem. They kept most of the money and still left a hole. A model that only knows "churned yes or no" would call this account a success, and be right about the wrong thing. The money still dropped.
> This is why accuracy at Trellix is measured on quarterly drops in revenue (ARR), not on a churn flag.

You came from backend and web3. Enterprise customer success is a different world with its own words. You do not need to become a CSM. You need to follow a customer call without translating in your head. This chapter is the translation.

## The words, in the order they will be thrown at you

- **ARR and ACV.** Annual recurring revenue and annual contract value. Every report is money-weighted. "1,444 renewals worth $37.8M" is the headline, not the count.
- **Churn.** The customer leaves. It is the thing being predicted.
- **GRR (gross retention).** Revenue kept, before any upsell. It can never exceed 100 percent. It measures leakage.
- **NRR (net retention).** Revenue kept plus expansion. Above 100 percent means the base grows without any new customers. It is the number a board reads.
- **Renewal motion.** The 90 to 180 days before a contract ends, where someone works to keep it. Needle movers exist to fire before this starts.
- **CSM.** Customer Success Manager. Owns a book of 40 to 80 accounts. The person the product is for.
- **CCO or VP of CS.** Runs the customer success organisation. The person who buys.
- **QBR.** Quarterly business review with a customer. A deck gets shown. FunnelStory generates them.
- **Book of business.** The accounts one CSM owns. A real configuration need: Photon's owner-email mapping is exactly this.
- **Expansion or upsell.** More money from an existing account. Predicted with the same machinery as churn, with the opposite sign.
- **Adoption.** Whether they actually use what they bought. The early half of any early warning.

## Partial churn and the denominator

Back to the story. Because enterprise customers hold many products, they almost never leave entirely. They drop one product, shrink the seat count, or renew at 60 percent. So:

- "Did they churn, yes or no" is the wrong label for training a model and for judging it. Almost every row says "no", so the model looks brilliant and is useless.
- The real shape is **partial churn and partial expansion**.
- The model config has a matching idea: a design exists for filling `churned_at` inside `products_info` when a product's ARR drops from an earlier value. Partial product churn as a first-class concept.

## Precision, recall, and the sentence that stopped a meeting

In the 31 August standup, Alok interrupted the whole discussion: "Hold on, take a step back. What does precision and recall basically mean?" He was not confused about the metric. He was refusing to continue on an unstated definition.

The two metrics, as this team uses them:

- **Precision:** of the accounts we flagged as at risk, how many really dropped.
- **Recall:** of the accounts that really dropped, how many we flagged. This is the one that matters commercially, because a miss is a surprise churn, and surprise churn is the product's entire promise.

And the rule he stated: **presenting recall for a small set would be very misleading.** A recall of 100 percent on four hand-picked accounts earned no credit at all. Bring the denominator before the number. State the target set: every account that came up for renewal in the last 90 days, at account level first, product level later.

When an early attempt gave 12 percent recall on a wrongly defined set, Preetam's answer was: first of all, set up the experiment properly. Unless that is correct, the rest does not matter.

## Where the early signals live

Two halves.

- **Structured:** the warehouse, the CRM, product analytics, tickets, billing. Countable, but late.
- **Unstructured:** calls on Zoom, Gong, Fathom or Chorus, Slack, email, chat, notes. Early, and invisible to every warehouse.

The early signals a CSM would recognise: a champion leaving, a single point of contact (called single-threaded), engagement going quiet, a pricing objection, a competitor named, a feature request open for three quarters, a Sev 1 ticket at the wrong moment.

## What it looks like when it goes wrong

All real, from the record:

- At Trellix, Brent opened the first account in a report and found a score of 22 on an account whose renewal was already confirmed. The meeting never got past it. Four product screens disagreed about the same account.
- A customer user wrote: everything in needle movers seems reset today, I cannot find my assigned needle mover and the assignee column is blank.
- In a shared channel: why is Navan marked as zero health?

Every one of those is a **trust event**, not a bug report. The product's currency is a number somebody is willing to act on. One number nobody can explain costs more than ten missing features.

## Traps

- Saying "churn rate" when the account can only partially churn.
- Quoting a recall number without saying what set it was measured on.
- Assuming the CSM wants a better score. They want to know what to do on Tuesday.

> [!PROJECT] Where you see this in your week
> The agent-adoption work Arun gave you is a measurement problem with a hidden denominator: adoption of what, among whom, over what window. The Descope recall question (about 1,700 closed-lost deals in HubSpot versus 70 churned accounts in their view) is the same trap in a customer's data.

## Check yourself

1. Why does an account holding six products almost never "churn", and what does that force the accuracy measurement to become?
2. State the denominator-before-the-number rule, and whose rule it is.
3. Name two early signals that no warehouse can see.
