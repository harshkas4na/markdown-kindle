# Testing in Go

**Fast overview:** the standard library's `testing` package needs no third-party framework for the vast majority of real-world Go test suites — that's not a minimalist boast, it's a genuine, load-bearing fact about how the ecosystem writes tests. This chapter covers `go test` and table-driven tests (the single most copied pattern in the language), benchmarks, fuzzing, and how Go does test doubles without a mocking framework, by leaning on the same implicit-interface trick from Chapter 7.

## The basics: `go test`, `TestXxx`, and the two ways to fail

A test file is named `xxx_test.go` and lives alongside the code it tests. It can declare `package foo` (white-box testing, with access to unexported identifiers) or `package foo_test` (black-box testing, importing `foo` like any other consumer would — useful for making sure your public API is actually usable from outside). `go test` compiles and runs every function matching `func TestXxx(t *testing.T)` in the package.

Inside a test, `t.Errorf(...)` records a failure and **keeps running the rest of the test function** — use it when later checks in the same test are still useful even after an earlier one failed. `t.Fatalf(...)` records a failure and **stops the test function immediately** (via `runtime.Goexit`, running deferred cleanup first) — use it when a failed precondition makes the rest of the test meaningless or unsafe, like a `nil` value you're about to dereference:

```go
func TestParseConfig(t *testing.T) {
    cfg, err := ParseConfig("testdata/valid.yaml")
    if err != nil {
        t.Fatalf("ParseConfig returned error: %v", err) // nothing after this is safe without cfg
    }
    if cfg.Port != 8080 {
        t.Errorf("Port = %d, want 8080", cfg.Port) // keep checking other fields even if this fails
    }
    if cfg.Host != "localhost" {
        t.Errorf("Host = %q, want %q", cfg.Host, "localhost")
    }
}
```

## Table-driven tests: the pattern everyone copies

Once you have more than one input/output pair to check, Go's culture converges on one shape almost universally: a slice of small structs describing each case, and a single loop that runs them all through `t.Run` as named subtests.

```go
func TestAdd(t *testing.T) {
    cases := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive numbers", 2, 3, 5},
        {"negative numbers", -2, -3, -5},
        {"zero", 0, 0, 0},
        {"overflow-adjacent", math.MaxInt32, 1, math.MaxInt32 + 1},
    }

    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            got := Add(tc.a, tc.b)
            if got != tc.expected {
                t.Errorf("Add(%d, %d) = %d, want %d", tc.a, tc.b, got, tc.expected)
            }
        })
    }
}
```

`t.Run` matters for more than just organization: each subtest gets its own pass/fail line in `go test -v` output, named `TestAdd/positive_numbers`, so a failure points you straight at the offending case instead of making you `bisect` a shared `for` loop by eye. `-run TestAdd/negative` filters down to just that subtest during iteration. And calling `t.Parallel()` as the first line inside the subtest closure lets independent cases run concurrently, which matters once a table grows into dozens of cases with any real per-case setup cost — *connect the dot:* this is an ordinary use of Chapter 10's goroutines, scheduled by `go test` itself rather than by your own code.

Table-driven tests are worth internalizing as the default shape for *any* function with more than two or three interesting input classes — new cases are one more struct literal in the slice, not a new copy-pasted test function, which is exactly why the pattern spread across essentially every serious Go codebase.

## Benchmarks

`func BenchmarkXxx(b *testing.B)` measures performance instead of correctness. The body runs in a loop `b.N` times, with the testing framework automatically adjusting `N` upward until the measurement is statistically stable:

```go
func BenchmarkFib20(b *testing.B) {
    for i := 0; i < b.N; i++ {
        fib(20)
    }
}
```

Run with `go test -bench=. -benchmem` (the `-benchmem` flag adds allocations-per-operation to the output, often more actionable than raw timing). One trap worth naming explicitly: if the compiler can prove a computed value is never used, it may optimize the whole loop body away, making your benchmark measure nothing. The fix is to assign the result to a package-level variable so the compiler can't discard it:

```go
var sink int

func BenchmarkFib20(b *testing.B) {
    var r int
    for i := 0; i < b.N; i++ {
        r = fib(20)
    }
    sink = r // prevents the compiler from eliminating the call entirely
}
```

*Connect the dot:* Chapter 31 goes further into benchmarking methodology (statistical noise, `benchstat` for comparing runs) and pairs benchmarks with `pprof` profiling to find out *why* something is slow, not just *that* it is.

## Fuzzing

Since Go 1.18, fuzzing is built into `testing` directly: `func FuzzXxx(f *testing.F)` seeds a corpus of known interesting inputs with `f.Add(...)`, then defines a fuzz target with `f.Fuzz(func(t *testing.T, ...) { ... })`. Running `go test -fuzz=FuzzXxx` generates random mutations of the seed corpus and hunts for inputs that panic or fail an assertion — genuinely effective at finding edge cases a human wouldn't think to write by hand, especially around parsing and encoding code:

```go
func FuzzParseCSVRow(f *testing.F) {
    f.Add("a,b,c")
    f.Add("")
    f.Add(`"quoted, field",b`)
    f.Fuzz(func(t *testing.T, input string) {
        fields, err := ParseCSVRow(input)
        if err == nil && len(fields) == 0 && input != "" {
            t.Errorf("ParseCSVRow(%q) returned zero fields with no error", input)
        }
    })
}
```

Any crashing input the fuzzer finds is saved as a file under `testdata/fuzz/FuzzParseCSVRow/`, which `go test` (without `-fuzz`) replays as an ordinary regression test forever after — so a fuzz-discovered bug becomes a permanent part of the normal test suite the moment it's found and fixed.

## Test doubles without a mocking framework

*Connect the dot:* Chapter 7 established that Go interfaces are satisfied implicitly and are cheapest to define at the point of *use*, not at the point of implementation. Testing is where that habit pays for itself most directly. Instead of reaching for a mocking library that generates a double from an existing concrete type, idiomatic Go code defines a small interface for exactly what the caller needs, and a test provides a hand-written fake that implements it:

```go
type UserStore interface {
    GetUser(id string) (*User, error)
}

type fakeUserStore struct {
    users map[string]*User
    err   error
}

func (f *fakeUserStore) GetUser(id string) (*User, error) {
    if f.err != nil {
        return nil, f.err
    }
    return f.users[id], nil
}

func TestGreetUser(t *testing.T) {
    store := &fakeUserStore{users: map[string]*User{"1": {Name: "Ada"}}}
    got, err := GreetUser(store, "1")
    if err != nil || got != "Hello, Ada" {
        t.Errorf("GreetUser = %q, %v; want %q, nil", got, err, "Hello, Ada")
    }
}
```

This scales surprisingly far without external dependencies: no code generation step, no reflection-based matcher DSL, and the fake is just an ordinary Go struct you can read and modify like any other. Where teams do reach for a generated-mock library (`gomock`, `mockery`) is usually at scale, when dozens of tests need the same interface faked with varied call-count and argument-matching expectations — at that point, hand-writing every fake's conditional logic becomes its own maintenance burden, and generation (*connect the dot:* Chapter 23's `go generate`) starts paying for itself. `testify`'s `assert`/`require` packages are the most common third-party addition even in otherwise-stdlib-only codebases, purely because `assert.Equal(t, want, got)` is less boilerplate than a hand-rolled `if got != want { t.Errorf(...) }` at every call site, without changing the underlying philosophy.

For functions that produce large, structured output (a rendered template, a serialized API response), a **golden file** — the expected output checked into `testdata/`, compared against on every run, and regenerated with a `-update` flag when the output legitimately changes — beats hand-writing a giant expected-string literal in the test file itself.

Next: Chapter 22 explains *why* the standard library composes as well as it does — starting from the two smallest, most reused interfaces in Go, `io.Reader` and `io.Writer`.
