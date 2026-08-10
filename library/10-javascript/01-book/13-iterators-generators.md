# 13 — Iterators, generators & the collection types

Level 5 — the stuff that separates "I write JS" from "I understand JS." None of it is exotic; we *use* `Set`, `Map`, `for...of`, and spread all over the codebase. The goal here is to understand the protocol underneath them, because once you see that `for...of`, spread, and destructuring all secretly call the *same* method, a lot of the language clicks into one idea.

The mental model:

**"Iterable" isn't a vague adjective — it's a contract. Any object with a `[Symbol.iterator]` method is iterable, and *everything* that consumes a sequence — `for...of`, spread `...`, array destructuring, `Promise.all` — works by calling that one method. Generators are a language feature for *producing* iterables without writing the protocol by hand. And `Map`/`Set` are purpose-built iterables that fix real shortcomings of plain objects and arrays.**

---

## The iteration protocol — the hidden contract

When you write `for (const x of thing)`, JS doesn't magically know how to loop `thing`. It calls `thing[Symbol.iterator]()` to get an **iterator**, then calls `.next()` on it repeatedly. Each `.next()` returns `{ value, done }`; the loop stops when `done` is `true`.

```ts
const arr = [10, 20];
const it = arr[Symbol.iterator]();
it.next(); // { value: 10, done: false }
it.next(); // { value: 20, done: false }
it.next(); // { value: undefined, done: true }
```

Arrays, strings, `Map`, `Set`, `NodeList`, and `arguments` all ship a `[Symbol.iterator]`. Plain objects **do not** — which is exactly why `for...of` doesn't work on `{}` (you use `for...in` or `Object.entries()` instead). That single fact explains a confusing beginner error.

And here's the unifying payoff: **everything that consumes a sequence uses this protocol.**
```ts
for (const x of thing) {}      // calls thing[Symbol.iterator]()
const copy = [...thing];        // spread → same protocol
const [a, b] = thing;           // array destructuring → same protocol
new Set(thing);                 // Set constructor → same protocol
```
So when our matcher does `const [h1, m1] = time1.split(":").map(Number)` (article 05/06), the destructuring is invoking the array's iterator. When the WS does `for (const handler of handlers)` over a `Set`, it's the Set's iterator. One protocol, many syntaxes. `Symbol` itself (article 14's neighbor) exists partly to give this method a name that can never collide with a real property key — that's what `Symbol.iterator` is: a guaranteed-unique key.

---

## `Symbol` in one paragraph

A `Symbol` is a primitive (article 01's 7th type) whose only purpose is to be **unique** — `Symbol("x") !== Symbol("x")`. They're used as collision-proof property keys. You rarely *create* them in app code, but the language uses "well-known symbols" like `Symbol.iterator` (makes a thing iterable) and `Symbol.asyncIterator` (for `for await...of`) to let your objects hook into language features. Mentally: "a Symbol is a guaranteed-unique key, and the built-in ones are how you opt into protocols."

---

## Generators — producing iterables the easy way

Writing `[Symbol.iterator]` + a `.next()` state machine by hand is tedious. **Generators** (`function*` + `yield`) do it for you: a generator function returns an iterator automatically, and `yield` is "produce this value, then pause here until the next `.next()`."

```ts
function* range(start, end) {
  for (let i = start; i < end; i++) yield i;   // pause and hand out i each time
}
for (const n of range(0, 3)) console.log(n);   // 0, 1, 2
[...range(0, 3)];                              // [0, 1, 2] — it's iterable, so spread works
```

The mind-bending, powerful part: a generator **pauses and resumes, keeping its local state between calls.** Execution freezes at each `yield` and continues from there on the next `.next()`. That gives you two things:

1. **Lazy / infinite sequences** — values computed on demand, not all up front:
   ```ts
   function* ids() { let i = 0; while (true) yield i++; }   // infinite, but safe — lazy
   const gen = ids();
   gen.next().value; // 0
   gen.next().value; // 1   ← only computes when asked
   ```
   You couldn't make an infinite *array*; you can make an infinite *generator* because it only ever produces the next value when pulled.
2. **Custom iteration** — make any object `for...of`-able by giving it a `*[Symbol.iterator]()`. Our `MinHeap` (article 04) *could* expose iteration this way (e.g. drain in priority order), though we don't need it.

We don't use generators heavily in the app — most of our "produce a sequence" needs are met by arrays and `map`. But understanding them explains how `async/await` works under the hood (early async libraries were literally generators + a runner that resumed them on promise resolution), and they're a favorite interview topic for "lazy evaluation."

---

## `Map` vs object, `Set` vs array — and we use both

Our codebase reaches for `Map` and `Set` deliberately. Knowing *why* over a plain `{}`/`[]` is the senior call.

### `Set` — a collection of unique values, iterable

The WebSocket file uses Sets for its registries:
```ts
const handlers = new Set<MessageHandler>();          // each handler registered once
const connectionListeners = new Set<() => void>();
handlers.add(fn);       // add (duplicates ignored automatically)
handlers.delete(fn);    // remove in O(1)
for (const h of handlers) h(msg);   // iterate
```
Why `Set` and not an array? **Uniqueness and O(1) add/delete.** With an array you'd risk registering the same handler twice and pay O(n) to remove one (`indexOf` + `splice`). A `Set` guarantees each handler appears once and deletes in constant time — exactly what a subscriber registry needs (article 10's observer pattern). Plus it's iterable, so `for...of` just works.

### `Map` — keyed entries with any key type, iterable, ordered

The conversations route uses a `Map` for per-room receipts:
```ts
[...receiptMap.values()].reduce((min, val) => (val < min ? val : min));
```
Why `Map` over a plain object? Four reasons, each a real advantage:
- **Any key type** — objects, not just strings (a plain object coerces every key to a string).
- **Reliable size** — `map.size` vs counting `Object.keys(obj).length`.
- **Clean iteration** — `map.keys()`, `.values()`, `.entries()` are iterables (note the `[...receiptMap.values()]` spread — Map values are iterable, so spread collects them into an array to `reduce`).
- **No prototype pollution** — a `Map` has no inherited `toString`/`constructor` keys, so it's safe as a user-keyed dictionary (article 04's footgun). A plain object used as a dict can collide with inherited keys.

The rate-limiter's `limiters` (article 10) is a `Map` for the same reasons — keyed, sized, clean.

### `WeakMap`/`WeakSet` — the memory-friendly variants

From article 12: these hold their keys **weakly**, so an entry vanishes when its key object is otherwise unreachable. The trade-off: they're **not iterable** and have **no `.size`** (you can't enumerate them — that's the price of weak references, since entries can disappear at any GC). Use a `WeakMap` to attach metadata to objects you don't own the lifecycle of (DOM nodes, external instances) without leaking them. The "weak" is precisely "does this reference keep the key alive?" — `Map` yes, `WeakMap` no.

---

## Quick decision guide

| Need | Use |
|---|---|
| Ordered list, duplicates OK, index access | **Array** |
| Unique values, fast add/remove/has | **Set** |
| Key→value, non-string keys, size, safe dict | **Map** |
| Object-keyed cache that shouldn't leak | **WeakMap** |
| Fixed-shape record (known fields) | plain **object** |

---

## The interview angle

- *"What makes something iterable?"* → "A `[Symbol.iterator]` method returning an iterator with `.next()` yielding `{value, done}`. `for...of`, spread, array destructuring, and the `Set`/`Map` constructors all consume that one protocol. Arrays/strings/Map/Set have it; plain objects don't, which is why `for...of` fails on `{}`."
- *"What's a generator good for?"* → "Producing iterables without hand-writing the protocol, and lazy or infinite sequences — it pauses at `yield` and resumes on `.next()`, keeping local state. It's also conceptually how async/await resumes."
- *"`Map` vs object?"* → "`Map` allows any key type, has `.size`, iterates cleanly, preserves insertion order, and has no inherited keys — so it's the safe choice for a real dictionary or when keys aren't strings. Object for fixed-shape records. I use a `Map` for rate-limiters and receipts, a `Set` for handler registries."
- *"`Set` vs array for a registry?"* → "`Set` — automatic uniqueness and O(1) add/delete/has, versus an array's duplicate risk and O(n) removal. My WebSocket keeps its message handlers in a `Set`."
- *"Why `WeakMap`?"* → "Weak keys — entries get collected when the key object is otherwise unreachable, so it won't leak. Cost is no iteration and no size."

---

## Concept checklist

- [ ] I can describe the iteration protocol (`Symbol.iterator` → iterator → `.next()` → `{value,done}`).
- [ ] I can explain that `for...of`, spread, and destructuring all use it, and why `{}` isn't iterable.
- [ ] I can explain what a `Symbol` is and what `Symbol.iterator` does.
- [ ] I can write a generator and explain pause/resume + lazy/infinite sequences.
- [ ] I can justify `Set` over array for our handler registries.
- [ ] I can list `Map`'s advantages over a plain object and point at our uses.
- [ ] I can explain `WeakMap`'s weak keys and its no-iteration/no-size trade-off.

Next up: **[14 — Metaprogramming & the JS↔TS boundary](./14-metaprogramming-and-ts.md)** — the final article: getters, Proxy, monkey-patching, and what TypeScript really is.
