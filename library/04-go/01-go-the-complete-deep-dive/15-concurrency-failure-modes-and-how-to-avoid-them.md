# Concurrency Failure Modes and How to Avoid Them

**Fast overview:** Chapters 10–14 built the toolbox and the shapes. This chapter is the field guide to how they break in practice — deadlock, goroutine leaks, and livelock — with a concrete example of each and the specific habit that prevents it. Of the three, goroutine leaks are by far the most common bug in real Go services, precisely because they're the quiet failure: nothing crashes, nothing errors, memory just climbs until someone notices.

## Deadlock: everyone waiting, nobody moving

A **deadlock** is a set of goroutines each waiting on something only another goroutine in the same stuck set can provide — a channel receive with no corresponding send, two mutexes locked in opposite orders by two different goroutines, a `WaitGroup.Wait()` for a `Done()` that will never come.

```go
func main() {
    ch := make(chan int) // unbuffered
    ch <- 1               // nobody is receiving — blocks forever
    fmt.Println(<-ch)
}
```

Go's runtime has one genuinely useful safety net here: if it detects that **every single goroutine in the process** is asleep waiting on a channel, mutex, or similar — literally nothing left that could ever wake anything else up — it crashes the program immediately with `fatal error: all goroutines are asleep - deadlock!` and a full stack dump of every blocked goroutine. The example above triggers exactly that. This is a real, useful diagnostic, but its coverage is narrower than it sounds: the runtime can only detect *global* deadlock. If even one goroutine is still doing something — sleeping on a timer, blocked on network I/O, spinning in a loop — the runtime has no way to know the *other* nine goroutines are permanently stuck, because from its point of view the process isn't fully asleep. A partial deadlock, where a handful of goroutines wedge each other while the rest of the program keeps serving other requests just fine, produces no crash, no log line, nothing — just a slowly growing pile of stuck goroutines that a load balancer eventually notices as rising latency.

The classic two-mutex version is worth internalizing because it's subtle enough to survive code review:

```go
// goroutine A                    // goroutine B
mu1.Lock()                        mu2.Lock()
mu2.Lock()  // waits for B        mu1.Lock()  // waits for A
```

Each goroutine holds the lock the other one needs next. Neither will ever release. The fix is boring and absolute: **always acquire multiple locks in the same, globally consistent order**, everywhere in the codebase — usually enforced by convention (document the order) or by collapsing to a single lock protecting both pieces of state, which is often the simpler fix anyway.

## Goroutine leaks: the quiet one

A **goroutine leak** is a goroutine blocked forever on a channel operation that will never be serviced, because whoever was supposed to send or receive on the other end has already given up and moved on. Unlike deadlock, this doesn't stop the program — the rest of the system keeps running, request after request, each one potentially leaving one more goroutine stranded, until memory and scheduler overhead eventually degrade the whole service. It is, empirically, the single most common concurrency bug shipped to production Go services.

Here's the shape almost every real leak takes:

```go
// LEAKS: if the caller times out and returns before the goroutine
// finishes, the goroutine blocks forever trying to send on `out` —
// nobody is left to receive.
func doWorkWithTimeout(ctx context.Context) (int, error) {
    out := make(chan int) // unbuffered

    go func() {
        result := slowComputation()
        out <- result // blocks forever if nobody's listening anymore
    }()

    select {
    case res := <-out:
        return res, nil
    case <-ctx.Done():
        return 0, ctx.Err() // we leave — the goroutine above is now stranded
    }
}
```

The moment `ctx.Done()` fires first, `doWorkWithTimeout` returns — and the spawned goroutine, still running `slowComputation()`, eventually tries to send on `out` to a caller that no longer exists. Nothing will ever receive from `out` again. That goroutine is now leaked, permanently, holding its stack and anything it closed over until the process itself exits.

Two standard fixes, and the choice between them depends on whether the leaked goroutine can be told to stop early:

```go
// Fix 1: buffer the channel so the send never blocks, even if
// nobody ever receives. The goroutine still runs to completion, but
// it isn't stuck — it exits normally once the send succeeds.
out := make(chan int, 1)

// Fix 2: give the goroutine itself a way to notice ctx is done and
// bail out early, instead of only the caller watching for it.
func doWorkWithTimeout(ctx context.Context) (int, error) {
    out := make(chan int, 1)

    go func() {
        result := slowComputation()
        select {
        case out <- result:
        case <-ctx.Done():
        }
    }()

    select {
    case res := <-out:
        return res, nil
    case <-ctx.Done():
        return 0, ctx.Err()
    }
}
```

Fix 2 is the more complete answer whenever `slowComputation` itself can be interrupted (it should also take `ctx` and check it internally) — the goroutine stops doing wasted work the instant the caller stops caring, rather than running to completion for no one. *Connect the dot:* this is precisely why Chapter 14 insisted `context.Context` be threaded through every function that blocks or does I/O — a goroutine with no way to observe "the caller left" has no way to leak-proof itself, no matter how carefully the channel around it is sized.

## Livelock: busy, but going nowhere

**Livelock** is rarer than the other two but worth recognizing: goroutines that are actively running — burning CPU, making function calls, definitely *not* asleep — while making no actual forward progress, because they keep reacting to each other in a way that undoes their own progress. The textbook case is two goroutines that both back off and retry whenever they detect contention, timed such that they perpetually retry into each other's retry window — each one polite enough to yield, and each one yielding at exactly the moment that guarantees another collision. Unlike deadlock, the runtime's "all goroutines asleep" detector never fires, because nothing is asleep; unlike a leak, no goroutine is permanently stuck on one blocking call — the symptom instead is CPU pinned near 100% with throughput near zero. The standard mitigation is the same one distributed systems use for the identical problem at a larger scale: add randomized jitter to any retry/backoff logic, so competing goroutines stop retrying in lockstep.

## How real teams actually catch these

None of the three failure modes above reliably announces itself with an error message, which is why production Go teams build habits around catching them before they ship, not after:

- **`-race` in CI, on every commit, not just locally.** Chapter 12 covered the mechanics; the operational point is that a race caught in a PR costs minutes, and the same race caught in production costs an incident. Teams that skip this in CI find these bugs the hard way, later, and usually more than once.
- **Thread `context.Context` through everything that can block.** This single discipline is the actual fix underneath most goroutine leaks — a goroutine that can observe "the caller gave up" can always bail out cleanly; a goroutine that can't, structurally can't leak-proof itself no matter how careful the surrounding code is.
- **Watch the goroutine count in production.** `runtime.NumGoroutine()` as a metric, or `pprof`'s goroutine profile (Chapter 31 covers `pprof` properly), turns a leak from an invisible slow bleed into a visible, alertable trend line — a service whose goroutine count only ever grows, request after request, never returning to baseline, is leaking somewhere, and the profile shows exactly which stack trace is accumulating.
- **A code-review habit, not a tool:** for every `go func() { ... }()` in a diff, the reviewer's reflex should be "how does this stop?" — can it always finish on its own, is it selecting on a cancellable context, is its target channel guaranteed to have a receiver for the goroutine's entire lifetime? A goroutine nobody can answer that question about, in one sentence, is a goroutine that's likely to leak the first time some upstream caller behaves unexpectedly.

Part 2 of this book closes here, on a deliberately unglamorous note: the primitives in Chapters 10–14 are genuinely elegant, and the bugs in this chapter are genuinely mundane — a channel with no receiver, two locks taken in the wrong order. That's the honest shape of concurrent Go in production: not exotic race conditions requiring a PhD to spot, but the same three failure modes, recurring, caught by the same small set of habits every time.

Next: Part 3 — error handling, and the design argument for why Go rejected exceptions in favor of an explicit, if occasionally repetitive, value you check at every call site.
