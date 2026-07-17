# Channels: The Core Primitive

**Fast overview:** Tony Hoare's 1978 paper on Communicating Sequential Processes proposed a different foundation for concurrent programs than shared memory and locks: processes that don't touch each other's state at all, only pass messages through typed channels. Go's channels are that idea, made into a first-class, garbage-collected, type-checked language primitive — and the language's own proverb states the philosophy outright: **"Don't communicate by sharing memory; share memory by communicating."** Chapter 10 gave you goroutines that run independently; this chapter is how they coordinate and exchange data without a mutex in sight (mutexes get their own chapter — 13 — for the cases where a channel is genuinely the wrong shape).

## Making, sending, and receiving

A channel is a typed conduit, created with `make`:

```go
ch := make(chan int)        // unbuffered
buffered := make(chan int, 10) // buffered, capacity 10

ch <- 42       // send: blocks until someone receives (unbuffered) or there's room (buffered)
v := <-ch      // receive: blocks until someone sends
v, ok := <-ch  // comma-ok form: ok is false if the channel is closed and drained
```

The arrow points in the direction data flows: `ch <- 42` pushes into the channel, `<-ch` pulls out of it. A channel's zero value is `nil` — declared but not `make`'d — and operations on a nil channel block forever, which sounds useless until the `select` section below shows why that's actually a deliberately useful property.

## Unbuffered vs buffered: rendezvous vs queue

This distinction is the one to internalize before anything else about channels makes sense.

An **unbuffered** channel (`make(chan T)`, capacity 0) is a synchronous rendezvous: a send blocks until exactly one receiver is ready to take the value *at that instant*, and a receive blocks until exactly one sender is ready to hand one over. Neither side "wins" a race to go first — they meet, or neither proceeds. This gives you a strong guarantee for free: when a send on an unbuffered channel returns, you know the receiver has already received the value (not merely that it was queued somewhere) — a real synchronization point, not just a data pipe.

A **buffered** channel (`make(chan T, n)`, capacity `n > 0`) decouples sender and receiver up to `n` items: a send only blocks once the buffer is full, and a receive only blocks once the buffer is empty. This is closer to a bounded queue than a handoff, and it's the right tool when you want to smooth out bursts of work without forcing the producer to wait on a consumer that's momentarily behind — but be precise about what it buys you: it does *not* give you the "receiver has definitely processed this" guarantee unbuffered channels do, only "this is sitting in the queue, someone will get to it."

```go
// unbuffered — the send genuinely waits for a receiver
done := make(chan struct{})
go func() {
    doWork()
    done <- struct{}{}   // this send blocks until main() below receives
}()
<-done  // guarantees doWork() has fully returned before we proceed

// buffered — sends up to 3 don't block even with no receiver yet
results := make(chan int, 3)
results <- 1
results <- 2
results <- 3 // still doesn't block — buffer isn't full
```

## Directional channel types: compile-time API contracts

A function parameter can restrict a channel to send-only or receive-only, and the compiler enforces it:

```go
func producer(out chan<- int) { // out: can only send
    for i := 0; i < 5; i++ {
        out <- i
    }
    close(out)
}

func consumer(in <-chan int) { // in: can only receive
    for v := range in {
        fmt.Println(v)
    }
}
```

`chan<- int` (send-only) and `<-int` — written `<-chan int` (receive-only) — are ordinary bidirectional `chan int` values narrowed at the call site; a bidirectional channel converts implicitly to either directional form, but not back. This is documentation the compiler enforces rather than a comment that can drift: reading `producer`'s signature tells you, with certainty, that it will never try to read from `out` — no need to read the function body to know that.

## select: waiting on more than one channel at once

`select` is to channels what `switch` is to values — except every case is a channel operation, and `select` blocks until at least one of them is ready to proceed, then runs that one case:

```go
select {
case v := <-ch1:
    fmt.Println("from ch1:", v)
case v := <-ch2:
    fmt.Println("from ch2:", v)
case ch3 <- 99:
    fmt.Println("sent to ch3")
default:
    fmt.Println("nothing ready — didn't block at all")
}
```

If **multiple** cases are ready simultaneously, `select` picks one **uniformly at random** — a deliberate design choice that prevents a program from accidentally depending on case-order priority (and prevents one channel from starving another, the way "always check the first case first" would under sustained contention on both). A `default` case makes the whole `select` non-blocking: if no other case is immediately ready, `default` runs instead of waiting — the standard way to "try to send/receive, but don't wait if you can't."

## The nil-channel trick

Recall that a receive or send on a nil channel blocks forever. That sounds purely bad — until you put it inside a `select`, where a case that can never fire is exactly a case you want to **disable**:

```go
func merge(a, b <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for a != nil || b != nil {
            select {
            case v, ok := <-a:
                if !ok {
                    a = nil // disable this case for future loop iterations
                    continue
                }
                out <- v
            case v, ok := <-b:
                if !ok {
                    b = nil // disable this case
                    continue
                }
                out <- v
            }
        }
    }()
    return out
}
```

Once channel `a` closes, setting the local variable `a` to `nil` makes that `select` case permanently unable to fire (a nil channel never becomes ready), effectively removing it from consideration without an `if`-laden mess of conditionally-included cases — `select` just never picks a case reading from a nil channel again. This exact pattern is the seed of Chapter 14's fan-in.

## Closing: the sender's job, and what happens after

`close(ch)` signals "no more values are coming." Three rules govern it precisely, and getting any one backward is a runtime panic: **only the sender should close a channel** (a receiver has no way to know if another receiver or the sender itself will send again, so it can never safely decide "we're done"); **sending on a closed channel panics**; **closing an already-closed channel panics**. Receiving from a closed channel never blocks and never panics — it returns immediately, giving you the channel's zero value and `ok == false` once every buffered value has already been drained:

```go
ch := make(chan int, 2)
ch <- 1
ch <- 2
close(ch)

fmt.Println(<-ch) // 1, true (buffered value, drained first)
fmt.Println(<-ch) // 2, true
v, ok := <-ch
fmt.Println(v, ok) // 0, false — channel closed and empty
```

`range` over a channel is built on exactly this: `for v := range ch` receives repeatedly and exits automatically the moment the channel is closed *and* drained — no explicit `ok` check needed in the common case of "consume everything until the producer says it's done."

## Two jobs, one primitive: data versus signal

Channels do two genuinely different jobs, and idiomatic Go keeps them visually distinct. When you're passing **data**, the channel's element type carries meaning (`chan int`, `chan Result`). When you're purely **signaling** — "this happened," with no payload — the idiom is `chan struct{}`, because `struct{}` is the zero-size type: it costs nothing to allocate and its only useful property is existing (or, via `close`, ceasing to block forever). `close()` on a signal channel is itself a broadcast: every goroutine currently blocked on a receive from that channel, and every future receive, unblocks simultaneously and immediately — this is the standard way to tell an *unknown number* of goroutines "stop now," which a single send could never do (one send only wakes one receiver).

```go
stop := make(chan struct{})
for i := 0; i < 5; i++ {
    go func(id int) {
        <-stop // every one of these five goroutines wakes up together
        fmt.Println(id, "shutting down")
    }(i)
}
close(stop) // one call, five goroutines unblocked
```

*Connect the dot:* this broadcast-via-close pattern is exactly what `context.Context`'s cancellation is built from internally (Chapter 25 uses `ctx.Done()`, a receive-only channel that closes when the context is canceled) — once you've seen it here, the standard library's implementation stops looking like magic.

You now have both of Go's core concurrency primitives — goroutines that run, channels that let them talk. Before building real patterns on top of them, Chapter 12 has to establish the rule that makes any of this trustworthy under concurrent access at all: the Go memory model, and precisely what a data race is.
