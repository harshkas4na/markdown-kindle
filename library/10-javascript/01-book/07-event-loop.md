# 07 — The event loop & the two queues

Level 3, and the most important article in the course. Everything async in JavaScript — every `await`, every `setTimeout`, every `fetch`, every WebSocket callback in our app — is governed by one mechanism: the event loop. If I understand this diagram cold, *nothing* about async surprises me again. This is the single most-asked senior interview topic.

The mental model:

**JavaScript runs on ONE thread — it can only do one thing at a time. So how does it handle network requests, timers, and clicks without freezing? It doesn't do the waiting itself. It hands slow work to the environment (browser/Node), keeps running, and the environment hands back a *callback* later. The event loop is the dispatcher that decides when those callbacks get to run on the one thread.**

The phrase to burn in: **"JavaScript is single-threaded, but its runtime is not."** The language has one call stack; the browser/Node around it has timers, network, file I/O running on other threads. The event loop is the bridge.

---

## The pieces

```
┌─────────────┐     ┌──────────────────┐
│  Call Stack │     │   Web APIs /      │
│ (1 thread,  │────▶│   Node APIs       │  timers, fetch, WS — run OUTSIDE the thread
│  runs JS)   │     └──────────────────┘
└─────────────┘              │ when done, push callback to a queue
       ▲                     ▼
       │            ┌─────────────────────┐
       │            │  Microtask queue    │  ← promises, await, queueMicrotask
       │   loop     │  (HIGH priority)    │
       └────────────┤─────────────────────┤
                    │  Macrotask queue    │  ← setTimeout, setInterval, I/O, events
                    │  (LOWER priority)   │
                    └─────────────────────┘
```

1. **Call stack** — where JS actually executes, one frame at a time. Synchronous code runs here top to bottom.
2. **Web/Node APIs** — when you call `setTimeout`, `fetch`, or attach `ws.onmessage`, the *environment* takes over the waiting. The stack moves on immediately.
3. **Two queues** — when the async thing is ready, its callback goes into a queue: **macrotasks** (timers, I/O, events) or **microtasks** (promise reactions).
4. **The event loop** — the rule it enforces: *when the call stack is empty*, drain **all** microtasks, then take **one** macrotask, then repeat (with a render in between, in the browser).

---

## The one rule that explains everything: microtasks beat macrotasks

After each synchronous chunk finishes (stack empties), the loop **empties the entire microtask queue before touching a single macrotask.** This is *the* interview question:

```ts
console.log("1: sync");
setTimeout(() => console.log("2: macrotask"), 0);
Promise.resolve().then(() => console.log("3: microtask"));
console.log("4: sync");

// Output: 1, 4, 3, 2
```

Walk it:
- `1` and `4` are synchronous — run immediately, in order.
- `setTimeout(…, 0)` registers a **macrotask** (even with 0ms — "0" means "as soon as possible," not "now").
- `Promise.resolve().then(…)` registers a **microtask**.
- Stack empties. Loop drains microtasks first → `3`. *Then* one macrotask → `2`.

So `setTimeout(fn, 0)` does **not** run `fn` now — it runs it after all current sync code *and* all pending promises. "0ms" is a lie; it's "next macrotask turn, minimum." This is why `await` (a microtask) always resolves before a `setTimeout(0)` queued at the same time.

> **Why two queues at all?** Promises were designed to settle *before the browser does anything else* (like rendering or handling the next event), so chains resolve in one tight batch and the UI sees a consistent state. Timers and events are intentionally lower priority. That priority split is the microtask/macrotask distinction.

---

## Where this lives in our code

Our WebSocket file (`lib/hooks/use-websocket.ts`) is a tour of the macrotask side:

**Timers are macrotasks.** The reconnect backoff and the heartbeat are both `setTimeout`:
```ts
reconnectTimer = setTimeout(connect, delay);   // macrotask: run `connect` after `delay`ms

heartbeatTimer = setTimeout(() => {
  if (singletonWs === ws) ws.close();           // macrotask: if no message in 45s, kill it
}, HEARTBEAT_TIMEOUT_MS);
```
Neither blocks. `setTimeout` registers the callback with the environment and returns instantly; the thread keeps running. `delay` ms later, *if the stack is empty*, the loop runs it. (Note "if the stack is empty" — if your sync code runs for 50ms, a `setTimeout(0)` can't fire until that's done. Timers are a *minimum* delay, not a guarantee.)

**Events are macrotasks.** `ws.onmessage`, `ws.onopen`, `ws.onclose` — each network event the browser receives gets queued as a macrotask and runs when the stack clears. That's why our handlers can safely assume nothing else is mid-execution when they run: the loop runs them one at a time.

**`clearTimeout` cancels a queued macrotask** before it fires — which is exactly what `teardown()` and `resetHeartbeat()` do:
```ts
if (heartbeatTimer) clearTimeout(heartbeatTimer);   // cancel the pending "kill the socket" task
heartbeatTimer = setTimeout(/* fresh 45s */);       // and re-arm it
```
Every incoming message calls `resetHeartbeat()` → cancel the old timeout, set a new one. So the "zombie killer" only fires after a *genuine* 45s of silence. That's macrotask scheduling used as application logic.

**Promises/`await` are microtasks.** `await supabase.auth.getSession()` in `connect()` suspends the function and schedules its continuation as a microtask when the promise settles (article 08 details this). The `for (const handler of handlers) handler(msg)` inside `onmessage` is plain synchronous — it runs to completion on the stack before the loop moves on.

---

## Why "single-threaded" matters: don't block the loop

Because there's one thread, **any long synchronous loop freezes everything** — no clicks, no renders, no timers, no message handling. If `runDijkstra` (article 09's algorithm) took 5 seconds of synchronous CPU, the whole tab would lock for 5 seconds. It doesn't, because the metro graph is small (~300 nodes) and the work is milliseconds — but that's a *deliberate* property. The general lesson: **the event loop only spins when the stack is empty, so never hog the stack.** Heavy CPU work belongs in a Web Worker (a genuinely separate thread) so the loop keeps turning.

This is also why async I/O is the whole point of Node: while one request waits on the database, the single thread isn't blocked — it serves other requests, and the loop wakes the waiter when the DB responds.

---

## The interview angle

- *"Explain the event loop."* → "JS is single-threaded with one call stack. Slow work — timers, network, I/O — is handed to the environment, which runs it off-thread and queues a callback when done. When the stack is empty, the event loop drains all microtasks (promise reactions), then runs one macrotask (timer/event), and repeats. So async callbacks always run *after* the current synchronous code finishes."
- *"Why does a `Promise.then` run before `setTimeout(0)`?"* → "`.then` queues a microtask, `setTimeout` queues a macrotask. The loop empties the entire microtask queue before taking any macrotask, so the promise wins even at 0ms."
- *"Is `setTimeout(fn, 0)` immediate?"* → "No. It's 'after all current sync code and all pending microtasks, at the next macrotask turn.' The 0 is a minimum delay, not a guarantee — if the stack is busy, it waits."
- *"What happens if you run a 5-second `for` loop?"* → "It blocks the single thread — no rendering, no events, no timers fire until it finishes. Heavy CPU should go to a Web Worker so the loop keeps turning."

---

## Concept checklist

- [ ] I can draw the diagram: stack, Web APIs, micro + macro queues, the loop.
- [ ] I can say "single-threaded language, multi-threaded runtime" and explain it.
- [ ] I can predict the output of the `1,4,3,2` snippet and explain each step.
- [ ] I can explain why microtasks drain fully before any macrotask.
- [ ] I can explain why `setTimeout(fn, 0)` isn't immediate.
- [ ] I can point at our WS timers/events as macrotasks and `await` as a microtask.
- [ ] I can explain why blocking the stack freezes the whole app and what fixes it.

Next up: **[08 — Promises & async/await](./08-promises-async-await.md)** — what a promise actually is, and how `await` is just `.then` in disguise.
