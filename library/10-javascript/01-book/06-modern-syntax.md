# 06 — Modern syntax that's everywhere

This one's less "concept" and more "fluency." Modern JS (ES2015+) added a pile of syntax that's now *everywhere* in our code, and reading my own files fast means these have to be automatic — I shouldn't have to stop and parse `singletonWs?.readyState`. Each of these is small; together they're the difference between reading code and decoding it.

The mental model:

**Most modern syntax exists to express one of two intents more safely: "pull this value out" (destructuring, optional chaining) or "spread this collection out" (spread/rest). And a cluster of them — `?.`, `??`, `??=` — exist specifically to handle `null`/`undefined` *without* the truthiness bugs from article 01.**

---

## Destructuring — "pull these out by name/position"

**Object destructuring** unpacks by key. Straight from `rate-limit.ts`:
```ts
const { success, limit, remaining, reset } = await limiter.limit(key);
```
That's four `const`s in one line, each grabbing the matching property off the returned object. Versus the noise of `const success = result.success; const limit = result.limit; …`.

**Array destructuring** unpacks by position — `matching.ts`:
```ts
const [h1, m1] = time1.split(":").map(Number);   // h1 = first, m1 = second
```

Power moves you'll see and should recognize:
```ts
const { label = "Untitled" } = route;     // default if key is missing/undefined
const { start_station: from } = route;    // rename while unpacking (from = route.start_station)
function f({ url, enabled = true }) {}     // destructure a param object with a default
```
That last one is exactly our `useWebSocket({ url, enabled = true })` signature — destructure the options object right in the parameter list, with `enabled` defaulting to `true`. Clean API surface, no `options.url` everywhere inside.

> Note: array destructuring is the *consumer* side of the iteration protocol (article 13) — `const [a, b] = thing` works on anything iterable, not just arrays.

---

## Spread `...` — "expand a collection in place"

Spread takes an iterable/object and splays its contents out where you wrote it.

```ts
const copy = [...messageQueue];        // new array with the same items (article 05 immutability)
const merged = { ...defaults, ...overrides }; // later keys win — config merge pattern
const max = Math.max(...numbers);      // pass array items as individual args
```

The merge-with-override (`{ ...a, ...b }`, where `b`'s keys win) is one of the most useful patterns in the language — it's how you update one field immutably: `{ ...trip, status: "active" }`.

---

## Rest `...` — "collect the leftovers"

Same three dots, opposite job: **gather** multiple things into one array/object. Our `cn` helper in `lib/utils.ts`:
```ts
export function cn(...inputs: ClassValue[]) {   // collect ALL args into one array
  return twMerge(clsx(inputs));
}
cn("a", "b", cond && "c");   // inputs === ["a", "b", false]
```
`...inputs` in a parameter list means "however many arguments they pass, bundle them into the `inputs` array." It's the modern, type-safe replacement for the old `arguments` object — and it's a *real* array (so `map`/`filter` work), which `arguments` never was.

Rule of thumb: **spread expands (on the right of `=` / in a call), rest collects (on the left / in a param list).** Same `...`, decided by position.

---

## Optional chaining `?.` — "stop if it's nullish"

`a?.b` returns `undefined` if `a` is `null`/`undefined`, instead of throwing `Cannot read property 'b' of undefined`. The WS code is full of it:
```ts
if (singletonWs?.readyState === WebSocket.OPEN) { /* ... */ }
```
If `singletonWs` is `null` (no connection yet), `singletonWs?.readyState` is just `undefined` — the comparison is safely `false`, no crash. Without `?.` that line would throw whenever the socket is null, which is *exactly* the state it's checking for. It also works on calls and indexes:
```ts
session?.access_token        // property
arr?.[0]                     // index
onClose?.()                  // call only if it exists
```
And from the WS auth code: `if (!session?.access_token) return;` — "if there's no session, or there is but it has no token, bail." One operator, both nullish layers handled.

---

## Nullish coalescing `??` — "default, but only for null/undefined"

This is the fix for article 01's falsy trap. `a ?? b` gives `b` **only** when `a` is `null` or `undefined` — *not* when `a` is `0`, `""`, or `false`.

The graph builder relies on this distinction:
```ts
weightTime: times[i] ?? 2.5,        // if no measured time, default 2.5 — but 0 stays 0
weightDistance: distances[i] ?? 1.3,
```
If a real travel time were `0` (hypothetically), `times[i] ?? 2.5` keeps the `0`. The old `times[i] || 2.5` would wrongly replace `0` with `2.5`, because `0` is falsy. **`??` checks for "nothing"; `||` checks for "falsy."** That difference is a guaranteed interview question.

Compare with the deliberate `||` use in `saved-routes.ts`:
```ts
label: route.label || null,    // empty string OR undefined both become null
```
Here `||` is *correct* — we genuinely want an empty `label` string to collapse to `null`. So the rule isn't "always `??`": it's **`??` when only null/undefined should trigger the default, `||` when any falsy value should.** Picking the right one on purpose is the skill.

---

## `??=` and friends — logical assignment

`x ??= y` means "assign `y` to `x` only if `x` is currently null/undefined." It's `x = x ?? y` compressed. The functional version of `buildStationIndex` would use it:
```ts
(index[s.name] ??= []).push(entry);   // if no array yet, create one, then push
```
"Make sure this key has an array, then use it." There's also `||=` (assign if falsy) and `&&=` (assign if truthy) — same falsy-vs-nullish distinction as their non-assignment cousins.

---

## Short-circuiting `&&` / `||` as control flow

`&&` and `||` don't return booleans — they return *one of their operands*, evaluated left to right, stopping early:
- `a && b` → returns `a` if `a` is falsy, else `b`. Used as "do `b` only if `a`": `cond && doThing()`.
- `a || b` → returns `a` if `a` is truthy, else `b`. The classic "default" before `??` existed.

This is why our `cn("a", cond && "c")` works — if `cond` is false, `cond && "c"` is `false`, which `clsx` ignores; if true, it's `"c"`. And it's why JSX does `{isLoading && <Spinner/>}`. Knowing these return *values*, not booleans, is what makes the idioms click.

---

## The interview angle

- *"`??` vs `||`?"* → "`||` falls back on any falsy value — `0`, `''`, `false` included. `??` falls back *only* on `null`/`undefined`. So for a numeric default where `0` is valid, you need `??`, or `0` gets wrongly replaced. My graph uses `times[i] ?? 2.5` so a real `0` survives."
- *"What does `?.` do?"* → "Optional chaining short-circuits to `undefined` if the left side is null/undefined instead of throwing. `singletonWs?.readyState` is safe even when the socket is null — which is the exact case it's testing."
- *"Spread vs rest?"* → "Same `...`. Spread expands a collection into pieces — copying an array, merging objects, passing args. Rest collects pieces into one — gathering function arguments into a real array, like my `cn(...inputs)`."
- *"Do `&&` and `||` return booleans?"* → "No — they return one of the operands and short-circuit. `cond && value` returns `value` only if `cond` is truthy, which is why it works as inline conditional rendering."

---

## Concept checklist

- [ ] I can destructure objects and arrays, including renames, defaults, and param-list destructuring.
- [ ] I can explain spread vs rest and tell which is which by position.
- [ ] I can explain `?.` and why it's safe when the left side is null.
- [ ] I can explain `??` vs `||` and give the `0` example where they differ.
- [ ] I can explain `??=` / `||=` / `&&=` logical assignment.
- [ ] I know `&&`/`||` return operands (not booleans) and short-circuit.
- [ ] I can read `if (!session?.access_token) return;` aloud and explain both nullish checks.

Next up: **[07 — The event loop & the two queues](./07-event-loop.md)** — Level 3 begins, and this is the big one.
