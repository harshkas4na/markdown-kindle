# 04 — Objects, prototypes & classes

Now Level 2. We use objects constantly — every API response, every config, every `{ start_station, end_station }`. But the thing interviewers actually probe is the layer *underneath* objects: the **prototype chain**, which is JavaScript's real (and weird) inheritance model. `class` is just a friendly mask over it.

The mental model:

**Every object has a secret link to another object called its prototype. When you ask for a property and the object doesn't have it, JS doesn't give up — it follows that link to the prototype, then *its* prototype, and so on, until it finds the property or hits `null`. That chain of links is the prototype chain, and it *is* inheritance in JavaScript. `class` is syntax sugar that sets up these links for you.**

---

## Objects: the basics we lean on

An object is a bag of key→value pairs. Keys are strings (or symbols); values are anything. We use them three ways constantly:

```ts
// 1. As records (the shape of data) — saved-routes.ts
const route = { start_station: "Rajiv Chowk", end_station: "Kashmere Gate" };

// 2. As lookup maps — matching.ts station index
const index: Record<string, { line, seqIndex }[]> = {};
index["Rajiv Chowk"] = [/* ... */];

// 3. As config bundles — rate-limit.ts
const config = { limit: 30, windowSeconds: 60 };
```

Two access styles: `route.start_station` (dot, when you know the key) and `index[name]` (bracket, when the key is dynamic/computed). The bracket form is what makes objects usable as dictionaries — `index[name]` where `name` is a variable.

A subtle but important point for the lookup-map use: a plain `{}` actually **inherits** properties like `toString`, `constructor`, `hasOwnProperty` from its prototype. So `"toString" in index` is `true` even if you never set it. That's a real footgun when an object is used as a user-keyed dictionary — and it's one reason `Map` exists (article 13). For our station index the keys are controlled station names, so a plain object is fine.

---

## The prototype chain — the real inheritance

Here's the part that makes JS different from Java/C++. There are no classes under the hood — there are just objects linking to other objects.

```ts
const arr = [1, 2, 3];
arr.map(x => x * 2);   // where does `.map` come from? arr doesn't have it.
```

`arr` doesn't own a `map` property. JS looks up the chain: `arr` → `Array.prototype` (has `map`, `filter`, `push`, …) → `Object.prototype` (has `toString`, `hasOwnProperty`) → `null`. It finds `map` on `Array.prototype` and calls it with `this = arr`. **That walk is the whole mechanism.** Every array shares the *same* `Array.prototype` methods — they're not copied onto each array, they're inherited by link. (That's also why it's memory-efficient: a million arrays, one `map` function.)

You can see the chain directly:
```ts
Object.getPrototypeOf([]) === Array.prototype          // true
Object.getPrototypeOf(Array.prototype) === Object.prototype  // true
Object.getPrototypeOf(Object.prototype) === null       // top of the chain
```

Property **lookup** walks up the chain. Property **writes** (`obj.x = 1`) always happen on the object itself, never up the chain. And `obj.hasOwnProperty("x")` asks "is this *yours*, or inherited?" — the distinction the chain creates.

---

## `class` is sugar — see it with our `MinHeap`

Our `lib/metro/graph.ts` has a hand-written `MinHeap`. It looks like a class from any other language:

```ts
class MinHeap {
  private heap: { state: State; cost: number }[] = [];

  push(state: State, cost: number) {
    this.heap.push({ state, cost });
    this.bubbleUp(this.heap.length - 1);
  }

  pop(): { state: State; cost: number } | undefined { /* ... */ }

  get size() { return this.heap.length; }

  private bubbleUp(i: number) { /* ... */ }
  private sinkDown(i: number) { /* ... */ }
}
```

What the `class` keyword actually does here, desugared:

1. **`MinHeap` is really a function** (the constructor). `new MinHeap()` creates a fresh object, links it to `MinHeap.prototype`, runs the constructor body with `this` = the new object, and returns it. (That's rule 1 of `this` from article 03.)
2. **The methods (`push`, `pop`, `bubbleUp`, `sinkDown`) live on `MinHeap.prototype`,** not on each instance. So `new MinHeap()` doesn't copy four functions — it just *links* to the one shared prototype. Call `heap.push(...)` and JS walks `heap` → `MinHeap.prototype`, finds `push`, runs it with `this = heap`.
3. **`get size()`** is an accessor property — `heap.size` *looks* like a field but runs a function. (Getters/setters are article 14's metaprogramming.)
4. **`private heap`** is a TypeScript-enforced privacy (compile-time). JS's own true-private is the `#field` syntax. Either way the intent: `heap` is internal state, the public surface is `push`/`pop`/`size`.

So the class is doing exactly what you'd otherwise hand-wire with `function MinHeap(){}` + `MinHeap.prototype.push = function(){}`. The `class` keyword is *only* nicer syntax — there is no new mechanism. Being able to say that out loud ("classes are sugar over prototypes and constructor functions") is the senior answer.

### The instance-vs-prototype split, made concrete

```ts
const a = new MinHeap();
const b = new MinHeap();
a.heap === b.heap                              // false — each has its OWN data
Object.getPrototypeOf(a).push === Object.getPrototypeOf(b).push  // true — SHARED method
```

Per-instance **data**, shared **behavior**. That's the design the prototype chain gives you for free.

---

## Three ways to make a linked object (good to recognize)

```ts
// 1. class (sugar) — what we use
class MinHeap { /* ... */ }

// 2. constructor function (what class compiles toward)
function MinHeap() { this.heap = []; }
MinHeap.prototype.push = function () { /* ... */ };

// 3. Object.create — link directly to a prototype, no constructor
const proto = { push() {} };
const heap = Object.create(proto);  // heap's prototype IS proto
```

All three produce the same thing: an object whose prototype has the shared methods. `class` is the one to write; the other two are what you'll see in libraries and what the interviewer means by "do you know what's under the hood?"

---

## Copying objects (the reference trap, revisited)

From article 01: objects are references, so `const copy = original` shares, doesn't clone. To actually copy:

```ts
const shallow = { ...route };              // spread: new top-level object
const shallow2 = Object.assign({}, route); // same, older syntax
const deep = structuredClone(route);       // true deep clone (modern, built-in)
```

**Shallow** copies the top level but nested objects are *still shared references*. `structuredClone` (or the old `JSON.parse(JSON.stringify(x))` hack, which drops functions/dates) goes all the way down. Our `toDisplay` in `saved-routes.ts` is doing a deliberate, explicit shallow remap — building a *new* object field-by-field rather than mutating the input. That immutability instinct is article 05.

---

## The interview angle

- *"How does inheritance work in JS?"* → "Prototypally. Every object links to a prototype object; property lookup walks that chain until it finds the property or hits null. Methods live on the shared prototype, data lives on the instance."
- *"What is a `class` really?"* → "Sugar. `class` defines a constructor function and puts the methods on its `.prototype`. `new` creates an object linked to that prototype. No new mechanism — just nicer syntax over prototypes."
- *"Where do a class's methods live — on each instance or shared?"* → "On the prototype, shared. Each `new` instance only holds its own data and a link to the one prototype. That's why a million instances don't duplicate the methods."
- *"Shallow vs deep copy?"* → "Spread/`Object.assign` copy the top level but share nested references; `structuredClone` deep-copies. The classic bug is mutating a nested object you thought you'd cloned."

---

## Concept checklist

- [ ] I can explain the prototype chain and how property lookup walks it.
- [ ] I can explain that methods live on the prototype, data on the instance.
- [ ] I can desugar our `MinHeap` class into constructor-function + prototype terms.
- [ ] I can explain what `new` does step by step.
- [ ] I know the three ways to create a linked object (`class`, constructor fn, `Object.create`).
- [ ] I can explain `hasOwnProperty` and why `"toString" in {}` is `true`.
- [ ] I can explain shallow vs deep copy and when each shares references.

Next up: **[05 — Arrays, iteration & immutability](./05-arrays-iteration-immutability.md)** — the methods that run our matching scorer.
