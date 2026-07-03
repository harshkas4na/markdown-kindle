# Autoscaling — Letting a Machine Press the Button

So far, every step has assumed a human decides "add more servers now." That doesn't scale (ironically) — traffic changes minute to minute, and no team wants to be manually watching a dashboard 24/7 to add/remove capacity. The fix is to let a controller watch a metric and adjust capacity itself. This is **autoscaling**, and it's worth understanding at the level of "what is it actually doing," not just "it magically adds servers."

## AWS: Auto Scaling Groups + target tracking

You pick a **target metric and value** — the common one is "keep average CPU utilization across the fleet at 60%." AWS then automatically creates the CloudWatch alarms behind the scenes and continuously adjusts how many instances are running to converge on that target — the official comparison is a **thermostat**: it doesn't just react once, it keeps nudging capacity to hold the target value over time.

A few mechanics worth actually knowing, because they explain real behavior you'd otherwise find confusing in production:

- **Scale-out is eager, scale-in is conservative.** If load spikes hard, a fresh scale-out alarm can fire and add capacity *immediately*, even overriding an in-progress scale-in cooldown. But scaling *in* (removing instances) deliberately waits out its cooldown period — the reasoning is asymmetric on purpose: being briefly over-provisioned costs money, being under-provisioned during a real spike costs availability, and availability is worth more.
- **New instances have a warm-up period** before they're counted toward the metric at all — this prevents a newly-launched, still-booting instance (with artificially low CPU because it isn't serving traffic yet) from confusing the controller into thinking the fleet needs even more capacity.
- If you have **multiple target-tracking policies** on the same group, AWS scales out if *any* of them says to, but only scales in if *all* of them agree it's safe — again, biased toward keeping capacity rather than removing it too eagerly.

## Kubernetes: the Horizontal Pod Autoscaler (HPA)

Same idea, different mechanics. The **metrics-server** collects CPU/memory usage from every node roughly every 15 seconds and exposes it through the Kubernetes API. The HPA controller then applies a genuinely simple formula:

```
desiredReplicas = ceil( currentReplicas × (currentMetricValue / desiredMetricValue) )
```

Concretely: if you target 60% CPU and current usage is sitting at 90%, that's 1.5x over target, so the HPA multiplies your replica count by 1.5 (rounded up). Simple, and worth internalizing because it means autoscaling isn't some black box — it's proportional control based on one ratio.

One asymmetry mirrors AWS's: **scaling up has no stabilization window** (it reacts as soon as the metric crosses the line), but **scaling down waits a 300-second stabilization window** by default — again, biased against flapping capacity down too fast and then having to scale right back up.

## The three layers people conflate

This trips up almost everyone the first time they meet Kubernetes autoscaling, because all three sound like "autoscaling" but solve completely different problems:

- **HPA (Horizontal Pod Autoscaler)** — adds/removes **pod replicas**. Best fit for stateless workloads with fluctuating demand (web APIs, frontends). This is "more copies," exactly like an ASG.
- **VPA (Vertical Pod Autoscaler)** — adjusts the **CPU/memory request of each individual pod** based on its actual historical usage, i.e. automated vertical scaling for a pod that's over- or under-provisioned. Good for right-sizing, bad for anything that needs to react in seconds (resizing a pod usually means evicting and recreating it).
- **Cluster Autoscaler (CA)** — adds/removes actual **nodes (machines)** in the cluster, but only in response to pods being unable to schedule anywhere (`Pending`). HPA can decide it wants 20 pods, but if the cluster physically doesn't have room, those pods sit `Pending` until CA notices and adds a node. **HPA without CA underneath it just runs out of room.**

**A genuinely interesting gotcha:** if you run HPA and VPA on the *same raw metric* (CPU) for the same workload, they can fight each other in a feedback loop informally called the **Kubernetes death spiral** — VPA raises a pod's CPU *request* (to fix an actual under-provisioning problem) → that lowers the pod's utilization *percentage* → HPA sees lower utilization and scales the replica count *down* → fewer pods means each one's utilization rises again → VPA raises the request again → repeat. Neither controller is "wrong," they just don't coordinate. The real-world fix is to not drive both off the same metric — e.g. HPA on a custom/external metric (requests per second) while VPA handles CPU/memory right-sizing underneath it.

## The blind spot both share: lag

Autoscaling is *reactive* — it responds to a metric that's already a few seconds to a couple minutes stale, and the new capacity it adds isn't instantly useful (a new EC2 instance needs to boot and go through its warm-up period; a new pod needs to be scheduled, pull its image, and pass readiness checks). For a gradual traffic ramp, this lag is invisible. For a **sudden spike** — a marketing blast, a post going viral in minutes — pure reactive autoscaling structurally cannot keep up; by the time it reacts and new capacity is ready, the spike may already be over, or your existing capacity may already be timing out.

This is exactly why real teams use **scheduled/predictive scaling** for *known* events (a sale, a product launch, a live stream) — pre-scale capacity ahead of time on a schedule, rather than trusting reactive autoscaling to save you during the first few critical minutes.

## Commonly skipped

- People say "Kubernetes autoscales" as if it's one thing, when HPA/VPA/Cluster Autoscaler solve three different problems and can actively conflict if misconfigured.
- The asymmetry (fast scale-out, slow/cautious scale-in) surprises people who expect scaling to be symmetric — it's a deliberate availability-over-cost tradeoff, not a bug.
- Autoscaling lag is rarely mentioned, and it's the reason "we have autoscaling, we're fine" is a false sense of security against sudden, sharp spikes specifically.

## In practice (what you'd actually type)

Kubernetes: `kubectl autoscale deployment shadow-api --cpu-percent=60 --min=3 --max=20`, then `kubectl get hpa` to watch it react in real time. AWS: `aws autoscaling put-scaling-policy` with a `TargetTrackingConfiguration`, or the equivalent console flow (Auto Scaling Group → create a target-tracking policy → pick "Average CPU Utilization" or a custom CloudWatch metric → set the target value). During a real launch, a team will typically run a load test (see `01-capacity-estimation.md`) while watching the scaling policy actually trigger on the dashboard, specifically to confirm the lag between "metric crosses threshold" and "new capacity is actually serving traffic" is acceptable for their traffic pattern.

## Go deeper

- [Target tracking scaling policies — AWS docs](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)
- [HorizontalPodAutoscaler Walkthrough — Kubernetes docs](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/)
- [Cluster Autoscaler vs HPA vs VPA](https://tasrieit.com/blog/cluster-autoscaler-vs-hpa-vs-vpa-2026)
