# The Sharpest Misconceptions + Facts Worth Knowing

Everything here is a callback to the other files — this is the review pass. If you only re-read one file before recording anything, make it this one; each point below is something that sounds obviously true until you look closely, and each is a real, documented cause of real incidents.

## Misconceptions

**"More servers = more capacity."** Only true once the servers are stateless (`03`). Add servers to a stateful app and you don't get more capacity, you get randomly broken sessions — capacity didn't increase, correctness decreased.

**"Load balancer health checks prove the server is healthy."** An L4 check only proves a *port is open* — not that the application behind it is actually functioning. A very real, documented failure mode: an app deadlocks internally, the OS-level port stays open, an L4 (NLB-style) health check keeps passing, and the load balancer keeps happily sending real users into a server that can't actually respond. L7 checks (a real HTTP request expecting `200`) catch this; L4 checks structurally cannot (`04`).

**"Round robin is the load balancing algorithm."** It's *an* algorithm, and it silently assumes every request costs the same amount of work — false for almost any real API where some endpoints are cheap and others trigger heavy DB queries or long-lived connections. Least connections (or a weighted variant) is the better real-world default for uneven workloads (`04`).

**"We have autoscaling, so we're covered for spikes."** Autoscaling is reactive to a metric that's already stale by seconds-to-minutes, and new capacity takes real time to boot/warm up/pass health checks. For a sudden, sharp spike (something going viral in minutes), the new capacity often isn't ready until the spike has already caused damage or already passed. Known spikes (launches, sales) need *scheduled* pre-scaling, not just reactive autoscaling (`05`).

**"Vertical scaling is the old-fashioned / lazy option."** In practice it's usually the *correct first move* — zero architecture change, minutes to apply, fully reversible. Real teams reach for it before horizontal scaling almost every time, specifically because horizontal scaling has a hidden prerequisite (statelessness) that vertical scaling doesn't (`02`).

**"Average latency tells you how the service is performing."** It tells you almost nothing about your most active users' experience. p99 latency is what your heaviest, most valuable users actually feel, and it can be terrible even when the average looks great (`01`).

**"Microservices are just how you scale at any real size."** The actual, honest trigger is uneven load profile + organizational/blast-radius pain, not raw traffic volume by itself. Splitting a service before you have that specific pain is "premature microservices" — you pay real network/ops/observability cost for a problem you don't have yet (`06`).

**"We split it into microservices, so we're decoupled now."** Not if both services still write to the same database table — that's a **distributed monolith**: all of the network and deployment cost of microservices, none of the actual independence (`06`).

## Interesting facts

- The exact math behind "how many servers do I need" (Little's Law: concurrency = arrival rate × latency) is over 60 years old and originally comes from queueing theory, not software — it applies identically to bank teller lines, hospital waiting rooms, and API servers, because it's a property of *any* queue, not a software-specific trick.
- **Consistent hashing** — the algorithm that decides which server handles a given cache key with minimal disruption when servers are added/removed — is the same underlying idea used by CDNs, distributed caches, and peer-to-peer DHTs to decide "who owns this piece of data." One idea, reused across a huge range of systems that otherwise look nothing alike.
- Cloud autoscaling's asymmetry (fast to scale out, slow/cautious to scale in) isn't a technical limitation, it's a deliberate design choice — being briefly over-provisioned costs money; being under-provisioned during a real spike costs availability, and every major provider's default behavior weights availability higher.
- Running Kubernetes' Horizontal and Vertical Pod Autoscalers on the *same raw metric* for the same workload can make them fight each other indefinitely — informally called the "Kubernetes death spiral." Two individually-correct automated systems, actively undermining each other because neither is aware the other exists (`05`).
- The default AWS load balancer deregistration delay is a fairly generous 300 seconds — most real teams tune it down to 30–60 seconds once they understand what it's actually for, because the default optimizes for "never cut off a slow request" at the cost of slower deploys and scale-downs (`04`).
