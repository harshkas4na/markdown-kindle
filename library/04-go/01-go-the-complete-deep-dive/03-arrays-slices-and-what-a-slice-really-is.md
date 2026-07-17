# Arrays, Slices, and What a Slice Really Is

**Fast overview:** a Go slice is not "a resizable array" the way a beginner-friendly explanation usually puts it — it's a small, three-field struct (pointer, length, capacity) that points *at* an array, and almost every confusing slice bug in existence comes from not holding that struct in your head while you code. This is the single most important chapter in Part 1: understand this one value type completely and half of the "why did my data disappear" bugs you'll ever hit in Go become predictable instead of mysterious.

## Arrays first, briefly, because they're not what you'll actually use

```go
var a [5]int              // an array of exactly 5 ints, zero-valued
b := [3]string{"a", "b", "c"}
c := [...]int{1, 2, 3}    // length inferred from the literal: [3]int
```

An array's length is part of its **type** — `[5]int` and `[10]int` are different, incompatible types, the same way `int` and `int64` are. Arrays are copied by value: assigning an array, or passing one to a function, copies every element. This is exactly the behavior you'd expect from Chapter 2's "everything is a value" rule, and it's also exactly why arrays are rarely used directly in idiomatic Go — copying a large fixed-size array on every function call is wasteful, and the fixed length makes them inflexible for anything read from user input or built incrementally. Arrays exist mostly as the backing storage *underneath* a slice, and as a way to represent genuinely fixed-size data (a SHA-256 hash is naturally `[32]byte`).

## The slice header: three words, that's it

A slice is formally described in the spec as a descriptor of a contiguous segment of an underlying array. Concretely, at runtime, a slice value is three machine words:

| Field | Meaning |
|---|---|
| `ptr` | pointer to the first element the slice can see, inside some backing array |
| `len` | number of elements currently accessible (`len(s)`) |
| `cap` | number of elements available in the backing array from `ptr` onward, before a reallocation is needed (`cap(s)`) |

```go
s := make([]int, 3, 5)  // len=3, cap=5 — 2 elements of headroom, unused but reserved
fmt.Println(len(s), cap(s)) // 3 5
```

That's the whole trick. A slice **value** (the header) is copied by value just like anything else in Go — but the `ptr` field inside it still points at the *same* backing array. So copying a slice header is cheap (three words), but two slice headers with the same `ptr` are looking at the same underlying data. This single fact explains almost everything below.

## Slicing shares memory — until it doesn't

```go
original := []int{1, 2, 3, 4, 5}
window := original[1:3]     // len=2, cap=4 — shares original's backing array
window[0] = 99
fmt.Println(original)       // [1 99 3 4 5] — the mutation is visible in `original`
```

`window` is not a copy of the data — it's a new three-word header pointing into the *same* backing array as `original`, starting at index 1. Writing through `window` writes through `original` too, because there is, at the byte level, only one array. This is the behavior new Go programmers expect the least and hit the soonest: two variables that look independent are actually aliases of the same memory.

## `append` and the reallocation trap

This is where the real bugs live. `append` either grows the slice **in place** (if `cap` has headroom) or **allocates a brand-new backing array** (if it doesn't) and copies everything over — and which one happens is invisible at the call site unless you specifically check `cap`.

```go
func addItem(items []int) []int {
    return append(items, 99)
}

base := make([]int, 3, 3)   // len=3, cap=3 — NO headroom
result := addItem(base)
result[0] = -1
fmt.Println(base[0])        // 0 — unaffected! append had to reallocate,
                             // so `result` now points at a completely different array
```

Now change one number:

```go
base2 := make([]int, 3, 10)  // len=3, cap=10 — headroom exists
result2 := addItem(base2)
result2[0] = -1
fmt.Println(base2[0])        // -1 — affected! append grew in place, same backing array
```

Same function, same-looking call, opposite behavior — purely because of a capacity number the caller never sees printed anywhere. This is the canonical Go bug: a function appends to a slice parameter and returns the result, the caller only uses the return value inconsistently (sometimes reading the original variable instead), and whether the mutation "worked" depends on a capacity coincidence upstream. The fix is a discipline, not a language feature: **always use the return value of `append`, and never assume a slice parameter is or isn't shared** — treat every slice you didn't just create yourself as potentially aliased.

Go's growth strategy when reallocation is needed: for small slices, capacity roughly **doubles**; once a slice gets large (historically around a few thousand elements, tuned periodically by the runtime team), growth slows to a smaller multiplier — around 1.25× — to avoid wasting memory on very large slices. You should never hard-code an assumption about the exact growth factor; the guarantee that matters is only that repeated `append` calls have **amortized O(1)** cost, not that any single call is cheap.

## `make`, capacity, and pre-sizing

```go
s1 := make([]int, 5)      // len=5, cap=5 — 5 zero-valued elements, ready to index
s2 := make([]int, 0, 5)   // len=0, cap=5 — empty, but 5 elements of backing storage reserved
```

If you know roughly how many elements you'll append, pre-sizing capacity with `make([]T, 0, n)` and appending into it avoids repeated reallocation-and-copy cycles — a real, measurable performance habit in hot loops, and one `go vet`-adjacent linters (`prealloc`) will flag when it's missing in an obvious loop.

## Full slice expressions: capping capacity on purpose

```go
s := []int{1, 2, 3, 4, 5}
window := s[1:3]        // len=2, cap=4 (extends to end of backing array)
safe := s[1:3:3]        // len=2, cap=2 (three-index form: low:high:max)
```

The three-index slice expression `s[low:high:max]` sets the resulting slice's capacity to `max - low`, instead of letting it silently extend to the rest of the backing array. This is the direct fix for the aliasing problem above: if you hand out a sub-slice of something you own and don't want the recipient's future `append` calls to accidentally overwrite data past `high` (because that memory happens to still be part of your backing array), cap the capacity explicitly with the three-index form. The very next `append` to `safe` is then guaranteed to reallocate rather than silently corrupt `s`'s data past index 3.

## nil slices vs. empty slices: same length, different identity

```go
var a []int          // nil slice: len=0, cap=0, a == nil is true
b := []int{}         // empty slice: len=0, cap=0, b == nil is false
c := make([]int, 0)  // also empty, non-nil

fmt.Println(len(a), len(b))  // 0 0 — behave identically for len/range/append
fmt.Println(a == nil, b == nil) // true false
```

For almost every practical purpose — `len()`, `range`, `append` — a nil slice and an empty slice behave identically; you can `append` to a nil slice with no special-casing required, and it will allocate a backing array on first use exactly like any other slice would on overflow. The distinction matters in two places: an explicit `== nil` check (common when a function's zero-value return communicates "nothing here" versus "an empty result"), and JSON encoding, where `encoding/json` marshals a nil slice as `null` and an empty-but-non-nil slice as `[]` — a detail that has caused real API contract bugs when a caller expects `[]` and gets `null` instead. *Connect the dot:* this exact nil-vs-empty distinction reappears for maps in the next chapter, with a sharper edge — a nil map panics on write, where a nil slice does not.

## `copy`: the escape hatch when you genuinely need independence

```go
src := []int{1, 2, 3}
dst := make([]int, len(src))
n := copy(dst, src)   // n == 3; dst is now a fully independent copy
dst[0] = 99
fmt.Println(src[0])   // 1 — unaffected
```

`copy(dst, src)` copies `min(len(dst), len(src))` elements and returns the count actually copied — it never grows `dst`, so you must size the destination yourself first. This is the tool to reach for whenever you deliberately want a slice that does **not** alias its source — most commonly when handing external code a value you don't want it to be able to mutate behind your back, or when trimming a large backing array down so the garbage collector can reclaim the unused tail (append-and-reslice-tricks that keep a reference to a huge original array otherwise leak memory silently, since the whole backing array stays alive as long as *any* slice still points into it).

*Connect the dot:* everything in this chapter is really one idea in five costumes — a slice's identity is its backing array, not its header — and it's the exact same shape of idea you'll meet again in Chapter 5 when we cover why mutating through a slice or map *parameter* works even though Go passes the header by value: the header is copied, the thing it points at is not.

Next: maps, structs, and embedding — Go's answer to grouping and reusing data without a class system.
