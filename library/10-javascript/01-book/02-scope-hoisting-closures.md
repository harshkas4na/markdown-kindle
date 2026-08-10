# 02 — Scope, hoisting, closures & the TDZ

This is where JavaScript stops being "like every other C-ish language" and becomes its own thing. The payoff at the end of this article — **the closure** — is, no exaggeration, the single most important concept in the language. Half our "clever" files are just closures wearing a costume.

The mental model:

**A scope is a box that holds variables. JavaScript decides which box a variable lives in by *where you wrote it in the source* (lexical scope), not by who called what at runtime. And here's the magic: a function permanently remembers the boxes it was born inside — even after those boxes "should" be gone. That memory is a closure.**

---

## Scope: where a name is visible

Three kinds of scope:

- **Global** — declared outside any function/block. Avoid; it's shared by everything.
- **Function** — `var` and function parameters live here. Visible anywhere in the function.
- **Block** — `let`/`const` live in the nearest `{ }` (an `if`, a `for`, any braces).

**Lexical (static) scope** is the key phrase: a function can see the variables of the place it was *written*, not the place it's *called from*. You can determine every variable's scope just by reading the source — you never need to run it. This is what makes closures predictable.

---

## `var` vs `let` vs `const` (and why `var` is retired)

```ts
var   x = 1;  // function-scoped, hoisted & initialized to undefined, can redeclare
let   y = 2;  // block-scoped, hoisted but NOT initialized (TDZ), can reassign
const z = 3;  // block-scoped, same TDZ, cannot reassign the binding
```

`const` doesn't mean "the value is frozen" — it means **the binding can't be re-pointed.** A `const` object is still mutable (`const o = {}; o.a = 1` is fine — article 01's reference rule). It just can't be reassigned to a *different* object.

Our codebase is `const` by default, `let` only when something genuinely reassigns — like `calculateAge`'s `let age = ...; age--`, or the WS singleton's `let singletonWs = null` that gets swapped on each (re)connect. That "`const` unless it must change" habit makes reassignment *visible* — when I see `let`, I know to watch that variable.

---

## Hoisting & the Temporal Dead Zone

**Hoisting:** declarations are "moved to the top" of their scope before any code runs. But the three kinds hoist differently:

- `function foo(){}` — fully hoisted. You can call it *above* where it's written. (That's why our files can call helper functions defined lower in the file.)
- `var x` — hoisted and initialized to `undefined`. Reading it before the assignment line gives `undefined`, not an error.
- `let`/`const` — hoisted but **left uninitialized.** Touching them before their declaration line throws `ReferenceError`. That gap between "scope starts" and "declaration line" is the **Temporal Dead Zone (TDZ).**

```ts
console.log(a); // undefined   (var: hoisted + initialized)
console.log(b); // ReferenceError  (let: in the TDZ)
var a = 1;
let b = 2;
```

The TDZ is a *feature* — it catches the bug where you use a variable before you meant to define it, instead of silently giving `undefined`. This is half the reason to prefer `let`/`const`.

> **Interview:** "Hoisting moves declarations up. `var` initializes to `undefined`; `let`/`const` stay uninitialized in the temporal dead zone and throw if touched early; function declarations are fully hoisted so you can call them before their line."

---

## The closure — the whole point

A **closure** is a function bundled together with the variables from the scope where it was *defined*. When a function "escapes" its birthplace (gets returned, stored, passed as a callback), it carries those variables with it. They don't get garbage-collected, because the function still references them.

Here's the textbook version:

```ts
function makeCounter() {
  let count = 0;                 // a private box
  return function () {           // this inner fn closes over `count`
    count++;
    return count;
  };
}
const next = makeCounter();
next(); // 1
next(); // 2  ← `count` survived, even though makeCounter already returned
```

`count` is *private* — nothing outside can touch it except through `next`. That's the superpower: **closures give you private, persistent state without a class.**

### Where this is literally in our code

Look at `lib/rate-limit.ts`. This is a closure pattern shipped to production:

```ts
const limiters = new Map<string, Ratelimit>();   // private cache, created once

function getLimiter(config: RateLimitConfig): Ratelimit {
  const key = `${config.limit}:${config.windowSeconds}`;
  let limiter = limiters.get(key);
  if (!limiter) {
    limiter = new Ratelimit({ /* ... */ });
    limiters.set(key, limiter);
  }
  return limiter;
}
```

`limiters` is declared once at module load and then *closed over* by `getLimiter`. Every call to `getLimiter` reaches back into that same `Map` — it persists between calls, it's not rebuilt, and nothing else in the app can reach it directly. That's **memoization via closure**: "build it once, remember it, hand back the cached one." (We'll see the exact same shape in `face-detection.ts` with a promise instead of a Map — article 09.)

The module itself is doing the `makeCounter` trick at file scale: the module-level `const limiters` is the private `count`, and the exported functions are the `next`. Article 11 makes that "a module *is* a closure" idea explicit.

### The classic closure-in-a-loop bug

The interview favorite, and the reason `let` exists:

```ts
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0); // prints 3, 3, 3
}
for (let i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0); // prints 0, 1, 2
}
```

With `var`, all three callbacks close over the **same** function-scoped `i`, which is `3` by the time they run. With `let`, each loop iteration gets a **fresh block-scoped binding**, so each callback captures its own `i`. This single example tests closures *and* scope *and* the event loop (why it runs later) at once — worth being able to explain cold.

---

## The interview angle

- *"What's a closure?"* → "A function plus the variables from where it was defined. It keeps those variables alive after the outer function returns, giving private persistent state. In my rate-limiter, a `getLimiter` function closes over a module-level `Map` to memoize limiter instances."
- *"`var` vs `let`?"* → "`var` is function-scoped and hoists to `undefined`; `let` is block-scoped with a temporal dead zone that throws if you read it early. `let`/`const` by default; the TDZ catches use-before-define bugs."
- *"Why does the loop print 3,3,3 with `var`?"* → "All callbacks share one function-scoped `i`, which is 3 when they finally run. `let` gives each iteration its own binding, so you get 0,1,2."

---

## Concept checklist

- [ ] I can explain lexical scope — scope is decided by where code is *written*.
- [ ] I can explain `var`/`let`/`const` differences including the TDZ.
- [ ] I know `const` freezes the binding, not the object.
- [ ] I can explain hoisting for functions, `var`, and `let`/`const` separately.
- [ ] I can define a closure and write `makeCounter` from memory.
- [ ] I can point at `getLimiter` and explain how it's a memoizing closure.
- [ ] I can explain the `var`-in-a-loop bug and why `let` fixes it.

Next up: **[03 — `this`, call/apply/bind & arrow functions](./03-this-and-functions.md)** — the other famously-confusing JS concept, demystified.
