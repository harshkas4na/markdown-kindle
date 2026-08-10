# 08 — Promises & async/await

Now that I understand the event loop (article 07), promises stop being magic. A promise is just an object that represents a value that isn't ready yet, plus a way to register callbacks the *microtask queue* will run when it is. `async/await` is a thin, beautiful layer of syntax over that. Our entire data layer — every `fetch`, the face detector, the WS auth — runs on this.

The mental model:

**A promise is a placeholder for a future value, and a tiny state machine. It starts `pending`, then settles exactly once — either `fulfilled` (with a value) or `rejected` (with an error) — and never changes again. `.then`/`.catch` register what to do when it settles; `await` is syntax that lets you write that as if it were synchronous, while the event loop handles the actual waiting.**

---

## A promise is a 3-state machine

```
            ┌─────────────┐
            │   pending   │   (not settled yet)
            └──────┬──────┘
        resolve()  │  reject()
        ┌──────────┴──────────┐
        ▼                     ▼
  ┌───────────┐         ┌───────────┐
  │ fulfilled │         │ rejected  │   ← settled, FROZEN forever
  │  (value)  │         │  (reason) │
  └───────────┘         └───────────┘
```

Two unbreakable rules: it settles **once** (a second `resolve`/`reject` is ignored), and once settled it's **immutable**. That's what makes promises safe to pass around and `await` in multiple places — the answer can't change underneath you.

`.then(onFulfilled, onRejected)`, `.catch(onRejected)`, and `.finally(onSettled)` register callbacks. When the promise settles, those callbacks are scheduled as **microtasks** (article 07 — that's why a resolved promise's `.then` beats a `setTimeout(0)`).

---

## `await` is `.then` wearing better clothes

These two are the *same thing*:

```ts
// promise chain
function load() {
  return fetch("/api/saved-routes")
    .then(res => res.json())
    .then(data => data.map(toDisplay))
    .catch(() => []);
}

// async/await — identical behavior, linear shape
async function load() {
  try {
    const res = await fetch("/api/saved-routes");
    const data = await res.json();
    return data.map(toDisplay);
  } catch {
    return [];
  }
}
```

That second version *is* our `getSavedRoutes` in `lib/saved-routes.ts`. Two things to internalize about `await`:

1. **`await` pauses the function, not the thread.** When you hit `await fetch(...)`, the function suspends and *returns control to the event loop* — the rest of the app keeps running. When the promise settles, the function's continuation is scheduled as a microtask and picks up where it left off. So `await` is non-blocking despite *looking* blocking. This is the article-07 event loop cashing out: `await` = "schedule the rest of me as a microtask when this settles."
2. **`async` functions always return a promise.** `return data.map(...)` inside an `async` function doesn't return the array — it returns a promise that *fulfills* with the array. `throw` inside one returns a *rejected* promise. That's why callers must `await` (or `.then`) the result.

---

## `try/catch` is how you handle rejection with `await`

With `.then` chains, errors go to `.catch`. With `await`, a rejected promise **throws** at the `await` line — so you catch it with a normal `try/catch`. Our `saved-routes.ts` does exactly this, and the pattern is worth memorizing as the "safe fetch":

```ts
export async function getSavedRoutes(): Promise<SavedRouteDisplay[]> {
  try {
    const res = await fetch("/api/saved-routes");
    if (!res.ok) return [];          // ← important: see below
    const data: SavedRoute[] = await res.json();
    return data.map(toDisplay);
  } catch {
    return [];                       // network error → safe empty fallback
  }
}
```

The senior detail hidden in there: **`fetch` only rejects on *network* failure, not on HTTP errors.** A 404 or 500 still *fulfills* the promise — `res.ok` is just `false`. So you need *both* the `if (!res.ok)` check *and* the `try/catch`: one for "the server answered with an error," the other for "we never reached the server." Missing the `res.ok` check is one of the most common real bugs in fetch code. Our `saveRoute`/`removeRoute` follow the same shape — `if (!res.ok) return null`, `catch { return null }` — degrading gracefully instead of throwing into the UI.

---

## Creating a promise from scratch: wrapping a callback API

You rarely write `new Promise` — *except* to wrap an old callback/event-based API so you can `await` it. `lib/face-detection.ts` does this beautifully, turning the image `onload` event into something awaitable:

```ts
const img = new Image();
await new Promise<void>((resolve, reject) => {
  img.onload = () => resolve();                       // success path
  img.onerror = () => reject(new Error("Failed to load image"));  // failure path
  img.src = url;                                       // trigger the load
});
// ...only runs after the image has actually loaded
```

This is *the* `new Promise` pattern: the **executor** function gets `resolve` and `reject`, and you wire them into the callback API's success/failure hooks. `img.onload` fires → `resolve()` → the `await` continues. `img.onerror` fires → `reject()` → the `await` throws. You've converted an event-driven API into a linear `await`. (Note `img.src = url` comes *last* — set the handlers before triggering the load, or you could miss a cached image that loads instantly.)

This is the bridge between the two async styles: callbacks/events (the old world, still how DOM and WebSocket work) and promises (the world you actually want to write in). `new Promise` is the adapter.

---

## Promise memoization: caching the promise itself (a gem)

`face-detection.ts` has a genuinely advanced move worth slowing down on:

```ts
let detector: FaceDetector | null = null;
let initPromise: Promise<FaceDetector> | null = null;

async function getDetector(): Promise<FaceDetector> {
  if (detector) return detector;          // already built
  if (initPromise) return initPromise;    // ← build in progress: return the SAME promise

  initPromise = (async () => { /* expensive: load WASM + model */ })();
  return initPromise;
}
```

The clever line is `if (initPromise) return initPromise`. The detector takes ~1MB of WASM and a model download to build. Without this, if two parts of the app call `getDetector()` nearly at once, you'd kick off *two* expensive loads. By **caching the promise itself** (not just the resolved value), the second caller gets handed the *in-flight* promise and `await`s the same single load. One promise, many awaiters — because a settled promise is immutable, they all get the same result safely.

There's even correct error recovery: in the `catch`, it resets `initPromise = null` so a *failed* load doesn't get cached forever — the next call retries. That "cache the success, not the failure" detail is exactly the kind of thing that separates a robust async cache from a naive one. (This same shape — memoize the promise — comes back in article 09 as request deduplication.)

---

## The interview angle

- *"What is a promise?"* → "An object representing a future value and a small state machine — pending, then settled once as fulfilled or rejected, immutable after. `.then` registers callbacks that run as microtasks when it settles."
- *"How does `await` relate to `.then`?"* → "It's syntax over it. `await p` suspends the async function and schedules its continuation as a microtask when `p` settles — same mechanism as `.then`, but written linearly. It pauses the function, not the thread."
- *"Does `fetch` reject on a 404?"* → "No — only on network failure. A 404 or 500 still fulfills; you check `res.ok`. So robust fetch needs both an `res.ok` check and a `try/catch`. That's exactly what my `getSavedRoutes` does, falling back to an empty array."
- *"When do you write `new Promise`?"* → "To wrap a callback or event API so it's awaitable — like turning `img.onload`/`onerror` into a promise. The executor gets `resolve`/`reject`; you wire them to the success/failure callbacks."
- *"How would you avoid doing an expensive init twice?"* → "Memoize the promise, not just the value. Store the in-flight promise; concurrent callers await the same one. And null it out on failure so errors aren't cached — which is what my face detector does."

---

## Concept checklist

- [ ] I can draw the promise state machine and say "settles once, then immutable."
- [ ] I can rewrite a `.then` chain as `async/await` and explain they're equivalent.
- [ ] I can explain that `await` pauses the function (via microtask), not the thread.
- [ ] I know `async` functions always return a promise; `throw` → rejected promise.
- [ ] I can explain why `fetch` needs both `res.ok` and `try/catch`.
- [ ] I can write the `new Promise` wrapper around `img.onload`/`onerror`.
- [ ] I can explain promise memoization and why you reset it on failure.

Next up: **[09 — Async concurrency & cancellation](./09-async-concurrency.md)** — running things in parallel, racing, and cancelling.
