# Where This Road Ends: The Microservices Trigger

Everything so far scales **the whole application, as one unit** — more copies of the exact same server, all running identical code. That works for a while. This file is about exactly where and why it stops working, because that breaking point is the actual, honest reason microservices exist — not "microservices are the modern way," but a specific, nameable pain.

## The problem with scaling a monolith horizontally forever

Real applications don't load evenly across their own features. Shadow's site probably has an auth/login path hit on *every* request, a browse/search path hit constantly, and a checkout path hit rarely but doing heavy work (payment processing, inventory locks, emails). When you scale "the whole app" horizontally, you're scaling **all of that together** — paying to run 20 copies of the checkout logic just because the login logic needs the headroom, because they live in the same deployable unit.

Beyond pure cost, there's a **blast radius** problem: a bug or a bad deploy anywhere in the monolith can take down the *entire* app, including the parts that had nothing to do with the bug. A memory leak in the image-processing code can eventually OOM-kill the same process serving login requests, because it's all one process.

And there's an **organizational** problem, which in practice is usually the first one teams actually feel: once enough engineers/teams work in one shared codebase, merge conflicts and coordination overhead become a constant tax — teams start blocking each other just by working in the same place at the same time, a one-line hotfix needs sign-off and a deploy window from multiple teams, and a single migration can lock the whole system for everyone.

## The actual signs it's time (not a vibe, real signals)

- One specific part of the app has a genuinely different scaling profile than the rest (e.g. video processing is CPU-heavy and bursty; the API is I/O-bound and steady) — scaling them together wastes money in one direction or the other.
- Multiple teams are stepping on each other in the same codebase as a matter of routine, not occasionally.
- A tiny, unrelated change keeps breaking something else — a sign the codebase's internal boundaries are already too tangled for one team to safely reason about the whole thing.
- A single hotfix regularly needs multiple teams and a scary off-hours deploy window.

## The trap: picking the wrong first service, and fake boundaries

Two very real mistakes worth knowing before this is ever attempted for real:

- **Don't extract the "most important" or most painful service first.** The instinct is to carve out the scariest, most central piece to "get the big win" — but the right first candidate is whichever piece has the *fewest remaining dependencies* on the rest of the system, because that's the one you can actually cut loose cleanly. Extracting the most tangled piece first means dragging half the monolith's dependencies out with it.
- **A shared database table is not a real boundary.** If both the monolith and a newly extracted service still write to the same table, you haven't created two services — you've created what's bluntly called a **distributed monolith**: all the network/deployment complexity of microservices, with none of the actual independence, because a schema change to that table can still break both sides. A real service boundary means each piece of data has exactly one service that's allowed to write to it; everyone else asks that service for it (or reads a replica of it), never touches its table directly.
- **Don't rush this to "show progress."** If observability (can you tell which service failed?), CI/CD, and routing between services aren't solid first, a badly-operated microservice is a worse position to be in than the monolith you started with — you've added network calls, partial failure, and deployment complexity without the tooling to manage any of it.

## How it's actually done safely: the strangler fig pattern

Nobody sane rewrites a monolith into microservices in one big-bang cutover — that's an enormous, high-risk bet with no partial credit if it goes wrong. The standard, safer approach is named after the **strangler fig tree**, which grows around a host tree and gradually takes over, rather than cutting the host down first:

1. **Transform** — build the new, modernized piece as an independent service, alongside the still-running monolith.
2. **Coexist** — put a routing layer (often just an HTTP proxy rule) in front that intercepts calls for that specific piece of functionality and sends them to the new service, while everything else keeps going to the monolith unchanged.
3. **Eliminate** — once traffic is fully and confidently flowing to the new service, remove that functionality from the monolith.

This means at every point in the migration, you have a fully working system, and you can stop or roll back at any step — it's incremental by design, not a leap of faith with the whole product on the line.

## Why this is the cliffhanger into the next video

Here's the part of the story that actually connects everything: once your code genuinely lives across multiple independently-deployed services talking over a network, every shortcut a monolith quietly got away with stops being free. "Just import the other module and call its function directly" isn't an option anymore — there's a network boundary now, with latency, partial failure, and versioning to worry about. Global shared state, tight coupling between modules, and vague, implicit contracts between parts of the code — all things a monolith can survive on for years — actively break things once those parts are separate services owned by separate teams shipping on separate schedules.

**This is exactly why OOP, SOLID, and pattern recognition stop being "good practice for interviews" and become "the only way this doesn't collapse":** clean interfaces, explicit contracts, and well-defined boundaries between modules are precisely the skills that let you draw a *correct* line when you eventually do split something out — and they're what keep a service's internals sane once a team owns it independently. You can't safely decompose a system whose internal boundaries were never clean in the first place. That's the story's actual reason for pivoting to the code/LLD video next, not an arbitrary "now let's also cover some CS theory."

## Commonly skipped

- "Microservices" is often taught as a scaling technique on its own, when the honest trigger is almost always organizational/blast-radius pain first, uneven scaling profile second — raw traffic volume alone is rarely the real reason.
- **Premature microservices** is a very real and common mistake — paying the network/ops/observability tax before you actually have the org-scale problem that justifies it. A monolith that's merely "big" doesn't automatically need this; a monolith with the specific signs above does.
- The "shared table = distributed monolith" trap is almost never mentioned in casual explanations, and it's the most common way a microservices migration technically happens but delivers none of the promised benefits.

## Go deeper

- [Strangler fig pattern — AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/strangler-fig.html)
- [Pattern: Strangler application — microservices.io](https://microservices.io/patterns/refactoring/strangler-application.html)
