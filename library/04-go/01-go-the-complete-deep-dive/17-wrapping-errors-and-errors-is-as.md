# Wrapping Errors and errors.Is/As

**Fast overview:** Chapter 16 left one problem unsolved: a sentinel error compared with plain `==` stops working the instant any intermediate layer adds context, because a new error was created along the way and it's no longer *identical* to the sentinel. Go 1.13 (August 2019) closed this gap with **error wrapping** — a convention, an interface, and four functions in the `errors` package — that let an error carry a whole chain of causes back to its root, inspectable at any point without ever parsing a string. This chapter is that machinery, precisely, plus the taste question every team eventually has to answer: how much context is too much.

## Unwrap: the one-method interface that makes a chain

Wrapping is, like `error` itself, just an interface convention — nothing the compiler treats specially:

```go
type Wrapper interface {
    Unwrap() error
}
```

Any error whose type implements `Unwrap() error` returning a non-nil value is said to **wrap** that value, and the standard library's `errors` package knows how to walk that chain. A hand-written wrapping type looks like this:

```go
type QueryError struct {
    Query string
    Err   error
}

func (e *QueryError) Error() string { return fmt.Sprintf("query %q: %v", e.Query, e.Err) }
func (e *QueryError) Unwrap() error { return e.Err }
```

`e1.Unwrap()` returning `e2` means `e1` wraps `e2` — and if `e2` itself has an `Unwrap` method, the chain continues, potentially several layers deep, each one added by a different function as the original failure propagates up through the call stack.

## fmt.Errorf and %w: wrapping without a custom type

Writing a dedicated wrapper struct for every place you want to add context is more ceremony than most call sites need, so the common case uses `fmt.Errorf` with the `%w` verb instead — identical to `%v` in how it formats, but it additionally attaches an `Unwrap() error` method to the returned error, pointing at the argument you passed to `%w`:

```go
func loadConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("load config %s: %w", path, err)
    }
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("parse config %s: %w", path, err)
    }
    return &cfg, nil
}
```

Every layer that calls `loadConfig` and wraps its own error again builds the chain longer — a caller three functions up can still recover the original `os.ReadFile` failure (a `*fs.PathError`, itself wrapping a `syscall.Errno`) at the bottom of the chain, with every layer's added context still readable in the combined error string on the way there.

## errors.Is: walking the chain for identity

`errors.Is(err, target)` replaces the old `err == target` comparison, but walks the *entire* chain instead of comparing only the outermost error:

```go
var ErrNotFound = errors.New("not found")

func Lookup(id string) error {
    return fmt.Errorf("lookup %s: %w", id, ErrNotFound)
}

// elsewhere
err := Lookup("42")
if errors.Is(err, ErrNotFound) {
    // true — ErrNotFound is found by unwrapping, even though
    // err itself is a different, wrapping value
}
```

At each step, `errors.Is` checks identity by default (`==`), but an error type can override this by implementing its own `Is(target error) bool` method — useful when "equal" should mean something looser than pointer/value identity, such as matching on an error code embedded in different instances of the same type. *Connect the dot:* this is exactly the sentinel-error use case Chapter 16 introduced — `errors.Is` is the fix that makes sentinel errors survive wrapping.

## errors.As: walking the chain for type, and extracting it

`errors.As(err, &target)` walks the same chain, but instead of checking for one specific value, it looks for the first error in the chain whose *concrete type* matches `target`'s type, and if found, assigns it into `target`:

```go
type QueryError struct {
    Query string
    Err   error
}

func (e *QueryError) Error() string { return fmt.Sprintf("query %q: %v", e.Query, e.Err) }
func (e *QueryError) Unwrap() error { return e.Err }

// elsewhere, err came back wrapped several layers deep
var qe *QueryError
if errors.As(err, &qe) {
    log.Printf("failing query was: %s", qe.Query) // structured data, not a string parse
}
```

This is Chapter 16's custom-error-type use case getting the same treatment: a caller several layers removed from where `*QueryError` was created can still pull it — and its `Query` field — back out, without knowing or caring how many layers of `%w` wrapping sit in between. Like `Is`, `As` can be customized per type via an `As(target any) bool` method, though this is rare in practice.

## errors.Unwrap and errors.Join

`errors.Unwrap(err)` performs a single step manually — it calls `err`'s `Unwrap` method if it has one and returns the result, or `nil` otherwise. It exists mostly as a building block; `errors.Is` and `errors.As` are almost always the better choice because they walk the *whole* chain in one call rather than requiring you to loop by hand.

Go 1.20 (February 2023) added `errors.Join(errs ...error) error`, solving a different problem: combining *multiple, independent* errors into one, for situations like cleanup code that must attempt several operations and report every failure, not stop at the first:

```go
func closeAll(closers ...io.Closer) error {
    var errs []error
    for _, c := range closers {
        if err := c.Close(); err != nil {
            errs = append(errs, err)
        }
    }
    return errors.Join(errs...) // nil if errs is empty
}
```

The joined error's `Error()` method concatenates every wrapped error's message on its own line, and both `errors.Is` and `errors.As` walk *all* of the joined errors when searching — `errors.Join` builds a tree rather than a strict chain, but the same two inspection functions handle both shapes transparently.

## How much to wrap: good context versus noise

Wrapping is easy to overdo. Every layer adding its own generic context produces error strings like this, which technically satisfies "add context at every layer" while telling the reader almost nothing useful:

```
failed to process: failed to handle: failed to execute: failed to run: connection refused
```

Four layers, four generic verbs, and the only information anywhere in that string — `connection refused` — is buried at the end, indistinguishable from noise until you read carefully. Compare a version where each layer adds something the *next* layer up doesn't already know:

```
sync job 4471: fetch batch 3 of 6 from https://api.example.com/records: dial tcp: connection refused
```

Same underlying failure, but every segment adds identifying information — which job, which batch, which URL — that a human debugging this at 3am can act on immediately without attaching a debugger. The working guideline the standard library's own authors give: **wrap when you're adding real, specific context the caller doesn't already have; return the error bare (or don't wrap it at all — just return it as-is) when you have nothing to add.** A thin pass-through function that just forwards a database error upward doesn't need `fmt.Errorf("error: %w", err)` wrapped around it — that adds a word, not information.

The Go standard library's own guidance draws one more distinction worth carrying forward: wrap an error to expose it *as part of your API contract* — a `Parse` function built on top of an `io.Reader` the caller supplied should let I/O errors surface, because the caller owns that reader and needs to know if it failed. But don't wrap an error that would leak an implementation detail across an abstraction boundary — a `LookupUser` function built on `database/sql` internally should not propagate `sql.ErrNoRows` as part of its own public error surface, because swapping the underlying datastore later would then be a breaking API change for every caller who came to depend on matching that specific sentinel.

*Connect the dot:* this is where Part 3 pays off. Chapter 16 gave you sentinel errors and custom types as two ways to make failure *inspectable*; this chapter gave you the machinery to keep that inspectability intact across an arbitrarily deep call stack. Chapter 19 is next, and it's the payoff — reading how real, widely-used Go libraries actually design their error surfaces with both halves of this machinery, so an API's errors are as pleasant to handle as its success path.
