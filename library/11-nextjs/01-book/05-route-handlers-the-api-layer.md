# 05 — Route Handlers (our API layer)

We've been calling `/api/trips`, `/api/search`, `/api/profile` for four articles now. Time to walk *inside* one and see what a request actually goes through. Because here's the realization that made the backend click for me:

**A Route Handler is just a function the server runs when a URL is hit. There's no Express, no server file, no `app.listen()`. The folder is the route (article 02), and the exported `GET`/`POST`/`PATCH` function *is* the endpoint.**

That's the whole backend. `app/api/search/route.ts` exporting `async function GET()` *is* `GET /api/search`. Next.js spins it up on demand (serverless), runs it, returns the response, and forgets about it.

---

## The anatomy of one handler

A Route Handler takes a standard Web `Request` and returns a standard Web `Response` (Next gives us `NextResponse` as a nicer wrapper). Nothing framework-magic about the signatures — they're the actual web platform:

```ts
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);   // read query params
  const start = searchParams.get("start_station");
  // ... do work ...
  return NextResponse.json({ results });            // return JSON
}
```

For dynamic routes, the second arg carries the params (a Promise, like in pages):

```ts
// app/api/trips/[id]/route.ts
export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  ...
}
```

That's it. `GET`, `POST`, `PATCH`, `PUT`, `DELETE` — export the verb you want to handle.

---

## Our pattern — the 4-step pipeline (this is the gold)

Every serious route in our app follows the *same* four steps in the *same* order. Once you see it, you can read any of our 60+ routes in ten seconds. Here it is, distilled from `app/api/search/route.ts` and `app/api/profile/route.ts`:

```ts
export async function GET(request: Request) {
  // ── STEP 1: AUTHENTICATE ──────────────────────────────
  const supabase = await createClient();           // server client (reads cookie)
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  // ── STEP 2: RATE LIMIT ────────────────────────────────
  const rl = await rateLimit(`search:${user.id}`, RATE_LIMITS.search);
  if (!rl.success) return rateLimitResponse(rl);     // 429

  // ── STEP 3: VALIDATE / SANITIZE INPUT ─────────────────
  if (!isValidStationName(startStation)) {
    return NextResponse.json({ error: "Invalid station name" }, { status: 400 });
  }

  // ── STEP 4: DO THE WORK + RESPOND ─────────────────────
  const data = await cached(key, 120, async () => { /* query + logic */ });
  return NextResponse.json(data);
}
```

**Auth → Rate-limit → Validate → Work.** That order is deliberate, and *why* it's that order is a great interview talking point:

- **Auth first** because there's no reason to spend any effort on a request we'll reject anyway. Also, the rate-limit key is *per user* (`search:${user.id}`), so we need the user id before we can rate-limit.
- **Rate-limit second** to stop an authenticated-but-abusive user before they hit the database. Cheap check (one Redis call) guarding the expensive stuff.
- **Validate third** so garbage input never reaches the query layer.
- **Work last**, by which point the request is trusted, throttled, and clean.

---

## Step 1 deep-dive — `getUser()` and the cookie

`const supabase = await createClient()` uses our **server** client (`lib/supabase/server.ts`), which reads the auth cookie from the incoming request. Then `supabase.auth.getUser()` validates that token.

⚠️ **Important nuance I want to remember:** `getUser()` sends a request to Supabase's auth server to *verify* the JWT is genuine — it's a network call. `getSession()` just decodes the cookie locally, no network. `getUser()` is the secure choice (a forged cookie would fail verification), which is right for a route that's about to mutate data. But notice: *every one of our routes calls `getUser()`*, so a dashboard load that fires 5 API calls does 5 separate auth-server round-trips. That's a real latency cost we flagged in the perf audit — for read-only routes where we just need the id, `getSession()` would be faster. **Security vs. speed tradeoff, and knowing which to pick per-route is the skill.** (Article 06 covers the two clients; 07 covers the auth flow.)

---

## Step 2 deep-dive — rate limiting (`lib/rate-limit.ts`)

Our rate limiter is built on Upstash + Redis with a **fixed-window** algorithm:

```ts
limiter: Ratelimit.fixedWindow(config.limit, `${config.windowSeconds} s`)
```

Fixed window = "max N requests per W seconds, counted in fixed buckets." Simple and cheap (one Redis `INCR` + TTL). The tradeoff (interview-worthy): a fixed window allows a burst at the boundary — e.g. 30 requests at 0:59 and 30 more at 1:01. Sliding-window or token-bucket smooth that out at higher cost. For our scale, fixed window is the right call.

We pre-define limits per *kind* of action in `RATE_LIMITS`:

```ts
search: 30/min,  write: 20/min,  reports: 5/hour,
profileUpdate: 10/hour,  tripCreate: 15/hour,  global: 200/min
```

The reasoning is risk-based: reads are generous (30/min), writes are tighter (20/min), and *abusable* writes are strict (reports 5/hour, so no one can mass-report someone). And the key is **per-user-per-action** (`search:${user.id}`), so hitting your search limit doesn't block your messaging. The 429 response includes a `Retry-After` header — a polite, standards-correct way to tell the client when to come back.

One detail worth copying: the limiters are **memoized in a `Map`** so we don't construct a new `Ratelimit` object on every request. Small thing, but it's the kind of per-invocation hygiene that matters in serverless where the function may stay warm.

---

## Step 3 deep-dive — sanitize vs validate (`lib/sanitize.ts`)

Two different jobs that people conflate:

- **Validate** = reject bad input. `isValidStationName`, `isValidDate`, `isValidTime`, `isValidUUID` — if the shape is wrong, return `400` and stop.
- **Sanitize** = clean accepted input before it's stored. `sanitizeText` trims, strips control characters (null bytes etc.), collapses excessive newlines, and enforces a max length.

A subtle, correct comment lives in our `sanitizeText`:

> "Does NOT escape HTML — React auto-escapes in JSX, so we only need to sanitize for storage safety."

That's an important XSS insight: **React escapes by default when it renders text**, so the XSS risk isn't in storing `<script>`, it's in *bypassing* React's escaping (e.g. `dangerouslySetInnerHTML`). So we sanitize for *storage integrity* (no null bytes, no 50,000-char blobs) and rely on React for *display* safety. The danger zone is anywhere we use `dangerouslySetInnerHTML` — which we do for the JSON-LD script in the root layout, but that's our own trusted data, not user input. Knowing exactly where the escaping happens is what separates "I added a sanitize function" from "I understand my XSS surface."

---

## Step 4 — the work, and choosing a response

The body varies per route, but the response vocabulary is consistent. Status codes we use and what they *mean*:

| Code | Meaning | When we return it |
|---|---|---|
| 200 | OK | normal success (`NextResponse.json(data)`) |
| 400 | Bad Request | validation failed (bad station/date) |
| 401 | Unauthorized | no logged-in user |
| 403 | Forbidden | logged in but not allowed (e.g. editing locked profile fields, non-admin) |
| 404 | Not Found | profile row doesn't exist yet (new user) |
| 429 | Too Many Requests | rate limit hit |
| 500 | Server Error | DB error we didn't expect |

The 401 vs 403 distinction is a classic interview gotcha: **401 = "I don't know who you are" (not authenticated); 403 = "I know who you are and you still can't" (not authorized).** Our profile PATCH returns `403` when you try to change a locked field after onboarding — you're authenticated, just not permitted. Our `getAdminUser()` gate in `push/send` returns `403` for non-admins. Right codes, used deliberately.

---

## A second auth pattern — service role + internal secret

Most routes use the cookie-based user client. But look at `app/api/push/send/route.ts` — it does something different:

```ts
const isInternalCall = internalSecret === process.env.INTERNAL_SECRET;
if (!isInternalCall) {
  const admin = await getAdminUser();
  if (!admin) return NextResponse.json({ error: "Forbidden" }, { status: 403 });
}
// then uses a SERVICE ROLE client that bypasses RLS
const db = createServiceRoleClient();
```

Two things to learn here:

1. **Dual auth:** this endpoint can be called either by a human admin (cookie session) *or* by our own backend/cron (a shared `INTERNAL_SECRET` header). That's how internal service-to-service calls authenticate when there's no user — a shared secret, not a cookie.
2. **Service-role client:** this client uses the `SUPABASE_SERVICE_ROLE_KEY`, which **bypasses Row Level Security entirely.** It can read *anyone's* push subscriptions. That's necessary here (sending a notification to user B on behalf of user A's message) but it's a loaded gun — it must *never* be reachable by an unauthenticated caller, which is exactly why the secret/admin gate sits in front of it. (We unpack RLS and why this is dangerous in article 06.)

---

## The interview angle

- *"Walk me through one of your API endpoints."* → "Every route follows auth → rate-limit → validate → work. Auth first because the rate-limit key is per-user and there's no point processing a request I'll reject. Rate-limit on Redis with a fixed window guards the DB. Then I validate and sanitize, then query, then return JSON with a meaningful status code."
- *"`getUser` vs `getSession`?"* → "`getUser` hits the auth server to verify the token — secure, but a network call. `getSession` reads the cookie locally — fast, but trusts the cookie. I use `getUser` for mutations; for read-only routes `getSession` would cut latency."
- *"401 vs 403?"* → "401 is 'who are you', 403 is 'I know you and no'."
- *"How do you protect a privileged internal endpoint?"* → "Shared-secret header for service-to-service, admin session for humans, and a service-role DB client that bypasses RLS only behind that gate."

---

## Concept checklist

- [ ] I can write a Route Handler from scratch — read params, return `NextResponse.json` with a status.
- [ ] I can recite the auth → rate-limit → validate → work pipeline and *justify the ordering*.
- [ ] I can explain `getUser()` vs `getSession()` and the per-route tradeoff.
- [ ] I can explain fixed-window rate limiting and its boundary-burst weakness.
- [ ] I understand sanitize (storage safety) vs validate (reject) vs React's auto-escaping (display safety).
- [ ] I can explain 401 vs 403, and when we return each.
- [ ] I can explain the service-role client + internal-secret pattern and why it's dangerous if exposed.

Next up: **[06 — Supabase fundamentals](./06-supabase-fundamentals.md)** — RLS, the two clients, and why cookies are the whole trick.
