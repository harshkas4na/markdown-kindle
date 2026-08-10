# Learning Next.js (and the whole stack) through Metro Diaries

This is a course I'm writing for myself, using my own codebase as the textbook. The idea is simple: instead of reading generic tutorials where everything is a `TodoApp`, I'm going to learn every Next.js concept by pointing at real code that I already shipped and asking *"wait, why did I do it this way, and what was actually happening under the hood?"*

By the end I want two things at the same time:

1. I should be able to walk into an interview and explain SSR vs CSR vs streaming, RSC, caching, auth, real-time — confidently, with examples.
2. I should understand my own app so deeply that I can rebuild any part of it from memory.

So we go slow at the start (mental models), then keep raising the level until we're reading the Dijkstra route-finder and the WebSocket chat engine like they're nothing.

---

## How to read this

Read top to bottom. Every article assumes you read the one before it. Each one has:

- **The mental model** — the one-paragraph "what is this really" that I want burned into my head.
- **In our codebase** — the exact files where we do this, and *why* we did it that way.
- **The interview angle** — how this exact topic shows up in interviews.
- **Concept checklist** — boxes to tick once I can explain it without looking.

---

## The curriculum (and master checklist)

### Level 1 — The foundation (how to even think about Next.js)

- [ ] **[01 — The mental model](./01-the-mental-model.md)** — server vs client, RSC vs Client Components, the "rendering spectrum". The single most important article.
- [ ] **[02 — Routing & file conventions](./02-routing-and-file-conventions.md)** — App Router, route groups `(app)`, layouts, `loading.tsx`, dynamic routes `[id]`, how *our* folder tree maps to URLs.
- [ ] **[03 — Rendering & the SSR balance](./03-rendering-and-the-ssr-balance.md)** — SSR / SSG / ISR / CSR / streaming, *when to pick which*, and the exact place our app gets this wrong (the client-side waterfall).

### Level 2 — Moving data around

- [ ] **[04 — Data fetching & caching](./04-data-fetching-and-caching.md)** — server fetching vs client SWR, our `useTrips`/`useConnections` hooks, dedup, revalidation, the Redis cache-aside layer.
- [ ] **[05 — Route Handlers (our API layer)](./05-route-handlers-the-api-layer.md)** — the `app/api/*` request lifecycle, our `auth → rate-limit → sanitize → query` pattern, `NextResponse`, status codes.

### Level 3 — Supabase and how it bolts onto Next.js

- [ ] **[06 — Supabase fundamentals](./06-supabase-fundamentals.md)** — Postgres + RLS + Auth + Realtime + Storage, and the *two clients* (`server.ts` vs `client.ts`) and why cookies are the whole trick.
- [ ] **[07 — Auth deep dive](./07-auth-deep-dive.md)** — the Google OAuth flow, `AuthProvider`, `onAuthStateChange`, the route guard, `getUser()` vs `getSession()`, and writing the `middleware.ts` we're missing.

### Level 4 — The hard, fun parts

- [ ] **[08 — Real-time & chat architecture](./08-realtime-and-chat.md)** — the singleton WebSocket, Supabase Realtime channels, optimistic UI, the retry/queue logic in `use-ws-chat`.
- [ ] **[09 — Algorithm: the metro route-finder](./09-algorithm-route-finder.md)** — modeling the network as a graph, Dijkstra with a hand-rolled min-heap, and the three weight modes (fastest / cheapest / fewest interchanges).
- [ ] **[10 — Algorithm: trip matching & search](./10-algorithm-trip-matching.md)** — the station index, distance + direction scoring, fallback suggestions, and why search is cached.

### Level 5 — Making it production-grade

- [ ] **[11 — Performance & the production checklist](./11-performance-and-production.md)** — the rendering waterfall, middleware auth, caching layers, fonts, and the ranked break-points in our app.
- [ ] **[12 — Security & PWA](./12-security-and-pwa.md)** — CSP, rate-limiting design, service worker, push notifications, the "is this production-grade?" scorecard.

---

## The "can I explain this in an interview?" master list

Tick these only when I can say them *out loud* to another person:

**Rendering & React**
- [ ] What is a React Server Component and how is it different from a Client Component?
- [ ] What does `"use client"` actually do? Where's the boundary?
- [ ] SSR vs SSG vs ISR vs CSR vs streaming — define each and give a use case.
- [ ] What's hydration? What's a hydration mismatch?
- [ ] What is a "waterfall" and how do you kill one?

**Next.js specifics**
- [ ] App Router vs Pages Router (and why App Router exists)
- [ ] Route groups, layouts, templates, `loading.tsx`, `error.tsx`
- [ ] Route Handlers vs Server Actions
- [ ] `middleware.ts` — what runs there and why it's special (the edge)
- [ ] How does caching work in App Router (request memoization, data cache, full route cache, router cache)?

**Data & state**
- [ ] When do I fetch on the server vs the client?
- [ ] What does SWR give me (stale-while-revalidate, dedup, focus revalidation)?
- [ ] Optimistic updates — what and why

**Supabase / backend**
- [ ] What is Row Level Security and why does it let me talk to the DB from the browser?
- [ ] Why are there two Supabase clients and what's different about them?
- [ ] `getUser()` vs `getSession()` — which hits the network?
- [ ] How does auth state survive a page refresh?

**Systems**
- [ ] How does a WebSocket connection survive across pages in a SPA?
- [ ] Dijkstra: how does it work, and why a priority queue?
- [ ] How do you rate-limit an API?

---

*Status: all 12 articles written. Now the work is to actually tick the boxes — and turn the article-11 fix order into commits.*
