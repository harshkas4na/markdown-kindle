# Generics

**Fast overview:** for its first decade, Go had exactly one form of built-in polymorphism — `interface{}` plus a type assertion, which threw away compile-time type safety to get there. Go 1.18 (March 2022) added a second, proper one: type parameters and constraints, letting a function or type be written once and instantiated for many concrete types, checked entirely at compile time. This chapter covers the syntax precisely, then spends real effort on the question that matters more than the syntax: when generics are the right tool in idiomatic Go, and when the answer is still a plain interface — because the two solve genuinely different problems, and conflating them is the single most common way new Go generics code goes wrong.

## Why it took twelve years

Go's designers didn't miss that parametric polymorphism was useful — C++ had templates in the 1990s, and Java added erasure-based generics in 2004. They were wary of the specific costs those designs impose: C++ templates can produce famously unreadable, page-long compiler errors and unbounded compile-time code bloat through unconstrained specialization; Java's erasure-based generics throw type information away at runtime, producing its own category of surprises (you can't `new T[]` or overload on erased types). Go's founding goals — fast compilation, simple and predictable error messages, a small orthogonal language — were in direct tension with every existing generics design the team studied. The eventual solution, contributed largely by Ian Lance Taylor and Robert Griesemer over several public draft proposals, resolved the tension with **constraints expressed as interfaces**: a type parameter's constraint is just an interface listing the methods or underlying types it must support, checked at compile time, with no runtime type erasure and no unbounded template expansion. It took that long because the team wanted a design that didn't compromise the properties in Chapter 1 — and shipped it only once they had one.

## Type parameters, precisely

A generic function declares type parameters in square brackets, right after the function name, before the ordinary parameter list:

```go
func Map[T, U any](s []T, f func(T) U) []U {
    result := make([]U, len(s))
    for i, v := range s {
        result[i] = f(v)
    }
    return result
}

doubled := Map([]int{1, 2, 3}, func(n int) int { return n * 2 })
labels  := Map([]int{1, 2, 3}, func(n int) string { return fmt.Sprintf("#%d", n) })
```

`T` and `U` are placeholders for real types, filled in either by explicit instantiation (`Map[int, string](...)`) or, in almost all real code, by **type inference** — the compiler works out `T` and `U` from the arguments you actually passed, so you write `Map(nums, f)` and never touch the brackets. `any` here is the loosest possible constraint (Chapter 7's `interface{}` alias): "any type at all is acceptable."

## Constraints: interfaces that describe what a type parameter must support

`any` works for `Map` because the function never operates *on* the values of `T` — it just moves them around. The moment you need to compare, add, or otherwise operate on values of the type parameter, you need a tighter constraint:

```go
type Number interface {
    ~int | ~int32 | ~int64 | ~float32 | ~float64
}

func Sum[T Number](values []T) T {
    var total T
    for _, v := range values {
        total += v
    }
    return total
}
```

A constraint is an ordinary interface, but with an extra feature: a **union** of types (`int32 | int64`) means "any one of these," and the **tilde** (`~int32`) means "this type, or any type whose *underlying type* is this" — so a constraint written `~int` also accepts `type Meters int`, a named type you defined, not just the predeclared `int` itself. Without the tilde, `int` in a constraint matches only the literal predeclared type `int`, rejecting your own named types built on it — a subtle distinction that trips up a lot of first-generics-code.

Go predeclares two constraints so you rarely need to write your own for common cases: `any` (zero methods, matches everything — an alias for `interface{}`) and `comparable` (matches any type usable with `==`/`!=`, which is what map keys require):

```go
func Keys[K comparable, V any](m map[K]V) []K {
    keys := make([]K, 0, len(m))
    for k := range m {
        keys = append(keys, k)
    }
    return keys
}
```

For ordering (`<`, `<=`, `>`, `>=`), the standard library's `cmp` package (Go 1.21+) provides `cmp.Ordered` — a constraint union of every built-in numeric type plus `string` — so you rarely need to hand-write it either:

```go
func Max[T cmp.Ordered](a, b T) T {
    if a > b {
        return a
    }
    return b
}
```

## Generic types

Type parameters aren't limited to functions — a type declaration can carry them too, which is how Go finally got a real generic container without `interface{}` and type assertions on every read:

```go
type Stack[T any] struct {
    items []T
}

func (s *Stack[T]) Push(v T) {
    s.items = append(s.items, v)
}

func (s *Stack[T]) Pop() (T, bool) {
    var zero T
    if len(s.items) == 0 {
        return zero, false
    }
    v := s.items[len(s.items)-1]
    s.items = s.items[:len(s.items)-1]
    return v, true
}

ints := &Stack[int]{}
ints.Push(1)
ints.Push(2)
v, ok := ints.Pop() // v == 2, ok == true, v is a real int — no assertion needed
```

Note the `var zero T` idiom: since `T` is unknown inside the generic method body, `var zero T` is the general way to get "the zero value of whatever T ends up being" (Chapter 2's zero-value rules apply per-instantiation). Since Go 1.21, the standard library ships generic building blocks built exactly this way in the `slices` and `maps` packages (`slices.Contains`, `slices.Sort`, `maps.Keys`) — before generics, these existed only as one-off, type-specific implementations or as reflection-based library code (Chapter 23) that was slower and gave up compile-time checking entirely.

## The real decision: generics for data, interfaces for behavior

This is the distinction that matters more than any syntax above. Compare two ways of writing "a container that can report its total size":

```go
// Interface — behavior polymorphism. Different types, different logic,
// unified by a shared method each type implements on its own terms.
type Sized interface {
    Size() int
}

func TotalSize(items []Sized) int {
    total := 0
    for _, it := range items {
        total += it.Size() // each concrete type decides HOW to compute this
    }
    return total
}
```

```go
// Generics — data polymorphism. The SAME logic, running unmodified
// against different concrete types, with no behavioral variation at all.
func Sum[T Number](values []T) T {
    var total T
    for _, v := range values {
        total += v // the exact same operation, whichever numeric type T is
    }
    return total
}
```

`TotalSize` needs an interface because a `File`'s notion of "size" and a `Directory`'s notion of "size" are computed by genuinely different code — that's polymorphism over *behavior*, and generics can't help here at all (a type parameter gives you no way to call type-specific logic; that's precisely what a method set is for). `Sum` needs generics, not an interface, because the logic is identical for every `T` — writing an interface with a `Sum` method would force every numeric type to separately implement the same three-line loop, which is exactly the boilerplate generics exist to delete. The rule of thumb worth keeping: **reach for an interface when different types need to do the same job differently; reach for generics when the same code needs to run against different types unchanged** — containers, algorithms (`Map`/`Filter`/`Reduce`-style helpers), and anything that used to be `interface{}` plus a type assertion purely to dodge writing the same function five times for `[]int`, `[]string`, and `[]float64`.

## The overuse debate, and where the community landed

Generics shipped into a language culture that had spent a decade actively avoiding "clever" abstraction (Chapter 1), so the backlash was immediate and is still ongoing in 2026: early generic libraries appeared offering fully generic functional-programming toolkits — heavily parameterized `Option[T]`, `Result[T, E]`, monadic pipelines — that read closer to Scala than to the rest of the standard library, and the broader community pushed back hard, favoring the standard library's own restraint (`slices`, `maps`, `cmp` — small, targeted, unglamorous) as the model to imitate. The Go team's own guidance has stayed consistent since the proposal era: don't add a type parameter to a function until you have a second concrete type that actually needs to call it, don't build a generic abstraction speculatively "in case it's useful later" (the same anti-speculation instinct from this repo's own engineering principles), and prefer a plain interface if the polymorphism you need is over behavior rather than data. Four years in, the pattern that's stuck is narrow and pragmatic: generic containers (queues, sets, trees), generic algorithms over slices and maps, and not much else — exactly the shape of the standard library's own additions.

Generics close out the type-system arc that started with Chapter 2's basic types. The next chapter turns from *what a type looks like* to *where code and types live* — packages, modules, and the build system that ties a whole program together.
