# 07 — Auth deep dive

Auth feels like magic until you trace it once, end to end. So that's what this article is: follow one user from "clicks a protected link while logged out" all the way to "sees their dashboard," touching every file involved. Then I'll write the `middleware.ts` we keep saying we need.

The mental model:

**Auth is just answering two questions on every request — "who are you?" (authentication) and "are you allowed?" (authorization) — and then *remembering the answer* in a cookie so we don't re-ask on every click.**

The remembering-in-a-cookie part is the session. Everything else is plumbing around it.

---

## The cast of characters

| File | Role |
|---|---|
| `app/(app)/layout.tsx` | the client-side guard — kicks off OAuth, redirects to onboarding |
| `app/auth/callback/route.ts` | the OAuth landing strip — exchanges the code for a session |
| `lib/auth-context.tsx` | global auth state (`user`, `profile`) via React Context |
| `lib/supabase/client.ts` / `server.ts` | the two clients from article 06 |
| `middleware.ts` | **doesn't exist yet** — we'll build it |

---

## The full OAuth flow, step by step

Here's what happens when a logged-out user hits `/dashboard`:

```
1. User visits /dashboard
2. app/(app)/layout.tsx mounts, useAuth() says user === null
3. The guard effect fires:
      supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: ".../auth/callback?next=/dashboard" }
      })
   → browser is sent to Google's consent screen
4. User picks their Google account, approves
5. Google redirects back to: /auth/callback?code=XXXX&next=/dashboard
6. app/auth/callback/route.ts runs ON THE SERVER:
      await supabase.auth.exchangeCodeForSession(code)
   → this sets the session COOKIE
7. Same route checks: does this user have a completed profile?
      - no profile / not onboarded → redirect to /onboarding
      - otherwise → redirect to `next` (/dashboard)
8. Browser lands on /dashboard, now WITH a session cookie
9. AuthProvider's onAuthStateChange fires INITIAL_SESSION → user is set → app renders
```

Let me zoom into the two interesting files.

### `app/auth/callback/route.ts` — where the code becomes a session

This is a Route Handler (server-side), and it does the critical exchange:

```ts
const code = searchParams.get("code");
const next = searchParams.get("next") ?? "/dashboard";

if (code) {
  const supabase = await createClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);  // ← THE moment
  if (!error) {
    const { data: { user } } = await supabase.auth.getUser();
    const { data: profile } = await supabase
      .from("profiles").select("onboarding_completed").eq("id", user.id).single();

    if (!profile || !profile.onboarding_completed) {
      return NextResponse.redirect(`${origin}/onboarding`);   // first-timer
    }
  }
  return NextResponse.redirect(`${origin}${next}`);           // returning user
}
return NextResponse.redirect(`${origin}/?error=auth`);
```

This is the **OAuth Authorization Code flow with PKCE**. The `code` from Google is a one-time token. `exchangeCodeForSession` trades it (server-to-server with Supabase) for a real session and writes that session into the cookie. Two things to appreciate:

1. **It happens on the server** (a Route Handler), which is exactly *why* it can set the session cookie — remember from article 06 that Server Components can't set cookies but Route Handlers can. The callback being a `route.ts` is not an accident.
2. **The `next` param** is how we preserve "where the user was trying to go." We stuffed it into `redirectTo` back in step 3, Google echoed it through, and now we honor it. That's why logging in from a deep link sends you back to that deep link.

### `lib/auth-context.tsx` — the global "who are you" state

Once the cookie exists, the whole app needs to *know* about the user reactively. That's `AuthProvider`, a Client Component that wraps the app (mounted in the root layout). Its engine is one subscription:

```ts
supabase.auth.onAuthStateChange((event, session) => {
  setUser(session?.user ?? null);
  setLoading(false);
  if (event === "INITIAL_SESSION" || event === "SIGNED_IN") {
    fetchProfile();    // load /api/profile
  }
});
```

There's real, hard-won wisdom encoded here in the comments, and it's worth internalizing because these are the exact bugs everyone hits:

- **Why `onAuthStateChange` and not `getSession()` on mount?** The comment explains: `getSession()` can return `null` before the browser client has hydrated the server-set cookies — a race condition. `onAuthStateChange` fires an `INITIAL_SESSION` event *with the correct state* once it's read the cookies. So subscribing is more reliable than asking once.
- **Why the `if (event === ...)` guard around `fetchProfile`?** Because `TOKEN_REFRESHED` fires *every time the tab regains focus* (Supabase auto-refreshes). If we re-fetched the profile on every refresh, the UI would flash/reload on every tab switch. So we only fetch the profile on genuine sign-in or first load. This is a beautiful example of "the bug taught us the code."
- **The `hasLoadedProfile` ref** ensures the loading spinner only shows on the *first* profile fetch; later refreshes update silently in the background.

So `AuthProvider` exposes `{ user, profile, loading, profileLoading, refreshProfile, signOut }` to the whole tree via `useAuth()`. Every data hook (article 04) reads `user` from here to decide whether to fetch.

### The guard — `app/(app)/layout.tsx`

The actual "are you allowed here" decision currently lives client-side:

```ts
if (loading) return;                          // still figuring out who you are
if (!user) { signInWithOAuth(...); return; }  // not logged in → OAuth
if (profileLoading) return;
if (!profile || !profile.onboarding_completed) router.replace("/onboarding");
```

It's *correct* — but it runs **in the browser, after the bundle loads**, which is the waterfall from article 03. A logged-out user still downloads the whole app JS before being told "go log in." That's the thing middleware fixes.

---

## Authentication vs Authorization (don't blur them)

- **Authentication** = *who are you.* Handled by the OAuth flow + the session cookie. Answered by `getUser()`.
- **Authorization** = *what are you allowed to do.* Handled in **two** places in our app:
  1. The route guard / middleware (can you even see this page).
  2. **RLS in the database** (article 06) — can you read/write these specific rows.

This is defense in depth: even if someone bypassed the page guard, RLS still won't let them read another user's data. Two independent layers. (Interview: always mention that page-level guards are UX, and the *real* authorization boundary is at the data layer.)

---

## Now let's write the `middleware.ts` we keep promising

`middleware.ts` lives at the project root and runs **on the server (the edge), before the request reaches any page** — for every URL matched by its `config.matcher`. It's the perfect place for auth because it runs *before* a single byte of page HTML is generated.

It does two jobs for us:
1. **Refresh the Supabase session cookie** (remember article 06: the server client's `setAll` was *relying* on middleware to do this).
2. **Redirect logged-out users away from protected routes** before they download the app.

```ts
// middleware.ts
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll(); },
        setAll(cookiesToSet) {
          // write refreshed cookies onto BOTH request and response
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options));
        },
      },
    }
  );

  // IMPORTANT: this call refreshes the token if needed and writes the new cookie
  const { data: { user } } = await supabase.auth.getUser();

  // Gate protected routes at the edge — no client waterfall
  const isProtected = request.nextUrl.pathname.startsWith("/dashboard")
    || request.nextUrl.pathname.startsWith("/search")
    || request.nextUrl.pathname.startsWith("/messages")
    /* ...the rest of (app)/* ... */;

  if (!user && isProtected) {
    const url = request.nextUrl.clone();
    url.pathname = "/";              // or kick straight into OAuth
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  // run on app pages but skip static assets and the OAuth callback
  matcher: ["/((?!_next/static|_next/image|favicon.ico|auth/callback|api).*)"],
};
```

What this buys us (the payoff of the whole course so far):
- Logged-out users are redirected **before** downloading the app bundle — the waterfall's first leg disappears.
- The session cookie is refreshed at the edge, so the `try/catch` in `lib/supabase/server.ts` (article 06) is finally backed by the middleware it assumed existed.
- The client guard in `(app)/layout.tsx` can be slimmed to just the onboarding check, because "are you logged in" is now decided upstream.

One caution worth knowing for interviews: middleware runs on *every* matched request, so keep it lean — one `getUser()` and cheap logic. Don't do heavy DB work there.

---

## The interview angle

- *"Walk me through your auth flow."* → "OAuth code flow: the client kicks off `signInWithOAuth` with a `redirectTo`, Google sends a code back to a server-side callback route, which exchanges it for a session cookie and routes the user to onboarding or their destination. A React context subscribes to `onAuthStateChange` to expose the user app-wide."
- *"How does auth survive a refresh?"* → "It's in a cookie. On load, `onAuthStateChange` fires `INITIAL_SESSION` with the session read from cookies — I use that instead of `getSession()` to avoid a hydration race. Middleware refreshes the token at the edge."
- *"Where do you enforce authorization?"* → "Two layers: middleware/guard for page access (UX), and RLS in the database for data access (the real boundary). Defense in depth."
- *"Why middleware for auth?"* → "It runs on the edge before the page renders, so I can redirect unauthenticated users before they download the app, and refresh the session cookie — which Server Components can't do themselves."

---

## Concept checklist

- [ ] I can narrate the full OAuth flow from protected-link-click to dashboard, naming each file.
- [ ] I can explain why the callback is a Route Handler (cookie-setting) and what `exchangeCodeForSession` does.
- [ ] I can explain why `AuthProvider` uses `onAuthStateChange` over `getSession()`, and why it guards `fetchProfile`.
- [ ] I can clearly separate authentication vs authorization and name where each lives in our app.
- [ ] I can write a `middleware.ts` that refreshes the session and gates protected routes.
- [ ] I understand how middleware closes the loop on the `server.ts` cookie `try/catch` from article 06.

Next up: **[08 — Real-time & chat architecture](./08-realtime-and-chat.md)** — the singleton WebSocket, Supabase Realtime, and optimistic chat.
