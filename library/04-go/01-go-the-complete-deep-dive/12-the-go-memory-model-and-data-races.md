# The Go Memory Model and Data Races

**Fast overview:** goroutines and channels (Chapters 10–11) let you write concurrent code that *reads* correctly. Whether it *runs* correctly is a separate question, governed by a much stricter document: the Go memory model, which specifies exactly when a write in one goroutine is guaranteed to be visible to a read in another. Get this wrong and you don't get a compile error or even a reliable crash — you get a data race, which Go defines as genuine undefined behavior. This chapter is the precise rules, why "it worked when I tested it" is worthless evidence for concurrent code, and the tool (`-race`) that actually catches the bug instead of hoping you don't hit it in production.

## Program order is not the same as global order

Inside a single goroutine, Go guarantees your code behaves exactly as written — the compiler and CPU can reorder instructions for performance, but never in a way that a single-threaded observer (the goroutine itself) could detect. The spec calls this the **sequenced-before** relation, and it's the same guarantee every language gives you for straight-line code.

The trap is assuming that guarantee extends *across* goroutines. It doesn't, at all. If goroutine A writes a variable and goroutine B reads it with no synchronization between them, the compiler and CPU are free to reorder, cache, or delay that write in ways B might never observe — not because Go is buggy, but because nothing in the language told the runtime these two operations needed to be ordered relative to each other. Two independent goroutines are, absent synchronization, two independent sequential programs that happen to share memory.

## Happens-before: the only relation that matters

The Go memory model defines a single relation, **happens-before**, and the entire correctness story for concurrent Go code is: *a read is only guaranteed to observe a write if the write happens-before the read*. No happens-before edge, no guarantee — the read might see the new value, might see the old one, might (for multi-word values) see a torn mix of both. The model was substantially rewritten and formalized for Go 1.19 (2022), adopting the same **DRF-SC** guarantee (data-race-free implies sequential consistency) that C, C++, Java, JavaScript, Rust, and Swift give race-free programs: *in the absence of data races, your goroutines behave as if they were all interleaved on a single processor, in some order consistent with each goroutine's own program order.* That guarantee is exactly as strong as it sounds, and exactly as conditional — it only holds once your program has no data races. Every synchronization primitive in the standard library exists to manufacture happens-before edges on purpose:

| Primitive | The happens-before edge |
|---|---|
| `go f()` | The `go` statement happens-before `f`'s execution begins |
| Channel send (buffered or unbuffered) | The send happens-before the corresponding receive *completes* |
| Channel receive on unbuffered channel | The receive happens-before the corresponding send *completes* — the two block until they rendezvous, so it's really a mutual edge |
| Channel close | The close happens-before a receive that returns because the channel is closed |
| `mu.Unlock()` then a later `mu.Lock()` | Unlock call *n* happens-before Lock call *n*+1 succeeds, for the same mutex |
| `sync.Once.Do(f)` | The one execution of `f` happens-before *every* call to `Do` returns |
| `sync/atomic` operations | If atomic operation A's effect is observed by atomic operation B, A happens-before B — all atomics in a program act as if executed in one sequentially consistent order |
| Package `init()` | If package `p` imports `q`, all of `q`'s `init` happens-before any of `p`'s; all `init` happens-before `main.main` |

*Connect the dot:* every one of these is a primitive you already met — channels in Chapter 11, `sync.Mutex`/`Once`/`atomic` are next in Chapter 13 — and this table is the actual reason they exist. A channel isn't just a queue; it's a happens-before edge with a value attached. A mutex isn't just mutual exclusion; it's a happens-before edge between whoever held the lock last and whoever acquires it next.

A worked example, straight from the spec's own style:

```go
var a string

func f() {
    print(a)
}

func hello() {
    a = "hello, world"
    go f()
}
```

`hello` writes `a` *before* the `go` statement, and the `go` statement happens-before `f` begins — so `f` is guaranteed to print `"hello, world"`. Now the unbuffered-channel version, which is the pattern you'll actually write:

```go
func main() {
    c := make(chan int)
    var a string

    go func() {
        a = "hello, world"
        c <- 0 // happens-before the receive completes
    }()

    <-c
    print(a) // guaranteed to see "hello, world"
}
```

Remove the channel and this program has a data race: `main` might print `a` before the goroutine ever runs, might print an empty string, might in principle print a corrupted value, and the language makes zero promises about which.

## What a data race actually is, formally

The spec is precise: a **data race** is two memory operations on the same location, at least one of them a write, executed by different goroutines, with no happens-before relationship between them in either direction. Note what that definition does *not* require: it doesn't require the operations to actually collide at the hardware level, it doesn't require a "wrong" value to actually appear, and it doesn't require the bug to reproduce on your machine. The race exists the instant the ordering is unenforced — whether or not today's compiler, today's CPU, and today's scheduler happen to produce a visible symptom.

This is the part experienced engineers coming from Java or C# under-appreciate: those languages give unsynchronized access to ordinary variables a *weaker but still bounded* guarantee (you might get a stale value, but not garbage). Go makes no such promise. A race on a multi-word value — and this is where it gets genuinely dangerous — can produce a **torn read**: half the old value and half the new one, byte-for-byte garbage that was never written by anyone. *Connect the dot:* a slice header (Chapter 3) is three words — pointer, length, capacity — and an interface value (Chapter 7) is two — a type descriptor and a data pointer. Race on either without synchronization and you can observe a length that doesn't match its pointer, or a type descriptor paired with the wrong concrete value underneath it — the kind of corruption that can crash the runtime itself, not just return a wrong answer. This is why Go's official position, stated almost verbatim in the memory model document, is blunt: *if you find yourself needing to reason carefully about reordering to convince yourself code is correct, the code is wrong — serialize the access instead.*

## The race detector: catching it before production does

Go ships a race detector built on Google's ThreadSanitizer technology, enabled with one flag on any of the standard commands:

```sh
go test -race ./...
go run -race main.go
go build -race -o app .
```

At a high level, the instrumented binary tracks, for every memory access, which goroutine touched it and what that goroutine's current logical "clock" is relative to every synchronization event it has participated in — a vector-clock-style algorithm operating on shadow memory alongside your program's real memory. When two accesses to the same address are found with no happens-before relationship between their clocks, and at least one is a write, the detector reports the exact pair of stack traces: where the conflicting accesses happened, and which goroutines they were on.

Two properties matter for how you actually use it. First, it's **dynamic, not static** — it can only report races that occur during the specific execution it observed. A race on a code path your test suite never exercises concurrently is invisible to `-race` no matter how many times you run it; this is why table-driven tests (Chapter 21) that explicitly exercise concurrent call patterns matter more than a normal test suite would suggest, and why some teams run their race-enabled test suite hundreds of times in CI (`go test -race -count=100`) specifically to increase the odds a rare interleaving gets triggered. Second, the instrumented binary is genuinely slower (roughly 2–20x CPU, 5–10x memory) — nobody ships a `-race` binary to production, but every serious Go team runs their full test suite with it in CI on every commit, because the alternative is finding these bugs from a stack trace at 3am, or worse, not finding them at all and shipping quietly wrong answers.

## Why this chapter earns its place before sync and patterns

Chapters 13 and 14 are full of primitives and patterns that look like plumbing — lock this, wait for that, select on a `Done()` channel. Every one of them is, underneath, a happens-before edge being deliberately constructed so that a later chapter's code is provably race-free rather than *probably* race-free. Read them with this chapter's table in the back of your mind, and each primitive stops being an API to memorize and becomes an answer to one question: *what happens-before edge does this create, and between which two goroutines?*

Next: `sync.Mutex`, `RWMutex`, `WaitGroup`, `Once`, and `atomic` — the toolbox for building those edges when a channel is the wrong shape for the problem.
