# You, at 2am: The Whole Arc as One Sequence

Everything in this folder so far has been one concept at a time. This file is the opposite — it's all of it stitched into a single, continuous sequence of actions, told as if you're the engineer it's actually happening to. The point is to feel how these pieces connect in real time, not in a diagram.

## The trigger

Shadow's site got mentioned somewhere it shouldn't have — a popular account shared it. Traffic is climbing fast. Your phone buzzes: a CloudWatch/Grafana alert fired because **p99 latency** crossed the threshold and the **error rate** is climbing. You're on-call. This is now yours.

## Step 1 — Don't guess, look

First thing, open the dashboard. Not to "fix" anything yet — to find out what's actually true. Is CPU pegged on the app servers? Is it memory? Is the database connection pool maxed out? Is this happening across *every* endpoint, or is it concentrated on one (login? the homepage? one viral post's page?). This 90 seconds of looking determines everything that follows — treating a DB bottleneck like a compute problem (or vice versa) wastes the most valuable minutes of the incident.

Say the dashboard shows: CPU on the app servers is pegged at 95%+, the DB looks fine, and it's happening across most endpoints, not just one. That tells you this is a genuine compute capacity problem, not a code bug or a downstream dependency issue — the fix lives in `01`–`05` of this folder, not in application code.

## Step 2 — Buy time the fast way

You don't have time to redesign anything right now. The fastest lever that requires zero architecture change is **vertical scaling** (`02`): if there's runway, bump the running instances to a bigger type. On AWS this is a stop → resize → start cycle per instance — a couple minutes of reduced capacity per instance you do this to, so you'd do it to one or two at a time if you have several behind a load balancer, never all at once.

This buys time. It does not solve the actual problem, because you still have a hardware ceiling ahead of you and no redundancy story.

## Step 3 — Actually add capacity, safely

While that buys breathing room, you check the thing that decides whether horizontal scaling will help or hurt: **is this service actually stateless?** (`03`) If sessions live in each server's memory or uploads land on local disk, adding more servers right now will start silently logging users out or 404ing images — trading one visible problem (slow) for a worse one (broken). If that's not already fixed, this is the moment you either fix it fast (point the session store at Redis if it isn't already) or, as a stopgap, turn on the load balancer's sticky-sessions attribute knowing it's temporary.

With that confirmed safe, you bump capacity for real — either raise the max on an existing **Auto Scaling Group** / **Kubernetes HPA**, or if none exists yet, stand one up: a target group with a real `/healthz` HTTP health check (`04`), an ALB in front of it, an ASG behind it set to a target-tracking policy on CPU (`05`). On Kubernetes this is `kubectl scale deployment shadow-api --replicas=<n>` right now, with `kubectl autoscale ... --cpu-percent=60 --min=<n> --max=<n>` going in immediately after so a human doesn't have to do this again for the next spike.

## Step 4 — Watch it happen without hurting anyone

As new instances/pods come online, they go through a **warm-up period** before they're trusted with real metric weight (`05`) — don't panic if the metric doesn't instantly drop. As old, overloaded instances eventually get cycled out (if you're also replacing unhealthy ones), the load balancer's **connection draining** window (`04`) makes sure in-flight requests on those instances finish instead of getting cut off mid-response. You watch p99 latency and error rate on the dashboard start coming back down — that's the confirmation the fix is actually working, not just "it looks calmer."

## Step 5 — After the fire's out

Once things are stable, you don't just close the incident. You run an actual **load test** (`01`) — k6 or Locust, ramping simulated traffic — to find out what the *new* real ceiling is, so next time you have a number instead of a guess. You update the target-tracking/HPA thresholds if this incident revealed they were too conservative (scaling out too late). You check whether the peak-to-average ratio you assumed (`01`) was actually right, or whether this event just taught you it's higher than you thought.

## Step 6 — The pattern that changes everything

Here's the part that matters for where the *story* goes next, not just this one incident: if this keeps happening — and it keeps being the **same one feature** every time (say, the video-upload endpoint, or the checkout flow) that drags the whole fleet down while the rest of the app is fine — that's not a capacity problem anymore. That's the concrete, numeric version of the signal in `06`: one part of your app has a genuinely different load profile than the rest, and scaling the whole monolith to protect that one hot path is throwing money at the wrong problem. That's the moment the story stops being "add more of the same server" and starts being "maybe this one thing needs to be its own service" — which is exactly where the next video picks up.
