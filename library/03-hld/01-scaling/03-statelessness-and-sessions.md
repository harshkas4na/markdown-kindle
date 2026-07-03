# The Prerequisite Nobody Mentions: Statelessness

Here's the failure that hits almost everyone the first time they horizontally scale something for real: you go from 1 server to 3, traffic gets split between them, and users start getting **randomly logged out**, or their **cart empties**, or an **uploaded file 404s** half the time. The servers are all healthy. Nothing crashed. So what broke?

## The actual problem

Shadow logs in. That request lands on **server A**. Server A, the naive way most tutorials teach it, stores "Shadow is logged in" in its own memory (an in-process session object). Shadow's next click gets routed — by whatever is splitting traffic — to **server B**. Server B has never heard of Shadow. As far as it's concerned, Shadow was never logged in. Logged out, cart gone, whatever that server's memory was holding is simply not there.

This is **state** — information about a specific user/request that gets remembered *by one specific server* between requests. A server that does this is **stateful**. A server that remembers nothing between requests — where every request carries everything needed to handle it, and any server could have answered it identically — is **stateless**.

**Horizontal scaling only actually works if your servers are stateless**, because the entire premise of "add more identical servers" is that they *are* identical — interchangeable, no server more "correct" to talk to than another. The moment one server knows something another doesn't, they stop being interchangeable, and splitting traffic between them starts silently corrupting the user's experience instead of just adding capacity.

## Where state hides (the usual suspects)

- **In-memory sessions** — the classic one above. Login state, shopping cart, "wizard step 3 of 5" progress, held in server RAM.
- **Local file uploads** — user uploads a profile picture, your code saves it to `/uploads/` *on that server's local disk*. Works great with one server. With three servers behind a load balancer, the picture exists on exactly one of them — a 404 two out of three times.
- **In-process caches** — a server caches a computed value in a local variable/dict. Fine for correctness (each server just recomputes it), but it means your "cache" is actually N separate caches with N separate cold-start costs and no shared benefit.
- **Local rate limiting / counters** — "block this IP after 5 failed logins" tracked in a local variable means an attacker just needs to get routed to a *different* server to get 5 more free tries.

## Fixing it — push state out of the server

The fix is always the same shape: move anything that needs to persist between requests **out of the server's own memory/disk and into something shared** that every server can reach identically.

- **Sessions →** an external, shared store like **Redis** or **Memcached**. Every server, on every request, asks the same shared Redis instance "who is this," instead of asking its own memory. Now any server gives the same answer.
- **Sessions, alternative approach →** don't store session state server-side at all. Issue the client a **JWT** (a signed token containing the user's identity/claims) and have every server verify the signature and read the claims directly from the token itself. The "state" now travels with the request instead of living on a server — this is why JWTs are popular specifically *because* they make horizontal scaling trivial, not because they're inherently more secure than session cookies.
- **File uploads →** don't write to local disk at all. Write to shared object storage (**AWS S3** or equivalent) that every server can read from and write to identically.
- **Rate limiting / counters →** same idea, a shared Redis counter instead of a local one.

Once all of this is true, your servers are genuinely interchangeable, and horizontal scaling (and the load balancer sitting in front of it, `04-load-balancers.md`) actually works the way people assume it does by default.

## Sticky sessions — the band-aid, not the fix

There's a shortcut that avoids fixing statelessness immediately: configure the load balancer to always send a given client to the *same* server every time (via a cookie, or by hashing their IP — see `04-load-balancers.md`). This is called **session affinity** or **sticky sessions**. It "solves" the symptom — Shadow keeps talking to server A, so server A's in-memory session keeps working.

**Why it's a band-aid and not a real fix:**
- If server A dies or is removed during a scale-down, every session pinned to it is lost — you've just moved the single-point-of-failure problem from "one server for everyone" to "one server for each specific user," which is only marginally better.
- It defeats even load distribution — if a disproportionate number of "sticky" users land on one server (or one user is unusually heavy), that server can't be relieved by shifting them elsewhere.
- It's a real, legitimate tool for a specific narrow case: fronting a legacy stateful service you can't easily rewrite yet, as a stopgap while you migrate. It should never be the permanent design for a new system.

## Commonly skipped

- This entire topic is usually skipped or glossed over in "just add a load balancer" explanations, and it's the single most common reason a first attempt at horizontal scaling causes *more* visible bugs (random logouts, lost data) than it fixes.
- People treat sticky sessions as *the* solution rather than a temporary workaround — it should be viewed the same way you'd view a `TODO: fix properly` comment.
- Local file uploads are an especially sneaky one — they work perfectly in dev (one server, always) and only break in a multi-server production environment, which means they're rarely caught before launch.

## In practice (what you'd actually change)

Concretely, this usually looks like: swapping `session middleware` config from an in-memory store to a Redis-backed store (e.g. Express's `connect-redis`, or the equivalent in your framework), changing file-upload code to write to an S3 client instead of the local filesystem, and — if you need a stopgap on day one — enabling the load balancer's built-in **stickiness** attribute (AWS ALB target groups have a `stickiness.enabled` attribute with a configurable duration) while the real fix ships.

## Go deeper

- [Sticky sessions vs stateless design — Kunal Ganglani](https://www.kunalganglani.com/learning-paths/backend-developer/be-lb-sticky-sessions/)
- [Stateful vs. Stateless Web App Design — DreamFactory](https://blog.dreamfactory.com/stateful-vs-stateless-web-app-design)
