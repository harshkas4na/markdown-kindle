# Pointers and Value Semantics

**Fast overview:** Go passes everything by value — always, no exceptions — and once that single sentence is fully internalized, pointers stop being a scary C-flashback topic and become exactly what they are: a way to opt into sharing instead of copying, on purpose, at specific call sites. This chapter nails down the value-semantics rule precisely (including the trick that makes slices and maps *feel* like they mutate through function calls even though their headers are copied), when to reach for a pointer receiver on a method, and a first, deliberately incomplete look at escape analysis — the compiler decision that decides whether any of this ends up on the stack or the heap.

## The rule, stated once, precisely

**Every function call in Go copies its arguments.** No exceptions, no special cases for "big" types, no reference-passing keyword. When you pass a struct, you pass a full copy of that struct's fields. When you pass an array, you copy every element (Chapter 3). When you pass an `int`, you copy the int. This is true of every single value in the language, always.

```go
type Point struct{ X, Y int }

func moveRight(p Point) {
    p.X++          // mutates the local copy only
}

func moveRightPtr(p *Point) {
    p.X++          // dereferences the pointer, mutates the pointee
}

pt := Point{X: 1, Y: 2}
moveRight(pt)
fmt.Println(pt.X)     // 1 — unchanged, moveRight only had a copy

moveRightPtr(&pt)
fmt.Println(pt.X)     // 2 — changed, moveRightPtr had the real address
```

`&pt` takes the address of `pt`, producing a `*Point`. `*p` inside `moveRightPtr` dereferences that pointer back to the `Point` value it points at. There's no pointer arithmetic in Go — you cannot do `p + 1` to walk to "the next `Point` in memory" the way you could in C — pointers exist for exactly one purpose in Go: referring to a specific, shared piece of memory so you can read or mutate it without copying, or share access to it across multiple call sites. Every pointer is also tracked by the garbage collector, which is why Go pointers are memory-safe in a way C's are not: you cannot construct a pointer to arbitrary memory, dereference a freed pointer, or walk off the end of an allocation and land in someone else's data.

## Why slices and maps *look* like they break the rule

This is the single most common "wait, I thought everything was copied" moment in Go, and Chapter 3 and 4 already gave you the answer without naming it yet:

```go
func addOne(nums []int) {
    nums[0] = 99   // mutates the shared backing array
}

s := []int{1, 2, 3}
addOne(s)
fmt.Println(s[0])   // 99 — it changed!
```

`nums` really is a copy — a copy of the three-word slice **header** (pointer, len, cap). But that copied header's pointer field still points at the exact same backing array as `s`'s header does. Writing `nums[0] = 99` follows that shared pointer and mutates the one array both headers describe. **The header was copied by value, exactly as the rule promises — it's the data the header points at that was never copied**, because slicing and passing a slice never implicitly copies the backing array. The identical logic applies to maps (a reference type, one pointer-sized word under the hood) and channels (also a reference type, Chapter 11). It does *not* apply to arrays or plain structs — passing a `[3]int` or a `Point` genuinely copies every byte of the value, with no shared backing store to alias.

This is why the earlier `moveRight` example above — an ordinary struct, passed by value — genuinely does not mutate the caller's copy, while a slice or map argument, passed by that exact same value-copying rule, appears to. Both examples follow the same rule; they just copy different things (a struct's fields directly, versus a small header that happens to alias external memory).

## Pointer receivers vs. value receivers on methods

```go
type Counter struct{ n int }

func (c Counter) ValueInc()  { c.n++ }   // mutates a copy — useless
func (c *Counter) PtrInc()   { c.n++ }   // mutates the real receiver

c := Counter{}
c.ValueInc()
fmt.Println(c.n)   // 0

c.PtrInc()
fmt.Println(c.n)   // 1 — Go automatically takes &c for you here
```

A method's receiver — the `(c Counter)` or `(c *Counter)` before the method name — follows exactly the same value-vs-pointer rule as a function parameter, because that's all a receiver is: syntactic sugar for a first argument. `ValueInc` receives a full copy of `Counter`; any mutation dies with that copy. `PtrInc` receives the real address and mutates the caller's actual value. Go quietly inserts the `&` for you when you call `c.PtrInc()` on an addressable value like a local variable — this is a compiler convenience, not evidence that value and pointer receivers behave the same.

The decision of which receiver type to use comes down to three questions, roughly in priority order:

1. **Does the method need to mutate the receiver, or take the address of a field?** If yes, it must be a pointer receiver — a value receiver physically cannot mutate the caller's original.
2. **Is the struct large enough that copying it on every method call is a real cost?** Structs with many fields, or an embedded array, are cheaper to pass as a pointer (one machine word) than to copy wholesale on every call.
3. **Consistency**: if *any* method on a type needs a pointer receiver, the strong convention is to make *all* of that type's methods pointer receivers, even ones that don't strictly need to mutate anything — a type with a mix of value and pointer receivers is a common source of confusion about whether a given method call is safe to use on a non-addressable value (like a map element, which is not addressable in Go, so `m[key].PtrMethod()` doesn't compile if the map holds struct values rather than pointers).

*Connect the dot:* this exact receiver choice is also what decides whether a type satisfies an interface — a method with a pointer receiver is only in the **method set** of `*T`, not `T` itself, which is a subtle but real gotcha covered fully once interfaces are on the table in Chapter 7.

## `new` vs. a composite literal's address

```go
p1 := new(Point)          // *Point, pointing at a zero-valued Point{0, 0}
p2 := &Point{X: 1, Y: 2}  // *Point, pointing at an initialized Point

fmt.Println(*p1, *p2)     // {0 0} {1 2}
```

`new(T)` allocates zeroed storage for a `T` and returns `*T` — it's rarely used directly in idiomatic Go outside of a few standard-library patterns, because taking the address of a composite literal (`&Point{...}`) does the same job while also letting you initialize fields inline, which is what you almost always want. Both forms produce a genuinely usable pointer to real, GC-managed memory — there is no meaningful difference in what you get, only in whether you can initialize inline.

## A first look at escape analysis

Here's a question that would be a memory bug in C and is a completely normal, safe pattern in Go:

```go
func newPoint(x, y int) *Point {
    p := Point{X: x, Y: y}
    return &p   // returning the address of a local variable
}
```

In C, returning `&p` for a stack-local `p` is a use-after-free waiting to happen — the stack frame is gone the instant the function returns, and the pointer is left dangling. Go makes this completely safe through **escape analysis**: at compile time, the Go compiler proves whether a value's lifetime can be provably bounded to its function's stack frame or not. If a value's address is ever taken and might outlive the frame — returned, stored in a struct that itself escapes, sent on a channel, captured by a closure that escapes — the compiler allocates it on the **heap** instead of the stack, automatically, with no annotation required from you. If the analysis proves the value truly never leaves the function, it stays on the stack, which is dramatically cheaper (no GC involvement at all).

This is why Go code never needs a `malloc`/`free` pair, and why "does this variable escape to the heap" is a real, measurable performance question rather than a correctness one — a value that escapes unnecessarily costs you an allocation and later GC work, but never costs you correctness the way it would in a language without a tracing garbage collector. *Connect the dot:* Chapter 31 (performance, profiling, and the GC) is where this becomes a practical, actionable skill — you'll use `go build -gcflags="-m"` to see the compiler's actual escape decisions printed out, and `pprof` to see where heap allocations are actually costing a real service time.

Next: control flow, functions, and closures — the machinery that decides, statement by statement, which of the values and types from this chapter actually run.
