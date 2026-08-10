# 11 — Performance & the production checklist

Every previous article hinted at a performance lesson. This one pulls them into a single, ranked, actionable picture — the kind of thing I'd want in my head before saying any app is "production-grade."

The mental model:

**Performance is almost never about slow code. It's about *doing work in the wrong place* or *at the wrong time* — fetching on the client when you could on the server, doing things in series that could be parallel, or not caching things that never change. Find the waterfalls and the wrong-world work; the rest is noise.**

---

## The one diagram that explains our slowness

Cold-loading `/dashboard` today (from article 03, repeated because it's *the* lesson):

```
HTML shell (empty) → download JS bundle → AuthProvider mounts → read cookie
   → fetch /api/profile  ⏳ ROUND TRIP #1  (whole app shows a spinner here)
   → guard passes → page mounts → SWR hooks fire
   → /api/trips, /api/connections, /api/discover  ⏳ ROUND TRIP #2
   → finally paint
```

Two serial network round-trips behind a full-screen spinner, all because the authenticated app is a Client Component (`"use client"` in `app/(app)/layout.tsx`) with no `middleware.ts`. **This is wrong-world work** (auth + first data should be server-side) **plus a waterfall** (profile *then* data). Everything below is either this problem or a smaller cousin of it.

---

## The ranked break-points (with the fix and which article explains it)

### 🔴 1. Client-side auth waterfall — *the big one*
The whole `(app)` zone is CSR. **Fix:** `middleware.ts` for edge auth (article 07) + server-render the shell (article 03). Turns a CSR blob into a streaming-SSR shell. Biggest perceived-speed win, zero infra cost.

### 🔴 2. Profile fetch gates the entire UI
`if (loading || profileLoading) return <MetroPageLoader/>` — nothing renders until `/api/profile` resolves, every load, though profile rarely changes. **Fix:** render profile on the server, or hydrate from `localStorage` instantly and revalidate in the background (article 03). Kills the spinner on repeat visits.

### 🔴 3. WS chat server cold-starts (2–3 min) on Render free tier
The worst UX break, and it's *infra*, not code (article 08). **Fix:** keep the server warm (paid tier / health-check pinger) or rewrite as an always-on Go service. No amount of retry code fixes a sleeping server.

### 🟠 4. Every API route does a network round-trip just to authenticate
Each route calls `supabase.auth.getUser()` (verifies the JWT over the network). A dashboard load = ~5 routes = ~5 auth round-trips. **Fix:** use `getSession()` (local cookie decode) for read-only routes; reserve `getUser()` for mutations (article 05).

### 🟠 5. Refetch storm on tab focus
`revalidateOnFocus: true` globally + Supabase's token refresh on focus → switching back to the tab refetches everything (article 04). **Fix:** turn off `revalidateOnFocus` globally, opt in per-hook, or set a `focusThrottleInterval`.

### 🟠 6. Constant background chatter regardless of page
Presence heartbeat (every 60s), WS connection, Supabase realtime channel, and `useChatNotifications` (which fires an *extra* `/api/chat-messages` fetch per new notification to build the preview) all run app-wide. **Fix:** include the preview text in the notification payload so no extra fetch is needed; consider pausing the heartbeat when the tab is hidden (`visibilitychange`).

### 🟡 7. `loading.tsx` gives only half its benefit
The skeletons show, but because pages fetch client-side via SWR, you don't get true streaming (article 03/04). **Fix:** falls out of #1 — once data is fetched server-side, the skeletons become real streaming boundaries.

### 🟡 8. Hot-path `console.log` + no edge caching on API
`/api/profile` logs on every call; all `/api/*` are `no-store` (article 04/05). **Fix:** strip hot-path logs; add cache headers to the read-only routes that can tolerate it (we already do this well on `/api/discover`).

### 🟢 9. Fonts
Three Google families (Oswald ×4 weights, Caveat ×4, DM Sans). `next/font` self-hosts and handles `font-display` so it's not render-blocking, but trimming unused weights shaves bytes.

---

## The mental toolkit (so I can find these myself next time)

Concepts to internalize, each illustrated by a break-point above:

- **Waterfall vs parallel.** Serial dependent fetches are the #1 enemy. Ask: "does B *really* need A's result, or did I just write them in order?" (#1, #2)
- **Wrong-world work.** Auth, first-paint data, and shared content belong on the server/edge; only interactivity belongs on the client (#1, #4). This is article 01's mental model cashing out as performance.
- **Cache what doesn't change per request.** Profile (#2), the metro graph (memoized — article 09), search results (Redis — article 04). Match the cache lifetime to how often the data actually changes.
- **Push, don't poll.** Realtime events → SWR revalidate beats interval polling (article 04/08) — but watch that the "push" doesn't trigger *extra* fetches (#6).
- **Measure the round-trips.** Open the Network tab, count the requests before first meaningful paint, and ask which are serial. The number itself is the diagnosis.
- **Infra is part of performance.** The cold-start (#3) can't be fixed in React. Knowing when a problem is infra vs code is senior judgment.

---

## A balanced fix order (what I'd actually do)

Not everything at once — sequence by leverage-per-risk:

1. **`middleware.ts` + slim the guard** (#1, #2 partial) — pure win, no infra, huge perceived-speed jump. *Do first.*
2. **`revalidateOnFocus: false` + visibility-aware heartbeat** (#5, #6) — one-line-ish changes, removes background jank.
3. **`getSession()` on read routes** (#4) — shaves latency off every page.
4. **Notification preview in payload** (#6) — removes the per-notification fetch.
5. **Keep the WS server warm** (#3) — small infra change, fixes the worst chat UX.
6. **Server-render the shell + profile** (#1, #2 full, #7) — bigger refactor, do once the quick wins are banked.

That ordering *is* the skill: knock out the cheap high-impact fixes, then tackle the architectural one deliberately.

---

## The "is this production-grade?" scorecard

Beyond speed, "production-grade" means it survives reality. Where we stand:

| Dimension | Status | Notes |
|---|---|---|
| Security headers / CSP | ✅ strong | (article 12) |
| Rate limiting | ✅ done | per-user-per-action (article 05) |
| Input validation/sanitization | ✅ done | (article 05) |
| RLS / data authorization | ✅ done | (article 06) |
| First-paint performance | ⚠️ weak | the waterfall (#1) |
| Observability (logs/metrics/tracing) | ❌ missing | only `console.log`; no metrics, no error tracking |
| Error boundaries | ⚠️ partial | need `error.tsx` coverage |
| Caching strategy | ✅ good | 4 layers (article 04) |
| Graceful degradation | ✅ good | chat retry/queue, face-detection fallback |

The two real gaps for "production-grade" are **first-paint perf** (#1) and **observability** (no structured logging / metrics / error tracking like Sentry). Those are the things to add next if the goal is genuinely production-quality, not just feature-complete.

---

## The interview angle

- *"How do you approach a 'the app feels slow' report?"* → "I don't guess — I open the Network tab and count round-trips before first meaningful paint, and look for serial dependencies. In my app the killer was a client-side auth-then-fetch waterfall: the whole authenticated zone was a client component with no middleware, so it downloaded the bundle, fetched the profile, *then* fetched page data — two serial round-trips behind a spinner. The fix was moving auth to the edge and rendering the shell server-side."
- *"What makes something production-grade beyond features?"* → "Security (headers, RLS, rate limiting — done), performance (fast first paint), and operability (structured logs, metrics, error tracking, graceful degradation). My app is strong on security and caching, weak on first-paint and observability — that's my next work."

---

## Concept checklist

- [ ] I can recite the dashboard waterfall and name the two root causes (wrong-world + serial).
- [ ] I can rank our break-points and give the fix + risk for each.
- [ ] I can explain waterfall-vs-parallel, wrong-world work, and "push don't poll."
- [ ] I can explain why some of these (cold start) are infra, not code.
- [ ] I can give a sensible fix *ordering* and justify it by leverage-per-risk.
- [ ] I can list what "production-grade" means beyond features and where we fall short.

Next up: **[12 — Security & PWA](./12-security-and-pwa.md)** — the last layer: CSP, the service worker, push, and the final scorecard.
