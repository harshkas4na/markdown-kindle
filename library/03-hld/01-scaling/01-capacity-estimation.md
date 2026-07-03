# Why Scale? — Capacity Estimation

Before you scale anything you need to answer a boring but load-bearing question: **how do you actually know one server isn't enough?** Not "the site feels slow" — an actual number, because every decision after this (vertical or horizontal, how many servers, when to autoscale) is downstream of this number being right.

## The three numbers that describe any server

Every request-handling system, no matter how complicated, can be described with just three things:

- **Arrival rate** — how many requests show up per second (this is your **QPS**, queries per second, or **RPS**, requests per second — same thing, different name).
- **Latency** — how long each request takes to be handled, start to finish.
- **Concurrency** — how many requests are "in flight," being worked on, at any given instant.

These three aren't independent. That relationship is called **Little's Law**, and it's the whole trick behind back-of-envelope capacity math:

```
concurrency (L) = arrival rate (λ) × average latency (W)
```

Say it in words: if 100 requests arrive per second, and each one takes 200ms (0.2s) to finish, then on average you always have `100 × 0.2 = 20` requests being worked on simultaneously, at any instant.

That "20" is the number that actually matters for capacity — it tells you how many concurrent workers/threads/connections you need. Not the QPS. QPS alone tells you nothing about how *busy* your server is; latency is the multiplier that turns arrival rate into real load.

**This is the single most under-appreciated fact in capacity planning:** a slow downstream call (a DB query that used to take 20ms now taking 200ms) doesn't change your QPS at all — the same number of users are hitting you — but it multiplies your required concurrency by 10x. If your server only has 30 worker threads, you just went from "fine" to "queueing and timing out" without a single extra user showing up. This is why "traffic didn't grow but the site is on fire" incidents are almost always a latency regression somewhere downstream, not an actual load spike.

The inverse is also a useful quick formula: for a single-threaded/single-connection worker, `max QPS ≈ 1000 / latency_in_ms`. A worker that takes 100ms per request can do ~10 req/sec, full stop, no matter what else you do — the only way past that ceiling is more workers (concurrency) or lower latency.

## Latency isn't one number — averages lie

Never estimate or monitor using the average/mean latency alone. Use **percentiles**:

- **p50** (median) — half your requests are faster than this. This is basically "the typical good day."
- **p95** — 95% of requests are faster than this; the remaining 5% are your emerging problem.
- **p99** — the slowest 1%. This is what determines whether your *heaviest* users (the ones with the most items in cart, the most followers, the biggest queries) think your product is broken.

Averages hide tail latency completely. A server can have a beautiful 50ms average while 1% of users sit on a 8-second spinner — and that 1% might be your highest-value users, because expensive requests correlate with active/power users. Real dashboards (CloudWatch, Grafana, Datadog) always plot p50/p95/p99 side by side for exactly this reason — if you only ever look at the average, you're structurally blind to the exact users most likely to churn or complain.

## Rough numbers worth memorizing (so estimation isn't a guess)

You don't need exact figures, you need the right **order of magnitude**, because that's genuinely all back-of-envelope math is for — telling "needs one server" apart from "needs one hundred servers."

| Operation | Rough latency |
|---|---|
| L1/L2 CPU cache read | ~1–10 ns |
| Main memory (RAM) read | ~100 ns |
| SSD random read | ~100 µs – 1 ms |
| Round trip within the same datacenter | ~0.5 ms |
| Round trip across regions/continents | ~100–150 ms |
| Disk seek (spinning disk, mostly historical now) | ~10 ms |

The takeaway isn't the exact numbers, it's the *ratios*: RAM is ~100,000x faster than a cross-region network call. This single fact is why caching and keeping things "close" (same region, same rack, in-memory) is worth more than almost any other optimization — and it's why, later, adding a cache in front of a DB has such an absurd payoff.

## Peak traffic is not average traffic

If Shadow's site gets 864,000 requests in a day, that sounds like "10 requests/sec" if you just divide by 86,400 seconds. Nobody's traffic is flat like that. Real traffic has a peak-to-average ratio — usually **2x to 10x** depending on the product (a food-delivery app spikes hard at lunch/dinner; a B2B tool is flat 9-to-5; a "went viral on social media" moment can spike 50-100x for a few minutes).

**The mistake almost everyone makes here:** sizing capacity for the average and getting blindsided by the peak. Always estimate for peak, and separately ask "what's our peak-to-average ratio going to look like," because that ratio *is* the actual scaling problem — average traffic almost never breaks anything.

## Read:write ratio

One more number worth having before you estimate anything: what fraction of requests read data vs write data? Most consumer apps are extremely read-heavy (100:1 or higher — think of how many people view a tweet vs post one). This matters enormously later (read replicas, caching are entirely about exploiting a read-heavy ratio) but it also matters *now*: a write-heavy workload hits your database's concurrency ceiling much faster than a read-heavy one, because writes typically can't be cached or parallelized as freely.

## A worked example (Shadow's site)

Say Shadow's site has 50,000 daily active users, each making roughly 20 requests during their visit. That's 1,000,000 requests/day.

- Average QPS: 1,000,000 / 86,400 ≈ **11.5 req/sec**. Looks trivial.
- But usage isn't flat — most of it lands in a 4-hour evening window. Concentrate 60% of the day's traffic into 4 hours (14,400s): 600,000 / 14,400 ≈ **41.6 req/sec** average *within* that window.
- Within that window there are still spikes — assume a 3x peak-to-average burst: **~125 req/sec** at the actual peak second.
- Each request averages 150ms server-side latency. By Little's Law: concurrency needed = 125 × 0.15 ≈ **19 concurrent requests** in flight at peak.

If a single server, given its CPU/memory, can comfortably handle ~15–20 concurrent requests before latency starts degrading — Shadow is *right at the edge* on a normal day, and one good spike (a post going semi-viral, a marketing email blast) pushes well past it. That's the actual, numeric version of "the site is getting popular and one server isn't enough anymore" — not a vibe, a number you calculated.

## Commonly skipped

- Estimating from average traffic instead of peak traffic — the single most common back-of-envelope mistake.
- Ignoring that latency, not request count, is what determines concurrency (Little's Law) — people ask "how many requests?" when the real question is "how many *at once*?"
- Treating p50/average latency as if it represents the user experience, when p99 is what your most active/valuable users actually feel.
- Forgetting the read:write ratio exists as a number worth knowing before deciding *how* to scale (this becomes critical again in the DB-scaling arc).

## In practice (what you'd actually look at)

A real engineer doesn't do this math from memory during an incident — they look at a dashboard that already plots QPS, p50/p95/p99 latency, error rate, and CPU/memory per service (Grafana/CloudWatch/Datadog are the common tools). Before *launching* something, though, this exact napkin math is what decides the starting instance size/count. And to find the *actual* breaking point instead of guessing, teams run synthetic load tests with tools like **k6**, **Locust**, or **JMeter** — ramping simulated concurrent users up until p99 latency or error rate blows past an acceptable threshold, and calling that the real ceiling for that server size.

## Go deeper

- [Back-of-the-envelope Estimation — ByteByteGo](https://bytebytego.com/courses/system-design-interview/back-of-the-envelope-estimation)
- [Understanding Little's Law](https://shekhargulati.com/2021/11/20/understanding-littles-law/)
- [Latency Numbers Every Programmer Should Know (interactive)](https://colin-scott.github.io/personal_website/research/interactive_latency.html)
