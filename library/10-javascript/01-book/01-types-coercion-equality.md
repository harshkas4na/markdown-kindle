# 01 — Types, coercion & equality

Quick refresher to start, because I half-know this already. But "half-know" is exactly where the interview trick questions live, so I'm going to nail down the edges.

The mental model:

**JavaScript has two families of values: primitives (copied by value) and objects (shared by reference). Almost every "wait, why did that happen?" bug — equality surprises, mutation surprises, `NaN`, coercion — comes from not being crystal clear about which family a value is in.**

---

## The two families

**Primitives** — there are 7: `string`, `number`, `boolean`, `null`, `undefined`, `symbol`, `bigint`. They're immutable and **copied by value**. When I assign or pass one, the other side gets its *own copy*.

**Everything else is an object** — `{}`, `[]`, functions, `Date`, `Map`. They're **copied by reference**. When I assign or pass one, both sides point at the *same thing* in memory.

This is the whole game. Watch it bite in real code from `lib/utils.ts`:

```ts
const birth = new Date(dob);   // birth is an object (reference)
const today = new Date();      // today is a different object
```

`new Date()` gives an *object*. So if I ever wrote `const copy = today` and then mutated `copy.setFullYear(...)`, I'd be mutating `today` too — same reference. That's why `calculateAge` never mutates; it only *reads* (`.getFullYear()`, `.getMonth()`). Reading is always safe; mutation through a shared reference is the trap.

```ts
// value (primitive): independent copies
let a = 5; let b = a; b = 9;          // a is still 5

// reference (object): same thing
let x = { n: 5 }; let y = x; y.n = 9; // x.n is now 9 too
```

> **Interview phrasing:** "Primitives copy by value, objects copy by reference. Assigning or passing an object doesn't clone it — it shares it." If I can say that and give the `{n:5}` example, I've answered half the "spot the bug" questions there are.

---

## `null` vs `undefined` vs `NaN` (the three "nothings")

- **`undefined`** — "this was never given a value." A variable declared but unassigned, a missing object property, a function with no `return`, a missing argument.
- **`null`** — "intentionally empty." *I* put it there to mean "no value on purpose." Notice `saved-routes.ts` uses exactly this: `label: route.label || null` — store an explicit `null`, not an accidental `undefined`.
- **`NaN`** — "Not a Number," the result of invalid math (`new Date("garbage").getTime()` → `NaN`). The cursed part: **`NaN !== NaN`.** It's the only value not equal to itself. That's *why* `utils.ts` checks `isNaN(birth.getTime())` instead of `=== NaN` — the latter is always false.

```ts
if (isNaN(birth.getTime())) return null;  // can't write `=== NaN`, it never matches
```

And the famous gotcha: `typeof null === "object"`. It's a 1995 bug that can never be fixed without breaking the web. Just memorize it — it's a classic interview "gotcha."

---

## `==` vs `===` (and just use `===`)

- `===` (strict) — equal type **and** value, no conversion. `1 === "1"` is `false`.
- `==` (loose) — coerces types first, then compares. `1 == "1"` is `true`. The coercion rules are a maze (`[] == ![]` is `true`, `null == undefined` is `true` but `null == 0` is `false`).

The rule: **always `===`.** The one *useful* `==` is `x == null`, which is `true` for both `null` and `undefined` and nothing else — a handy "is this nothing?" check. But our code prefers being explicit; you'll see `?? undefined` and `|| null` instead.

> **Interview:** "I use `===` always. The only `==` worth knowing is `== null` as a null-or-undefined check. Loose equality coerces, and the coercion table has enough edge cases (`[] == 0`) that it's not worth the cognitive load."

---

## Truthiness (memorize the falsy list)

Every value is truthy *except* these 8 falsy ones:

```
false   0   -0   0n (bigint zero)   ""   null   undefined   NaN
```

Everything else is truthy — including `"0"`, `"false"`, `[]`, and `{}`. (Empty array and empty object are **truthy** — a common trap.)

This is why `getTimeAgo` and friends can branch on values directly, and why `if (!dob) return null` in `calculateAge` correctly catches `null`, `undefined`, *and* `""`. One check, three bad inputs handled — because they're all falsy.

The danger: `if (count)` is `false` when `count` is `0`, which might be a *valid* number. That's the bug `??` was invented to fix (article 06) — `0 ?? 5` is `0`, but `0 || 5` is `5`.

---

## Template literals & string coercion

`getTimeAgo` builds strings with backticks: `` `${diffMins}m ago` ``. The `${}` coerces whatever's inside to a string. Numbers become their digits, but watch objects — `` `${obj}` `` gives `"[object Object]"` unless the object has a custom `toString`. Arrays coerce by joining: `` `${[1,2,3]}` `` → `"1,2,3"`. Knowing *when* JS silently calls `toString`/`valueOf` is what separates "coercion is spooky" from "coercion is a defined algorithm."

---

## The interview angle

- *"`==` vs `===`?"* → "`===` checks type and value with no coercion; `==` coerces first. Always `===`, except `== null` as a nothing-check."
- *"Difference between `null` and `undefined`?"* → "`undefined` is the absence the language gives you — unset variable, missing property. `null` is the absence *you* assign on purpose. I store `null` deliberately, like `label || null`."
- *"What's `typeof null`?"* → "`'object'` — a legacy bug that can't be fixed. And `NaN !== NaN`, which is why you test with `isNaN`."
- *"Is `[]` truthy?"* → "Yes. Only 8 values are falsy: `false`, `0`, `-0`, `0n`, `''`, `null`, `undefined`, `NaN`. Empty array and empty object are both truthy."

---

## Concept checklist

- [ ] I can list the 7 primitives and explain value-copy vs reference-copy with an example.
- [ ] I can explain why mutating a shared object reference affects both variables.
- [ ] I can explain `null` vs `undefined` vs `NaN` and why `NaN !== NaN`.
- [ ] I know `typeof null === "object"` and that it's a legacy bug.
- [ ] I always reach for `===`, and I know `== null` is the one useful loose check.
- [ ] I can recite the 8 falsy values and explain why `[]` and `{}` are truthy.
- [ ] I can explain when JS coerces to string (template literals, `+` with a string).

Next up: **[02 — Scope, hoisting, closures & the TDZ](./02-scope-hoisting-closures.md)** — where JS stops being like other languages.
