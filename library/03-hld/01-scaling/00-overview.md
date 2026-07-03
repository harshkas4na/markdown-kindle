# The Scaling Arc — Overview

**Goal:** to actually *understand* the part of the story where Shadow's one server stops being enough — not just enough to narrate it in a video, but enough that if you were handed the keys to a real struggling service tomorrow, you'd know exactly which knob to turn first and why. Simple words, but the underlying model has to be correct — no hand-waving.

This is a personal study set, not a script. Read it to build the intuition. The video will only ever use 10% of what's here — but you can't pick the *right* 10% unless you know the other 90%.

## Where this sits in the bigger story

v3 already told the audience: Shadow has a website → domain + server + code + DB. Then load grows. This arc picks up exactly there and answers, in order:

1. How do you even know one server isn't enough? (you need a number, not a feeling)
2. What are your two options once you know it isn't enough?
3. Why doesn't "just add more servers" work the moment you try it?
4. Something has to *decide* which server gets which request — what is that thing, really?
5. Who presses the button to add/remove servers — and can a machine do it instead of you?
6. Where does this road actually end? (spoiler: it ends at "this isn't one service anymore" — which is the cliffhanger into the code/LLD video)

## File map

| File | What it answers |
|---|---|
| `01-capacity-estimation.md` | How do you know you need to scale at all? (Little's Law, QPS, percentiles, the Shadow numbers) |
| `02-vertical-vs-horizontal-scaling.md` | Your two options, how each is actually done, why real teams reach for vertical first |
| `03-statelessness-and-sessions.md` | The trap: horizontal scaling silently breaks logins/carts unless you fix this first |
| `04-load-balancers.md` | The thing that makes "many servers" look like "one service" from outside |
| `05-autoscaling-in-practice.md` | How AWS/Kubernetes do steps 2–4 automatically, and where that automation itself breaks |
| `06-monolith-to-microservices-trigger.md` | Why scaling the *whole* app eventually stops making sense — the actual trigger for microservices |
| `07-misconceptions-and-facts.md` | The sharpest "everyone gets this wrong" list + a few things worth knowing just because they're neat |
| `08-end-to-end-scenario-playbook.md` | You, at 2am, as the on-call engineer — the whole arc as one continuous action sequence |
| `SOURCES.md` | Where the specific claims/numbers came from, in case you want to go deeper on any one of them |

## The full syllabus (so you know what exists, even if we don't go deep on all of it here)

This arc deliberately stops at the microservices *trigger* — it does not cover DB scaling, caching, or queues in depth. Those belong to the next HLD phase (after the code/LLD detour), because the story goes: scale the servers → feel the code pain → learn OOP/SOLID/patterns → *then* come back and scale the data layer with that discipline in hand. For now, just know the full tree so nothing feels like it came out of nowhere later:

- **Capacity & estimation:** QPS/RPS, concurrency, Little's Law, percentiles (p50/p95/p99), peak-vs-average traffic, read:write ratio
- **Scaling shape:** vertical (scale up) vs horizontal (scale out), cost curves, hardware ceilings
- **The horizontal prerequisite:** statelessness, session stores, sticky sessions as a stopgap
- **Traffic distribution:** L4 vs L7 load balancing, algorithms (round robin / least connections / consistent hashing / IP hash), health checks, connection draining, DNS-level load balancing
- **Automation:** AWS Auto Scaling target tracking, Kubernetes HPA/VPA/Cluster Autoscaler, scheduled/predictive scaling
- **The ceiling of "just scale the monolith":** uneven load across features, blast radius, org friction → strangler-fig decomposition into services
- *(deferred to the next arc)* DB scaling: read replicas, sharding, connection pooling, caching (Redis/CDN), message queues, eventual consistency
- *(deferred further)* observability/monitoring at scale, service mesh, distributed tracing

Read 01 → 08 in order once; after that they stand alone as reference.
