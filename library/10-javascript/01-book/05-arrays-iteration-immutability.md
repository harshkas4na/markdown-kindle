# 05 — Arrays, iteration & immutability

Arrays are where day-to-day JS actually happens — every list of trips, every set of search results, every `split` on a string. The interview signal isn't "do you know `map`," it's "do you reach for the *right* iteration method, and do you avoid mutating things you shouldn't." Both are habits visible in our code.

The mental model:

**Prefer transforming data over mutating it. The array methods (`map`, `filter`, `reduce`, `some`, `find`) each answer one specific question and return a *new* value, leaving the original alone. Reaching for the method that matches the question — instead of a `for` loop with a mutable accumulator — is what makes code read like a sentence.**

---

## The method-per-question table

Each higher-order method exists to answer exactly one question. Knowing which is which means you never write the wrong loop:

| Question | Method | Returns |
|---|---|---|
| "transform every item" | `map` | a new array, same length |
| "keep only some items" | `filter` | a new array, ≤ length |
| "is there *at least one* that…?" | `some` | boolean |
| "are they *all*…?" | `every` | boolean |
| "give me the first that matches" | `find` | the item (or `undefined`) |
| "where is it?" | `findIndex` / `indexOf` | index (or `-1`) |
| "fold everything into one value" | `reduce` | anything |
| "do something for each (side effect)" | `forEach` | nothing |

The key shared idea: **`map`/`filter`/`reduce` don't touch the original array.** They return new ones. That's immutability, and it's why they compose so cleanly and why React (which compares references) loves them.

---

## These are all over our code

**`map` to transform** — `saved-routes.ts` converts DB rows to display objects:
```ts
const data: SavedRoute[] = await res.json();
return data.map(toDisplay);   // each snake_case row -> a camelCase display object
```
One row in, one object out, same count — that's the `map` signature. Note `toDisplay` is passed *by reference* (not `data.map(r => toDisplay(r))`); since `toDisplay` takes one arg, that's clean. (Careful with this trick when the function takes extra args — `["1","2"].map(parseInt)` famously breaks because `map` passes the index as `parseInt`'s radix.)

**`split` + `map(Number)` to parse** — `matching.ts` turns `"09:30"` into numbers:
```ts
const [h1, m1] = time1.split(":").map(Number);   // "09:30" -> ["09","30"] -> [9, 30]
```
Three things in one line: `split` makes an array of strings, `map(Number)` coerces each to a number, and destructuring (article 06) pulls them into `h1`/`m1`. `Number` here is the same "pass a function by reference" move — and unlike `parseInt`, `Number` ignores the index arg, so it's safe.

**`some` to ask "any match?"** — `isRouteSaved` in `saved-routes.ts`:
```ts
return routes.some(
  (r) => r.startStation === startStation &&
         r.endStation === endStation &&
         r.travelTime === travelTime
);
```
`some` short-circuits — it stops at the first `true`. Perfect for "is this route already saved?": we don't need to check all of them, just whether *one* matches. The boolean-returning question maps directly to the boolean-returning method.

**`in` for key existence** — not an array method but worth noting next to `some`: `isKnownStation` uses `stationName in stationIndex` to check a key exists on an object. Different tool, different question ("does this key exist?" vs "does any element match?").

---

## When a plain `for` loop is actually right

Our `getMinStationDistance` and `isSameDirection` use nested `for...of` loops, *not* `map`/`reduce`:

```ts
let minDist = Infinity;
for (const e1 of entries1) {
  for (const e2 of entries2) {
    if (e1.line === e2.line) {
      const dist = Math.abs(e1.seqIndex - e2.seqIndex);
      if (dist < minDist) minDist = dist;   // mutating a local accumulator
    }
  }
}
```

This is a *deliberate, correct* choice, and knowing *why* is the senior bit:

- It needs to **short-circuit / track a running minimum** across a nested loop — awkward with `reduce`.
- `isSameDirection` needs to **`return true` early** out of four nested loops the moment it finds a same-direction match — `for` with `return` is the cleanest way; you can't `return` out of a `forEach`.
- The mutation (`minDist = ...`) is a **local** variable, never a shared one. Mutating a local you just created is fine — the immutability rule is about not mutating data you were *handed*.

So the principle isn't "always use `map`." It's: **`map`/`filter`/`reduce` for transforming data into new data; `for...of` when you need early exit, complex control flow, or performance on a hot path.** Our matcher's inner loops run for every candidate trip, so tight `for` loops are the right call. `map` for clarity, `for` for control.

> The `forEach` vs `for...of` distinction worth knowing: you can `break`/`continue`/`return` out of `for...of`, but **not** out of `forEach` (the callback can't break the loop). If you need early exit, `for...of`.

---

## Immutability: why we don't mutate

Mutating shared data is the source of "spooky action at a distance" bugs (article 01's reference rule). The discipline:

**To "change" an array, produce a new one.**
```ts
const added   = [...list, newItem];           // append → new array
const removed = list.filter(x => x.id !== id); // remove → new array
const updated = list.map(x => x.id === id ? { ...x, done: true } : x); // edit one → new array
const sorted  = [...list].sort();              // sort COPIES first (sort mutates!)
```

That last one is a classic trap: **`sort`, `reverse`, `splice`, `push`, `pop`, `shift` all mutate in place.** If `list` came from somewhere shared (React state, a function argument), spread it first: `[...list].sort()`. The "new array methods" `toSorted`/`toReversed`/`with` do this for you now, but the spread-first habit is universal.

Why this matters beyond cleanliness: **React decides whether to re-render by comparing references.** If you mutate state in place, the reference is unchanged, and React thinks nothing happened — the screen goes stale. Returning new arrays/objects is *why* the whole React data flow works. Our hooks (`useTrips`, etc., from the Next.js course) lean on this — SWR replaces the data reference, components re-render.

---

## `reduce` — the one people fear

`reduce` folds a list into a single value by carrying an accumulator. It's just a `for` loop with the accumulator made explicit:

```ts
// sum
[1,2,3].reduce((acc, n) => acc + n, 0);          // 6

// build an object (like buildStationIndex, but functional)
allStations.reduce((idx, s) => {
  (idx[s.name] ??= []).push({ line: s.line, seqIndex: s.sequenceIndex });
  return idx;                                      // MUST return the accumulator
}, {} as Record<string, ...>);
```

That's literally what `buildStationIndex` does with a `for` loop instead — both are valid; the `for` version is arguably clearer for a grouping operation, which is exactly why our code uses it. The one rule with `reduce`: **always return the accumulator**, and **always pass the initial value** (the `0` / `{}` second arg) or it breaks on empty arrays.

---

## The interview angle

- *"`map` vs `forEach`?"* → "`map` transforms and returns a new array; `forEach` just runs a side effect and returns nothing. If I want a result, `map`; if I want an action, `forEach` — and `for...of` if I need to break early."
- *"How do you update an array immutably?"* → "Produce a new one: spread to add, `filter` to remove, `map` to edit one. Never `push`/`splice`/`sort` on shared data — those mutate. It matters because React compares references to decide re-renders."
- *"When would you use a plain `for` loop over `map`?"* → "When I need early exit, a running accumulator with control flow, or it's a hot path. My matcher uses nested `for...of` with early `return` because it bails the moment it finds a same-direction match — you can't return out of a `forEach`."
- *"What does `reduce` do?"* → "Folds a list into one value via an accumulator. It's a `for` loop where the accumulator is explicit — just remember to return it and seed the initial value."

---

## Concept checklist

- [ ] I can match each question to its method (`map`/`filter`/`some`/`find`/`reduce`).
- [ ] I can explain that `map`/`filter`/`reduce` return new arrays and don't mutate.
- [ ] I can explain the `data.map(toDisplay)` and `split(":").map(Number)` patterns.
- [ ] I know which array methods mutate (`sort`, `push`, `splice`, …) and how to avoid it.
- [ ] I can explain why immutability matters for React re-renders.
- [ ] I can justify when a `for...of` loop beats `map` (early exit, control flow, hot path).
- [ ] I can write a `reduce` and explain "always return the accumulator, always seed it."

Next up: **[06 — Modern syntax that's everywhere](./06-modern-syntax.md)** — destructuring, spread, `?.`, `??`, and reading my own code fluently.
