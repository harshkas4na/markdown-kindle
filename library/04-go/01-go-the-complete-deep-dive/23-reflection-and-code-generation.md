# Reflection and Code Generation

**Fast overview:** Go is aggressively statically typed everywhere in this book so far, but two escape hatches let some dynamism back in: `reflect`, for inspecting and manipulating values at runtime whose exact type isn't known at compile time, and code generation, Go's strongly preferred alternative for the cases where you'd reach for runtime metaprogramming in other languages. This chapter covers both, and — more importantly — when a senior Go engineer will tell you to reach for neither.

## `reflect`: types and values, examined at runtime

The `reflect` package is built around two core concepts: a `reflect.Type` (the static type description — its name, kind, fields, methods) and a `reflect.Value` (the actual runtime data), obtained from any interface value via `reflect.TypeOf(x)` and `reflect.ValueOf(x)`. A third concept, `Kind`, tells you the underlying *category* of a type — `reflect.Struct`, `reflect.Slice`, `reflect.Int` — independent of its name, since two differently-named types can share the same underlying kind (*connect the dot:* the same "named type vs. underlying type" distinction Chapter 2 introduced for the static type system reappears here, at runtime).

```go
type User struct {
    Name string `json:"name"`
    Age  int    `json:"age"`
}

func describe(v any) {
    t := reflect.TypeOf(v)
    val := reflect.ValueOf(v)
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        fmt.Printf("%s (%s) = %v, tag: %q\n",
            field.Name, field.Type, val.Field(i), field.Tag.Get("json"))
    }
}
```

Walking a struct's fields and reading their tags at runtime — exactly what `describe` does above — is not a toy example: it's *literally how `encoding/json`, `encoding/xml`, most validation libraries, and most lightweight ORMs work under the hood.* *Connect the dot:* Chapter 4 introduced struct tags as string metadata attached to fields (`` `json:"name"` ``) with no fixed meaning enforced by the compiler; `reflect` is the mechanism that gives those strings meaning at runtime, by letting a general-purpose library read them off a type it has never seen before and decide how to (de)serialize each field.

### The real costs

Reflection is not free, in three separate ways worth knowing before reaching for it. It **loses compile-time type safety** — a typo in a field name passed to `reflect.Value.FieldByName` fails at runtime, not at `go build`, so a whole category of errors the type system would normally catch for free becomes a runtime bug instead. It is **meaningfully slower** than direct field access or a direct method call — every `reflect` operation goes through extra indirection and type-checking that a compiled direct access skips entirely, which matters in hot paths (`encoding/json`'s reflection-based path is a large part of why faster JSON libraries exist that generate direct marshal/unmarshal code instead — see below). And it produces **harder-to-debug code**: a panic inside reflective code often surfaces as a generic "reflect: call of reflect.Value.Field on zero Value" rather than a clear type error pointing at your actual mistake.

The standard guidance, and it's a strong one: reach for `reflect` when you're writing **generic infrastructure** that genuinely cannot know its input types ahead of time — a serialization library, a dependency-injection container, a general-purpose test-assertion helper (`reflect.DeepEqual`, used all over the standard library's own tests) — not in everyday application code, where the types are known at compile time and a direct field access or a type switch (Chapter 7) does the same job more safely and faster. *Connect the dot:* Chapter 8's generics closed off a meaningful slice of the cases reflection used to be the *only* option for — a generic `Max[T constraints.Ordered](a, b T) T` no longer needs `reflect` or an `any`-typed signature to work across multiple concrete types, because the type parameter gives the compiler everything it needs statically. Reflection remains necessary for the genuinely dynamic cases — you don't know the type until you receive a JSON blob or an arbitrary struct at runtime — but it's no longer the default reach for "I want one function that works on several types."

## Code generation: Go's preferred alternative

Where many languages lean on runtime metaprogramming or heavier reflection to avoid writing repetitive code by hand, Go's culture leans the other way: **generate the repetitive code once, as real, readable, statically-typed `.go` source, and commit it to the repository.** The mechanism is a `//go:generate` directive — a specially formatted comment that `go generate` (run manually, or as a Makefile/CI step, never automatically by `go build`) executes as an external command:

```go
//go:generate stringer -type=Status
type Status int

const (
    StatusPending Status = iota
    StatusActive
    StatusClosed
)
```

Running `go generate ./...` invokes `stringer`, which reads the `Status` type's `const` block and writes a new file, `status_string.go`, containing a real `func (s Status) String() string` with a proper switch or lookup table — turning `StatusActive.String()` into `"StatusActive"` instead of an unhelpful integer, without you hand-writing or hand-maintaining that switch statement. The generated file is checked into version control like any other source file: it shows up in diffs, is readable in a code review, compiles with zero runtime magic, and needs no explanation to a reader who's never heard of `stringer` — it's just an ordinary Go file that happens to have been produced by a tool instead of typed by hand.

The same pattern scales to much bigger generators: `protoc` with the Go plugin turns a `.proto` schema into typed Go structs and (de)serialization code for gRPC services (*connect the dot:* Chapter 28 covers this directly), `mockgen` reads an interface and generates a full test-double implementation of it (an alternative to Chapter 21's hand-written fakes, useful once a codebase needs the same interface mocked dozens of times with call-count and argument-matching assertions), and `sqlc` reads raw SQL queries and generates typed Go functions and structs matching their result columns (*connect the dot:* Chapter 27's alternative to a runtime ORM). In every case, the shape is identical: an external tool reads some source of truth (a type, a schema, a query) and emits real Go source that gets compiled normally.

### Why this fits Go's whole design ethos

*Connect the dot:* Chapter 1 made the case that Go's designers treated *removing* features — exceptions, implicit conversions, inheritance — as the actual design work, in service of code that's boring and predictable to read. Code generation is the same instinct applied to metaprogramming: instead of a runtime system clever enough to synthesize behavior on the fly (which a reader then has to mentally simulate to understand what a piece of code actually does), Go pushes that cleverness to a build-time step whose *output* is ordinary code anyone can read top to bottom with no special knowledge of the generator. You pay the complexity cost once, at generation time, and every reader after that gets a plain, statically-typed, `go doc`-able artifact instead of a black box. This is also, not coincidentally, why generated files conventionally carry a `// Code generated by ... DO NOT EDIT.` header near the top — a signal, honored by tooling and reviewers alike, that hand-editing the file is pointless because the next `go generate` run will overwrite it.

## Closing Part 4

Chapters 20 through 23 covered the layer above the language itself: the naming, formatting, and documentation conventions that make Go code recognizable at a glance (Chapter 20); the `testing` package and the table-driven pattern that structures nearly every real test suite (Chapter 21); the two small `io` interfaces that explain why the standard library composes without a shared framework (Chapter 22); and this chapter's two escape hatches for dynamism, used deliberately and sparingly. Together with Parts 1–3, you now have the full language and its idioms.

Next: Part 5 turns from idioms to a real, running service — starting with Chapter 24, `net/http` built up from its single core interface.
