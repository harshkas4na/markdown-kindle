# The Error Handling Philosophy

**Fast overview:** Part 2 was concurrency — the language feature people learn Go *for*. Part 3 is the one people argue about: Go has no exceptions, no `try`/`catch`, no `throw`. A function that can fail returns an ordinary `error` value alongside its normal result, and the calling convention — `if err != nil { return err }`, repeated at nearly every call site in every Go file you'll ever read — is either the language's most disciplined design decision or its most tedious wart, depending who you ask. This chapter makes the actual argument the language's designers made, shows that the whole mechanism is nothing more than an interface (Chapter 7 in different clothes), and sets up the sentinel-vs-custom-type decision that Chapter 17 builds real machinery on top of.

## The argument against invisible control flow

Every mainstream language before Go that dealt seriously with failure reached for exceptions: a `throw` anywhere in a call stack, caught by a `catch` block possibly many frames above, with the entire path in between invisible at the call site unless the reader already knows which calls might throw and goes looking. Go's designers — building a language explicitly for codebases with thousands of engineers touching the same code over years (Chapter 1) — judged that invisibility to be a real cost, not a stylistic quibble. A function call that can silently unwind your stack and jump to a handler you can't see from where you're standing is a function call whose true behavior isn't fully expressed by its signature. At Google's scale, where the person reading a piece of code is very often not the person who wrote it, that gap between "what the call looks like" and "what the call can actually do" was judged expensive enough to design around.

The alternative Go chose is blunt: **make failure an ordinary value.** A function that can fail returns two things — its normal result, and an `error` that is `nil` on success and non-nil on failure:

```go
func Divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}
```

Nothing about calling `Divide` is invisible. The signature itself tells you it can fail, the compiler won't let you silently ignore the second return value in most idiomatic code (nothing *stops* you from writing `result, _ := Divide(a, b)`, but the underscore is a visible, deliberate act of ignoring it — not an accident), and the failure path is exactly as visible in the source as the success path, because it's the same kind of thing: a value, checked with an `if`, like any other value in the language.

## error is just an interface — two lines, no magic

The entire mechanism rests on a two-line interface declared in the `builtin` package:

```go
type error interface {
    Error() string
}
```

*Connect the dot:* this is Chapter 7's implicit interface satisfaction, doing all the work. Any type with an `Error() string` method — a struct, a named `int`, anything — satisfies `error`, automatically, with no `implements` keyword and no registration. There is nothing built into the compiler that treats errors specially beyond ordinary interface mechanics; `error` is a convention enforced by the standard library and the community, not a distinct kind of type. Once that clicks, error handling stops looking like a separate subsystem of the language and starts looking like the same interface satisfaction you already use everywhere else, aimed at one specific, extremely common job.

## The repetition is a design choice, not an oversight

`if err != nil { return err }`, or some close variant, appears after nearly every fallible call in idiomatic Go — sometimes several times in a ten-line function. This is the most common complaint from newcomers, and it's worth taking seriously rather than dismissing, because the language's designers *knew* this would be the reaction and made the trade anyway, for reasons worth stating plainly rather than hand-waving away:

- **Every failure path is searchable and greppable.** `grep -rn "if err != nil"` finds every place your codebase currently handles — or fails to handle — an error. There is no equivalent single search for "every place an exception might be silently swallowed by an overly broad `catch (Exception e) {}` three layers up," because exception handling doesn't have to be local to where it applies.
- **There is no hidden jump.** Reading a Go function top to bottom, in order, tells you the true control flow — every branch is a visible `if`, `return`, or `switch`, nothing more. A reviewer doesn't need to separately audit "what happens if this specific call throws," because that behavior is spelled out in the same function, in the same place, in the same syntax as everything else.
- **The cost is paid once, visibly, at write time — not unpredictably, at read time.** Exceptions save a few keystrokes per call site and shift the cost onto whoever later has to trace an exception's actual path through the codebase to understand what a piece of code really does under failure. Go's designers bet that the second cost, paid by strangers reading unfamiliar code years later, is larger in aggregate than the first, paid once by the original author.

None of this makes the repetition pleasant, and the Go community itself has repeatedly proposed lighter syntax to reduce it without reintroducing invisible control flow — most notably the 2019 "check/handle" proposal, which would have added `check f()` as sugar for exactly the `if err != nil { return err }` pattern while keeping the return-value semantics underneath. It was ultimately withdrawn after extensive community debate, and no replacement has shipped as of this writing — which is itself worth knowing: this is a live, still-unresolved tension in the language's design, not a settled question the rest of this book is pretending was solved cleanly. Go 1.20's `errors.Join` (Chapter 17) is the most recent concrete change in this area, and it addresses a different problem (combining several errors) rather than this one.

## Sentinel errors: comparable identity, for expected outcomes

A **sentinel error** is a package-level `error` value, declared once, that callers compare against to detect one specific, expected condition:

```go
var ErrNotFound = errors.New("not found")

func Lookup(id string) (*Record, error) {
    rec, ok := store[id]
    if !ok {
        return nil, ErrNotFound
    }
    return rec, nil
}
```

Historically, callers checked with plain equality — `if err == ErrNotFound`. That still works for an error returned directly, but breaks the moment the error has been wrapped by an intermediate layer adding context (Chapter 17 is entirely this problem and its fix, `errors.Is`). Sentinel errors are the right tool for an outcome the caller is expected to handle as a normal branch of program logic — `io.EOF` (returned by `Read` to signal a clean end of input, not a malfunction) is the standard library's own canonical example, checked constantly in read loops without anyone treating it as exceptional.

## Custom error types: structured data, for outcomes that need more than a string

When a caller needs more than "which specific error was this," a **custom error type** — an ordinary struct implementing `Error() string`, carrying whatever fields matter — is the idiomatic answer:

```go
type ValidationError struct {
    Field string
    Msg   string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Msg)
}

func Validate(input Form) error {
    if input.Email == "" {
        return &ValidationError{Field: "email", Msg: "required"}
    }
    return nil
}
```

A caller that needs the field name — an HTTP handler mapping this to a 400 response with a specific error body, say — extracts it with `errors.As` (Chapter 17), pulling the concrete `*ValidationError` back out of whatever `error` interface value it arrived in, rather than parsing a string.

## Choosing between the two

The decision is really about what the caller needs to *do*, not what feels more sophisticated to write. A sentinel error answers "was it *this* specific, known condition?" — cheap to declare, cheap to check, and appropriate whenever the failure is a single well-known case (not found, already exists, EOF). A custom type answers "what, specifically, went wrong, and what data do I need to act on it?" — appropriate whenever a caller needs structured detail, not just a yes/no on one known condition. Well-designed Go APIs — Chapter 19 goes through several real examples in detail — use both at once: a package might export a handful of sentinel errors for its most common expected outcomes, and one or two custom error types for cases that carry genuinely structured failure data, with everything else simply wrapped with added context, which is exactly where the next chapter picks up.

Next: Chapter 17 — how `fmt.Errorf("%w", err)` and the `errors` package's `Is`, `As`, `Unwrap`, and `Join` functions let sentinel errors and custom types survive being wrapped through several layers of a call stack without losing the information this chapter just taught you to attach.
