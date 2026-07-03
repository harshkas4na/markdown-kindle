# Sources

Reference material used while researching this arc, grouped by file. These are starting points for going deeper, not exhaustive citations — the notes themselves are written in plain language on purpose, this is where the denser/original material lives.

## 01 — Capacity estimation
- [Back-of-the-envelope Estimation — ByteByteGo](https://bytebytego.com/courses/system-design-interview/back-of-the-envelope-estimation)
- [Understanding Little's Law — Shekhar Gulati](https://shekhargulati.com/2021/11/20/understanding-littles-law/)
- [Little's Law and Service Latency](https://uvdn7.github.io/littles-law-and-service-latency/)
- [Latency Numbers Every Programmer Should Know (interactive)](https://colin-scott.github.io/personal_website/research/interactive_latency.html)
- [Latency numbers gist (jboner)](https://gist.github.com/jboner/2841832)

## 02 — Vertical vs horizontal scaling
- [Scaling Up vs Scaling Out — DIRA](https://medium.com/@drajput_14416/scaling-up-vs-scaling-out-392c03df6119)
- [Stateful and Stateless Horizontal Scaling for Cloud Environments — RoseHosting](https://www.rosehosting.com/blog/stateful-and-stateless-horizontal-scaling-for-cloud-environments/)
- [Scalability in System Design: Vertical vs Horizontal — DEV Community](https://dev.to/imsushant12/scalability-in-system-design-vertical-vs-horizontal-scaling-4nmp)

## 03 — Statelessness and sessions
- [Sticky sessions vs stateless design — Kunal Ganglani](https://www.kunalganglani.com/learning-paths/backend-developer/be-lb-sticky-sessions/)
- [Stateful vs. Stateless Web App Design — DreamFactory](https://blog.dreamfactory.com/stateful-vs-stateless-web-app-design)
- [Scaling Stateless vs Stateful Services — DreamFactory](https://blog.dreamfactory.com/scaling-stateless-vs-stateful-services)

## 04 — Load balancers
- [L4 vs L7 Load Balancing deep dive — Codeshbhai](https://medium.com/@codeshbhai/stop-crashing-on-black-friday-a-deep-dive-into-l4-vs-l7-load-balancing-768c536a6956)
- [AWS Load Balancers Deep Dive: ALB vs NLB](https://joudwawad.medium.com/aws-load-balancers-deep-dive-application-vs-network-explained-6efdafd1192e)
- [Load Balancing Algorithms Explained](https://www.mayhemcode.com/2025/11/load-balancing-algorithms-explained.html)
- [Deregistration Delay on AWS ALBs](https://blogs.reliablepenguin.com/2025/12/20/deregistration-delay-on-aws-application-load-balancers-alb)
- [AWS ELB: Understanding Connection Draining](https://issackpaul95.medium.com/aws-theory-elb-graceful-goodbyes-understanding-connection-draining-deregistration-delay-67c921a781e5)

## 05 — Autoscaling
- [Target tracking scaling policies for EC2 Auto Scaling — AWS docs](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)
- [Scaling cooldowns for EC2 Auto Scaling — AWS docs](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-scaling-cooldowns.html)
- [HorizontalPodAutoscaler Walkthrough — Kubernetes docs](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/)
- [Horizontal Pod Autoscaling — Kubernetes docs](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
- [Cluster Autoscaler vs HPA vs VPA — Tasrie IT](https://tasrieit.com/blog/cluster-autoscaler-vs-hpa-vs-vpa-2026)
- [HPA vs VPA — ScaleOps](https://scaleops.com/blog/hpa-vs-vpa/)

## 06 — Monolith to microservices
- [Strangler fig pattern — AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/strangler-fig.html)
- [Pattern: Strangler application — microservices.io](https://microservices.io/patterns/refactoring/strangler-application.html)
- [Strangler Fig Pattern for Refactoring Monolith into Microservices — Mehmet Ozkaya](https://mehmetozkaya.medium.com/strangler-fig-pattern-for-refactoring-monolith-into-microservices-%EF%B8%8F-88e667c096c8)
