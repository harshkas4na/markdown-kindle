# Vertical vs Horizontal Scaling

So now you have a real number telling you Shadow's one server is at its edge (see `01-capacity-estimation.md`). There are exactly two directions to go from here, and it's worth understanding both properly before deciding — because the "obviously horizontal is better" instinct most people have is wrong more often than you'd think.

## Vertical scaling — make the one server bigger

Same server, more muscle: more CPU cores, more RAM, faster disk. In cloud terms this is an **instance type** change — e.g. an AWS EC2 `t3.medium` (2 vCPU, 4GB RAM) becomes a `t3.xlarge` (4 vCPU, 16GB RAM). Nothing about your architecture changes. Your code doesn't know or care.

**How it's actually done:** on AWS, you stop the instance, change its instance type, start it again — this means downtime (seconds to a couple of minutes) unless you're behind a load balancer with other instances still serving. On Docker, this is `docker update --cpus=... --memory=...` on a running container, or just editing the resource limits in `docker-compose.yml` and recreating it. On Kubernetes, this is editing a pod's resource `requests`/`limits` — which is exactly what the **Vertical Pod Autoscaler** automates (more on that in `05-autoscaling-in-practice.md`).

**Why real teams reach for this first, not horizontal:** it requires zero code changes, zero architecture changes, and takes minutes. If your service is stateful, has in-memory sessions, or was never designed to run as multiple copies, vertical scaling is the *only* option that doesn't also require you to first solve statelessness (see `03-statelessness-and-sessions.md`). This is why, in practice, "just get a bigger box" is usually the very first move a team makes, not a last resort.

**Where it stops working:**
1. **There's a hardware ceiling.** Eventually you're on the biggest instance type that exists. You cannot buy a bigger box past that point, full stop.
2. **It's a single point of failure.** One box, however big, is one box. If it dies, everything is down. Vertical scaling never gives you redundancy.
3. **Cost stops being linear near the top.** Going from a medium to a large instance roughly doubles cost for roughly double capacity — reasonable. But the largest instance types in a family are disproportionately expensive per unit of compute compared to the mid-range ones, because you're paying for scarcity/exclusivity of high-end hardware, not just raw resources.

## Horizontal scaling — add more identical servers

Instead of one bigger server, run N identical copies of the same server and split traffic between them. In cloud terms this is an **Auto Scaling Group** (AWS) growing from 2 instances to 10, or a Kubernetes **Deployment** going from `replicas: 2` to `replicas: 10` (`kubectl scale deployment shadow-api --replicas=10`), or plain `docker-compose up --scale api=5`.

**Why it's more powerful long-term:**
- No hardware ceiling — you can (in principle) keep adding machines indefinitely.
- It gives you redundancy for free: if one of ten servers dies, you lose 10% of capacity, not 100% of the service.
- Cost scales roughly linearly, which is more predictable than vertical's cost curve near the top.

**Why it's harder than it sounds — the catch nobody mentions when they say "just add more servers":** the moment you have more than one server, *something* has to decide which server gets which request (that's `04-load-balancers.md`), and your servers have to actually be interchangeable — meaning any of them can handle any request with the same result. That second part is not automatic. It requires your application to be **stateless**, and most applications, written without this in mind, are not. That's the entire subject of the next file, and it's the part almost every "just horizontally scale it" explanation skips.

## So which do you actually pick?

In the real world, almost nobody picks purely one or the other — the realistic sequence, and the one that matches how Shadow's story should play out, is:

1. **Vertical first**, because it's fast and free of architectural consequences — buys you breathing room immediately.
2. **Horizontal once vertical hits its ceiling, or once you need redundancy** regardless of raw capacity (you never want "one server" to be a single point of failure even if that one server could technically handle the load).
3. Horizontal scaling is also the *only* path that unlocks automatic scaling driven by real-time metrics (`05-autoscaling-in-practice.md`) — a single big vertical box can't "add more of itself" on demand the way a fleet can.

## Commonly skipped

- People treat vertical scaling as outdated/lazy. In practice it's the correct first move almost every time — it's cheap, instant, and reversible.
- "Horizontal scaling" is casually said as if it's a single action, when it actually silently assumes your app is already stateless — a huge, often false, assumption.
- The redundancy argument is usually left out — horizontal scaling isn't just about *more* capacity, it's about not having a single point of failure at all, which matters even for services with low traffic.

## Interesting fact

The cost curve near the top of an instance family isn't a coincidence — cloud providers price the largest, highest-spec machines at a premium because demand for "the biggest box available" is inelastic (someone with a genuine need for it will pay), while the mid-tier instance types are where the real price competition between customers (and, indirectly, between cloud providers) happens.

## Go deeper

- [Scaling Up vs Scaling Out — DIRA (Medium)](https://medium.com/@drajput_14416/scaling-up-vs-scaling-out-392c03df6119)
- [Stateful and Stateless Horizontal Scaling for Cloud Environments](https://www.rosehosting.com/blog/stateful-and-stateless-horizontal-scaling-for-cloud-environments/)
