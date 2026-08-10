# Learning JavaScript (properly) through Metro Diaries

This is the companion course to my Next.js one — same idea, same voice: I'm not reading a tutorial where everything is a `Counter` and a `TodoApp`. I'm relearning JavaScript by pointing at code I *already shipped* and asking *"wait, why does this actually work? what is the language really doing here?"*

The Next.js course was about the framework. **This one is about the language underneath it** — the thing that's still true whether I'm in Next, Node, a browser, or a Cloudflare worker. Frameworks change every two years; the event loop doesn't.

Because I'm *revising*, not learning from zero, this is deliberately **weighted toward the advanced end.** The first three articles are a fast refresher on the foundations (types, scope, `this`) — I move quick because I half-know them. Then the course slows *down* and goes *deep* exactly where it matters for interviews and for understanding my own code: closures-as-architecture, the event loop, promises, async patterns, memory, generators, metaprogramming.

By the end I want two things at once:

1. I can walk into an interview and explain the event loop, closures, prototypes, `this`, promises, and async concurrency — confidently, with examples from real code.
2. I understand the JavaScript in my own app so deeply that the "clever" files (the WebSocket singleton, the promise-memoized face detector, the hand-rolled min-heap) read like plain English.

---

## How to read this

Top to bottom. Each article assumes the one before it. Every article has the same shape as my Next.js course:

- **The mental model** — the one-paragraph "what is this *really*" I want burned in.
- **In our codebase** — the exact file where we do this, and what the language is doing under the hood.
- **The interview angle** — how this exact topic gets asked, and the answer out loud.
- **Concept checklist** — `- [ ]` boxes I only tick when I can explain it to another human without looking.

A note on TypeScript: our codebase is `.ts`/`.tsx`, but **TypeScript is just JavaScript with types erased before it runs.** Every runtime behavior in here is pure JS — the types are a compile-time ghost. Article 14 makes that boundary explicit; until then, mentally strip the `: string` annotations and what's left is the JavaScript.

---

## The curriculum (and master checklist)

### Level 1 — Foundations (fast refresher, I half-know these)

- [ ] **[01 — Types, coercion & equality](./01-types-coercion-equality.md)** — primitives vs objects, value vs reference, `==` vs `===`, truthiness, `null` vs `undefined`, the coercion rules that bite. Grounded in `calculateAge` and `getTimeAgo`.
- [ ] **[02 — Scope, hoisting, closures & the TDZ](./02-scope-hoisting-closures.md)** — `var`/`let`/`const`, the temporal dead zone, lexical scope, and the single most important idea in JS: the **closure**. Grounded in the rate-limiter's memo.
- [ ] **[03 — `this`, call/apply/bind & arrow functions](./03-this-and-functions.md)** — the four rules of `this`, why arrow functions don't have their own, and where this bites in real event handlers. Grounded in the WS callbacks.

### Level 2 — Objects, data & the shapes we move around

- [ ] **[04 — Objects, prototypes & classes](./04-objects-prototypes-classes.md)** — the prototype chain (the *real* inheritance model), `class` as sugar over it, `Object.create`, property descriptors. Grounded in the `MinHeap` class.
- [ ] **[05 — Arrays, iteration & immutability](./05-arrays-iteration-immutability.md)** — `map`/`filter`/`reduce`/`some`/`find`, why we don't mutate, shallow vs deep copy. Grounded in the trip-matching scorer and `saved-routes`.
- [ ] **[06 — Modern syntax that's everywhere](./06-modern-syntax.md)** — destructuring, spread/rest, default params, optional chaining `?.`, nullish coalescing `??`, template literals, short-circuiting. The syntax tax of reading my own code fluently.

### Level 3 — Asynchrony (the heart of the course)

- [ ] **[07 — The event loop & the two queues](./07-event-loop.md)** — call stack, Web APIs, the macrotask queue vs the **microtask** queue, why `Promise.then` beats `setTimeout(0)`. The model that explains *all* async behavior.
- [ ] **[08 — Promises & async/await](./08-promises-async-await.md)** — what a promise actually *is* (a state machine), the three states, chaining, `await` as syntax over `.then`, error propagation, the `try/catch` boundary. Grounded in every `fetch` wrapper and `face-detection`.
- [ ] **[09 — Async concurrency & cancellation](./09-async-concurrency.md)** — `Promise.all`/`allSettled`/`race`/`any`, sequential vs parallel, **promise memoization** (the dedup trick), `AbortController`, debounce/throttle as timing control. The advanced async patterns.

### Level 4 — Closures as architecture & the module/runtime boundary

- [ ] **[10 — Closures in the wild: state without classes](./10-closures-as-architecture.md)** — module singletons, private state, memoization, the refcounted WebSocket, the rate-limiter map. How our app uses closures to hold *real* application state.
- [ ] **[11 — Modules, the runtime & `globalThis`](./11-modules-and-runtime.md)** — ESM vs CommonJS, what `import`/`export` compile to, module-level code runs *once*, the server/browser global split, `typeof window` guards. Why a module is itself a closure.
- [ ] **[12 — Memory, references & leaks](./12-memory-and-leaks.md)** — the heap, garbage collection by reachability, reference cycles, the classic listener/timer leaks — and exactly how our WS refcount + cleanup functions avoid them.

### Level 5 — Mastery (the parts that separate senior from mid)

- [ ] **[13 — Iterators, generators & the collection types](./13-iterators-generators.md)** — the iteration protocol (what `for...of` and spread secretly call), `Symbol.iterator`, generators & lazy sequences, `Map`/`Set`/`WeakMap` and when each beats a plain object.
- [ ] **[14 — Metaprogramming & the JS↔TS boundary](./14-metaprogramming-and-ts.md)** — getters/setters, `Proxy`, monkey-patching (our `window.fetch` override), and the honest truth about what TypeScript is and isn't at runtime. The closing article.

---

## The "can I explain this in an interview?" master list

Tick only when I can say it *out loud* to another person:

**Types & values**
- [ ] The 7 primitives, and why objects/arrays/functions are reference types
- [ ] Value copy vs reference copy — what gets shared when I pass an object
- [ ] `==` vs `===` and the coercion rules I should actually memorize
- [ ] `null` vs `undefined` vs `NaN`; what `typeof null` returns and why
- [ ] Truthy/falsy: the full list of falsy values

**Scope & closures**
- [ ] `var` vs `let` vs `const`, hoisting, and the temporal dead zone
- [ ] What a closure *is*, and one real thing I'd build with it
- [ ] Lexical scope vs dynamic scope

**Functions & `this`**
- [ ] The four binding rules for `this` (default/implicit/explicit/`new`)
- [ ] Why arrow functions are special (no own `this`, used for callbacks)
- [ ] `call` vs `apply` vs `bind`

**Objects**
- [ ] The prototype chain and how property lookup walks it
- [ ] `class` is sugar over what?
- [ ] Shallow vs deep copy; how I clone an object safely

**Async (the big one)**
- [ ] Draw the event loop: stack, Web APIs, macro vs microtask queue
- [ ] Why does a `Promise.then` run before a `setTimeout(0)`?
- [ ] What is a promise — the three states and how `await` maps to `.then`
- [ ] `Promise.all` vs `allSettled` vs `race` vs `any`
- [ ] Sequential vs parallel awaits — the `await` in a loop trap
- [ ] How do I cancel an in-flight request? (`AbortController`)
- [ ] Implement debounce / throttle from memory

**Runtime & memory**
- [ ] How does garbage collection decide what to free?
- [ ] Name a real memory leak and how to prevent it
- [ ] ESM vs CommonJS; why module code runs once

**Mastery**
- [ ] The iteration protocol — what does `for...of` actually call?
- [ ] What's a generator good for?
- [ ] `Map` vs object; `WeakMap` and why "weak"
- [ ] What is a `Proxy` / what's metaprogramming?
- [ ] What is TypeScript at runtime? (trick question)

---

*Status: all 14 articles written. The foundations move fast; the async (07–09) and closures-as-architecture (10) sections are where the real time goes. Now the work is to tick the boxes — out loud.*
