# Panic, Recover, and Defer

**Fast overview:** Go has a real exception-like mechanism — `panic` and `recover` — but it deliberately sits outside the error-handling story from Chapter 16, reserved for programmer bugs and truly unrecoverable situations rather than routine failure. Wiring the two together is `defer`, Go's scope-exit primitive, which runs a function call when its surrounding function returns, in reverse order of registration, no matter how that return happens. This chapter nails down the exact semantics of all three, because the exact semantics are where people get bitten: when arguments to a deferred call are evaluated, how a deferred function can rewrite a named return value, and why a panic in an unrecovered goroutine takes down your whole process, not just that goroutine.

## `defer`, precisely

A `defer` statement schedules a function call to run when the *surrounding function* returns — not when the current block ends, not when the current loop iteration ends. Two details matter more than people expect:

```go
func process(id int) {
    fmt.Println("start", id)
    defer fmt.Println("cleanup", id) // arguments evaluated NOW
    id = 999
    fmt.Println("end", id)
}
```

Calling `process(1)` prints `start 1`, `end 999`, `cleanup 1` — the `id` argument to the deferred `fmt.Println` was evaluated the instant the `defer` statement executed, capturing `1`, even though `id` was reassigned to `999` before the function returned. This is the single most misunderstood detail of `defer`: **the function value and its arguments are evaluated immediately; only the call itself is postponed.** If you want a deferred call to see a variable's *final* value, wrap it in a closure instead:

```go
defer func() { fmt.Println("cleanup", id) }() // reads id at call time, prints 999
```

The second detail: multiple defers in one function run in **LIFO order** — last deferred, first executed — which matches how you'd want resource cleanup to unwind (close what you opened last, first):

```go
func openAll() error {
    f, err := os.Open("a.txt")
    if err != nil {
        return err
    }
    defer f.Close()

    g, err := os.Open("b.txt")
    if err != nil {
        return err
    }
    defer g.Close() // runs before f.Close()
    // ... use f and g ...
    return nil
}
```

`defer` runs on *every* exit path — a normal `return`, an early `return` from a guard clause, or a `panic` unwinding through the function — which is exactly why it's the idiomatic way to release a mutex (*connect the dot:* `mu.Lock(); defer mu.Unlock()`, Chapter 13), close a file, or roll back a transaction. You write the cleanup right next to the acquisition, and the compiler guarantees it runs regardless of which of the function's several `return` statements actually fires.

### Defer can rewrite the return value

If a function uses **named return values**, a deferred function closing over those names can read *and modify* them after the `return` statement has already set them but before the function actually hands control back to its caller. This is the mechanism behind Go's single most common panic-to-error conversion idiom:

```go
func safeDivide(a, b int) (result int, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("safeDivide: recovered from panic: %v", r)
        }
    }()
    result = a / b // panics with "integer divide by zero" if b == 0
    return result, nil
}
```

Here, if `a / b` panics, the deferred function runs during the unwind, calls `recover()` to stop it, and assigns to the named return `err` — so `safeDivide` returns a normal `(0, error)` pair to its caller instead of crashing. This is the standard pattern for turning a panic into an ordinary Chapter 16 error *at a package boundary*, and it only works because `err` is a named return: an unnamed `(int, error)` return has nothing for the deferred closure to assign into.

## `panic`: what triggers it, and what it does

`panic` can be triggered explicitly (`panic("something is badly wrong")`, or `panic(myError)` — a panic value can be anything, though an `error` is conventional) or implicitly, by the runtime itself, when your program does something with no sane recovery: indexing a slice out of bounds, dereferencing a `nil` pointer, dividing an integer by zero, a failed type assertion using the single-value form (Chapter 7), or sending on a closed channel (Chapter 11). These runtime panics are the language telling you a precondition was violated — they are bugs, not "errors" in the Chapter 16 sense.

When a panic happens, the current function stops executing immediately. Go runs any deferred functions registered in that function (in LIFO order, as above), then does the same in the *caller*, and the caller's caller, unwinding the whole call stack — unless, somewhere along the way, a deferred function calls `recover()`. If nothing recovers it, the program prints the panic value and a full stack trace, and exits with a non-zero status. There is no way to "catch" a panic from outside the goroutine where it happened; recovery must happen from within that same goroutine's unwind.

## `recover()`: only useful in exactly one place

`recover()` stops a panic's unwind and returns the value passed to `panic`, or `nil` if no panic is in progress. It has one, very specific, useful location: **called directly inside a deferred function**. Calling `recover()` anywhere else — mid-function, not inside a `defer`, or inside a deferred function that was itself called through another function — simply returns `nil` and does nothing, even if a panic is actively unwinding through that stack frame. This is not a stylistic preference; it's how the language defines `recover`'s behavior, and it's why every real recovery site looks like the `safeDivide` example above: `defer func() { if r := recover(); r != nil { ... } }()`.

## Why this is not Go's exception handling

*Connect the dot:* Chapter 16 made the case that Go rejected exceptions on purpose — an explicit `error` return keeps failure visible in a function's signature and at every call site, instead of letting control silently jump through frames that never mention it. `panic`/`recover` looks like it reintroduces exactly that invisible control flow, and used carelessly, it does. The idiomatic boundary is narrow: **panic for programmer bugs and unrecoverable states, error values for everything a caller might reasonably need to handle.** A function that fails because a user typed an invalid email address should return an `error`. A function that fails because an internal invariant it assumed was true turned out to be false — an index computed wrong, a map that should never be empty and is — is allowed to panic, because there's no sensible way for the immediate caller to "handle" a bug in your own logic; the right fix is to fix the bug, not to write recovery code around it.

The one broadly accepted exception to "don't recover in application code" is at a **boundary between independent units of work** — most commonly, a per-request HTTP handler. *Connect the dot:* Chapter 25 covers this as "recovery middleware": an HTTP server wraps every handler in a deferred `recover()` so that a panic triggered by one malformed request (a nil map write, a bad index, a third-party library bug) logs a stack trace and returns a 500 to that one client, instead of taking down every other in-flight request on the process. That's a deliberate, narrow use of recovery as a blast-radius firewall — not a general substitute for error handling inside the handler's own logic.

## A panic in a goroutine is a whole-process panic

Here is the detail that surprises people coming from languages with per-thread exception isolation: **if a goroutine panics and nothing recovers within that same goroutine, the entire program crashes** — not just that goroutine. There is no default supervisor that catches a stray goroutine's panic and lets the rest of the program continue.

```go
func worker(jobs <-chan int) {
    for j := range jobs {
        go func(n int) {
            if n == 13 {
                panic("unlucky job") // crashes the WHOLE program if unrecovered
            }
            fmt.Println("processed", n)
        }(j)
    }
}
```

*Connect the dot:* Chapter 15 covered goroutine leaks and deadlocks as the two everyday concurrency failure modes; an unrecovered panic in a spawned goroutine is the third, more violent one — and the standard defense is the same recovery pattern from this chapter, applied at the top of *every* goroutine you launch that isn't tightly supervised by a `WaitGroup`-joined caller: `defer func() { if r := recover(); r != nil { log.Printf("worker panic: %v", r) } }()` as the very first line inside the goroutine's function body. Skipping this on a long-running background goroutine in a production service is one of the most common ways a single edge case turns into a full outage.

Next: Chapter 19 closes out Part 3 by reading how real standard-library and popular-library code actually designs its error types — the payoff for everything Chapters 16 through 18 set up.
