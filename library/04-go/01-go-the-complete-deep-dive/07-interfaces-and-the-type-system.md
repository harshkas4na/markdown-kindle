# Interfaces and the Type System

**Fast overview:** an interface in Go is a set of method signatures, and any type that has those methods satisfies it — automatically, silently, with no `implements` keyword anywhere in the source. That one design choice is why Go code composes across package boundaries better than almost any mainstream language: you can write an interface for a type someone else wrote, in a package they'll never import. This chapter builds the mental model precisely — what an interface value actually *is* at runtime, why that model produces one of Go's most common real bugs, how method sets decide whether a type satisfies an interface at all, and why the idiomatic Go interface is almost always tiny.

## Structural typing: satisfaction by shape, not declaration

In Java or C#, a class states `implements Comparable` and the compiler checks it at the declaration site. Go inverts this entirely. Here is the whole interface:

```go
type Stringer interface {
    String() string
}
```

Any type — a struct you wrote, an `int` you defined a method on, a type from a third-party package — satisfies `Stringer` the moment it has a method with that exact signature. Nothing links the type to the interface except shape:

```go
type Temperature float64

func (t Temperature) String() string {
    return fmt.Sprintf("%.1f°C", float64(t))
}

var s fmt.Stringer = Temperature(21.5)  // satisfies fmt.Stringer, no declaration needed
```

The practical consequence is the idiom **"accept interfaces, return structs."** A function should ask for the smallest interface it actually needs as a parameter (so any caller's type can satisfy it, even types written after your function was), and return a concrete struct type (so callers get the full, discoverable API rather than a narrowed view). This is also what lets you define an interface *after the fact*, for a type you don't own and can't modify — the standard library does this constantly: `io.Reader` was never declared by `os.File`, `bytes.Buffer`, or `net.Conn`, yet all three satisfy it because they happen to have a `Read([]byte) (int, error)` method. *Connect the dot:* Chapter 22 is entirely this phenomenon — small stdlib interfaces (`io.Reader`, `io.Writer`) that dozens of unrelated types satisfy, letting you compose them like Unix pipes.

## What an interface value actually is

This is the part that separates "knows Go syntax" from "understands Go." An interface value is not the concrete value itself — it's a two-word pair: **(type, value)**. The type word records the concrete dynamic type stored inside, and the value word is a pointer to (or, for small values, an inlined copy of) the actual data.

```go
var r io.Reader          // (nil, nil) — the zero value of an interface
r = os.Stdin              // (*os.File, pointer to the Stdin File struct)
r = strings.NewReader("") // (*strings.Reader, pointer to that Reader struct)
```

An interface value is `nil` — meaning `r == nil` is true — only when **both** words are nil: no type and no value. This precision is the whole story behind Go's most notorious gotcha:

```go
type MyError struct{ msg string }
func (e *MyError) Error() string { return e.msg }

func doSomething() *MyError {
    return nil  // a nil *MyError
}

func run() error {
    var err *MyError = doSomething()
    return err  // returns a non-nil error!
}

func main() {
    if err := run(); err != nil {
        fmt.Println("got an error:", err) // this branch runs — surprise
    }
}
```

`doSomething()` returns a genuinely nil `*MyError` pointer. But when that nil pointer is assigned to the `error` interface variable being returned from `run()`, the interface value becomes `(*MyError, nil)` — a *non-nil type word* paired with a nil value word. Comparing that interface to the literal `nil` (which is `(nil, nil)`) fails, so `err != nil` is true even though the pointer inside is nil. The fix is almost always: don't declare a typed nil and return it through an interface-returning function — either return the untyped `nil` literal directly (`return nil` instead of `return err` when `err` is a typed nil), or check the concrete pointer before wrapping it. This bug shows up constantly in code that returns `error` from a function whose local variable was typed as a concrete `*SomeError` — keep the two-word model in your head and it stops being surprising.

## Method sets: why `*T` can satisfy things `T` can't

Go lets you declare a method with either a value receiver (`func (t T) M()`) or a pointer receiver (`func (t *T) M()`), and the choice changes which interfaces a type satisfies. The rule, precisely: the method set of type `T` contains only methods with a value receiver; the method set of `*T` contains methods with *both* value and pointer receivers.

```go
type Counter struct{ n int }
func (c *Counter) Inc()      { c.n++ }        // pointer receiver
func (c Counter) Value() int { return c.n }   // value receiver

var _ interface{ Inc() }        = &Counter{}  // OK: *Counter has Inc and Value
var _ interface{ Value() int }  = Counter{}   // OK: Counter has Value
// var _ interface{ Inc() }     = Counter{}   // compile error: Counter has no Inc
```

`Counter{}` (the value) does not have `Inc()` in its method set, because a pointer-receiver method needs an addressable value to call `c.n++` on and mutate the caller's copy — a plain interface value holding a `Counter` gives you no addressable storage to take that pointer from, so the compiler refuses the assignment outright rather than let the mutation silently vanish into a throwaway copy. *Connect the dot:* this is the same value-vs-pointer semantics from Chapter 5, showing up as a compile-time rule instead of a runtime surprise — which is Go trading a little rule-memorization now for catching the bug before it ships. The practical guideline: if *any* method on a type needs a pointer receiver (to mutate state, or just to avoid copying a large struct), make *all* its methods pointer receivers, so the type's method set is consistent and callers aren't surprised by which form satisfies which interface.

## The empty interface, assertions, and switches

`interface{}` — spelled `any` since Go 1.18, a plain built-in alias, nothing more — has zero methods, so *every* type satisfies it. It's Go's escape hatch for "I genuinely don't know the type yet": `fmt.Println(v ...any)`, `json.Unmarshal` into a `map[string]any`, and the value type inside a generic-free container. It is not, and never was, Go's version of dynamic typing for everyday code — reach for it only at real boundaries (deserialization, reflection, heterogeneous collections), because every value you shove into an `any` loses its compile-time type checking until you get it back out.

Getting it back out is a **type assertion**:

```go
var v any = "hello"
s, ok := v.(string)   // s = "hello", ok = true — the safe, comma-ok form
n, ok := v.(int)      // n = 0, ok = false — no panic
s2 := v.(string)      // panics if v does not hold a string — only use when you're certain
```

For more than one possible type, a **type switch** replaces a chain of assertions:

```go
func describe(v any) string {
    switch x := v.(type) {
    case int:
        return fmt.Sprintf("int: %d", x)
    case string:
        return fmt.Sprintf("string of length %d", len(x))
    case fmt.Stringer:
        return "stringer: " + x.String()
    case nil:
        return "nil"
    default:
        return fmt.Sprintf("unknown type %T", x)
    }
}
```

Each `case` re-binds `x` to the asserted type inside that branch. Note that a type switch can match against interfaces too (the `fmt.Stringer` case above), not just concrete types — case order matters when multiple cases could match, since the first match wins.

## Small interfaces, and the proverb that explains why

Go's standard library is built almost entirely from one- and two-method interfaces: `io.Reader`, `io.Writer`, `io.Closer`, `sort.Interface` (three methods), `fmt.Stringer`, `error` itself (one method: `Error() string`). This is a deliberate, repeatedly-stated design taste, summarized in one of the language's own proverbs, from Rob Pike: **"The bigger the interface, the weaker the abstraction."**

The reasoning is symmetric on both sides. For implementers, a small interface is cheap to satisfy — often for free, because some type you already had happens to have the right one or two methods. For consumers, a small interface is a small, honest promise: a function that takes an `io.Reader` tells you, precisely, that it will call `Read` and nothing else — it can't secretly depend on some tenth method you didn't think to check. A large interface with fifteen methods is really an implicit demand that every implementer build fifteen things, most of which any given caller never uses, and it makes mocking and testing harder (Chapter 21 leans on exactly this: small interfaces are what make hand-written fakes practical without a mocking framework). When you find yourself designing an interface with more than two or three methods, the idiomatic Go instinct is to ask whether it's actually two smaller interfaces wearing a trenchcoat — and whether your function really needs the whole thing, or just the one method it calls.

Interfaces are also where Go's type system meets its most consequential recent addition. Everything above is about polymorphism over *behavior* — the same code running against different types because they share a method. The next chapter is about polymorphism over *data* — the same code running against different types because you tell it to, at compile time, with no methods involved at all. Onward to generics.
