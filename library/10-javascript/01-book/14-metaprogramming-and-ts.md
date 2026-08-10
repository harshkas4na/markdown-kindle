# 14 — Metaprogramming & the JS↔TS boundary

The final article. "Metaprogramming" sounds intimidating but it just means *code that operates on code's behavior* — intercepting property access, wrapping functions, changing how objects respond. JavaScript is unusually open to this, and our app uses it in one genuinely advanced spot. Then we close the loop on the thing I waved away in the README: **what is TypeScript actually doing at runtime?** (Answer: nothing. And that matters.)

The mental model:

**Most code computes values. Metaprogramming code intercepts the *mechanics* — what happens when you read a property, call a function, or construct an object — and changes it. Getters/setters intercept one property; `Proxy` intercepts everything; monkey-patching replaces a function wholesale. Powerful, occasionally necessary, easy to abuse.**

---

## Getters & setters — properties that run code

The mildest metaprogramming, and we already met it. A getter makes a *method call* look like a *property read*. Our `MinHeap` (article 04):
```ts
get size() { return this.heap.length; }
// usage:
if (pq.size > 0) { ... }   // looks like a field, runs a function
```
`pq.size` has no stored value — every access runs the getter. Setters are the mirror (`set x(v) {...}` runs on assignment). They're for *computed* or *validated* properties that should still read like plain fields. The lesson: in JS, `obj.prop` is **not** guaranteed to be a simple memory read — it might be running arbitrary code. (That's also a subtle gotcha: a getter with side effects fires every time you "just read" the property.)

---

## `Proxy` — intercept *everything* about an object

A `Proxy` wraps an object and lets you intercept fundamental operations — property get/set, `in`, `delete`, function calls — via "traps":

```ts
const logged = new Proxy(target, {
  get(obj, key) {
    console.log("read", key);
    return obj[key];            // forward to the real object
  },
  set(obj, key, value) {
    if (key === "id") throw new Error("id is read-only");
    obj[key] = value;
    return true;
  },
});
```

Now *every* read on `logged` logs, and writing `id` throws — without modifying `target` itself. This is how reactivity systems work under the hood: **Vue 3's reactivity is built on `Proxy`** — it traps every property read to track dependencies and every write to trigger re-renders. (React took a different path — explicit `setState`/immutable updates, article 05 — which is why React needs you to *not* mutate, while Vue can let you mutate a proxied object.) We don't use `Proxy` in the app, but knowing "Proxy = programmable object, the basis of fine-grained reactivity" is exactly the kind of depth that lands in a senior interview.

`Reflect` is `Proxy`'s companion — it provides the *default* versions of those operations (`Reflect.get(obj, key)`), so inside a trap you can do "the normal thing plus my extra behavior" cleanly.

---

## Monkey-patching — replacing a built-in (we actually do this)

Monkey-patching means **reassigning an existing function** (often a built-in) to wrap or replace its behavior. It's metaprogramming's blunt instrument, and our `app/(app)/layout.tsx` uses it for a genuinely good reason — global 429 handling:

```ts
useEffect(() => {
  const originalFetch = window.fetch;              // 1. save the original
  window.fetch = async (...args) => {              // 2. replace with a wrapper
    const res = await originalFetch(...args);       //    call the real fetch
    if (res.status === 429) {                        //    intercept rate-limit responses
      router.push("/too-many-requests");
      return res.clone();                            //    clone so callers can still read the body
    }
    return res;
  };
  return () => { window.fetch = originalFetch; };   // 3. restore on cleanup
}, [router]);
```

This is a beautiful synthesis of the whole course, so let me name every concept in it:

- **It replaces a global function** (`window.fetch`) so *every* fetch in the app — from any component, any hook — automatically gets 429 handling without each call site knowing. One interception point, app-wide effect. That's the *reason* to monkey-patch: cross-cutting behavior you can't easily thread through every caller.
- **`...args` (rest, article 06)** captures whatever arguments fetch was called with; **`originalFetch(...args)` (spread)** forwards them unchanged. The wrapper is transparent — it doesn't need to know fetch's signature.
- **It's a closure (articles 02, 10)** — the wrapper closes over `originalFetch` and `router`. That captured `originalFetch` is how it calls through to the real implementation.
- **`async`/`await` (article 08)** — it awaits the real fetch, inspects the result, then returns it (or a clone).
- **`res.clone()`** — a Response body is a *stream you can only read once*. If the layout read it and passed the original on, the real caller's `.json()` would throw "body already used." Cloning hands the caller a fresh, unread copy. (A subtle, correct detail that shows real understanding of the fetch API.)
- **The cleanup restores `window.fetch`** (articles 10, 12) — monkey-patching a global is a *leak and a landmine* if you don't undo it. The effect cleanup puts the original back on unmount. Setup pairs with teardown, one more time.

So the single most "meta" thing in the codebase is also a recap of half the course. The cautionary note: monkey-patching a global is powerful but invasive — it affects code you don't own, can collide with other patches, and must be restored. We do it correctly (save → wrap → restore); doing it carelessly is how you get haunted-house bugs.

---

## The JS ↔ TS boundary — what TypeScript *is* at runtime

The whole course said "mentally strip the types." Now the honest, complete truth, because it's a favorite interview trap:

**TypeScript is a compile-time type checker that produces plain JavaScript by *erasing* all the types. At runtime, there is no TypeScript. None. The types do not exist.**

Concretely:
```ts
function getMinStationDistance(s1: string, s2: string): number { ... }
//                                ^^^^^^^      ^^^^^^^   ^^^^^^  ← all GONE after compile
```
compiles to:
```js
function getMinStationDistance(s1, s2) { ... }
```

Consequences that bite people:

- **No runtime type checking.** If a network response claims to be `SavedRoute[]` but the server sends garbage, TypeScript won't catch it — the `: SavedRoute[]` annotation in `saved-routes.ts` is a *compile-time promise*, not a runtime guard. That's why real apps validate untrusted input at the boundary with a library like **Zod** (which checks *actual values* at runtime) — types alone can't. The Next.js course's `lib/sanitize.ts`/validation is the runtime half that types can't do.
- **`interface`/`type` vanish entirely.** They emit *zero* JavaScript. `interface MetroStation {...}` is purely a compile-time description.
- **What survives are real JS constructs:** `class`, `enum` (emits an object), and `const`/`let`. The `MetroLine` enum is real runtime code; the `MetroStation` interface is a ghost.
- **`private` in our `MinHeap` is compile-time only** (article 04). TypeScript stops *you* from writing `heap.heap` in your editor, but at runtime `heap.heap` is fully accessible — the privacy is a lint, not a lock. JS's true private is `#heap`.
- **Generics, `as`, `satisfies`, union types** — all erased. `data as { statusCode: number }` (seen in the push-send route) doesn't *convert* anything at runtime; it just tells the compiler "trust me." If you're wrong, you get a runtime crash the types swore couldn't happen.

So the mental model to carry out of this course: **TypeScript is a very good linter with an excellent type system, running at build time. The thing that actually executes is the JavaScript underneath — the JavaScript these 14 articles are about.** Every runtime behavior — the event loop, closures, prototypes, `this`, GC — is pure JS and would be identical if you deleted every type annotation. That's *why* relearning JavaScript itself (not the framework, not the type layer) was worth doing: it's the only layer that's actually running.

---

## The interview angle

- *"What's metaprogramming in JS?"* → "Code that intercepts the mechanics of other code — getters/setters intercept a property, `Proxy` intercepts all object operations via traps, monkey-patching replaces a function. Vue's reactivity is a `Proxy` trapping reads and writes."
- *"Have you monkey-patched something?"* → "Yes — I wrap `window.fetch` in a layout effect to globally catch 429 responses and redirect, forwarding args with rest/spread, cloning the response so callers can still read the body, and restoring the original `fetch` on cleanup so it doesn't leak."
- *"What is TypeScript at runtime?"* → "Nothing — it's erased. TS is a compile-time checker that strips all types and emits plain JS. So there's no runtime type safety; for untrusted input you still validate values at runtime, e.g. with Zod. `interface`/`type`/generics emit zero code; only real JS constructs like `class`/`enum` survive."
- *"Is TS `private` actually private?"* → "No, it's compile-time only — the field is accessible at runtime. JavaScript's real private is the `#field` syntax."

---

## Concept checklist

- [ ] I can explain getters/setters and that `obj.prop` may run code.
- [ ] I can explain what a `Proxy` does and name reactivity as the killer use case.
- [ ] I can explain monkey-patching and read our `window.fetch` wrapper line by line.
- [ ] I can explain why `res.clone()` is needed (single-use body).
- [ ] I can explain why the patch must be restored on cleanup.
- [ ] I can state that TypeScript is erased at runtime and the consequences.
- [ ] I can explain why runtime validation (Zod/sanitize) is still needed despite types.
- [ ] I can explain that TS `private` is compile-time and `#field` is the real thing.

---

## 🎓 You finished the JavaScript course

That's all fourteen. The arc, looking back: foundations (types, scope, `this`) → the data shapes (objects/prototypes, arrays, modern syntax) → **async** (event loop, promises, concurrency — the heart) → closures-as-architecture and the runtime → mastery (iterators, metaprogramming, the TS truth).

The through-line worth keeping: nearly every "advanced" thing in our codebase is a *combination* of a few primitives. The WebSocket singleton is closures + module scope + the event loop + a Set. The face detector is promise memoization + `new Promise` wrapping + closures. The `fetch` patch is rest/spread + closures + async + cleanup. There were never that many concepts — just a lot of ways to combine them.

If I can tick every box across these fourteen articles *out loud*, I understand the language my whole app actually runs on — independent of any framework. The natural companion is the Next.js course (`../learn-nextjs/`); together they cover the framework *and* the language beneath it.
