# Designing APIs That Fail Well

**Fast overview:** Chapters 16–18 gave you the mechanics — errors as values, wrapping and unwrapping, panic as the narrow escape hatch. This chapter is the payoff: how do you actually *design* errors so the code calling your function can make a decision, not just print a string and move on? The standard library is the best teacher here, because every awkward edge case it handles (partial reads, timeouts, "this file doesn't exist" versus "you're not allowed to open it") had to be solved once and then lived with for over a decade. Read its choices as case law, then turn them into principles you can apply to your own APIs.

## Case study: `*fs.PathError` — structure over strings

Call `os.Open("/does/not/exist")` and you get back an error whose `Error()` string reads `open /does/not/exist: no such file or directory`. That string is for a human. But the actual returned value is a `*fs.PathError`:

```go
type PathError struct {
    Op   string
    Path string
    Err  error
}
```

A caller that wants to *do* something with this failure — retry, log structured fields, decide whether to create the file instead — doesn't have to parse the string. It can inspect `Op` (`"open"`), `Path` (`"/does/not/exist"`), and `Err` (the underlying `syscall.Errno`, which `errors.Is(err, fs.ErrNotExist)` can match against). *Connect the dot:* this is Chapter 17's wrapping chain in the wild — `PathError` wraps a lower-level `syscall` error and adds structured context, and `errors.Is`/`errors.As` are how you get at either layer without caring which one you actually received.

## Case study: `io.EOF` — a sentinel that isn't bad news

Chapter 16 introduced sentinel errors as `var Err... = errors.New(...)` values a caller compares against with `errors.Is`. `io.EOF` is the sentinel that teaches the most important lesson about them: **not every error means something went wrong.** Reading a file to the end is success, and Go represents "there is nothing more to read" as an `error` value anyway, because it has to be returned from the same `(n int, err error)` signature as a real failure — but callers are expected to treat `io.EOF` as an ordinary, planned control-flow signal, not something to log or retry:

```go
for {
    n, err := r.Read(buf)
    if n > 0 {
        process(buf[:n])
    }
    if err == io.EOF {
        break // done, not broken
    }
    if err != nil {
        return fmt.Errorf("reading: %w", err) // this one really is bad news
    }
}
```

*Connect the dot:* Chapter 22 covers `io.Reader`'s exact contract around `EOF` in full; the design lesson here is narrower — decide, for every sentinel you define, whether it means "stop, something is wrong" or "stop, you're done," and document it in the doc comment (Chapter 20) so nobody has to guess from the name alone.

## Case study: `net.Error` — an interface for a *decision*, not a type

The `net` package's errors can come from dozens of concrete types depending on OS and transport, but a caller almost never needs to know which one. Instead, `net.Error` is a small interface:

```go
type Error interface {
    error
    Timeout() bool
}
```

Any network error a caller receives can be asserted against this interface (`if ne, ok := err.(net.Error); ok && ne.Timeout() { retry() }`) to answer the one question that actually matters for control flow — *is this worth retrying?* — without a giant type switch enumerating every possible concrete error the networking stack could produce. This is the pattern to copy: when callers of your API will realistically want to branch on failure, **design the error around the question they're asking**, not around your internal implementation's type hierarchy.

## Four principles, distilled

**1. Design for the caller's next decision, not for a log line.** Before defining an error, ask what the calling code needs to know to decide what happens next — retry with backoff, give up and surface it to a user, escalate to an on-call engineer, or silently fall back to a default. A `LoadConfig` function that can fail because the file is missing versus because the file exists but is malformed JSON are different decisions for the caller (create a default config, versus refuse to start) — collapsing both into one generic `error` string forces the caller to string-match to tell them apart, which Chapter 16 already established is exactly what Go's error design is trying to avoid.

**2. Prefer a small, closed set of sentinels or types over an open set of formatted strings.** A caller can only branch reliably on `errors.Is`/`errors.As` (Chapter 17) if you've actually exported something to compare against. If every failure path in your package does `return fmt.Errorf("something went wrong: %v", detail)` with no sentinel or type behind it, you've made every one of those failures indistinguishable to code — only to a human reading logs. Export `ErrNotFound`, `ErrPermission`, a `*ValidationError` type with a `Field` string — whatever the small number of *actionable* categories actually are — and let everything else collapse into a generic wrapped error, because not every failure needs its own branch.

**3. Don't leak implementation details across a package boundary.** If your exported `LoadUser(id string) (*User, error)` is backed by a SQL query, a caller who doesn't import your database driver shouldn't receive a raw `*pq.Error` and have to import `github.com/lib/pq` just to inspect it. Wrap it: `return nil, fmt.Errorf("load user %s: %w", id, err)`, or better, translate specific known cases into your own package's sentinels (`if isUniqueViolation(err) { return nil, ErrDuplicateUser }`) so your API's error surface is defined by *your* package, not by whichever library you happen to depend on this year. This also means you can swap the database driver later without breaking every caller's `errors.As` type assertions.

**4. Decide deliberately how partial failure is represented.** When an operation can fail in more than one place at once — validating five form fields, fetching from three backends concurrently (*connect the dot:* Chapter 14's fan-out patterns) — you have three honest options, and picking one on purpose beats defaulting into whichever your code happened to do first: return only the *first* error encountered (simplest, loses information); collect and return *all* of them via `errors.Join` (Go 1.20+, itself unwrappable with `errors.Is`/`errors.As` against any joined member); or define your own structured multi-error type (e.g., a `ValidationErrors []FieldError`) when callers need to display every problem at once, like a form with several invalid fields highlighted simultaneously. `errors.Join` covers most cases now without needing a bespoke type:

```go
func validate(u User) error {
    var errs error
    if u.Name == "" {
        errs = errors.Join(errs, errors.New("name is required"))
    }
    if u.Age < 0 {
        errs = errors.Join(errs, errors.New("age must be non-negative"))
    }
    return errs // nil if nothing was joined
}
```

## Part 3, assembled

Put the four chapters together and you have the complete toolkit: **errors as ordinary values, checked explicitly** (Chapter 16) instead of invisible exceptions; **wrapping** to preserve a full cause chain while adding context at each layer, and `errors.Is`/`errors.As` to inspect that chain without caring how deep the real cause is buried (Chapter 17); **panic and recover** as the narrow, deliberate escape hatch for programmer bugs and process-boundary firewalls, not a general failure mechanism (Chapter 18); and this chapter's judgment calls for turning all of that into an API that a caller — not just a human reading a log — can actually act on. This is, not coincidentally, why so much of Go's standard library reads the same way once you know what to look for.

Next: Part 4 turns from error handling to the broader idioms that make Go code recognizable at a glance — starting with Chapter 20's tour of naming, formatting, and documentation conventions.
