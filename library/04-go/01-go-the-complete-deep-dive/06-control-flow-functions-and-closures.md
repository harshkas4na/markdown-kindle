# Control Flow, Functions, and Closures

**Fast overview:** Go has exactly one loop keyword, a switch that doesn't fall through by default (the opposite of C), and functions that are first-class values capable of capturing their surrounding scope as closures. None of this is exotic, but two details — how `range` variables behaved before Go 1.22 and how `defer` schedules work — have caused enough real production bugs across the ecosystem that they deserve full, careful treatment rather than a passing mention.

## `for`: the only loop, four ways to write it

```go
for i := 0; i < 10; i++ { }       // classic three-clause

i := 0
for i < 10 { i++ }                // while-style: just a condition

for { break }                     // infinite loop

for i, v := range []string{"a","b"} { }  // range: index+value over a slice
for k, v := range map[string]int{} { }   // range: key+value over a map (random order!)
for i, r := range "héllo" { }            // range: byte-index+rune over a string (Ch 2)
for v := range someChannel { }           // range: receives until the channel closes (Ch 11)
for i := range 5 { }                     // range over an int (Go 1.22+): i = 0,1,2,3,4
```

Go collapsed C's `for`, `while`, and `do-while` into one keyword because they're really the same control structure with different amounts of boilerplate filled in — another instance of Chapter 1's orthogonality argument. `range`'s behavior depends entirely on what you range over, and it's worth memorizing that table above rather than re-deriving it each time, especially the map case (order is randomized on purpose, per Chapter 4) and the channel case (a range loop over a channel is a blocking receive loop that exits cleanly when the channel is closed — you'll use this constantly starting in Chapter 11).

## `if` with an init statement, and why it shows up everywhere

```go
if err := doSomething(); err != nil {
    return err
}
// err is not visible here — its scope was the if statement itself
```

`if` (and `for`, and `switch`) can carry an optional init statement before the condition, scoped to the entire `if`/`else` chain and nowhere else. This is why `if err := f(); err != nil { ... }` is the single most common five-word shape in any Go codebase — it declares `err`, checks it, and lets it fall out of scope immediately after, instead of leaking a variable you'll never use again into the enclosing function body.

## `switch`: no fallthrough by default — the opposite of C

```go
switch status {
case "pending":
    handlePending()
case "active", "trialing":     // multiple values, one case
    handleActive()
default:
    handleUnknown()
}
```

Every `case` in Go implicitly breaks after its block — there's no accidental fall-through into the next case the way C's `switch` demands a `break` on every single branch to avoid. If you genuinely want fall-through behavior, it's available as an explicit keyword, `fallthrough`, as the last statement in a case — deliberately rare in real code because the whole point of the default behavior is that fall-through should be a decision you state, not a default you forget to guard against.

Go's `switch` also supports **no tag at all**, which turns it into a cleaner chain of `if`/`else if`:

```go
switch {
case n < 0:
    return "negative"
case n == 0:
    return "zero"
default:
    return "positive"
}
```

And it supports a **type switch**, which inspects the dynamic type stored inside an interface value rather than comparing an ordinary value — that's genuinely a different feature bolted onto the same keyword, and it's covered properly once interfaces themselves are introduced in Chapter 7, since a type switch only makes sense in the context of what an interface value actually stores.

## Multiple return values, and the convention that runs through the whole book

```go
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, fmt.Errorf("divide by zero")
    }
    return a / b, nil
}

result, err := divide(10, 0)
if err != nil {
    // handle it
}
```

Multiple return values are a real language feature, not a struct or tuple hack — a function can return as many values as it likes, and the `(T, error)` shape you see above is by far the most common use of it in the entire standard library and ecosystem. *Connect the dot:* this convention — error as the last return value, checked immediately, explicitly — is not just a style preference; it's the entire subject of Chapter 16, and everything in this book from here forward will use this exact shape without further comment, because you'll see it in literally every chapter that follows.

## Named returns and naked returns

```go
func split(sum int) (x, y int) {
    x = sum * 4 / 9
    y = sum - x
    return   // "naked" return — returns the current values of x and y
}
```

A function can name its return values in the signature, which pre-declares them (zero-valued) at the top of the function body and lets a bare `return` send back whatever they currently hold. This is genuinely useful for short functions, and essential for functions that need to modify a return value inside a `defer` (a pattern you'll meet properly once panic/recover interacts with named returns in Chapter 18). For anything longer than a handful of lines, most Go style guides — including the standard library's own conventions — actively discourage naked returns, because a `return` with no visible values forces the reader to scroll back up to the signature to know what's actually being returned, which is a real readability cost for a small typing convenience.

## Variadic functions

```go
func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}

sum(1, 2, 3)          // nums is []int{1, 2, 3}
nums := []int{4, 5, 6}
sum(nums...)           // spread an existing slice into a variadic call
```

`...T` in a parameter list packages any number of trailing arguments into a single `[]T` inside the function — `fmt.Println` is the variadic function you've already used without necessarily noticing. A variadic parameter must be the last one in the signature, and a caller can either pass individual arguments or "spread" an existing slice into the call with a trailing `...`, but never both at once.

## Functions as values, and closures

```go
func makeCounter() func() int {
    count := 0
    return func() int {
        count++
        return count
    }
}

next := makeCounter()
fmt.Println(next(), next(), next())  // 1 2 3
```

Functions in Go are first-class values — you can assign them to variables, pass them as arguments, store them in structs and maps, and return them from other functions, all with completely ordinary function-type syntax (`func() int`, `func(string) error`, and so on). A **closure** is a function literal that references variables from the scope it was defined in — `count` above isn't a global or a parameter, it's captured by reference from `makeCounter`'s local scope, and it survives as long as the returned closure itself does, because escape analysis (Chapter 5) promotes it to the heap the moment the compiler sees it needs to outlive the stack frame that declared it. Each call to `makeCounter()` creates a genuinely independent `count`, because each call creates a fresh closure over a fresh variable.

## The loop-variable trap, and how Go 1.22 fixed it

This is the single most infamous Go gotcha in the language's history, and it's worth understanding both the old broken behavior and the fix, because a huge amount of pre-2024 Go code, blog posts, and interview questions assume the old semantics:

```go
// Before Go 1.22, this printed 3 3 3 — not 0 1 2!
funcs := make([]func(), 0, 3)
for i := 0; i < 3; i++ {
    funcs = append(funcs, func() { fmt.Println(i) })
}
for _, f := range funcs { f() }
```

Before Go 1.22 (released February 2024), a `for` loop's index/range variables were declared **once** and reused across every iteration — every closure captured a reference to the *same* variable, and by the time any of the closures actually ran, the loop had finished and `i` held its final value. The traditional fix, still worth knowing because it appears throughout older code and other people's codebases, was to shadow the variable explicitly inside the loop body: `i := i` before the closure, creating a fresh, iteration-local copy to capture.

**Go 1.22 changed the language itself** so that `for` loop variables (both the classic three-clause form and `range` variables) are now a fresh variable **per iteration**, matching what most newcomers already assumed the behavior was. The example above now correctly prints `0 1 2` with no workaround needed. This is one of the very few semantic changes ever made to the language proper, and it was done carefully specifically because of Go 1's backward-compatibility promise from Chapter 1 — it's a behavior change but not a compatibility break, since no correct program could have depended on the old aliasing behavior in a way that the new behavior breaks.

## `defer`: scheduling cleanup, precisely

```go
func readConfig(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close()   // scheduled now, runs when readConfig returns — any exit path
    // ... use f ...
    return nil
}
```

`defer` schedules a function call to run when the surrounding function returns — regardless of which `return` statement triggers it, or even if the function exits via a panic (Chapter 18 covers that interaction fully). Two precise rules matter far more than they look like they should:

- **Deferred calls run in LIFO order** — last deferred, first executed — which matters the moment you defer more than one cleanup call in the same function (closing a database transaction before closing the connection it belongs to, for instance).
- **Arguments to a deferred call are evaluated immediately, at the `defer` statement itself — not when the deferred call actually runs.** `defer fmt.Println(x)` captures the value of `x` *right now*; if `x` changes later in the function, the deferred call still prints the value it had at defer-time. If you need the deferred call to see a value's *final* state, wrap it in a closure: `defer func() { fmt.Println(x) }()` evaluates `x` only when the closure itself finally runs.

`defer` is idiomatic Go's answer to the RAII-style cleanup that C++ gets from destructors and Python gets from `with` blocks — it's used constantly for unlocking a mutex right after locking it (`mu.Lock(); defer mu.Unlock()`), closing files and network connections, and any other "acquire, then guarantee release" pairing, precisely because putting the cleanup call immediately next to the acquisition, rather than at the bottom of the function past every early return, makes it far harder to accidentally forget.

Next: interfaces — the feature that makes closures, structs, and every other value type in this chapter pluggable into code that was never written with them in mind.
