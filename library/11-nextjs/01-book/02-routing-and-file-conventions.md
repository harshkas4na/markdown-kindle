# 02 — Routing & file conventions

In the App Router there's no router config file. You don't register routes anywhere. Instead — and this is the whole idea —

**The folder structure *is* the routing table. A URL is just a path through the `app/` folder, and special filenames decide what renders at each level.**

So `app/dashboard/page.tsx` becomes `/dashboard`. `app/blog/[slug]/page.tsx` becomes `/blog/anything`. Once that clicks, you can look at our `app/` tree and read off every URL in the app without running it.

Let me build it up from the special files, because each filename is a *role*, not just a name.

---

## The special filenames (each one has a job)

Inside any folder, these names mean specific things:

| File | What it is | Renders when |
|---|---|---|
| `page.tsx` | The actual page UI | the URL matches this exact folder |
| `layout.tsx` | A wrapper that *persists* across child navigations | always, around its `page` and all nested pages |
| `loading.tsx` | The fallback shown while the page loads | the page (or its data) is still loading |
| `error.tsx` | The fallback shown if the page throws | a child throws an error |
| `template.tsx` | Like layout but *remounts* on every navigation | every navigation (rarely needed) |
| `route.ts` | An API endpoint (no UI) | a request hits this path |
| `not-found.tsx` | The 404 UI | `notFound()` is called or no route matches |

The mental model for `layout` vs `page`: **a layout is the picture frame, the page is the photo you swap inside it.** When you navigate from `/dashboard` to `/search`, the `(app)` layout (sidebar, bottom nav) *stays mounted* — only the page swaps. That's why our sidebar doesn't flicker or re-fetch when you move around. Layouts are how you get an app-shell that survives navigation.

---

## Reading our actual tree

Here's the shape of our `app/` folder, annotated:

```
app/
├── layout.tsx                 → wraps EVERYTHING (root: fonts, SEO, providers)
├── page.tsx                   → "/"  (the public landing page)
├── loading.tsx                → fallback while "/" loads
│
├── (app)/                     → route GROUP (parens = invisible in URL)
│   ├── layout.tsx             → the logged-in app shell (auth guard + sidebar)
│   ├── dashboard/
│   │   ├── page.tsx           → "/dashboard"
│   │   └── loading.tsx        → skeleton while dashboard loads
│   ├── search/page.tsx        → "/search"
│   ├── messages/page.tsx      → "/messages"
│   ├── people/[id]/page.tsx   → "/people/<any-id>"   (dynamic)
│   ├── trips/
│   │   ├── page.tsx           → "/trips"
│   │   ├── new/page.tsx       → "/trips/new"
│   │   └── [id]/route.ts?     → (no, that's in app/api) ...
│   └── admin/...              → "/admin", "/admin/users", etc.
│
├── blog/
│   ├── page.tsx               → "/blog"
│   └── [slug]/page.tsx        → "/blog/<slug>"   (dynamic)
│
├── station/[slug]/page.tsx    → "/station/<slug>"
├── route/[slug]/page.tsx      → "/route/<slug>"
├── onboarding/page.tsx        → "/onboarding"
└── api/                       → all our backend endpoints (route.ts files)
```

Three concepts are doing all the heavy lifting here. Let me hit each one.

---

## Concept 1 — Route groups: the `(app)` folder

That `(app)` with parentheses is a **route group**. The rule:

**A folder in parentheses organizes files *without* adding anything to the URL.**

So `app/(app)/dashboard/page.tsx` is still just `/dashboard`, *not* `/app/dashboard`. The parens vanish from the URL.

So why do it? Because route groups let you **apply one layout to a set of pages without nesting the URL.** Everything inside `(app)/` shares `app/(app)/layout.tsx` — which is our auth guard + sidebar shell. So `/dashboard`, `/search`, `/messages`, `/trips` are *all* automatically protected and all get the sidebar, just by living inside `(app)/`. Meanwhile `/blog`, `/about`, `/` live *outside* `(app)/`, so they're public and don't get the app shell.

That's a genuinely elegant pattern and we used it correctly: **the route group is our "authenticated zone".** One layout = the boundary between public and private. (Interview: route groups are for "shared layout / organization without affecting the URL". You can also use them to have *multiple* root layouts.)

---

## Concept 2 — Layouts nest, and they persist

Layouts compose top-down. For `/dashboard`, the chain that wraps the page is:

```
app/layout.tsx               (root: <html>, fonts, AuthProvider, SWRProvider)
   └── app/(app)/layout.tsx  (auth guard, AppShell, ChatNotifications)
          └── app/(app)/dashboard/layout.tsx   (if present)
                 └── app/(app)/dashboard/page.tsx
```

Two things to really internalize:

1. **The root layout is the only one that renders `<html>` and `<body>`.** It's required, and it wraps every single route — public and private. That's why our fonts and the `AuthProvider` live there: they need to exist everywhere.
2. **Layouts don't re-render on navigation between their children.** Move from `/dashboard` to `/messages` and `app/(app)/layout.tsx` stays mounted — the WebSocket connection, the presence heartbeat, the notification subscription all keep living. That's *exactly why* we mounted those there (look at `app/(app)/layout.tsx`: `usePresenceHeartbeat()`, `<ChatNotifications />`). If we'd put them in a page, they'd tear down and reconnect on every navigation. Putting persistent, app-wide machinery in a layout is the correct instinct.

---

## Concept 3 — Dynamic routes: `[slug]` and `[id]`

A folder named `[something]` is a **dynamic segment** — it matches any value and hands it to you as a param.

We use this a lot:
- `app/blog/[slug]/page.tsx` → `/blog/how-to-recharge-metro-card`
- `app/(app)/people/[id]/page.tsx` → `/people/abc-123`
- `app/station/[slug]/page.tsx` → `/station/rajiv-chowk`

In a **Server Component** page you receive params like this (note: in current Next.js, `params` is a Promise you await):

```tsx
export default async function StationPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  // use slug to look up the station, fetch data, render
}
```

There are cousins worth knowing for interviews:
- `[...slug]` — **catch-all**, matches `/a/b/c` as an array `["a","b","c"]`.
- `[[...slug]]` — **optional catch-all**, also matches the bare `/`.

And the partner function: **`generateStaticParams()`**. If you export it from a dynamic page, Next.js pre-renders those pages at build time (SSG). This is *the* move for our blog and station pages — we know all the slugs ahead of time, so we can build them statically and serve them instantly. (We'll wire the reasoning in article 03.)

---

## `route.ts` — the same routing rules, but for the backend

Here's a neat unification: our entire API uses the *same* folder routing. `app/api/search/route.ts` becomes the endpoint `/api/search`. A `route.ts` exports functions named after HTTP verbs:

```ts
export async function GET(request: Request) { ... }
export async function POST(request: Request) { ... }
export async function PATCH(request: Request) { ... }
```

So `app/api/trips/[id]/route.ts` handles `GET/PATCH/DELETE` for `/api/trips/<id>`. Same `[id]` dynamic-segment rule as pages. The only difference from a `page.tsx`: a `route.ts` returns *data* (`NextResponse.json(...)`), not UI. We'll spend all of article 05 inside these.

This is why our structure feels coherent — **pages and APIs follow one routing system.** You never wonder "where does this endpoint live"; it's the folder that matches the URL.

---

## `loading.tsx` and Suspense — a small but important detail

We have `loading.tsx` files (`dashboard/loading.tsx`, `search/loading.tsx`, etc.). The rule:

**`loading.tsx` automatically wraps the sibling `page.tsx` in a `<Suspense>` boundary, and shows the loading file while the page's server work is pending.**

This is the foundation of streaming SSR. The server can instantly send the layout + the loading skeleton, then stream in the real page when its data resolves. The user sees *something* immediately instead of a blank screen.

BUT — and this is the catch I want to remember — **this only pays off if the page does its slow work on the server.** Our pages are `"use client"` and fetch via SWR *after* hydration, so the skeleton shows, but the real data still arrives via a client fetch, not a server stream. So we get the *visual* benefit of a skeleton but not the *speed* benefit of streaming. That mismatch is a recurring theme, and article 03 is where we finally confront it.

---

## The interview angle

Likely questions and the crisp answers:

- *"What's a route group?"* → "A folder in parens that groups routes under a shared layout without adding to the URL. I use one (`(app)`) as my authenticated zone — every page inside it inherits the auth-guard layout."
- *"How do layouts behave on navigation?"* → "They persist. Moving between sibling pages doesn't remount the layout, so I put my WebSocket and presence heartbeat in the layout — they survive navigation instead of reconnecting every time."
- *"How do dynamic routes work?"* → "`[param]` folders. The page receives `params`. With `generateStaticParams` I can pre-render all known values at build time — that's how I'd make my blog static."

---

## Concept checklist

- [ ] I can take any URL in the app and point to the exact file that renders it.
- [ ] I can explain route groups and *why* `(app)` is our auth boundary.
- [ ] I can explain why layouts persisting across navigation is *why* our WS/presence live in the layout.
- [ ] I know `[slug]`, `[...slug]`, `[[...slug]]` and when each matches.
- [ ] I know what `generateStaticParams` does and which of our pages should use it.
- [ ] I understand that `loading.tsx` = a Suspense boundary, and why we only get half its benefit today.

Next up: **[03 — Rendering & the SSR balance](./03-rendering-and-the-ssr-balance.md)** — the big one. When to use SSR vs CSR vs streaming, and fixing our slow first paint.
