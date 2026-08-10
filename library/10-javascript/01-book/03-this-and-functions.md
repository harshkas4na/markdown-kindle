# 03 — `this`, call/apply/bind & arrow functions

The other famously-confusing JS topic. But it's only confusing because people memorize cases instead of the one rule. There's one rule.

The mental model:

**`this` is not about where a function is *defined* — it's about how a function is *called*. The value of `this` is decided fresh on every single call, by looking at what's to the left of the dot at the call site. Arrow functions are the one exception: they don't get their own `this` at all, they borrow it from where they were written.**

That sentence — "`this` is set by the call site, not the definition site" — is the entire topic. Everything else is four sub-cases of it.

---

## The four binding rules (in priority order)

When a normal function runs, JS picks `this` by the first rule that applies:

**1. `new` binding.** Called with `new`? `this` is the brand-new object being constructed.
```ts
const heap = new MinHeap();   // inside the constructor, `this` is the new heap
```
This is exactly what happens in `lib/metro/graph.ts` when we do `new MinHeap()` — the constructor's `this.items = []` attaches to the fresh instance.

**2. Explicit binding.** Called with `.call`, `.apply`, or `.bind`? `this` is whatever you passed.
```ts
fn.call(obj, a, b);    // this = obj, args passed individually
fn.apply(obj, [a, b]); // this = obj, args as an array
const bound = fn.bind(obj); // returns a NEW fn permanently locked to obj
```
Mnemonic: **A**pply = **A**rray. `bind` doesn't call — it returns a pre-wired copy for later.

**3. Implicit binding.** Called as `obj.method()`? `this` is whatever's left of the dot — `obj`.
```ts
heap.push(x);   // inside push, `this` is heap
```

**4. Default binding.** Just `fn()` with nothing to the left? `this` is `undefined` in strict mode (which modules always are), or the global object in sloppy mode.

The gotcha that trips everyone: **rule 3 evaporates if you detach the method.**
```ts
const p = heap.push;
p(x); // `this` is undefined — there's no dot anymore. Boom.
```
The function didn't change; the *call site* did. No dot, no implicit `this`. This is the bug behind a thousand "cannot read property of undefined" errors when people pass `obj.method` as a callback.

---

## Arrow functions: the exception that fixes everything

Arrow functions **do not have their own `this`.** They don't participate in the four rules at all. Instead they capture `this` *lexically* — from the scope where the arrow was written — and it never changes, no matter how they're called. (Same for `arguments`, and they can't be used with `new`.)

This is precisely why arrows are the default for callbacks. Look at `lib/hooks/use-websocket.ts`:

```ts
ws.onopen = () => {
  setConnected(true);
  reconnectAttempt = 0;
  resetHeartbeat();
  // ...
};

ws.onmessage = (event) => {
  // ...
  for (const handler of handlers) handler(msg);
};
```

These run *later*, fired by the WebSocket as events — a classic "detached call." If they were regular `function`s, `this` inside would be the `ws` (or undefined) depending on how the browser invokes them, and any reference to outer state would be fragile. As **arrows**, they don't care about `this` at all — they just reach out (via closure, article 02) to `setConnected`, `handlers`, `reconnectAttempt` in the surrounding module scope. The arrow + closure combo is *the* pattern for event handlers: lexical `this`, lexical variables, zero surprises.

Compare with the old pain this solved. Before arrows, you'd see:
```ts
const self = this;
button.onclick = function () { self.doThing(); }; // capture `this` manually
// or
button.onclick = function () { this.doThing(); }.bind(this);
```
Arrows make all of that vanish: `button.onclick = () => this.doThing()`. The arrow already closed over the right `this`.

### When NOT to use an arrow

On an **object method that needs `this` to be the object**, or a **prototype/class method**, you want a normal function so implicit binding works:
```ts
const obj = {
  name: "metro",
  greet() { return this.name; },        // ✅ normal method, this = obj
  greetBad: () => this.name,            // ❌ arrow, this = module scope, undefined
};
```
And class methods like `MinHeap.push` are normal functions for exactly this reason — they *need* `this` to be the instance.

---

## Why `bind` exists (and where you'd reach for it)

`bind` returns a new function with `this` permanently fixed. The classic use is handing a method to something that will call it plain:

```ts
// without bind, `this` would be lost when the timer calls it:
setTimeout(obj.method.bind(obj), 1000);
```

In a codebase that leans on arrows + closures (like ours), you rarely *need* `bind` — the arrow already captured the scope. Knowing it exists, and that it's how you'd fix a detached-method bug in pre-arrow or class-heavy code, is the point.

---

## The interview angle

- *"How does `this` work?"* → "It's determined by the call site, not the definition. Four rules in priority: `new` → the new object; `call`/`apply`/`bind` → the explicit object; `obj.method()` → `obj`; plain `fn()` → undefined in strict mode. Arrow functions opt out — they capture `this` lexically."
- *"`call` vs `apply` vs `bind`?"* → "`call` and `apply` invoke immediately with an explicit `this` — `call` takes args individually, `apply` takes an array. `bind` doesn't invoke; it returns a new function permanently bound."
- *"Why use an arrow for an event handler?"* → "So `this` and the surrounding variables stay lexical. When the WebSocket fires `onmessage` later, an arrow ignores how it's called and just closes over the module state I need — no `self = this`, no `.bind`."
- *"What breaks if I pass `obj.method` as a callback?"* → "It detaches from `obj`, so implicit binding is gone and `this` becomes undefined. Fix with `.bind(obj)` or wrap it in an arrow `() => obj.method()`."

---

## Concept checklist

- [ ] I can state the one rule: `this` is set by the call site, not the definition.
- [ ] I can list the four binding rules in priority order with an example of each.
- [ ] I can explain why a detached method loses its `this`.
- [ ] I can explain that arrows have no own `this` and capture it lexically.
- [ ] I can explain why our WS event handlers are arrows.
- [ ] I know when *not* to use an arrow (object/class methods needing `this`).
- [ ] I can explain `call` vs `apply` vs `bind`.

Next up: **[04 — Objects, prototypes & classes](./04-objects-prototypes-classes.md)** — the real inheritance model, using our `MinHeap`.
