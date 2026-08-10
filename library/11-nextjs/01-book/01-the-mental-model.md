# 01 — The mental model

Goal: before touching a single API or a single hook, I want one clean mental model of what Next.js *is*. Because if this part is fuzzy, everything else stays fuzzy.

So let me start with a definition that I actually believe, not a textbook one:

**Next.js is a framework where your code runs in two completely different worlds, and the entire skill is knowing which world a given line of code is running in.**

That's it. That's the whole thing. Two worlds:

- **The server** — a computer somewhere (Vercel, in our case). It has secrets, a database connection, the file system, no concept of "a click". It runs code *once* to produce HTML and then mostly forgets about you.
- **The browser** — the user's phone. It has the DOM, clicks, scroll, `localStorage`, the WebSocket. It has *no* secrets and *no* direct database access.

Every confusing Next.js error you've ever hit ("you can't use `useState` in a Server Component", "`window is not defined`", "hydration mismatch") is really just one of these two worlds complaining that you put the wrong code in it.

So the question stops being *"how do I do X in Next.js"* and becomes *"which world should X happen in, and how do I move data between the two."*

---

## The two kinds of components

In the App Router (the `app/` folder), **every component is a Server Component by default.** That surprised me at first. It means the component runs on the server, produces HTML, and ships *zero* JavaScript to the browser for itself.

To opt a component *out* of the server and into the browser, you put one magic line at the very top of the file:

```tsx
"use client";
```

The moment you write that, you've said: *"this file, and everything it imports, ships to the browser and runs there."*

Think of it like a green dot / black dot tree (the way I think about git, honestly). The root of your component tree is green = server. Somewhere down the tree you hit a `"use client"` — from that node down, the subtree turns black = browser. You can't go back to green inside a black subtree. A Client Component can render a Server Component only if it was *passed in as a child* (`children`), not if it *imports* it.

### What can each one do?

| | Server Component (green) | Client Component (black, `"use client"`) |
|---|---|---|
| `useState`, `useEffect`, event handlers | ❌ no | ✅ yes |
| `async/await` directly in the component | ✅ yes | ❌ no (well, not the same way) |
| Read secrets / DB / `cookies()` | ✅ yes | ❌ no |
| Access `window`, `localStorage`, DOM | ❌ no | ✅ yes |
| Ships JS to the browser | ❌ no (good for speed) | ✅ yes (costs bytes) |

The cheat code: **Server Components are for *getting data and rendering it*. Client Components are for *interactivity*.** If a component just shows stuff, keep it green. If it has to react to the user (click, type, hover), it has to be black.

---

## In our codebase

Now let me look at our two layouts, because they are the perfect example of the two worlds sitting right next to each other.

### `app/layout.tsx` — the root (a Server Component)

Open it. Notice what's *missing*: there's no `"use client"` at the top. So this is a **Server Component**. And look at what it does — it sets `metadata`, loads fonts, injects the JSON-LD `<script>` for SEO. All of that is "render stuff once on the server" work. Perfect fit for green.

```tsx
export const metadata: Metadata = { /* ... SEO title, openGraph ... */ };

export default function RootLayout({ children }) {
  return (
    <html lang="en-IN">
      <body>
        <SplashScreen />
        <AuthProvider>      {/* <-- this is where it turns black */}
          ...
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

That `metadata` export is a giveaway you're on the server — you literally *cannot* export `metadata` from a `"use client"` file. (Interview gold: "metadata API only works in Server Components.")

### `app/(app)/layout.tsx` — the app shell (a Client Component)

Now open this one. First line:

```tsx
"use client";
```

Black. Why did it have to be black? Because look what it does: `useAuth()`, `useRouter()`, `useEffect()`, and it even monkey-patches `window.fetch`. Every one of those is a *browser* thing. State, effects, the router, `window` — none of that exists on the server. So this file *had* to opt into the browser.

And here's the thing I want to flag early (we'll fix it in article 03 and 11): **because this layout is a Client Component, our entire logged-in app is rendered in the browser.** The server sends an almost-empty shell, the browser downloads the JS, *then* figures out who you are, *then* fetches your profile, *then* draws the screen. That's why the app feels slow on first load. Hold that thought — it's the single most important performance lesson in this whole course, and it falls straight out of this mental model: *we put the whole app in the wrong world.*

---

## "But wait — if the server renders it, why does my browser also run React?"

Good question, this confused me for a while. The answer is **hydration**.

Here's the flow for a normal page:

1. **Server** runs your components → produces a string of HTML → sends it. The user sees content *immediately*, even before any JS loads. (This is why SSR is good for speed and SEO.)
2. **Browser** receives that HTML and paints it. Looks done, but it's "dead" — buttons don't work yet.
3. **Browser** downloads the React JS bundle and "hydrates" — it walks the same HTML, attaches event listeners, and wakes the page up. Now clicks work.

Hydration is React saying *"the server already drew this; let me re-attach my brain to it without re-drawing."*

A **hydration mismatch** happens when the HTML the server produced doesn't match what the browser would have produced — e.g. you rendered `new Date()` on the server and again on the client and they differ. React panics because its assumption ("the DOM already matches my virtual tree") broke. That's why you sometimes see `suppressHydrationWarning` on the `<html>` tag (we have it) — it tells React "I know this attribute might differ, chill."

---

## The rendering spectrum (the thing interviews love)

People say "SSR vs CSR" like there are two options. There are really *five*, and they're a spectrum of *when the HTML gets made*:

```
build time ───────────────────────────────────► request time ───► in the browser

   SSG            ISR                SSR (streaming)            CSR
 (made once,   (made once,        (made fresh on every      (made entirely
  at build)    re-made every       request, on the           in the browser
               N seconds)          server)                   after JS loads)
```

- **SSG (Static Site Generation)** — HTML built once at deploy. Fastest possible. Use for: our blog posts, the `/about` page, marketing pages. They don't change per-user.
- **ISR (Incremental Static Regeneration)** — like SSG but it quietly rebuilds every N seconds. Use for: a page that's mostly static but updates occasionally (e.g. a station page where fares rarely change).
- **SSR (Server-Side Rendering)** — HTML built fresh on every request, on the server, *with* the user's data. Use for: pages that are personalized but should still load fast and be crawlable.
- **Streaming SSR** — SSR but the server sends HTML in chunks as it's ready (using `<Suspense>` and `loading.tsx`), so the user sees the shell instantly and the slow parts pop in.
- **CSR (Client-Side Rendering)** — server sends an empty shell, browser does everything. Use for: deeply interactive, behind-login dashboards where SEO doesn't matter... *but* it's the slowest first paint, and **this is what our whole app currently does.**

The skill (article 03 is all about this) is matching the page to the right point on this spectrum. Our blog should be SSG. Our dashboard *could* be streaming SSR but is currently CSR. Our search results page is genuinely fine as CSR. Knowing the difference is the senior-engineer move.

---

## The interview angle

If someone asks *"explain Server Components"* — don't recite. Say this:

> "In the App Router everything is a Server Component by default — it runs on the server, can talk to the DB directly, and ships no JS. You opt into the browser with `"use client"`, which you only need for interactivity — state, effects, event handlers, browser APIs. The art is keeping the green/server part as big as possible and pushing `"use client"` as far down the tree as you can, because every client component costs the user download and execution time."

Then, if you want to show off, point at a real tradeoff: *"In my app I made a mistake — my authenticated layout is a client component, so my whole dashboard renders client-side and has a slow first paint. The fix is to move auth to middleware and render the shell on the server."* That answer gets you hired, because it shows you understand the *consequences*, not just the definitions.

---

## Concept checklist

- [ ] I can explain the "two worlds" (server / browser) and place any piece of code in the right one.
- [ ] I know what `"use client"` does and where the boundary sits (green/black tree).
- [ ] I can list 3 things a Server Component can do that a Client Component can't, and vice versa.
- [ ] I can explain hydration and what causes a hydration mismatch.
- [ ] I can name all 5 points on the rendering spectrum and give a use case for each.
- [ ] I can explain *why our app's first load is slow* using only this article's vocabulary.

Next up: **[02 — Routing & file conventions](./02-routing-and-file-conventions.md)** — how this folder tree literally becomes our URLs.
