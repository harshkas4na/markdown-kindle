# Types, Values, and Declarations

**Fast overview:** every value in Go has exactly one static type, decided at compile time, and the language gives you three ways to introduce a name for a value — `var`, `const`, and the short declaration `:=` — each with slightly different rules about scope and inference. This chapter works through the spec's own vocabulary for declarations, the full basic-type family (and why `int` doesn't have a fixed size), strings as the thing everyone gets subtly wrong at first, and named types — the single cheapest trick in the language for making illegal states unrepresentable.

## Three ways to declare, and why you need all three

```go
var count int           // declared, zero value (0), type explicit
var price float64 = 9.99 // declared, initialized, type explicit
name := "gopher"         // declared, initialized, type inferred
const MaxRetries = 5     // a constant, not a variable at all
```

`var` is the general form — it works at package level and inside functions, lets you declare without initializing (giving you the **zero value**, covered below), and lets you state the type explicitly even when it could be inferred, which matters for interface-typed variables (Chapter 7) where you want a wider type than the initializer alone would give you.

`:=`, the short variable declaration, only works *inside* functions — it cannot appear at package level, which is a deliberate scope restriction: package-level state should always be visibly and explicitly typed via `var`, never inferred in passing. `:=` also has a quirk worth internalizing early: in a multi-variable short declaration, only *at least one* variable on the left needs to be new — `x, err := f()` followed later by `y, err := g()` re-uses the existing `err` and only declares `y`. This is why Go code is full of `err` reuse instead of `err2`, `err3`.

`const` declares a genuine compile-time constant — not just a variable you promise not to reassign. Constants can be **untyped** until they're used in a context that forces a type (`const Pi = 3.14159` can be assigned to a `float32` or `float64` variable without a conversion, because the constant itself carries no fixed type until it's consumed) — this is one of the few places Go's normally strict "no implicit conversion" rule bends, and it's a deliberate convenience, not an inconsistency.

*Connect the dot:* the difference between package-level `var`/`const` and function-local `:=` is really a difference in **scope**, and scope in Go is lexical and block-based — every `{ }` introduces a new block, and a name declared inside is invisible outside it. This is the same block-scoping rule that governs the closures you'll meet properly in Chapter 6.

## Zero values: Go's answer to "uninitialized"

Go has no concept of an uninitialized variable holding garbage memory. Every type has a well-defined **zero value**, and `var x T` always gives you that value, deterministically:

| Type | Zero value |
|---|---|
| Numeric types (`int`, `float64`, …) | `0` / `0.0` |
| `bool` | `false` |
| `string` | `""` (empty string, not nil) |
| Pointers, slices, maps, channels, functions, interfaces | `nil` |
| Structs | every field set to *its own* zero value, recursively |

This one design decision quietly eliminates a huge class of bugs common in C — no more reading a stack variable that happens to contain leftover garbage from a previous call frame. It also makes struct literals genuinely pleasant: `var cfg Config` is always immediately usable, just with every field defaulted, no explicit constructor required (though idiomatic Go still often provides a `NewConfig()` function when zero values aren't sensible defaults).

## The numeric type family, and why `int` is the odd one out

```go
int8, int16, int32, int64      // signed, explicit width
uint8, uint16, uint32, uint64  // unsigned, explicit width
int, uint                      // platform-native width: 32 or 64 bits
uintptr                        // unsigned integer large enough to hold a pointer
byte                           // alias for uint8
rune                           // alias for int32 — a single Unicode code point
float32, float64
complex64, complex128
```

`int` and `uint` are the ones people trip over: their size is **implementation-defined**, and on every mainstream Go compiler target today that means 64 bits, but the language spec only guarantees "at least 32 bits." The rule of thumb the standard library itself follows: use plain `int` for ordinary counting and indexing (slice lengths, loop counters — this is what `len()` returns), and reach for an explicitly sized type (`int32`, `uint64`, …) only when the width genuinely matters — binary file formats, wire protocols, or bit manipulation where you need to know exactly how many bits you have. `byte` and `rune` are aliases, not distinct types, which matters for the next section.

Go has **no implicit conversion between numeric types**, full stop, even between `int` and `int32`, even between `int` and `int64` — you must write `int64(x)`. This is a direct consequence of the design philosophy in Chapter 1: silent numeric promotion is exactly the class of C bug (an `int` truncated into a `short` without warning) Go's designers chose to make impossible by construction, at the cost of visual noise in code that mixes numeric types.

## Strings: immutable, UTF-8, and not what you think they are

A Go `string` is an **immutable sequence of bytes** — not characters, not runes, bytes — that is *conventionally* (though not enforced by the type system) valid UTF-8. This one fact resolves almost every string-related confusion beginners hit:

```go
s := "héllo"
fmt.Println(len(s))        // 6, not 5 — 'é' is 2 bytes in UTF-8

for i, r := range s {
    fmt.Printf("%d: %c (%d bytes)\n", i, r, len(string(r)))
}
// range over a string decodes UTF-8 and yields (byte-index, rune) pairs —
// i jumps by more than 1 whenever a multi-byte rune is consumed
```

`len(s)` always returns the **byte** length, because a string is a byte sequence at the type level. If you index directly, `s[0]`, you get a single `byte`, not a character — for ASCII text this happens to look right and lulls people into thinking strings are char arrays, right up until the first non-ASCII input arrives and `s[i]` slices a UTF-8 sequence in half. A `rune` (an alias for `int32`) is Go's name for a single Unicode code point, and `for range` is the idiomatic way to walk a string character-by-character correctly, because it does UTF-8 decoding for you. Converting `[]byte(s)` and `[]rune(s)` are both real, allocating conversions — the former gives you the raw bytes to mutate, the latter gives you one slice element per Unicode code point, at the cost of re-encoding.

Because strings are immutable, "modifying" one always means building a new one — string concatenation in a loop with `+=` is a classic performance trap because each concatenation allocates a fresh string; `strings.Builder` exists specifically to accumulate text without that repeated-allocation cost, and you'll see it again in Chapter 22 alongside `io.Writer`.

## Type conversion vs. assignment: the strict line

```go
var i int = 42
var f float64 = float64(i)   // explicit conversion required
var f2 float64 = i           // compile error: cannot use i (type int) as type float64

type Celsius float64
type Fahrenheit float64

var c Celsius = 100
var f3 Fahrenheit = Fahrenheit(c) // also requires explicit conversion —
                                   // even though both are just float64 underneath
```

That last example is the important one. `Celsius` and `Fahrenheit` are both **named types** (sometimes called "defined types" in the spec) with the identical **underlying type** `float64` — but Go treats them as distinct types for the purposes of assignment and requires an explicit conversion between them, precisely so you cannot accidentally add a temperature in Celsius to one in Fahrenheit and get a value that compiles but means nothing. This is the cheapest safety trick in the language: wrapping a primitive in a named type costs you nothing at runtime (it's still stored as a `float64`) and buys you a compiler that will stop you from mixing up quantities that happen to share a representation.

Named types exist for exactly two reasons: to **attach methods** (you cannot define a method directly on `float64`, but you can on `Celsius` — Chapter 5 covers method declarations properly), and to **create a distinct type identity** for exactly this kind of mix-up prevention. You'll see this pattern constantly in real Go code — `type UserID int64`, `type Status string` with a small set of constants (built with `iota`, next) — because it turns a category of runtime bug into a compile error, for free.

## Constants and iota

```go
type Weekday int

const (
    Sunday Weekday = iota // 0
    Monday                 // 1
    Tuesday                 // 2
    Wednesday               // 3
    Thursday                 // 4
    Friday                    // 5
    Saturday                  // 6
)
```

`iota` is a predeclared identifier that resets to `0` at the start of each `const (...)` block and increments by one for every `ConstSpec` line inside it, whether or not that line explicitly mentions `iota`. It exists purely to make sequential, enumerated constants cheap to write and free of manually-typed-and-therefore-typo-prone numbers. Its second, more powerful idiom is bit flags:

```go
type Perm uint8

const (
    Read Perm = 1 << iota // 1 << 0 = 1
    Write                   // 1 << 1 = 2
    Execute                 // 1 << 2 = 4
)

// combine: Read | Write == 3
// check:   perm & Write != 0
```

Every `const` block re-derives its own `iota` from zero — it does not carry over between separate `const (...)` groups — and a blank identifier (`_`) can be used to deliberately skip a value in the sequence, which shows up in code parsing binary formats that skip a reserved slot.

*Connect the dot:* the `Weekday`/`Perm` pattern — a named type plus a `const` block of values — is Go's entire answer to what other languages call an `enum`. There's no dedicated enum keyword; it's just declarations, composed, which is the orthogonality argument from Chapter 1 playing out in miniature.

Next chapter takes the single value that causes more confusion than every type covered here combined: the slice, and the backing array it quietly shares with every other slice that was ever sliced from it.
