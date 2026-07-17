# The sync Package Deep Dive

**Fast overview:** channels (Chapter 11) are Go's headline concurrency tool, but they're not always the right one. Rob Pike's own summary of the tradeoff is the chapter's thesis: *use channels when goroutines need to hand off ownership of data or orchestrate a sequence of events; use `sync` and plain shared memory when goroutines just need to protect a piece of state they all touch.* A cache with a million reads and a thousand writes a second, guarded by a channel, means funneling every read through a goroutine that owns the map — needless indirection when a mutex says the same thing in one line. This chapter is the `sync` package: `Mutex`, `RWMutex`, `WaitGroup`, `Once`, `Cond`, `sync/atomic`, and `sync.Map` — with Chapter 12's happens-before table as the lens for understanding what each one actually guarantees.

## sync.Mutex: mutual exclusion, and the trap that isn't obvious

A `sync.Mutex` has two methods, `Lock` and `Unlock`, and one job: only one goroutine may hold it at a time. Everyone else calling `Lock` blocks until it's released.

```go
type Counter struct {
    mu sync.Mutex
    n  int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.n++
}
```

*Connect the dot:* Chapter 12's table said it precisely — `Unlock` call *n* happens-before `Lock` call *n*+1 succeeds on the same mutex. That's the entire correctness argument for this pattern: every goroutine's increment is ordered relative to every other's, so there's no data race on `c.n`, full stop.

The trap, specifically for anyone arriving from Java (`synchronized`, reentrant by default) or Python (`RLock`): **Go's `sync.Mutex` is not reentrant.** If a goroutine that already holds the lock calls `Lock()` again — even indirectly, through a second method on the same receiver — it deadlocks against itself, permanently, with no error message beyond a stack dump if the whole program deadlocks. There is no built-in recursive mutex in the standard library, on purpose: the Go team's position is that needing one is usually a sign the locking boundary is drawn in the wrong place, and the fix is almost always to split a public, locking method from a private, lock-free one that the public method calls internally after already holding the lock.

The `mu.Lock(); defer mu.Unlock()` idiom is the default for a reason beyond taste: `defer` (fully covered in Chapter 18) guarantees the unlock runs even if the function panics or returns early from one of several branches, which is exactly the situation where a hand-written `mu.Unlock()` at the bottom of the function gets skipped and the whole program silently wedges. The tiny overhead of `defer` is judged worth it for that guarantee everywhere except the very hottest of hot paths.

## sync.RWMutex: many readers, or one writer

A plain `Mutex` serializes everyone, even goroutines that only want to *read*. `sync.RWMutex` splits locking into two modes: `RLock`/`RUnlock` for readers (any number can hold a read lock simultaneously) and `Lock`/`Unlock` for writers (exclusive — blocks out both readers and other writers).

```go
type Cache struct {
    mu   sync.RWMutex
    data map[string]string
}

func (c *Cache) Get(key string) (string, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    v, ok := c.data[key]
    return v, ok
}

func (c *Cache) Set(key, value string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.data[key] = value
}
```

This is a clear win specifically when reads dominate writes by a wide margin — a config cache refreshed once a minute and read on every request is the textbook case. It is *not* a free upgrade: `RWMutex` has more internal bookkeeping than `Mutex`, so under heavy write contention, or when reads and writes are roughly balanced, a plain `Mutex` is often both simpler and faster. Benchmark before reaching for `RWMutex` reflexively; Chapter 21's benchmarking tools are exactly how you'd settle that question for your specific workload.

## sync.WaitGroup: waiting for a batch of goroutines to finish

`WaitGroup` has three methods — `Add(n)` increments an internal counter, `Done()` decrements it (equivalent to `Add(-1)`), and `Wait()` blocks until the counter hits zero.

```go
var wg sync.WaitGroup
results := make([]int, len(urls))

for i, url := range urls {
    wg.Add(1)
    go func(i int, url string) {
        defer wg.Done()
        results[i] = fetch(url)
    }(i, url)
}

wg.Wait()
```

The bug that catches nearly everyone once: calling `wg.Add(1)` *inside* the goroutine instead of before the `go` statement that starts it.

```go
// WRONG — a race on the WaitGroup itself
for _, url := range urls {
    go func(url string) {
        wg.Add(1)   // too late: Wait() may already be running
        defer wg.Done()
        fetch(url)
    }(url)
}
wg.Wait()
```

If the main goroutine reaches `Wait()` before any spawned goroutine has called `Add(1)`, the counter can still read zero and `Wait()` returns immediately — the program proceeds as if all the work finished when some or all of it hasn't even started. The fix is the ordering in the first example: `Add` happens in the loop, synchronously, before `go` hands off — guaranteeing the counter reflects the true number of outstanding goroutines *before* `Wait()` has any chance to observe it.

## sync.Once: exactly-once, safely, under concurrency

`Once.Do(f)` guarantees `f` runs exactly one time no matter how many goroutines call `Do` concurrently, and — per Chapter 12's table — that single execution happens-before *every* call to `Do` returns, including calls that arrived while `f` was still running and simply waited. This is the idiomatic lazy-singleton pattern:

```go
var (
    once     sync.Once
    instance *Client
)

func GetClient() *Client {
    once.Do(func() {
        instance = &Client{ /* expensive setup */ }
    })
    return instance
}
```

Every caller of `GetClient`, from any goroutine, is guaranteed to see a fully-initialized `instance` — not a partially-constructed one — because of that happens-before guarantee, not because of luck.

## sync.Cond: waiting for an arbitrary condition

`sync.Cond` is the primitive underneath the other three — a condition variable, for the shape of problem where a goroutine needs to block until some arbitrary predicate over shared state becomes true, not just until a lock is free or a counter hits zero. It's rarer in application code (most everyday cases are better served by a channel or a `WaitGroup`) but shows up in lower-level infrastructure, like implementing a bounded queue where producers block on "not full" and consumers block on "not empty":

```go
c := sync.NewCond(&sync.Mutex{})
ready := false

// waiter
c.L.Lock()
for !ready {
    c.Wait() // atomically unlocks, sleeps, and relocks on wake
}
c.L.Unlock()

// signaler
c.L.Lock()
ready = true
c.L.Unlock()
c.Signal() // or c.Broadcast() to wake every waiter, not just one
```

The `for !ready` loop, not an `if`, is the detail to internalize: `Wait` can return without the condition actually being true (a *spurious wakeup*, or simply because another waiter got there first), so the condition must always be re-checked after waking, never assumed.

## sync/atomic: lock-free operations on single values

For a single counter or flag touched extremely often, a full mutex can be more machinery than necessary. `sync/atomic` provides CPU-level atomic read-modify-write operations. Since Go 1.19, the package exposes typed wrappers — `atomic.Int64`, `atomic.Uint32`, `atomic.Bool`, `atomic.Pointer[T]`, and friends — which are now strongly preferred over the older function-based API (`atomic.AddInt64(&n, 1)` operating on a raw `int64`), because the typed versions make it a compile error to accidentally touch the underlying value non-atomically:

```go
var requests atomic.Int64

func handle() {
    requests.Add(1)
    // ...
}

func Stats() int64 {
    return requests.Load()
}
```

Per Chapter 12's table, atomic operations behave as if all atomics in the program execute in one global sequentially-consistent order — a real, load-bearing guarantee, not just "fast and probably fine." Reach for `atomic` for single-value counters and flags; reach for a `Mutex` the moment you're protecting more than one related field, because atomics give you no way to update two fields together consistently.

## sync.Map: a specialized tool, not a default upgrade

`sync.Map` is a concurrent-safe map with `Load`, `Store`, `Delete`, and `Range` methods — and it is *not* a general replacement for `map[K]V` plus a `Mutex`. The standard library's own documentation is explicit that it's optimized for two specific access patterns: either a cache where a key is written once and read many times by many goroutines ("write-once, read-many"), or workloads where disjoint sets of goroutines operate on disjoint sets of keys, so lock contention on a single mutex would otherwise be the bottleneck. For the common case — a moderately-contended map with a normal read/write mix — a plain `map` guarded by a `sync.RWMutex` is usually simpler to reason about and just as fast, sometimes faster, because `sync.Map`'s internal design (two internal maps, atomic pointer swaps, amortized cleanup) trades away performance on patterns it isn't specialized for. Benchmark, don't assume.

## Choosing between sync and channels, concretely

A rule of thumb that holds up in real codebases: if you're protecting a piece of *state* that multiple goroutines need to read and mutate in place — a cache, a counter, a connection pool's free list — reach for `sync`. If you're *transferring ownership* of a value from one goroutine to another, or *orchestrating* a sequence of stages, reach for a channel. The two aren't in tension; production Go code uses both, often in the same file — a worker pool (Chapter 14) typically uses a channel to distribute jobs and a `sync.WaitGroup` to know when they're all done.

Next: Chapter 14 puts these primitives and channels together into the concurrency patterns you'll actually reuse — worker pools, pipelines, fan-out/fan-in, and the `context` package that ties cancellation through all of them.
