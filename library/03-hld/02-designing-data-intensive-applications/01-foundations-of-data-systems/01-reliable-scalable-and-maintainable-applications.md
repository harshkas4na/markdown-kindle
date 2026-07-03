# Reliable, Scalable, and Maintainable Applications

Modern applications are rarely built on one do-everything database. A typical service composes a handful of specialized tools — a relational store for transactional data, a cache for hot reads, a full-text search index, a message queue for async work, a batch/stream pipeline for derived data — and stitches them together with application code. That composition is why this field is called **data-intensive** systems rather than just "databases": the interesting engineering is in choosing the right tool per job and keeping them consistent with each other, not in any single tool alone.

Almost every design decision in this space can be judged against three non-negotiable properties. They sound like vague virtues, but each has a precise, load-bearing definition.

## Reliability

Reliability means the system keeps doing the right thing even when things go wrong — not "nothing ever goes wrong." Two words worth separating:

- A **fault** is one component deviating from spec (a disk fails, a node crashes, a network link drops packets, a human runs the wrong command).
- A **failure** is when the *system as a whole* stops providing the required service to its users.

The whole discipline of reliability engineering is about building **fault-tolerant** systems: ones designed so that individual faults don't cascade into a failure. This means deliberately *introducing* faults in testing (this is the actual justification behind chaos engineering — killing a random production node on purpose — you want to find out whether your fault tolerance actually works, before an unplanned fault finds out for you).

Faults come from three places, and they need different defenses:
- **Hardware faults** (disk failure, RAM corruption, power loss) — traditionally handled with redundancy (RAID, replicated disks, dual power supplies). At large scale, hardware faults become so frequent (statistically, with thousands of machines) that redundancy alone isn't enough — you need software that assumes machines will die routinely and keeps working anyway.
- **Software bugs** — often correlated and systemic (unlike random hardware faults): a bug in a library or a resource leak can bring down every node running that code simultaneously, which is a much scarier failure mode than one disk dying.
- **Human error** — configuration mistakes are one of the leading causes of real outages. The fix isn't "hire people who don't make mistakes," it's designing systems that make mistakes hard to make and easy to undo: sandboxes for testing config changes safely, fast rollback, good telemetry to catch a problem quickly, and interfaces that decouple the easy/common path from the dangerous/rare path.

## Scalability

Scalability is not a single number a system either "has" or "doesn't have" — the question "does this scale?" is meaningless without first describing **load**: the specific parameters that describe how much work the system is under (requests/second, ratio of reads to writes, number of simultaneously active users, size of the fan-out per action).

The classic illustration is a social network's timeline: do you compute a user's feed by scanning all the people they follow at *read* time (cheap to write a post, expensive to read a feed, and gets worse the more people you follow), or do you push a copy of every new post into every follower's precomputed timeline at *write* time (cheap, fast reads, but a single post from an account with millions of followers now means millions of writes)? Neither approach is "correct" — the right one depends entirely on your actual read:write ratio and how skewed your follower counts are. Real systems often use a hybrid: fan-out on write for typical users, fan-out on read for accounts with huge followings, to avoid a single celebrity post triggering millions of writes.

Once you know your load, you need a way to describe **performance** under that load:
- For batch systems, this is usually **throughput** (records processed per second).
- For online systems, this is usually **response time** — and never as a single average. Use **percentiles** (p50, p95, p99): the tail (p99) is what your heaviest, most valuable users actually experience, and it's frequently an order of magnitude worse than the median. Averages hide exactly the users you most need to keep happy.

**Coping with load** is either scaling *up* (a bigger machine, vertical scaling) or scaling *out* (more machines sharing the work, horizontal scaling, aka a **shared-nothing architecture**). There's no universally "elastic" architecture that handles any load parameter automatically — a system built to handle 100,000 requests/second of small reads is a completely different design than one built to handle a few requests/second of enormous batch jobs. Scalability work is always specific to *your* load pattern.

## Maintainability

Most of the cost of software isn't writing it — it's the years of people afterward fixing bugs, adapting it to new requirements, and just keeping it running. Three sub-properties make a system maintainable:

- **Operability** — is it easy for operations teams to keep the system running smoothly (good monitoring, predictable behavior, good documentation, sane defaults)?
- **Simplicity** — is it easy for new engineers to understand the system? This isn't about fewer features, it's about managing **complexity**: unnecessary complexity (accidental complexity from implementation, not from the actual problem) is what makes systems hard to reason about and easy to break. The main tool against it is good **abstraction** — hiding implementation detail behind a clean interface (a SQL engine hides its storage/query-planning internals; a high-level language hides machine code).
- **Evolvability** (aka agility, at the data-system level) — how easily can the system be adapted for new, unanticipated requirements? Requirements always change; a system's long-term value depends heavily on how cheaply it can absorb that change.

## Quick reference

| Property | The real question it's asking | Common failure mode when ignored |
|---|---|---|
| Reliability | Does it keep working correctly when a component fails? | Silent data loss/corruption during a routine fault |
| Scalability | Have you defined *load*, and does performance stay acceptable as that load grows? | Fine at launch, falls over at 10x traffic because nobody defined "10x of what" |
| Maintainability | Can someone who isn't you safely change this in a year? | Working system nobody dares touch — every change is a gamble |

## Takeaways

- "Is this reliable/scalable?" is an incomplete question until you specify: reliable against *which* faults, scalable for *which* load parameter.
- Percentiles, not averages, are the only honest way to talk about response time.
- Simplicity (via good abstraction) and evolvability aren't nice-to-haves — they're the actual determinant of how much a system costs to own over its lifetime, which usually dwarfs the cost of building it.
