# Failing Well — Resilience and Observability

**Fast overview:** systems rarely die of the failure itself; they die of the *response* to it — retries that amplify load, queues that hide overload, one slow dependency freezing a fleet. This chapter covers how distributed systems actually fail (cascades, metastable states, gray failures), the defense kit (timeouts, backoff+jitter, circuit breakers, bulkheads, backpressure, shedding), and the instruments that let you see any of it happening (metrics, logs, traces, SLOs and error budgets). This is the operational conscience of every architecture drawn in Chapters 1–11.

## How systems actually fail

**The cascade, step by step.** A database replica slows (disk degrading — not down, *slow*: the dreaded **gray failure** that health checks miss). Requests to it stack up. Upstream services' threads block waiting (no timeout, or too long a one). Their thread pools exhaust — now *they're* down for everyone, including requests that never needed the sick replica. Clients time out and **retry**, multiplying load 2–3×. The healthy replicas, now serving retry-amplified traffic, saturate too. Total outage, root cause: one slow disk plus default settings.

**The queueing cliff.** Utilization vs latency is a hockey stick: at 70% busy, queues are short; at 90%+, wait times explode nonlinearly; at 100%, latency is unbounded and *arrival rate exceeds service rate* — the queue only grows. Corollaries: run hot fleets at ~60–75%, not 95; a growing queue (Chapter 9's shock absorber included!) is a pre-outage siren, so **queue depth and consumer lag are page-worthy metrics**; and once over the cliff, *only shedding load* — not adding it — recovers the system.

**Metastable failure.** The nastiest genus: the trigger passes, but the system stays broken — retries + cold caches (Chapter 8's 20×-load cold start) sustain the overload *after* the original cause heals. Recovery requires deliberately dropping work (or turning off features) to get back under the cliff. If your recovery plan is "wait for it to calm down," you don't have one.

## The defense kit

- **Timeouts, everywhere, tuned.** Every network call has a deadline — derived from the caller's own budget, not folklore. Better: **deadline propagation** — the edge assigns the request 500ms total; each hop passes the remaining budget downstream, so no service burns time computing an answer nobody upstream is still waiting for.
- **Retries: budgeted, jittered, capped.** Retry only idempotent operations (Chapter 11 — this is why idempotency was a whole section), only on *hopefully-transient* errors, with **exponential backoff + jitter** (synchronized retries are a self-inflicted DDoS — jitter decorrelates them), a small cap (2–3), and a **retry budget** (retries ≤ ~10% of traffic; beyond that you're amplifying an outage). Never retry at multiple layers simultaneously (client × gateway × mesh × app = 3⁴ amplification).
- **Circuit breakers.** Track a dependency's failure rate; past threshold, **open** — fail fast without calling — then periodically **half-open** to probe recovery. Converts "everyone hangs on the dead thing" into "everyone gets fast errors and the dead thing gets breathing room." Pairs with **fallbacks**: cached/stale response (Chapter 8's stale-while-revalidate as resilience), a default, or honest partial UI (feed unavailable, app still works).
- **Bulkheads.** Partition resources by dependency/tenant — separate thread pools, connection pools, even sub-fleets — so drowning dependency A can't consume the threads that dependency B's requests need. The cascade's step 3, structurally denied.
- **Backpressure and shedding.** When overloaded, the honest options are: push back (bounded queues that reject when full — beats unbounded queues that hide the problem then OOM), or shed by priority (drop analytics beacons, keep checkouts; drop unauthenticated traffic first). *Choosing* what to fail beats failing everything. Design the degraded mode; it will run whether designed or not.
- **Graceful degradation as product decision.** Features have importance tiers, agreed with product *before* the incident: search suggestions die before search; recommendations before the cart. Netflix's fallback-everything culture (and chaos engineering — deliberately injecting failure in production to verify all of the above actually engages) is the mature end state.

## Observability: the three signals

**Metrics** — cheap aggregated time series. The two framings worth standardizing: **RED** per service (Rate, Errors, Duration) and **USE** per resource (Utilization, Saturation, Errors). Duration means **percentiles, never averages**: latency is skewed, and the mean of 99 fast + 1 ten-second request reads "fine." p50 is the typical user; p99 is your heaviest users — often the biggest customers — and, per Chapter 1's fan-out amplification, a request touching 10 services experiences roughly one service's p99 *per request*. Tails are the product.

**Logs** — structured (JSON, not prose), centralized, and always carrying the **correlation/trace ID** minted at the gateway (Chapter 11), so one request's story is grep-able across twenty services.

**Traces** — the distributed call tree with timings per hop (OpenTelemetry is the 2026 lingua franca): the only signal that answers *where* a slow request spent its time. Sampled (head or tail-based — tail sampling keeps the interesting rare-slow traces) because tracing everything is a data firehose.

**SLOs and error budgets** — the management layer that makes reliability a number instead of a mood. Define SLIs (measurable: "fraction of requests under 300ms, successful"), set SLOs ("99.9% monthly" — note: 99.9% ≈ 43 minutes/month of allowed badness; each extra nine costs ~10× the engineering), and spend the **error budget** deliberately: budget healthy → ship fast; budget burnt → freeze features, fix reliability. Alert on **burn rate** (how fast the budget is depleting), not on individual machine sneezes — pages should mean "users are hurting," or nobody believes pages.

## The operational stance

Compressed to habits: every call has a deadline and a budgeted, jittered retry; every dependency has a breaker and a fallback; every queue is bounded and its depth graphed; every fleet has 30% headroom; every request has a trace ID; every service has RED dashboards and an SLO someone owns; and the degraded mode is designed, tested (chaos!), and product-approved. None of it is glamorous; all of it is the difference between "we had a slow replica for 20 minutes" and a headline.

The toolkit is complete — data, movement, and now survival. One chapter left: spend it all at once, on real designs with real numbers.
