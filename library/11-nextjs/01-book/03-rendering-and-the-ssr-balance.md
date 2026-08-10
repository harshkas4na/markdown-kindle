# 03 — Rendering & the SSR balance

This is the article I most wanted to write, because "should this be SSR or CSR" is the question I keep half-answering. So let me nail it properly, and then use it to explain *exactly* why my own app feels slow and how I'd fix it.

The mental model first:

**Rendering strategy is just one decision repeated per page: *at what moment do we turn data into HTML, and on whose computer?* Build-time on my machine, request-time on the server, or after-load on the user's phone. Everything else is detail.**

Earlier (article 01) I drew the spectrum. Now I want the *decision procedure* — given a page, how do I pick — and then I'll run our real pages through it.

---

## The decision procedure

Ask these in order. The first "yes" usually decides it.

**1. Does this page look the same for everyone, and rarely change?**
→ Yes: **SSG** (build it once). Example: `/about`, `/privacy`, `/terms`, a blog post.

**2. Same for everyone, but changes every so often (not per-user)?**
→ **ISR** (build once, auto-rebuild every N seconds). Example: a `/station/rajiv-chowk` page where fares/timings update occasionally. Best of both: static speed, fresh-ish data.

**3. Personalized (depends on *who* is asking), but needs fast first paint and/or SEO?**
→ **SSR**, ideally **streaming SSR**. Render on the server *with* the user's data, stream the shell first. Example: a logged-in dashboard that should still feel instant.

**4. Personalized, behind a login, SEO doesn't matter, and it's highly interactive?**
→ **CSR is acceptable.** Ship a shell, let the browser fetch and draw. Example: a live search results page, a chat window.

**5. Is it a piece of a page that's slow but the rest is fast?**
→ Wrap just that piece in `<Suspense>` and **stream** it. Don't make the whole page wait for the slowest query.

The senior move isn't "always SSR" or "always CSR" — it's **mixing them on one page**: static shell, server-rendered personalized core, and a couple of client islands for the interactive bits. Next.js App Router is built precisely for this mix, because Server and Client Components compose in the same tree.

---

## The cost of each choice (so the tradeoff is concrete)

| Strategy | First paint | Data freshness | Server cost | SEO | JS shipped |
|---|---|---|---|---|---|
| SSG | ⚡ instant | stale until rebuild | ~zero | ✅ | low |
| ISR | ⚡ instant | fresh every N s | low | ✅ | low |
| SSR (stream) | 🙂 fast (shell first) | fresh per request | medium | ✅ | medium |
| CSR | 🐢 slow (shell → JS → fetch → paint) | fresh | low | ❌ | high |

Read the CSR row carefully, because that's our whole app right now. "First paint slow" isn't an opinion — it's the literal sequence of round-trips, which I'll trace next.

---

## Our app on this table (honest audit)

| Page | What it should be | What it is today | Verdict |
|---|---|---|---|
| `/` landing | SSG or SSR | mostly client | ok-ish, could be static |
| `/blog`, `/blog/[slug]` | **SSG** (`generateStaticParams`) | partially static | should be fully static |
| `/station/[slug]`, `/route/[slug]` | **SSG/ISR** | — | prime candidates for static |
| `/about`, `/privacy`, `/terms` | **SSG** | static-ish | fine |
| `/dashboard` and all `(app)/*` | **streaming SSR** | **CSR** ❌ | the problem |
| `/search` results | CSR | CSR | genuinely fine |
| chat window | CSR | CSR | fine (it's a live socket) |

The marketing/SEO pages are basically fine. The **entire logged-in app is CSR when it shouldn't be**, and that's where the slowness lives.

---

## Tracing the actual slowness (the waterfall)

Let me trace what happens, in order, when I open `/dashboard` cold. This is the most important diagram in the course.

Because `app/(app)/layout.tsx` starts with `"use client"`, and there's **no `middleware.ts`**, here's the real sequence:

```
1. Browser requests /dashboard
2. Server returns a near-EMPTY html shell  (no dashboard content — it's a client component)
3. Browser downloads + parses the JS bundle           ⏳ round-trip-ish
4. AuthProvider mounts, Supabase reads the cookie → "ok you're user X"
5. fetchProfile() → fetch("/api/profile")             ⏳ NETWORK ROUND TRIP #1
       ↑ and the WHOLE app is showing <MetroPageLoader/> until this resolves
6. profile arrives → guard passes → layout renders → dashboard page mounts
7. page's SWR hooks fire: /api/trips, /api/connections, /api/discover  ⏳ ROUND TRIP #2 (parallel)
8. data arrives → dashboard finally paints real content
```

That's **two serial network round-trips** (profile, *then* page data) plus a JS download, all gated behind a full-screen spinner. On a phone on mobile data, that's the "this isn't fast" feeling. And it's not a code-quality problem — the code is fine — it's a *strategy* problem: **we picked CSR for a page that should stream from the server.**

Two specific sins stack on top:

1. **The profile fetch is a hard gate.** In the layout: `if (loading || !user || profileLoading) return <MetroPageLoader/>`. Nothing — not even the shell — renders until `/api/profile` comes back. Profile barely ever changes, yet we block the entire UI on it *every single load.*
2. **No middleware.** Auth/redirect decisions happen in the browser after the bundle loads, instead of at the edge before any HTML is sent.

---

## How I'd fix it (the SSR balance, applied)

I'm not going to "rewrite everything in SSR". The fix is to move each concern to the world where it's cheap:

**Fix 1 — Auth at the edge with `middleware.ts`.**
A `middleware.ts` runs on the server *before* the page, on every matching request. Move the "are you logged in? onboarded?" check there. Now an unauthenticated user gets redirected before a single byte of dashboard HTML is generated — no client round-trip to discover they're logged out. (Full code in article 07.)

```ts
// middleware.ts (sketch)
export async function middleware(req) {
  const { supabase, response } = createMiddlewareClient(req);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.redirect(new URL("/auth/...", req.url));
  return response; // also refreshes the session cookie
}
export const config = { matcher: ["/dashboard/:path*", "/search/:path*", ...] };
```

**Fix 2 — Stop gating the whole app on the profile fetch.**
Two options, both good:
- Render the profile *on the server* (it's just a `select` keyed by user id) and pass it down, so the page arrives already knowing who you are — zero client round-trip.
- Or, cheap version: cache the last profile in `localStorage`, hydrate from it instantly, and revalidate in the background. The spinner disappears on every repeat visit.

**Fix 3 — Make the shell server-rendered, stream the data.**
The app shell (sidebar, nav) has no reason to be client-only. Render it on the server. Keep the genuinely interactive bits (`ChatNotifications`, the swipe nav, the fetch-429 interceptor) as small client islands *inside* it. Then the user sees the shell + skeleton instantly (streaming SSR via `loading.tsx`), and the personalized data streams in.

The principle behind all three: **push work to the cheapest world.** Auth → the edge. Profile → the server (or cache). Interactivity → small client islands. The big slow client blob becomes a fast server shell with a few black dots in it.

---

## "When should I deliberately choose CSR then?"

Because the lesson isn't "SSR good, CSR bad." CSR is the *right* call when:

- The content is **100% behind auth** (no SEO value to server-rendering it) **and**
- It's **highly interactive / real-time** (a chat window, a live-updating search) **and**
- The data is **so user-specific and fast-changing** that server-caching buys nothing.

Our **chat window** and **search results** legitimately fit this — rendering them on the server would add complexity for no real first-paint win, because they're alive and socket-driven. So we *keep* them CSR. That's the balance: CSR where interactivity dominates, SSR/streaming where first-paint and SEO matter, SSG/ISR where content is shared and stable.

---

## A note on `dynamic`, `revalidate`, and caching knobs

Next.js lets you control strategy per-route with exports:

```ts
export const dynamic = "force-dynamic";  // never cache, always SSR fresh (our cron route uses this)
export const revalidate = 3600;          // ISR: rebuild at most once an hour
export const dynamic = "force-static";   // force SSG
```

You'll see `export const dynamic = "force-dynamic"` in `app/api/cron/birthday/route.ts` — that's us saying "never statically optimize this, run it fresh every time." Knowing these knobs exist is half the battle; article 04 goes into the caching layers they control.

---

## The interview angle

The question *"when do you use SSR vs CSR?"* is a trap if you answer with definitions. Answer with a **decision procedure and a tradeoff you actually lived**:

> "I decide per page by asking: is it shared or personalized, and does it need SEO or fast first paint? Shared + stable → static (SSG/ISR). Personalized + needs speed/SEO → streaming SSR. Behind-login + highly interactive → CSR is fine. In my app I learned this the hard way: I made my whole authenticated layout a client component, so the dashboard does a client-side auth-then-fetch waterfall and feels slow. The fix is auth in middleware, render the profile on the server, and keep only the interactive bits as client components — turning a CSR blob into a streaming-SSR shell."

That's a complete, senior answer with a real scar in it.

---

## Concept checklist

- [ ] I can run any page through the 5-question decision procedure and justify the choice.
- [ ] I can recite the CSR waterfall for `/dashboard` step by step.
- [ ] I can explain why blocking the app on the profile fetch is the wrong call.
- [ ] I know the three fixes (middleware auth, server/cached profile, server shell + streaming) and *why each moves work to a cheaper world*.
- [ ] I can defend keeping chat + search as CSR (i.e. CSR isn't always wrong).
- [ ] I know `dynamic`, `revalidate`, `force-static`/`force-dynamic` and what they control.

Next up: **[04 — Data fetching & caching](./04-data-fetching-and-caching.md)** — server fetching vs our SWR hooks, dedup, and the Redis cache layer.
