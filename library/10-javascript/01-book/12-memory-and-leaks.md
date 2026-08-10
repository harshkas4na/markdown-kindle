# 12 — Memory, references & leaks

JavaScript manages memory for you — there's no `free()`. But "automatic" isn't "foolproof": the garbage collector can only reclaim what's *unreachable*, and it's surprisingly easy to keep things reachable by accident. That's a memory leak, and in a long-lived SPA (ours never does a full page reload while you navigate) leaks accumulate. The good news: our cleanup code already prevents the classic ones, so this article is mostly "understand what that cleanup is *for*."

The mental model:

**The garbage collector frees memory by reachability: starting from "roots" (global scope, the call stack, live closures), it marks everything still reachable by a chain of references, and sweeps the rest. So memory leaks in JS aren't about forgetting to free — they're about accidentally keeping a reference alive: a timer, a listener, a growing array, a closure that outlives its usefulness.**

---

## How GC actually decides: reachability

The algorithm is **mark-and-sweep**. Roots = things always alive (the global object, the current call stack, active closures). The GC walks every reference from the roots, marks what it reaches, and frees everything it *didn't* reach.

The key consequence: **an object lives as long as something reachable points to it.** Set the last reference to `null` (or let it go out of scope) and it becomes collectable. This is why article 02's closures "keep variables alive" — the closure is a live reference, so the GC can't touch what it captures. Useful when you want it (the rate-limiter Map), a leak when you don't (a closure you forgot to release).

Old GCs used *reference counting* (free when count hits 0), but that can't handle **reference cycles** — A points to B, B points to A, nothing else points to either; counts never hit zero but they're unreachable garbage. Mark-and-sweep handles cycles correctly because it asks "reachable from a root?" not "how many references?" Knowing why reference counting was abandoned (cycles) is a senior-level detail.

---

## The four classic leaks (and how our code avoids each)

### 1. Timers that are never cleared

`setInterval`/`setTimeout` callbacks are held by the runtime, and they keep their closure (and everything it captures) alive until cleared. A timer you forget to clear is a leak that also keeps *running*.

Our WebSocket `teardown()` clears both of its timers:
```ts
function teardown() {
  if (heartbeatTimer) { clearTimeout(heartbeatTimer); heartbeatTimer = undefined; }
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = undefined; }
  if (singletonWs) { singletonWs.onclose = null; singletonWs.close(); singletonWs = null; }
  // ...
}
```
Every timer that gets created has a `clearTimeout` paired with it on teardown. And setting `singletonWs = null` drops the last reference to the socket so it can be collected. **The discipline: every `setTimeout`/`setInterval`/`addEventListener`/subscription needs a matching cleanup.** Notice `teardown` only fires when `refCount` hits 0 (article 10) — so cleanup is tied precisely to "nobody needs this anymore."

### 2. Event listeners that are never removed

`addEventListener` keeps the handler alive (and its closure, and any DOM/state it captured) until you `removeEventListener`. In React this is what effect cleanup is *for* — straight from `UserSearchAutocomplete`:
```ts
document.addEventListener("mousedown", handleClickOutside);
return () => document.removeEventListener("mousedown", handleClickOutside);
```
Add on mount, remove on unmount. Without that cleanup, every time the component mounts you'd stack another listener — and each one pins the component's closure in memory. The same shape appears for the WS `onAuthStateChange` and the `handlers` Set's unsubscribe (article 10). **Setup pairs with teardown** — that's the leak-prevention idiom for the whole language.

### 3. Unbounded growth

A collection that only ever grows is a leak even if every reference is "intentional." Our message queue guards against exactly this:
```ts
const MAX_QUEUE_SIZE = 100;
// in send():
if (messageQueue.length >= MAX_QUEUE_SIZE) {
  messageQueue.shift();   // drop the oldest to prevent unbounded growth
}
messageQueue.push(data);
```
If the socket is down and the user keeps sending, the queue would grow without limit (each queued object held in memory forever). Capping it — drop-oldest past 100 — bounds the memory. The comment literally says "prevent unbounded growth." This is the mindset: any buffer/cache/log that's fed continuously needs an eviction policy, or it's a slow leak. (The rate-limiter Map is bounded differently — its keys are a small fixed set of config strings, so it can't grow without limit.)

### 4. Stale references in long-lived scope

A reference parked in a module-level or closure scope that *outlives* its usefulness. The fix is the `= null` you see in `teardown` (`singletonWs = null`) and in the face detector's failure path (`initPromise = null; detector = null`) — explicitly dropping references when the thing they point to is no longer valid, so the GC can reclaim it and (in the detector's case) so a retry can rebuild fresh.

---

## `WeakMap`/`WeakSet`: references that *don't* prevent collection

There's a special tool for "associate data with an object *without* keeping that object alive." A normal `Map` holds its keys strongly — putting a DOM node in a `Map` keeps the node in memory forever. A **`WeakMap`** holds its keys *weakly*: if the only remaining reference to a key is the WeakMap, the entry is collectable. (Details in article 13, but it belongs to the memory story.) Use it for metadata/caches keyed by objects you don't own the lifecycle of — it auto-cleans when they go away.

---

## How to actually find a leak (practical)

The interview-and-real-life answer: **Chrome DevTools → Memory tab → heap snapshots.** Take a snapshot, do the suspect action (open/close a chat 20×), take another, and compare — if detached DOM nodes or listener counts climb and never drop, you've got a leak. The Performance monitor's "JS heap size" sawtooth that trends *upward* over time (instead of returning to baseline after GC) is the signature. For our app the things to watch would be exactly the four above: sockets, timers, listeners, the queue.

---

## The interview angle

- *"How does garbage collection work in JS?"* → "Mark-and-sweep by reachability. From roots — globals, the stack, live closures — it marks everything reachable and frees the rest. So an object lives as long as something reachable references it; you don't free manually, you drop references."
- *"Why not reference counting?"* → "It can't collect reference cycles — two objects pointing at each other keep nonzero counts even when unreachable. Mark-and-sweep asks 'reachable from a root?' so it handles cycles."
- *"Name a memory leak and how to prevent it."* → "An uncleared `setInterval` or an `addEventListener` without `removeEventListener` — both keep their closure alive forever. Prevention is pairing every setup with a teardown. My WebSocket clears its timers and nulls the socket on teardown, and removes listeners in effect cleanup."
- *"How do you stop a queue from leaking?"* → "Bound it with an eviction policy. My outbound message queue caps at 100 and drops the oldest, so a downed connection can't grow it without limit."
- *"What's a `WeakMap` for?"* → "Associating data with an object without keeping it alive — the key is held weakly, so the entry is collected when the object is otherwise unreachable. Good for object-keyed caches you don't want to leak."

---

## Concept checklist

- [ ] I can explain mark-and-sweep and reachability from roots.
- [ ] I can explain why reference counting fails on cycles.
- [ ] I can name the four classic leaks (timers, listeners, unbounded growth, stale refs).
- [ ] I can point at `teardown` clearing timers and nulling the socket.
- [ ] I can explain the `MAX_QUEUE_SIZE` drop-oldest as leak prevention.
- [ ] I can explain "every setup pairs with a teardown" and tie it to effect cleanup.
- [ ] I can explain `WeakMap`/`WeakSet` as non-retaining references.
- [ ] I can describe how to find a leak with heap snapshots.

Next up: **[13 — Iterators, generators & the collection types](./13-iterators-generators.md)** — Level 5: the iteration protocol and the modern data structures.
