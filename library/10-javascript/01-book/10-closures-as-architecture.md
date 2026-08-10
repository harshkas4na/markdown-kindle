# 10 — Closures in the wild: state without classes

Article 02 introduced the closure as a concept. This article is the payoff: closures aren't a trivia answer, they're how our app *holds real application state*. The WebSocket connection, the rate-limiter cache, the face-detector singleton — none of them are classes. They're all closures over module-level variables. Once you see this pattern, you see it everywhere.

The mental model:

**A closure is private, persistent state attached to functions. So any time you want "one shared thing that survives across calls, that only these specific functions can touch" — a cache, a connection, a counter, a singleton — a closure over module-scoped variables *is* the design. Classes are one way to bundle state and behavior; closures are the other, and JS leans on closures hard.**

---

## The module-as-closure insight

Here's the unlock: **a module's top-level variables are private state, and its exported functions are closures over them.** When you write:

```ts
// lib/rate-limit.ts
const limiters = new Map<string, Ratelimit>();   // ← private state, created ONCE at import

function getLimiter(config) {
  let limiter = limiters.get(key);               // ← closes over `limiters`
  if (!limiter) { limiter = new Ratelimit(...); limiters.set(key, limiter); }
  return limiter;
}
```

`limiters` is created exactly once (modules run once — article 11), and `getLimiter` closes over it. Nothing outside this file can reach `limiters` — it's not exported. That's **encapsulation through module scope**: the `Map` is as private as a `#field` in a class, enforced not by a keyword but by "you can't reference what you can't name." This is the `makeCounter` pattern from article 02, just at file scale — `limiters` is the private `count`, `getLimiter` is `next`.

This is *memoization*: build the expensive thing once, cache it keyed by its config, hand back the cached one forever after. Same shape as the face detector's `initPromise` (article 08) — the only difference is what's cached (a Map of limiters vs a single promise).

---

## The singleton: one shared resource for the whole app

The WebSocket file (`lib/hooks/use-websocket.ts`) is the masterclass. The *entire connection* — the socket, its state, the reconnect bookkeeping — lives in module-level variables that the hook's functions close over:

```ts
// ===== module-level singleton state (private, created once) =====
let singletonWs: WebSocket | null = null;
let singletonConnected = false;
let reconnectAttempt = 0;
let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
let refCount = 0;                          // how many components want the connection
const handlers = new Set<MessageHandler>();
const messageQueue: object[] = [];
```

Why module scope and not React state or a class instance? **Because there must be exactly ONE socket no matter how many components use it.** If `useWebSocket` kept the socket in `useState`, every component that called the hook would open its own connection — 5 chat components, 5 sockets. By hoisting the socket to *module* scope, every call to `useWebSocket` — every component, every render — closes over the *same* `singletonWs`. One module, one socket, shared by all. That's the Singleton pattern, implemented with nothing but a module-level `let` and closures.

### Reference counting: closures managing a shared lifecycle

The slickest part is how it knows when to *close* the socket. Each component that mounts increments `refCount`; each unmount decrements it; when it hits zero, tear down:

```ts
useEffect(() => {
  refCount++;                          // I want the connection
  if (enabled) { singletonEnabled = true; if (!singletonWs) connect(); }

  return () => {                       // cleanup closure, runs on unmount
    refCount--;                        // I no longer need it
    if (refCount === 0) teardown();    // last one out turns off the lights
  };
}, [url, enabled]);
```

Both the effect body and its cleanup function are **closures over `refCount`** (and `singletonWs`, `connect`, `teardown`). They share that one counter across every component instance. This is the exact mechanism a connection pool or a subscription manager uses: a shared resource, kept alive while ≥1 consumer needs it, freed when the last one leaves. The closure is what lets independent components coordinate over one number.

### Closures capturing the *specific* socket

There's a subtle, correct closure detail inside `connect()`. Each connection attempt creates a local `ws` and the heartbeat closes over *that specific* `ws`:

```ts
const ws = new WebSocket(...);
singletonWs = ws;
function resetHeartbeat() {
  heartbeatTimer = setTimeout(() => {
    if (singletonWs === ws) ws.close();   // ← `ws` here is THIS attempt's socket
  }, HEARTBEAT_TIMEOUT_MS);
}
```

The `if (singletonWs === ws)` check is only possible *because* the timeout closure captured the local `ws`. If a reconnect already swapped `singletonWs` to a newer socket, this stale timer sees `singletonWs !== ws` and correctly does nothing — it won't kill the *new* connection. That's a closure used to pin a callback to the exact resource it was created for. Beautiful, and exactly the kind of bug (killing the wrong socket) that this guard prevents.

---

## The observer/pub-sub pattern (also closures)

The `handlers` Set + `subscribe` function is the **observer pattern**, again built on a closure:

```ts
const handlers = new Set<MessageHandler>();        // private registry

const subscribe = useCallback((handler) => {
  handlers.add(handler);
  return () => { handlers.delete(handler); };       // unsubscribe closure
}, []);

// when a message arrives:
for (const handler of handlers) handler(msg);        // notify all subscribers
```

`subscribe` returns an *unsubscribe* function — a closure that remembers *which* handler to remove. This is the universal event-emitter shape (and it's exactly what `addEventListener`/`removeEventListener` and React's effect cleanup do). Returning a cleanup closure from a setup function is one of the most important idioms in all of JS — you'll see it in every `useEffect`, every subscription, every listener.

---

## The pattern, generalized

Every one of these is the same recipe:

```ts
// 1. private state at module scope (or inside a factory function)
const state = /* Map | Set | let | a connection */;

// 2. functions that close over it
export function use(...) { /* reads/writes `state` */ }

// 3. (optional) return a cleanup closure that knows what to undo
```

When you reach for this vs a class: **closures shine for singletons, factories, memoizers, and "setup returns teardown" APIs** — anywhere the state is private and the surface is a few functions. Classes shine when you need *many* instances each with their own state (like the `MinHeap`, article 04). Our app uses both, correctly: `MinHeap` is a class (many heaps), the WebSocket is a closure-singleton (one socket).

---

## The interview angle

- *"Give a real use for closures."* → "Private persistent state without a class. My rate-limiter closes over a module-level `Map` to memoize limiter instances; my WebSocket hook keeps the single socket and a refcount in module scope, and every component closes over the same ones — that's how I guarantee one shared connection."
- *"How do you implement a singleton in JS?"* → "Put the instance in module scope and export functions that close over it. Modules run once, so the variable is created once; every importer shares it. No class needed."
- *"What's the pattern of returning a function from a function?"* → "A closure that captures setup so it can tear down — unsubscribe, clearTimeout, removeEventListener. My `subscribe` adds a handler to a Set and returns a closure that deletes that exact handler. It's the basis of every `useEffect` cleanup."
- *"Closure or class?"* → "Closure for singletons/factories/memoizers where state is private and the API is a few functions. Class for many instances each holding their own state. My heap is a class; my socket is a closure-singleton."

---

## Concept checklist

- [ ] I can explain "a module's top-level vars are private state; its exports are closures over them."
- [ ] I can explain why the WebSocket must be module-scoped, not in `useState`.
- [ ] I can explain reference counting and how the cleanup closure shares `refCount`.
- [ ] I can explain the `if (singletonWs === ws)` guard as a closure pinning a callback to its socket.
- [ ] I can explain the observer pattern (`handlers` Set + unsubscribe closure).
- [ ] I can explain "return a cleanup closure" and where it shows up (every `useEffect`).
- [ ] I can decide closure-singleton vs class for a given problem.

Next up: **[11 — Modules, the runtime & `globalThis`](./11-modules-and-runtime.md)** — why modules run once, and the server/browser split.
