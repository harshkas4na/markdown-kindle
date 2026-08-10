# 09 — Async concurrency & cancellation

Article 08 was one promise at a time. Real apps juggle *many* async things at once — fetch two queries together, send 50 push notifications, cancel a search that's now stale. This article is the advanced async toolkit, and it's where "I know `async/await`" becomes "I know *concurrency*." All of these are in our codebase.

The mental model:

**`await` in a straight line is sequential — each one waits for the last. That's often accidental slowness. The skill is recognizing when async tasks are *independent* and firing them together with the `Promise` combinators, while knowing which combinator matches your failure tolerance. And the flip side: timing control — debounce, throttle, cancel — for when you have *too many* async tasks.**

---

## The sequential-await trap (the #1 perf bug)

```ts
// ❌ sequential — total time = A + B (they wait in line for no reason)
const a = await fetchA();
const b = await fetchB();

// ✅ parallel — total time = max(A, B) (they run together)
const [a, b] = await Promise.all([fetchA(), fetchB()]);
```

If `b` doesn't depend on `a`, the first version wastes time — it makes B wait for A to finish before it even *starts*. The fix is to kick both off (calling `fetchA()` starts it immediately — promises are eager), then `await` them together. **`await` in a loop is the same trap at scale:**
```ts
// ❌ each iteration waits for the last — N requests in series
for (const id of ids) { await sendTo(id); }

// ✅ all at once
await Promise.all(ids.map(id => sendTo(id)));
```

Spotting "these awaits are independent, why are they in series?" is exactly the article-07/Next.js-course *waterfall* lesson, now at the language level.

---

## The four combinators (know which to reach for)

| Combinator | Resolves when… | Rejects when… | Use for |
|---|---|---|---|
| `Promise.all` | **all** succeed | **any one** rejects (fail-fast) | independent things that must *all* work |
| `Promise.allSettled` | **all** settle (success or fail) | never — gives you a result array | "do as many as possible, report each" |
| `Promise.race` | the **first** settles (either way) | first settles as a reject | timeouts, "first to respond" |
| `Promise.any` | the **first** *success* | only if **all** reject | "any working source" / fallback |

The `all` vs `allSettled` choice is the one that actually matters in production, and our code picks each on purpose.

### `Promise.all` — when everything must succeed (`/api/conversations`)

```ts
const [recentMsgsResult, unreadMsgsResult] = await Promise.all([
  supabase.from("chat_messages").select(...).in("room_id", roomIds)...,   // query 1
  supabase.from("chat_messages").select(...).neq("sender_id", user.id)..., // query 2
]);
```

Two independent DB queries — last messages and unread counts. They don't depend on each other, so running them sequentially would double the latency for no reason. `Promise.all` fires both, waits for the slower one, and destructures both results. `all` is right here because if *either* query fails the whole conversations response is broken anyway — fail-fast is the correct behavior. This is the parallel-fetch fix from the perf article, shipped.

### `Promise.allSettled` — when partial success is fine (`/api/push/send`)

Sending push notifications to many devices is the textbook `allSettled` case:

```ts
const results = await Promise.allSettled(
  subscriptions.map(async (sub) => {
    try {
      await webpush.sendNotification({ endpoint: sub.endpoint, keys: {...} }, payload);
      return { success: true, id: sub.id };
    } catch (err) {
      // 404/410 → subscription expired, delete it
      if (statusCode === 404 || statusCode === 410) { await db.from("push_subscriptions")... }
    }
  })
);
```

Here `Promise.all` would be **wrong**: if one user's subscription is dead (a 410), `all` would reject the *entire* batch and the other 49 users wouldn't get their notification. `allSettled` says "try all of them, tell me how each went" — it never rejects, it returns an array of `{status: "fulfilled", value}` / `{status: "rejected", reason}`. That lets us deliver to everyone reachable *and* clean up the dead subscriptions individually. **The rule: `all` when failures should abort the batch, `allSettled` when each task is independent and partial success is a win.** Picking right here is a senior signal.

(Note the inner `.map(async sub => …)` returns an array of promises — `allSettled` consumes that array. And each task has its *own* `try/catch`, so a single failure is handled locally and never even reaches the rejected branch unless something truly unexpected happens.)

### `Promise.race` — timeouts

`race` settles with whoever finishes first. The canonical use is bolting a timeout onto a slow operation:
```ts
const result = await Promise.race([
  doSlowThing(),
  new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 5000)),
]);
```
Whichever wins — the real work or the 5-second timer — settles the race. If the timer wins, you get a rejection instead of hanging forever. (Our WS heartbeat from article 07 is the *event-based* cousin of this idea: a timer that fires if real activity doesn't beat it.)

---

## Cancellation: `AbortController`

Combinators run things; sometimes you need to *stop* one. `AbortController` is the standard way to cancel a `fetch` (and many other APIs):

```ts
const controller = new AbortController();
fetch(url, { signal: controller.signal });   // pass the signal
// later, to cancel:
controller.abort();   // the fetch rejects with an AbortError
```

The classic use is **stale search requests**: the user types fast, you fire a request per keystroke, and you want to cancel the in-flight one when a newer query arrives so a slow old response can't overwrite a fast new one (a race condition in the UI). Our admin autocomplete solves the same "too many requests" problem with the *other* tool — debounce — which for that case is even simpler:

---

## Timing control: debounce & throttle (implement these from memory)

When events fire too often (typing, scrolling, resizing), you don't want one async call per event. Two timing tools, and the difference is a guaranteed interview question:

- **Debounce** — "wait until the user *stops*." Reset a timer on every event; only act once it's been quiet for N ms. Great for search-as-you-type.
- **Throttle** — "at most once every N ms." Act immediately, then ignore events until the window passes. Great for scroll/resize.

Our `UserSearchAutocomplete` debounces search with the cleanest possible idiom — a `setTimeout` + cleanup:

```ts
useEffect(() => {
  // ... fetchSuggestions defined ...
  const debounceTimer = setTimeout(fetchSuggestions, 300);  // fire 300ms after the last keystroke
  return () => clearTimeout(debounceTimer);                  // each new keystroke cancels the previous timer
}, [query, selectedUser]);
```

This *is* debounce, expressed through React's effect cleanup: every time `query` changes, the effect re-runs — the cleanup `clearTimeout`s the previous pending fetch, and a fresh 300ms timer starts. Type 10 fast characters → 9 timers get cancelled, only the 10th (after you pause) actually fetches. One request instead of ten. The `setTimeout`/`clearTimeout` pairing (article 07's macrotask scheduling) *is* the debounce mechanism; React's cleanup just gives it a natural home.

The standalone version, worth being able to write cold:
```ts
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);                       // cancel the pending call
    timer = setTimeout(() => fn(...args), ms); // schedule a fresh one
  };
}
```
Notice it's a **closure** (article 02 + 10): `timer` is private state that survives between calls, remembered by the returned function. Debounce is closures + macrotask timers — two earlier articles meeting.

---

## The interview angle

- *"Run two independent async calls — sequential or parallel?"* → "Parallel with `Promise.all` — sequential `await`s make the second wait on the first for no reason. My conversations endpoint runs its two queries with `Promise.all`, so total time is the slower query, not the sum."
- *"`Promise.all` vs `allSettled`?"* → "`all` is fail-fast — one rejection rejects the whole thing — for when every task must succeed. `allSettled` never rejects; it reports each result, for independent tasks where partial success is fine. My push-send uses `allSettled` so one dead subscription doesn't block notifications to everyone else."
- *"How do you cancel a fetch?"* → "`AbortController` — pass its `signal` to `fetch`, call `abort()` to cancel; it rejects with an AbortError. Classic for cancelling stale search requests so a slow old response can't overwrite a newer one."
- *"Debounce vs throttle?"* → "Debounce waits for a pause — act once the events stop, like search-as-you-type. Throttle caps the rate — act at most once per interval, like scroll handlers. My autocomplete debounces with a `setTimeout` that the next keystroke clears."

---

## Concept checklist

- [ ] I can spot and fix the sequential-await / await-in-a-loop waterfall.
- [ ] I can explain all four combinators and when each fits.
- [ ] I can justify `Promise.all` in conversations and `allSettled` in push-send.
- [ ] I can explain `Promise.race` for timeouts.
- [ ] I can explain `AbortController` and the stale-search race it prevents.
- [ ] I can explain debounce vs throttle and read our `setTimeout`+cleanup as a debounce.
- [ ] I can write `debounce` from memory and explain its closure.

Next up: **[10 — Closures in the wild](./10-closures-as-architecture.md)** — Level 4: closures as real application architecture.
