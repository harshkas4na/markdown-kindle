# 12 — Security & PWA

The final layer. By now I understand how the app renders, fetches, authenticates, and runs its algorithms. This article is about the stuff that wraps all of it: keeping it safe, and making it feel like a real installable app on a phone. Then a closing scorecard.

The mental model for security:

**Security isn't one feature — it's a set of independent walls, arranged so that if one fails the next still holds. The goal isn't "unbreakable"; it's "no single mistake is fatal." That's defense in depth, and I want to be able to point at each wall in my own app.**

---

## Our walls (defense in depth, from outside in)

```
1. HTTP security headers / CSP   ← browser-enforced (next.config.ts)
2. Auth (OAuth + session cookie) ← who are you (article 07)
3. Rate limiting                 ← stop abuse before the DB (article 05)
4. Input validation / sanitize   ← reject/clean bad data (article 05)
5. RLS in Postgres               ← the REAL data boundary (article 06)
```

If someone bypasses the page guard (wall 2), RLS (wall 5) still won't hand over another user's rows. If they craft a malicious payload, sanitize (wall 4) + React's escaping neutralize it. No single failure is fatal. Let me go deep on the one we haven't covered: the headers.

---

## Wall 1 — security headers & CSP (`next.config.ts`)

Our `headers()` config sets a serious set of HTTP headers on every response. Each one closes a specific attack class — and being able to name the attack is the interview win:

| Header | Value | Attack it stops |
|---|---|---|
| `X-Frame-Options` | `DENY` | **Clickjacking** — nobody can iframe our site and trick clicks |
| `X-Content-Type-Options` | `nosniff` | **MIME sniffing** — browser won't guess a `.txt` is JS and run it |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | **Referrer leakage** — don't send full URLs (with params) to other sites |
| `Permissions-Policy` | `camera=(self), microphone=(), geolocation=()` | **Feature abuse** — only we can use the camera; mic/geo off entirely |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | **Protocol downgrade** — force HTTPS for 2 years (production only) |
| `Content-Security-Policy` | (big) | **XSS** — the heavy hitter |

### CSP — the big one

Content Security Policy is a browser-enforced allowlist of *where resources may come from*. Our policy says things like:

```
default-src 'self'                          ← by default, only load from our own origin
script-src 'self' 'unsafe-inline' https://analytics.ahrefs.com https://cdn.jsdelivr.net
connect-src 'self' https://*.supabase.co wss://*.supabase.co
            https://metrodiaries-ws.onrender.com wss://...  ← exactly our backends
img-src 'self' data: blob: https://*.supabase.co https://*.googleusercontent.com
frame-ancestors 'none'                      ← nobody can frame us (belt + suspenders with X-Frame-Options)
```

The point of CSP: even if an attacker *did* inject a `<script>` (an XSS), the browser would refuse to run it unless its source is on the allowlist — and refuse to let it phone home to an attacker server, because `connect-src` only permits our own backends. **CSP turns "XSS = game over" into "XSS = mostly contained."**

Two honest notes worth understanding (and great interview nuance):
- **`'unsafe-inline'` in `script-src`** weakens the policy — it's there because Next.js and our inline JSON-LD need it. The stricter alternative is nonce-based CSP, which is more work. Knowing *why* the compromise exists and what the stronger option is = senior.
- Notice every backend we talk to (Supabase, the WS server, the analytics script) is *explicitly* listed in `connect-src`. The CSP is a precise map of "who this app is allowed to talk to." If you add a new API, you add it here or the browser blocks it.

### The API cache header default

`next.config` also sets `Cache-Control: no-store` on all `/api/*` by default. This is a *security* choice as much as a perf one: personalized API responses must never be cached by a CDN/proxy and accidentally served to another user. Individual routes opt *into* caching deliberately (like `/api/discover`). Safe by default, fast by exception.

---

## Where the XSS escaping actually happens (don't get this wrong)

A point from article 05 worth re-stating because it's a common interview trap: **React auto-escapes any text you render in JSX.** So `{userBio}` renders `<script>` as literal text, not a tag. That's our primary XSS defense, *for free*. The danger is only when you *bypass* it:

- `dangerouslySetInnerHTML` — we use it for the JSON-LD `<script>` in the root layout, but that's *our own* trusted data, never user input. That's the rule: `dangerouslySetInnerHTML` only with data you generated, never with user content.
- Our `sanitizeText` cleans for *storage* safety (null bytes, length), not display — because React already handles display.

So the XSS story is: **React escapes display + CSP contains anything that slips through + sanitize keeps storage clean.** Three layers again.

---

## The PWA layer — making it a real app

A **PWA (Progressive Web App)** is a website that can be installed to the home screen, work offline-ish, and receive push notifications — i.e. feel native without app stores. The mental model:

**The whole PWA trick is the *service worker* — a script the browser runs in the background, separate from any page, that can intercept network requests and receive push events even when the site is closed.**

### The pieces we have

| Piece | File | Job |
|---|---|---|
| Service worker registration | `components/ServiceWorkerRegister.tsx` | registers `/sw.js` on load |
| The service worker | `public/sw.js` | background script: caching, push handling |
| Manifest | `public/manifest.json` | name, icons, theme color → makes it "installable" |
| Install prompt | `components/InstallPrompt.tsx` | the "Add to Home Screen" UX |
| Push subscribe/send | `app/api/push/*` | Web Push subscriptions + sending |

The registration is dead simple and correctly defensive:

```tsx
useEffect(() => {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js").catch((err) => console.warn("[SW]", err));
}, []);
```

Two correct instincts: the `"serviceWorker" in navigator` feature-check (graceful degradation on browsers that don't support it), and the `typeof window` guard (this is a Client Component, but the check makes the intent explicit). Notice in `next.config` the `/sw.js` route is served with `no-cache` headers — you *never* want a stale service worker cached, or users get stuck on an old version.

### Web Push — how a notification reaches a closed app

This is genuinely clever and worth understanding end to end (`app/api/push/send/route.ts` + `web-push`):

1. The browser subscribes to push and gets a **subscription object** (an endpoint URL at the browser vendor's push service + encryption keys). We store it in `push_subscriptions`.
2. To notify a user, our server uses the **VAPID** keys to sign a message and POSTs it to that endpoint.
3. The browser vendor's push service delivers it to the user's device, which wakes our **service worker**, which shows the notification — *even if the site is closed.*

Two security details we got right:
- The send endpoint uses the **service-role client** (bypasses RLS — it must, to send to other users) but is gated behind an admin session *or* an `INTERNAL_SECRET` header (article 05). The dangerous capability is locked behind a wall.
- **VAPID** keys authenticate *us* to the push service so randoms can't send notifications through our identity.

---

## The final "production-grade" scorecard

Bringing it all together — honest, not flattering:

| Dimension | Grade | What's there / missing |
|---|---|---|
| Auth & sessions | ✅ A | OAuth, cookie sessions, (need middleware) |
| Authorization | ✅ A | RLS + guards, defense in depth |
| Security headers / CSP | ✅ A | thorough; could go nonce-based CSP |
| Rate limiting | ✅ A− | per-user-per-action, fixed window |
| Input handling | ✅ A− | validate + sanitize + React escaping |
| XSS surface | ✅ A− | escaping + CSP; one trusted `dangerouslySetInnerHTML` |
| PWA / offline / push | ✅ B+ | installable, push works, SW could cache more |
| First-paint performance | ⚠️ C | the waterfall (article 11) |
| Observability | ❌ D | only `console.log`; no metrics/tracing/error tracking |
| Tests | ❌ D | none configured (per CLAUDE.md) |

**The verdict:** this is a *security-mature, feature-rich* app with two real gaps before "production-grade" is honest — **first-paint performance** and **operability** (observability + tests). Which, neatly, is exactly the roadmap from the very first conversation: the perf fixes (middleware, server-render), and the systems work (a warm Go service, structured logging, metrics) that doubles as the skill-building project.

---

## The interview angle

- *"How do you think about web security?"* → "Defense in depth — independent walls so no single mistake is fatal. In my app: CSP and security headers at the browser, OAuth + sessions for authn, rate limiting and validation at the API, and RLS in Postgres as the real data boundary. Even if the page guard is bypassed, RLS still protects the data."
- *"What does CSP actually do?"* → "It's a browser-enforced allowlist of where resources can load from and where the page can connect. It contains XSS — even an injected script can't run from a disallowed source or exfiltrate to an attacker server, because `connect-src` only lists my own backends."
- *"How does a push notification reach a closed app?"* → "A service worker — a background script. The browser subscribes and gives me an endpoint; my server signs a message with VAPID keys and posts it to the push service, which wakes the service worker to display it. The send capability uses a service-role DB client, gated behind admin/secret auth."

---

## Concept checklist

- [ ] I can name our 5 security walls and explain how defense-in-depth survives one failing.
- [ ] I can explain each security header and the specific attack it stops.
- [ ] I can explain CSP, why `connect-src` is a map of our backends, and the `'unsafe-inline'` tradeoff.
- [ ] I can explain exactly where XSS escaping happens (React) and where the danger is (`dangerouslySetInnerHTML`).
- [ ] I can explain what a service worker is and why it enables push + offline.
- [ ] I can explain the Web Push + VAPID flow end to end.
- [ ] I can give an honest production-grade scorecard of the app and name the two real gaps.

---

## 🎓 You finished the course

That's all twelve. If I can tick every checklist box across these articles — out loud, to another person — I understand both Next.js *and* my own app at a level I can defend in any interview. The natural next move is to **start applying the article-11 fix order**, turning this reading into shipped commits. The textbook becomes the changelog.
