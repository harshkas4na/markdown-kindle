# Maps, Structs, and Embedding

**Fast overview:** maps are Go's hash table, a reference type with two sharp edges (nil maps panic on write, and no map is ever safe for concurrent read+write) that beginners find the hard way. Structs are Go's only way to group fields — no classes, no constructors as a language feature — and embedding is how Go gets the useful 20% of inheritance (field and method reuse) without the fragile 80% (deep hierarchies, virtual dispatch, the diamond problem). This chapter is the full shape of how Go composes data.

## Maps: a hash table with two rules you must never forget

```go
m := make(map[string]int)     // ready to use
m["a"] = 1
m["b"] = 2

var m2 map[string]int         // nil map — reads are safe, writes panic
fmt.Println(m2["missing"])    // 0 — zero value, no panic
m2["x"] = 1                   // panic: assignment to entry in nil map
```

A map, like a slice, is a reference type — the variable holds a pointer to an underlying hash table structure, and copying a map header copies the pointer, not the data (two map variables can alias the same table, same as slices in Chapter 3). The rule that trips people up: a **nil map behaves like an empty map for every read operation** — indexing it, ranging over it, calling `len()` on it are all completely safe and return zero values or zero iterations — but **writing to a nil map panics**. This means `var m map[string]int` is a legitimate, useful zero value for a read-only or not-yet-populated map, but it is never a substitute for `make(map[string]int)` the moment you intend to write.

**Existence checking** uses the "comma-ok" idiom, and it exists precisely because a zero value and "the key is absent" are otherwise indistinguishable:

```go
count, ok := m["a"]
if !ok {
    // key genuinely absent — count would otherwise silently read as 0,
    // indistinguishable from a key that legitimately maps to 0
}
```

Deleting uses the built-in `delete(m, key)` — it's a no-op, not an error, if the key doesn't exist. **Iteration order is deliberately randomized** by the runtime, on every single run, specifically so that no one accidentally writes code that depends on it — this is Go's designers preemptively closing off a bug class before anyone could rely on it and then be surprised when the internal hash implementation changed. If you need sorted output, collect the keys into a slice and sort them yourself (`slices.Sort`, standard library since Go 1.21).

**Map keys must be comparable** — the spec requires this because the map needs to hash and equality-check keys — which rules out slices, maps, and functions as keys directly (they have no `==`), but allows arrays, structs (if every field is itself comparable), and pointers. A common pattern for "I want a slice-like thing as a key" is to convert it to a string or use an array of fixed size instead.

*Connect the dot:* the single most important rule about maps in this book doesn't show up until Chapter 12 — a map is **not safe for concurrent use** when at least one goroutine is writing; concurrent read-only access is fine, but any concurrent write racing with anything else is undefined behavior that the Go runtime will, helpfully, often (not always) catch and crash on with `fatal error: concurrent map writes` rather than silently corrupting data. `sync.Map` (Chapter 13) exists for the specific access patterns where a mutex-guarded regular map isn't the right shape.

## Structs: the only way to group fields

```go
type User struct {
    ID       int64
    Name     string
    Email    string
    Verified bool
}

u := User{ID: 1, Name: "Ada", Email: "ada@example.com", Verified: true} // keyed literal
u2 := User{2, "Grace", "grace@example.com", true}                       // positional literal
```

Structs are Go's only aggregate-with-named-fields construct — there is no `class` keyword, no visibility modifiers per-field beyond the same capitalization rule that governs everything else (Chapter 9), and no constructors as a language feature (idiomatic Go uses a plain function, conventionally named `NewUser(...)`, that returns a struct or pointer-to-struct with sensible defaults already applied).

**Keyed literals are strongly preferred, especially for exported types**, because positional literals break silently the moment a field is added, removed, or reordered — `go vet` will flag a positional composite literal for a struct from a different package specifically because of this fragility. Keyed literals also let you specify only the fields you care about, leaving the rest at their zero value.

Struct **comparability** follows the same rule as map keys: a struct value is comparable with `==` if and only if every one of its fields is comparable — a struct containing a slice, map, or function field cannot be compared with `==` at all (it's a compile error, not a runtime surprise), because slices/maps/funcs have no defined equality.

**Struct tags** are string literals attached to a field, conventionally holding key:"value" pairs that packages read via reflection (Chapter 23):

```go
type User struct {
    ID    int64  `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email,omitempty"`
}
```

The tag itself does nothing at compile time — it's inert metadata until some package (`encoding/json`, a validator, an ORM) reads it via `reflect.StructTag`. `encoding/json` is the tag consumer you'll meet earliest and most often; `omitempty` there means "drop this field from the output entirely if it holds its zero value," which is a JSON-specific convention, not a general Go one.

## Embedding: composition standing in for inheritance

```go
type Base struct {
    CreatedAt time.Time
}

func (b Base) Age() time.Duration {
    return time.Since(b.CreatedAt)
}

type Article struct {
    Base           // embedded — no field name, just the type
    Title string
}

a := Article{Base: Base{CreatedAt: time.Now()}, Title: "Go Embedding"}
fmt.Println(a.Age())        // Base's method, promoted onto Article
fmt.Println(a.CreatedAt)    // Base's field, promoted onto Article
```

Embedding a type — writing just the type name as a struct field, with no name of its own — **promotes** every one of that type's exported (and, within the same package, unexported) fields and methods onto the outer struct, as if they'd been declared directly on it. `a.Age()` and `a.CreatedAt` both work without ever writing `a.Base.Age()`, though that longer form is always also valid and is how you resolve an ambiguity.

This is deliberately **not inheritance**, and the difference matters in a way that trips up people arriving from Java or Python:

- **No virtual dispatch.** If `Base` had a method that called another method on itself, that call is *always* resolved against `Base`, never against whatever outer type happens to have embedded it. There is no way for `Article` to "override" `Age()` in a way that changes what `Base`'s own internal logic sees — Go has no `virtual`/`override` concept at all.
- **`Article` is not a `Base`.** You cannot pass an `Article` value to a function expecting a `Base` — embedding gives you promoted access to `Base`'s members, but `Article` and `Base` remain entirely distinct types with no assignability relationship between them (unlike Java's `extends`, which creates a genuine is-a subtype relationship).
- **Name collisions are resolved by depth, and ambiguity at the same depth is a compile error** you must resolve explicitly by qualifying the field (`a.Base.CreatedAt`) if two embedded types at the same level both have a `CreatedAt` field.

Because it's composition, not inheritance, embedding is honest about what it's doing: it's a code-reuse mechanism for "this type wants to behave like a bag of that other type's fields and methods, promoted up one level," and nothing more. Multiple embeds are completely normal (`type Server struct { Logger; Config; mux *http.ServeMux }`) in a way that would be multiple inheritance — and controversial — in most object-oriented languages, precisely because there's no diamond-problem ambiguity to worry about: Go just requires you to disambiguate explicitly if two embedded types' promoted names collide, rather than picking one for you via some resolution order.

## Embedding an interface: the pattern behind `io.ReadWriter`

Embedding isn't limited to structs embedding structs — a struct (or even another interface) can embed an interface type, and this is exactly how the standard library builds composite interfaces out of small ones:

```go
type Reader interface { Read(p []byte) (n int, err error) }
type Writer interface { Write(p []byte) (n int, err error) }

type ReadWriter interface {
    Reader
    Writer
}
```

`ReadWriter` is satisfied by any type that has both a `Read` and a `Write` method — the embedding here is just a shorthand for "list both method sets," and it's the exact mechanism `io.ReadWriter`, `io.ReadWriteCloser`, and friends use in the real standard library (Chapter 22 goes deep on why this small-interfaces-composed-together design is the reason so much of Go's I/O ecosystem plugs together without anyone having agreed on a shared base class in advance).

There's a second, subtler pattern worth knowing: a struct can embed an interface (not just another struct), which is a common trick for partially implementing an interface while delegating the rest — embed the interface field, override the one or two methods you care about, and every other method call falls through to whatever concrete value was assigned to the embedded interface field at runtime, panicking with a nil-pointer-style error only if that field was never set and the un-overridden method is actually called.

*Connect the dot:* the "promotion" mechanic here — fields and methods becoming visible on the outer type — is purely a compile-time, syntactic convenience. At runtime, an `Article` value really is just a `Base` value followed by a `Title` string, laid out in memory exactly like a struct with those fields written out directly, with zero indirection cost. Composition in Go is free; it's mechanical sugar for something you could always write by hand, which is very on-brand for a language whose entire founding argument (Chapter 1) is that a small set of honest primitives beats a larger set of magic ones.

Next: pointers — and the value-semantics rule that explains why mutating through a slice or map parameter works, even though Go copies everything.
