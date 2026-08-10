# 11 — Modules, the runtime & `globalThis`

Article 10 kept saying "modules run once" and "module scope is private." This article makes good on that — what a module actually *is*, how `import`/`export` really behave, and the thing that trips up every Next.js dev: the same `.ts` file might run on a *server* or in a *browser*, two completely different runtimes with different globals. Our codebase guards for this constantly.

The mental model:

**A module is a file with its own private scope that runs exactly once, the first time it's imported, and then caches its exports. `import`/`export` aren't copy-paste — they're *live links* to those single-instance exports. And the global environment around a module isn't fixed: the same code can run in Node (server) where there's no `window`, or a browser where there's no filesystem. Robust code checks which world it's in.**

---

## ESM vs CommonJS (the two module systems)

JavaScript has two module syntaxes, and you should know both on sight:

```ts
// ESM (ES Modules) — what we write, the standard
import { allStations } from "@/lib/metro-data";
export function getMinStationDistance() {}
export default Component;

// CommonJS (CJS) — older Node default
const { allStations } = require("./metro-data");
module.exports = { getMinStationDistance };
```

The differences that matter:

- **ESM is static.** `import`s are resolved *before* the code runs — they're hoisted, and the names are fixed at parse time. This is what enables **tree-shaking**: the bundler can see exactly which exports you use and drop the rest. CJS `require` is a runtime function call, so it can't be analyzed as cleanly.
- **ESM imports are live read-only bindings,** not copies. If a module exports a `let` that changes, importers see the new value. (You can't reassign it from outside, though — exports are read-only on the import side.)
- **ESM is always strict mode** and async-friendly (top-level `await` works). CJS is synchronous and loads on first `require`.

Our codebase is pure ESM (it's `.ts` with `import`/`export`), and the `@/` you see everywhere is just a path alias (`@/lib/...` → repo root) configured in `tsconfig` — not a special module feature, just a nicer way to write paths.

---

## Modules run **once** — the fact article 10 depended on

This is the single most important runtime property of modules, and it's what makes the closure-singletons of article 10 work:

**The first time a module is imported, its top-level code runs top to bottom. The resulting exports are cached. Every *later* import of that same module — from anywhere — gets the cached exports without re-running the file.**

So when `lib/matching.ts` does:
```ts
const stationIndex = buildStationIndex();   // runs ONCE, at first import
```
`buildStationIndex()` executes a single time, no matter how many files import `getMinStationDistance`. The index is built once and shared. Same with `const limiters = new Map()` in the rate-limiter and `let singletonWs = null` in the WebSocket file — **module-level state is effectively a singleton because the module body runs once.** That's not a coincidence we exploit; it's the *guarantee* the whole pattern rests on. "Run expensive setup at module top-level" = "do it once for the lifetime of the process/page."

(One caveat worth knowing: in dev with hot-reloading, modules *can* re-execute on file changes, which is why you sometimes see "why did my singleton reset?" — that's the dev server, not the language.)

---

## The two runtimes: server vs browser

Here's the Next.js-flavored gotcha. A `.ts` file isn't tied to one environment. The *same* module might be bundled into:

- **The server** (Node) — has `process`, `Buffer`, filesystem; has **no** `window`, `document`, `localStorage`, `WebSocket`.
- **The browser** — has `window`, `document`, `localStorage`, `fetch`, `WebSocket`; has **no** `process` or filesystem.

If module-level code touches a browser-only global, it crashes on the server during SSR (and vice versa). So defensive code **feature-detects the environment**. Our WebSocket file does exactly this at module top-level:

```ts
const supabase = typeof window !== "undefined" ? createClient() : null;
```

This runs when the module is imported — which on the server happens during SSR. `typeof window !== "undefined"` asks "am I in a browser?" `typeof` is special here: it's the *only* safe way to check for a variable that might not be declared at all — `window` on the server isn't `undefined`, it's a `ReferenceError` to even mention... except `typeof undeclaredThing` returns the string `"undefined"` instead of throwing. That's why the idiom is `typeof window !== "undefined"` and never `window !== undefined`.

The same guard wraps the auth listener:
```ts
if (typeof window !== "undefined" && supabase) {
  supabase.auth.onAuthStateChange(...);   // only wire this up in the browser
}
```
And in `face-detection.ts`:
```ts
if (typeof window === "undefined") {
  return { hasFace: true, faceCount: 0, faceSize: 0 };   // server: skip, can't run WASM
}
```

This is the language-level version of the Next.js course's `"use client"` boundary: the framework decides *where* a module runs; these `typeof window` guards make a module *survive* running in the wrong place. Module-level code is the dangerous spot because it runs at import time on whichever side bundles it — so any browser-only access up there needs a guard.

---

## `globalThis` — the one global to rule them all

Historically the global object had different names: `window` (browser), `global` (Node), `self` (web workers). `globalThis` is the standardized name that works everywhere — "the global object, whatever environment I'm in." You reach for it when you genuinely need a cross-environment global (rare in app code; common in libraries). For app code, the `typeof window` check is usually what you actually want, because you're asking "am I in the browser?" not "give me the global object."

A related pattern you'll see in Node/Next to survive hot-reload: stashing a singleton on `globalThis` so it persists across module re-execution (`globalThis.__myClient ??= createClient()`). It's the "modules run once... unless dev reloads them" escape hatch.

---

## The interview angle

- *"ESM vs CommonJS?"* → "ESM is the standard `import`/`export`, statically analyzable so it tree-shakes, with live read-only bindings and strict mode. CommonJS is Node's older `require`/`module.exports`, runtime-resolved and synchronous. Modern code is ESM."
- *"What happens when you import a module twice?"* → "It runs once. The first import executes the file top-to-bottom and caches the exports; later imports get the cache. That's why module-level state acts as a singleton — my station index and rate-limiter Map are built once and shared."
- *"Why `typeof window !== 'undefined'`?"* → "To detect the browser vs server runtime. The same module can run during SSR in Node, where browser globals don't exist. `typeof` is the only safe check because it returns `'undefined'` for an undeclared variable instead of throwing. I guard browser-only setup like creating a WebSocket or running WASM."
- *"What's `globalThis`?"* → "The standardized global object across browser/Node/workers, replacing `window`/`global`/`self`. Useful for cross-environment code and for persisting singletons across dev hot-reload."

---

## Concept checklist

- [ ] I can contrast ESM and CommonJS, including tree-shaking and live bindings.
- [ ] I can explain "a module runs once and caches its exports" and tie it to our singletons.
- [ ] I can explain why module-level state is effectively a singleton.
- [ ] I can explain the server vs browser runtime split and which globals each lacks.
- [ ] I can explain `typeof window !== "undefined"` and why `typeof` specifically.
- [ ] I can point at the WS and face-detection guards and say what they prevent.
- [ ] I know what `globalThis` is and one reason to use it.

Next up: **[12 — Memory, references & leaks](./12-memory-and-leaks.md)** — garbage collection, and how our cleanup code avoids leaks.
