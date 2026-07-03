# Load Balancers

You now have N stateless, interchangeable servers instead of one. Something still has to actually receive every incoming request and decide *which* of the N servers handles it — and it has to do this in a way that's invisible to the user, who should still feel like they're talking to one single website. That thing is a **load balancer**.

## What it actually is

A load balancer is a **reverse proxy with a health-check-driven routing decision baked in**. Two things are true about it that matter a lot:

1. Your domain name / DNS now points to the **load balancer**, not to any individual server. The servers themselves usually don't even have public IPs anymore — they're only reachable *through* it.
2. It constantly checks which servers are actually alive, and only sends traffic to the ones that are — this is what turns "one of my ten servers just died" from an outage into a non-event nobody notices.

## Layer 4 vs Layer 7 — how deep does it actually look?

This is the single most important distinction to get right, because it explains *why* two different load balancers can behave completely differently even though both are "load balancing."

**Layer 4 (L4)** operates at the TCP/UDP level — it sees IP addresses and port numbers, and forwards packets without ever opening or reading them. It has no idea if the payload is HTTP, a database protocol, or anything else. This makes it extremely fast (operations measured in **microseconds**, and able to push millions of requests/sec with very little CPU overhead) but also somewhat blind — it can confirm a **port is open**, but has no idea if the application behind that port is actually working correctly.

**Layer 7 (L7)** terminates the connection and actually reads the application protocol (HTTP, gRPC, WebSocket). Because it understands the content, it can route based on the URL path (`/api/*` to one fleet, `/images/*` to another), the hostname, or headers/cookies — and its health checks can be a real HTTP request that must return `200 OK`, not just "is the port open." The cost is a bit more latency per request (roughly **1–5ms**, versus L4's ~50–100 microseconds) because it's doing real work on the content.

On AWS specifically: **NLB (Network Load Balancer)** is L4, **ALB (Application Load Balancer)** is L7. A very concrete failure mode this explains: an NLB can keep sending traffic to a server whose *port* is open but whose *application* has deadlocked or crashed internally — because from L4's point of view, nothing looks wrong. An ALB, checking an actual HTTP endpoint, would catch that server as unhealthy and stop routing to it. This is exactly why most ordinary web services sit behind an L7 balancer, and L4 is reserved for cases that genuinely need the raw speed and don't need content-aware routing (raw TCP services, extremely high-throughput scenarios, or as the entry point in front of an L7 balancer for even more scale).

There's also a coarser layer above both of these: **DNS-level load balancing** (e.g. AWS Route 53's weighted or latency-based routing), which can send different users to entirely different regional load balancers before a single TCP packet is even sent — useful for routing users to their nearest datacenter, or for gradually shifting traffic percentages during a rollout.

## How it picks a server — the algorithms

Once it knows *which* servers are healthy, it still has to pick one for each request:

- **Round robin** — cycle through servers in order: 1, 2, 3, 1, 2, 3... Simple and predictable, but it silently assumes every request costs the same amount of work, which is rarely true (a request that triggers a heavy DB query costs far more than a static asset request).
- **Least connections** — send the new request to whichever server currently has the fewest active connections. This adapts to real load instead of assuming equal cost, and it particularly shines when connection lengths vary a lot — long-lived WebSocket connections, downloads, or streaming, where round robin would happily keep piling long-lived work onto an already-busy server.
- **Consistent hashing** — hash something about the request (often a user/session ID or cache key) to consistently land on the *same* server every time, for as long as the server pool doesn't change. This matters enormously for caching efficiency (if the same key always hits the same server, that server's local cache is actually useful) and it has a specific superpower: when you add or remove a server, only a small fraction of keys need to remap, instead of the entire mapping shuffling — this is the exact property that also makes it the backbone of CDNs, distributed caches, and DHTs (peer-to-peer systems). One idea, reused everywhere.
- **IP hash** — hash the client's IP to a server. This is actually the lightweight way to get **sticky sessions** without needing cookies (see `03-statelessness-and-sessions.md`) — same client IP, same server, as long as the pool doesn't change.

## Health checks — active vs passive

**Active** health checks mean the load balancer proactively pings a defined endpoint (commonly `/health` or `/healthz`) on a fixed interval and expects a specific response. **Passive** health checks mean it just watches real traffic and notices when requests to a given server start failing. Active checks are more common in practice because they catch a dying server *before* it fails a real user's request, not after.

## What happens when a server leaves — connection draining

When a server is being removed from the pool (a scale-down, or a deploy replacing it), the load balancer doesn't just yank it out mid-request. It stops sending it *new* requests immediately, but lets **in-flight** requests finish — this window is called **connection draining** (AWS specifically calls it **deregistration delay**, default 300 seconds, though most real teams tune it down to 30–60s). Get this wrong in either direction: too short, and real in-flight requests get cut off mid-response during every deploy or scale-in; too long, and scale-downs/deploys become sluggish and you keep paying for capacity you no longer need.

## Commonly skipped

- Treating "load balancer" as one generic concept, when L4 vs L7 is a fundamentally different depth of understanding of your traffic — and a real, documented cause of "healthy-looking but actually broken" outages (L4 health-checking an app that's silently deadlocked).
- Round robin is often assumed to be "the" load balancing algorithm, when it's actually the *worst fit* for most real-world uneven-cost APIs — least connections or a weighted variant is usually the better real default.
- Connection draining/deregistration delay is almost never mentioned in "add a load balancer" explanations, yet it's the exact setting that determines whether your users notice deploys and scale-downs at all.

## Interesting fact

The same consistent-hashing idea used to pick a server for a request is the *same underlying trick* content-addressed storage systems use to decide "who owns this piece of data" in a distributed cache or CDN — and it rhymes with something you already know from Git: Git decides where a blob "lives" (conceptually, its identity) by hashing its content; consistent hashing decides where a *request or cache key* "lives" by hashing an identifier. Same shape of idea, wildly different domains.

## In practice (what you'd actually click/type)

On AWS: create a **target group** with a health check path (e.g. `/healthz`, expecting `200`), create an **ALB**, point it at that target group, and attach your **Auto Scaling Group** so new instances register automatically. Tune the target group's deregistration delay attribute. Self-hosted equivalents: **NGINX** or **HAProxy** in front of your fleet, configured with `upstream` blocks and a chosen balancing method. As a preview of where this is going once "servers" become "many independent microservices talking to each other" — that job gets handled by a **service mesh** sidecar proxy (e.g. **Envoy**, via Istio/Linkerd), which does the same L7 routing/health-checking/load-balancing job but *between internal services*, not just at the edge.

## Go deeper

- [L4 vs L7 Load Balancing deep dive](https://medium.com/@codeshbhai/stop-crashing-on-black-friday-a-deep-dive-into-l4-vs-l7-load-balancing-768c536a6956)
- [AWS ALB vs NLB explained](https://joudwawad.medium.com/aws-load-balancers-deep-dive-application-vs-network-explained-6efdafd1192e)
- [Load Balancing Algorithms Explained](https://www.mayhemcode.com/2025/11/load-balancing-algorithms-explained.html)
- [Deregistration Delay on AWS ALBs](https://blogs.reliablepenguin.com/2025/12/20/deregistration-delay-on-aws-application-load-balancers-alb)
