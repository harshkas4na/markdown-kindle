# 06 — Supabase fundamentals

Everyone says "Supabase is a Firebase alternative" and that tells you nothing. Here's the definition I actually find useful:

**Supabase is just a Postgres database — a real, boring, powerful SQL database — wrapped in auto-generated APIs, with auth, file storage, and realtime bolted on, plus one killer feature (Row Level Security) that lets the *browser* talk to the database directly without it being a catastrophe.**

That last clause is the whole magic, and it's the thing I most need to understand, so let me build up to it.

---

## The five things Supabase gives us

We use all five:

1. **Postgres** — the actual database. `profiles`, `trips`, `connections`, `messages`, `chat_messages`, etc. Real tables, real foreign keys, real SQL.
2. **Auto-generated API** — every table is instantly queryable via the client SDK: `supabase.from("trips").select()`. No backend code needed to read a table.
3. **Auth** — Google OAuth, sessions, JWTs, all managed. (Article 07.)
4. **Realtime** — subscribe to table changes over a WebSocket and get pushed events. (We use this for notification badges.)
5. **Storage** — file buckets for profile pictures.

The "auto-generated API" is the part that feels like cheating at first. From the browser I can literally write:

```ts
const { data } = await supabase.from("trips").select("*");
```

…and get trips back. No `/api/trips` needed. Which raises the obvious terrifying question:

**If the browser can query the database directly, what stops me from running `supabase.from("profiles").select("*")` and stealing everyone's data?**

The answer is Row Level Security, and it's the most important Supabase concept there is.

---

## Row Level Security (RLS) — the heart of it

**RLS is a Postgres feature where you write rules, *in the database*, that decide which rows each user is allowed to see or change. The database itself enforces them on every query, no matter who's asking or how.**

The mental shift: in a traditional app, *your backend code* is the bouncer — it decides what data to return. With RLS, **the database is the bouncer.** Even if the request comes straight from the browser with the auto-generated API, Postgres silently filters every query through the rules.

A rule (policy) looks roughly like:

```sql
-- "You can only read your own profile"
CREATE POLICY "read own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

-- "You can only update a trip you created"
CREATE POLICY "update own trips" ON trips
  FOR UPDATE USING (auth.uid() = user_id);
```

`auth.uid()` is the magic function — it returns the id of the currently-authenticated user, pulled from the JWT in the request. So `USING (auth.uid() = id)` means "this row is only visible if its `id` equals the logged-in user's id." If I try to `select("*")` from `profiles`, Postgres returns *only my row* — not because my code filtered it, but because the database refused to hand over the rest.

Our CLAUDE.md says it plainly: *"All tables have Row Level Security (RLS) enabled."* That single fact is what makes it *safe* for our client components to ever touch Supabase directly. **RLS is the reason the anon key can be public.**

This is genuinely a top-tier interview topic. The crisp statement: *"RLS moves authorization from the application layer into the database, so it's enforced uniformly on every query path — your API, the auto-generated client, even a direct connection. The downside is your security logic lives in SQL policies you have to test carefully, and a missing policy fails open or closed depending on config."*

---

## The two keys (and why one is safe in the browser)

Supabase gives you two keys, and the difference is a security fundamental:

| Key | Where it lives | Respects RLS? | Power |
|---|---|---|---|
| **anon key** (`NEXT_PUBLIC_SUPABASE_ANON_KEY`) | public, shipped to browser | ✅ yes | only what RLS allows for that user |
| **service role key** (`SUPABASE_SERVICE_ROLE_KEY`) | server-only, secret | ❌ **bypasses RLS** | god mode — every row |

The `NEXT_PUBLIC_` prefix on the anon key literally means "this is bundled into the browser JS, anyone can read it" — and that's *fine*, because the anon key still has to obey RLS. It can't do anything a logged-in user couldn't do.

The **service role key** is the opposite — it ignores RLS completely. That's why you only ever saw it in server-only code: `app/api/cron/birthday/route.ts` and `app/api/push/send/route.ts` create a service-role client to do admin work (sending notifications to *other* users, reading all birthdays). If that key ever leaked to the browser, the entire database would be wide open. This is exactly why article 05's push endpoint guards the service-role client behind an admin/secret check.

**Rule of thumb burned in:** anon key = client OK. Service role = server only, behind a gate, never `NEXT_PUBLIC_`.

---

## The two clients — `server.ts` vs `client.ts`

This confused me until I realized: *both use the anon key.* The difference isn't the key — it's **how each one finds out who the user is**, because the server and the browser store the session in different places.

### `lib/supabase/client.ts` — the browser client

```ts
export function createClient() {
  return createBrowserClient(URL, ANON_KEY);
}
```

`createBrowserClient` knows how to read the session from the **browser's cookies/localStorage**. It's what client components and our hooks use. When you call `supabase.from(...)` here, it attaches your JWT automatically, and RLS does the rest.

### `lib/supabase/server.ts` — the server client

```ts
export async function createClient() {
  const cookieStore = await cookies();           // Next.js: read THIS request's cookies
  return createServerClient(URL, ANON_KEY, {
    cookies: {
      getAll() { return cookieStore.getAll(); },
      setAll(cookiesToSet) { /* write refreshed cookies back */ },
    },
  });
}
```

`createServerClient` can't reach into a browser — there's no browser on the server. So it reads the session from **the cookies on the incoming HTTP request** (via Next's `cookies()`). That's the whole reason this function is `async` and takes a `cookieStore`: it's wiring Supabase's session machinery into Next.js's request-scoped cookie store.

**This is the single most important Supabase-meets-Next.js concept:** the session lives in a cookie, the *browser* client reads it from the browser, the *server* client reads it from the incoming request's cookies. Same session, same anon key, two readers for two worlds (remember article 01's two worlds — this is them again).

```
        ┌──────────── the session (a JWT) ───────────┐
        │   stored in a cookie on the user's machine   │
        └──────────────────────────────────────────────┘
            ▲                                  ▲
   reads from browser                 reads from the request's
   (createBrowserClient)              cookies (createServerClient)
   used in: hooks,                    used in: Route Handlers,
   client components                  Server Components
```

### The `setAll` / `try-catch` detail

Notice `server.ts` has a `setAll` that writes cookies back, wrapped in a `try/catch` that silently ignores failures with the comment *"can be ignored if you have middleware refreshing sessions."* Here's the why: JWTs expire and need refreshing. When Supabase refreshes a token server-side, it needs to write the new cookie back to the response. But **Server Components can't set cookies** (they only render) — only Route Handlers and middleware can. So the `try/catch` swallows the "can't set cookie" error in the Server Component case, *relying on middleware to do the actual refresh.* 

And here's the kicker — **we don't have a `middleware.ts`** (flagged in article 03). So that refresh isn't happening at the edge the way this code assumes. This is one concrete reason adding middleware (article 07) isn't just a perf nicety — the Supabase SSR setup is literally written *expecting* it to exist.

---

## How a query actually flows (tying it together)

Let me trace `supabase.from("trips").select()` from a Route Handler, hitting every concept:

1. `createClient()` (server) reads the auth cookie from the request → has your JWT.
2. The SDK sends the query to Supabase's PostgREST API with your JWT attached.
3. Postgres receives it, runs `auth.uid()` from the JWT, and applies the RLS policies on `trips`.
4. You get back *only* the rows the policy allows (e.g. active, visible trips), enforced by the database — not by your code.
5. The result comes back as typed JSON.

The thing I want to never forget: **your `.eq()` and `.neq()` filters in the query are for *correctness*, not *security*. RLS is the security.** If you forget a `.eq("user_id", user.id)`, a *correct* RLS policy still protects you. That's defense in depth.

---

## The interview angle

- *"How can Supabase let the browser query the database safely?"* → "Row Level Security. Authorization rules live in Postgres and are enforced on every query via `auth.uid()` from the JWT. The public anon key can only ever do what RLS permits."
- *"What's the difference between the anon and service-role keys?"* → "Anon respects RLS and is safe to ship to the browser; service-role bypasses RLS and must stay server-side behind an auth gate."
- *"Why two Supabase clients in a Next.js app?"* → "The session is in a cookie. The browser client reads it from the browser; the server client reads it from the incoming request's cookies — because there's no browser on the server. Same session, two readers."
- *"What's RLS's downside?"* → "Security logic moves into SQL policies you must test, and forgetting a policy can expose data — so I treat query filters as correctness and RLS as the real boundary, defense in depth."

---

## Concept checklist

- [ ] I can explain RLS as "the database is the bouncer" and write a basic `USING (auth.uid() = ...)` policy.
- [ ] I can explain why the public anon key is safe and the service-role key is not.
- [ ] I can name which of our routes use the service-role client and why they're gated.
- [ ] I can explain why there are two clients and that the *cookie* is what differs, not the key.
- [ ] I understand the `setAll` try/catch and how it depends on middleware we don't have yet.
- [ ] I can trace a query through JWT → `auth.uid()` → RLS → filtered rows.

Next up: **[07 — Auth deep dive](./07-auth-deep-dive.md)** — the OAuth dance, `AuthProvider`, the guard, and finally writing that middleware.
