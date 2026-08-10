# 04 — Data fetching & caching

Now that I know *where* code runs (article 01) and *which page renders how* (article 03), the next question is the one every app lives or dies on: **how does data get from Postgres into the user's eyeballs, and how many times do we needlessly fetch it?**

The mental model:

**There are two completely separate ways to fetch in Next.js — fetch on the *server* while rendering, or fetch from the *browser* after the page is alive. They have different superpowers, different caches, and you should know which one you're using at all times.**

Our app uses the second one almost everywhere (client fetching via SWR). That's a deliberate-ish choice with real consequences, so let me lay out both and then read our code.

---

## Path A — fetching on the server (while rendering)

In a Server Component you just... `await` your data. No hook, no `useEffect`, no loading state. The component is `async`.

```tsx
// a Server Component (no "use client")
export default async function StationPage({ params }) {
  const { slug } = await params;
  const supabase = await createClient();           // server client
  const { data } = await supabase.from("...").select();  // runs ON THE SERVER
  return <div>{/* render data directly */}</div>;
}
```

Why this is powerful:
- The data is in the HTML on first paint — no spinner, no waterfall, great for SEO.
- The DB query runs server-side, close to the database, with secrets available.
- Next.js **automatically dedupes and caches** `fetch()` calls during a render (request memoization) and across requests (the data cache).

We barely use this path today (because our pages are client components). The fix in article 03 — server-rendering the profile and the shell — *is* moving things onto Path A.

---

## Path B — fetching from the browser (what we actually do)

Our pages are `"use client"`, so they fetch *after* hydration. We don't hand-roll `useEffect + fetch + useState` though — we use **SWR**. And honestly, our SWR setup is the best-built part of the codebase, so this is worth understanding deeply.

### What SWR even is

SWR = **stale-while-revalidate**. The strategy in one line:

**Show the cached (stale) data instantly, fire a fetch in the background to revalidate, and swap in fresh data when it arrives.**

So the user never stares at a spinner if we've seen the data before — they see the old data immediately, and it quietly updates. It's a caching layer that lives in the browser, keyed by the URL.

### Our global config — `lib/swr-config.tsx`

```tsx
<SWRConfig value={{
  fetcher,                    // default: fetch(url).then(r => r.json())
  dedupingInterval: 5000,     // identical requests within 5s → only ONE network call
  revalidateOnFocus: true,    // refetch when the tab regains focus
  keepPreviousData: true,     // while refetching, keep showing old data (no flash)
  errorRetryCount: 2,
}}>
```

Three of these are doing real work:

- **`dedupingInterval: 5000`** — this is why the dashboard mounting `useTrips`, and something else also calling `/api/trips`, results in *one* network request, not two. SWR sees the same key within 5s and shares the result. This is the single most underrated feature — it kills accidental duplicate fetches across components.
- **`keepPreviousData: true`** — when you navigate or refetch, you keep seeing the last data instead of a blank flash. Smooth.
- **`revalidateOnFocus: true`** — ⚠️ this one bites us. Every time you switch back to the tab, *every* active SWR key refetches. Combined with Supabase auto-firing a token refresh on focus, switching tabs triggers a little refetch storm. Worth turning off globally and opting in only where freshness matters. (Noted in the perf article.)

### Our hooks — the pattern worth copying

Every data hook follows the same clean shape. Look at `lib/hooks/use-trips.ts`:

```ts
export function useTrips() {
  const { user } = useAuth();
  const { data, error, isLoading, mutate } = useSWR(
    user ? "/api/trips" : null,        // <-- the conditional key trick
    { dedupingInterval: 5000 }
  );
  return { trips: (data ?? []) as Trip[], isLoading, error, mutate };
}
```

The `user ? "/api/trips" : null` is the **conditional fetching** pattern and it's important: **if the key is `null`, SWR doesn't fetch at all.** So we never hit `/api/trips` until we know there's a logged-in user. Every one of our hooks (`useConnections`, `useConversations`, `useDiscover`, `useNotifications`...) uses this exact guard. That's a deliberate, consistent design — data fetching is gated on auth at the hook level.

### `mutate` — the optimistic update lever

`mutate` is how you tell SWR "the data changed, update the cache." Two flavors, both used in `lib/hooks/use-notifications.ts`:

```ts
// 1. Optimistic: change the local cache immediately, don't even refetch yet
mutate((prev) => prev?.map(n => ids.includes(n.id) ? { ...n, read: true } : n),
       { revalidate: false });

await fetch("/api/notifications/read", { method: "PATCH", ... });

// 2. Then revalidate to confirm with the server
mutate();
```

This is **optimistic UI**: mark the notification read *instantly* in the UI (feels snappy), fire the request, then reconcile with the server. If the server disagrees, the revalidate corrects it. This is exactly how you make a UI feel fast without lying to the user for long. (The chat in article 08 takes this much further.)

### Revalidating *across* hooks — the realtime trick

Here's a clever bit. `useNotifications` and `useUnreadCount` both subscribe to a *shared Supabase Realtime channel* (`use-notification-channel.ts`). When the DB's `notifications` table changes for this user, Supabase pushes an event, and the hook calls `mutate()` — refetching *only when something actually changed*, instead of polling every few seconds.

```ts
useNotificationChannel(useCallback(() => { mutate(); }, [mutate]));
```

So our notification badges update in near-real-time with **zero polling**. That's a genuinely good pattern: *realtime event → SWR revalidate.* Push, don't poll. (We'll see the channel singleton itself in article 08.)

---

## The caching layers (this is interview catnip)

People think "caching" is one thing. In our stack there are *four* distinct caches data passes through. Knowing them separately is what senior looks like:

```
Postgres
   │
   ├─(1) Redis server cache  ──  lib/server-cache.ts  (our cache-aside, e.g. /api/search for 120s)
   │
   ├─(2) Next.js Data Cache  ──  caches server fetch() results across requests
   │
   ├─(3) HTTP cache headers  ──  e.g. /api/discover: "private, max-age=30, stale-while-revalidate=60"
   │
   └─(4) SWR client cache    ──  in the browser, keyed by URL, dedupes + stale-while-revalidate
```

### Layer 1 — our Redis cache-aside (`lib/server-cache.ts`)

This is the one I wrote myself, and it's the classic **cache-aside** pattern:

```ts
export async function cached<T>(key, ttlSeconds, fetcher) {
  const existing = await getCached<T>(key);     // 1. look in Redis
  if (existing !== null) return existing;        // 2. hit → return it
  const fresh = await fetcher();                 // 3. miss → do the real work
  await setCache(key, fresh, ttlSeconds);        // 4. store for next time
  return fresh;
}
```

You see it used in `app/api/search/route.ts`:

```ts
const results = await cached(cacheKey, 120, async () => {
  // the expensive query + scoring runs only on a cache miss
});
```

So if I search the same route twice within 2 minutes, the second search skips the DB query *and* the whole scoring pass — it just returns the Redis blob. The `cacheKey` includes the user id + all search params, so two different searches don't collide. This is a real, production-grade pattern (cache-aside with TTL and a composite key). Worth being able to draw on a whiteboard.

The matching set: `invalidateCache(prefix)` scans and deletes keys when the underlying data changes — that's **cache invalidation**, the famously hard problem. Knowing *when* to invalidate (on write) vs *expire* (TTL) is a great interview discussion.

### Layer 3 — HTTP cache headers

`/api/discover` sets `Cache-Control: private, max-age=30, stale-while-revalidate=60`. That tells the browser (and any CDN): "this is fine to reuse for 30s, and you can serve it stale for another 60s while you revalidate." It's the *same* stale-while-revalidate idea as SWR, but at the HTTP layer. Meanwhile `next.config` sets `no-store` on `/api/*` by default, so each route opts *in* to caching deliberately. Good default — personalized data shouldn't be cached by accident.

---

## Putting it together: the life of one piece of data

A search request, end to end, touching every concept above:

1. User types a route, hits search. The search page (client) calls `/api/search?...`.
2. SWR checks its **browser cache** (layer 4). Cold → it actually fetches.
3. The route handler authenticates, rate-limits, then calls `cached(key, 120, ...)`.
4. **Redis** (layer 1) is checked. Cold → run the real query + the matching/scoring algorithm.
5. Result is stored in Redis (120s TTL) and returned with cache headers.
6. SWR stores it in the browser cache, renders it, and (because `keepPreviousData`) future searches feel instant.
7. Switch tabs and back → `revalidateOnFocus` quietly refetches (mostly a Redis hit now).

Four caches, one request. *That's* the data layer.

---

## The interview angle

- *"Server vs client fetching — when do you use each?"* → "Server fetching for first-paint/SEO content and anything that should be in the HTML; it dedupes and caches automatically. Client fetching (I use SWR) for personalized, interactive, behind-login data that updates as the user works. The cost of client fetching is the waterfall — you only fetch after hydration."
- *"What's stale-while-revalidate?"* → "Serve cached data instantly, revalidate in the background, swap when fresh. I use it twice — in SWR on the client and as an HTTP cache header on my discover endpoint."
- *"How do you cache an expensive endpoint?"* → "Cache-aside in Redis with a TTL and a composite key. My search endpoint caches the query + scoring for 120s keyed by user + params, and I invalidate by prefix on writes."
- *"How do you avoid duplicate requests?"* → "SWR dedups identical keys within a window, and I gate every hook on the auth state with a conditional `null` key so nothing fetches before login."

---

## Concept checklist

- [ ] I can explain the two fetch paths (server-render vs client SWR) and their tradeoffs.
- [ ] I understand `dedupingInterval`, `keepPreviousData`, `revalidateOnFocus` and which one hurts us.
- [ ] I can explain the `user ? "/api/x" : null` conditional-fetch trick and why every hook uses it.
- [ ] I can implement optimistic UI with `mutate(updater, { revalidate: false })` then `mutate()`.
- [ ] I can name the 4 caching layers and which file/route uses each.
- [ ] I can whiteboard the cache-aside pattern from `server-cache.ts` and explain TTL vs invalidation.
- [ ] I can trace a search request through all four caches.

Next up: **05 — Route Handlers (our API layer)** — the `auth → rate-limit → sanitize → query` pattern that every `app/api/*` route follows. *(coming next)*
