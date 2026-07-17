# Concurrency Patterns

**Fast overview:** goroutines, channels, and `sync` (Chapters 10–13) are the primitives; this chapter is the small set of shapes real Go codebases actually assemble them into, over and over. Worker pools bound how much concurrent work runs at once. Pipelines chain processing stages together. Fan-out/fan-in spreads work across goroutines and merges the results. And underneath every one of them, `context.Context` is the thread that carries "please stop now" through a whole tree of goroutines that may be many calls deep. Learn these five shapes and you can read the concurrent portions of almost any production Go service.

## Worker pools: bounding concurrency on purpose

The naive way to process 100,000 items concurrently is `go process(item)` in a loop — 100,000 goroutines, each cheap individually (Chapter 10: ~2KB of stack), but not free in aggregate, and worse, each one might open a database connection, a file handle, or an HTTP connection to a downstream service that has no idea 100,000 requests are about to hit it at once. A **worker pool** fixes this by fixing the number of goroutines and feeding them work through a shared channel:

```go
func worker(id int, jobs <-chan int, results chan<- int) {
    for j := range jobs {
        results <- j * j // pretend this is expensive
    }
}

func main() {
    const numWorkers = 8
    jobs := make(chan int, 100)
    results := make(chan int, 100)

    for w := 1; w <= numWorkers; w++ {
        go worker(w, jobs, results)
    }

    go func() {
        for j := 1; j <= 20; j++ {
            jobs <- j
        }
        close(jobs)
    }()

    for a := 1; a <= 20; a++ {
        fmt.Println(<-results)
    }
}
```

Exactly `numWorkers` goroutines exist for the lifetime of the pool, no matter how many jobs arrive. `range jobs` is the detail worth noticing: ranging over a channel receives values until the channel is `close`d, at which point every worker's loop exits cleanly and the goroutines terminate — no separate "stop" signal needed for this simple case. *Connect the dot:* Chapter 11 covered `close` and `range` on channels individually; this is the pattern they were built for.

## Pipelines: chaining stages through channels

A **pipeline** is a series of stages connected by channels, where each stage is a function taking an input channel (or none, for the source) and returning an output channel:

```go
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for _, n := range nums {
            out <- n
        }
    }()
    return out
}

func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            out <- n * n
        }
    }()
    return out
}

// usage: generate(1, 2, 3, 4) -> square -> consume
for v := range square(generate(1, 2, 3, 4)) {
    fmt.Println(v)
}
```

Each stage owns exactly one goroutine, closes its own output channel when its input is exhausted (which is what tells the *next* stage's `range` loop to finish), and the whole pipeline runs concurrently — stage two can be squaring the first number while stage one is still generating the third. The discipline that makes pipelines composable is: **a channel has exactly one owner, and only the owner closes it.** Closing a channel you don't own, or closing one twice, panics — this ownership rule is the pipeline pattern's actual contract, more than any type signature enforces it.

## Fan-out, fan-in: parallelizing one stage

Sometimes one stage of a pipeline is the bottleneck and you want several goroutines running it concurrently, then merging their output back into a single stream — **fan-out** (multiple goroutines reading the same input channel) and **fan-in** (multiple channels merged into one):

```go
func fanIn(cs ...<-chan int) <-chan int {
    out := make(chan int)
    var wg sync.WaitGroup
    wg.Add(len(cs))

    for _, c := range cs {
        go func(c <-chan int) {
            defer wg.Done()
            for v := range c {
                out <- v
            }
        }(c)
    }

    go func() {
        wg.Wait()
        close(out)
    }()

    return out
}

// fan-out: three workers all reading from the same `square` output
in := generate(1, 2, 3, 4, 5, 6)
c1, c2, c3 := square(in), square(in), square(in)
for v := range fanIn(c1, c2, c3) {
    fmt.Println(v)
}
```

*Connect the dot:* the `WaitGroup` closing `out` only after every merging goroutine has finished is exactly Chapter 13's pattern — and it's the reason `fanIn` is safe to close `out` at all: closing it any earlier, while a merging goroutine might still send, would panic on a send to a closed channel. Order of shutdown matters as much as order of startup in every one of these patterns.

## Rate limiting

Feeding downstream systems (a third-party API, a database) at an unbounded rate is how a fast worker pool becomes a self-inflicted denial-of-service. `time.Ticker` gives you a simple fixed-interval limiter:

```go
limiter := time.NewTicker(200 * time.Millisecond) // 5 req/sec
defer limiter.Stop()

for _, req := range requests {
    <-limiter.C
    go handle(req)
}
```

For anything beyond a flat rate — bursts up to a cap, then throttling — the standard extension is `golang.org/x/time/rate`, a token-bucket limiter maintained by the Go team but shipped outside the standard library proper (it lives under `golang.org/x/...`, the same home as several other broadly-used, slower-moving packages). `Limiter.Wait(ctx)` blocks until a token is available or the context is cancelled — which is the segue into this chapter's last and most important primitive.

## context.Context: cancellation and deadlines through a call tree

Every pattern above has an unanswered question: what stops it? If the consumer of a pipeline gives up early, or an HTTP request times out three layers into a worker pool, something needs to tell every goroutine involved to unwind — and Go's answer, standardized across the entire ecosystem, is `context.Context`.

```go
type Context interface {
    Done() <-chan struct{}
    Err() error
    Deadline() (deadline time.Time, ok bool)
    Value(key any) any
}
```

`Context` is an interface (Chapter 7), and it's built to be threaded, not stored: the near-universal convention is that `ctx` is the *first parameter* of any function that might block or do I/O, and it is never held inside a struct field for later use — a struct field can't express "this specific call's deadline," only a stale, ambiguous one. You create a root context with `context.Background()` (top of a real call tree — `main`, a server's request handler) or `context.TODO()` (a placeholder while a function is being refactored to accept one properly), and derive child contexts that carry a cancellation reason downward:

```go
ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
defer cancel() // always call cancel, even on the success path — releases resources

result, err := fetchWithContext(ctx, url)
```

```go
func fetchWithContext(ctx context.Context, url string) (*Result, error) {
    select {
    case res := <-doFetch(url):
        return res, nil
    case <-ctx.Done():
        return nil, ctx.Err() // context.DeadlineExceeded or context.Canceled
    }
}
```

`WithCancel` gives you a `cancel func()` you call explicitly; `WithTimeout`/`WithDeadline` cancel automatically once the clock runs out; `WithValue` attaches a request-scoped key-value pair (used sparingly, for things like a request ID or an auth token — never for optional parameters a function should just take explicitly). Crucially, cancellation *propagates down the whole derivation tree at once*: cancel a parent context, and `Done()` closes on every context derived from it, transitively, no matter how many layers of function calls separate them. Every goroutine that's `select`ing on `ctx.Done()` — inside a worker, inside a pipeline stage, inside a database call — wakes up and can unwind, cleanly, in one coordinated motion.

*Connect the dot forward, twice:* Chapter 25 shows that `net/http` gives every single incoming request its own `Context`, automatically cancelled the instant the client disconnects — meaning every pattern in this chapter, wired to that request's context, gets client-disconnect cancellation for free. And Chapter 26's graceful shutdown is this same mechanism run in reverse: cancelling a top-level context when the process receives `SIGTERM`, and trusting that every goroutine downstream, because it was built to respect `ctx.Done()`, unwinds instead of getting killed mid-work.

## The pattern behind the patterns

Every shape in this chapter answers the same two questions differently: *who owns this channel and decides when to close it*, and *how does a "please stop" signal reach every goroutine involved without anyone polling*. Worker pools answer the second question with a closed `jobs` channel; pipelines with cascading closes; fan-in with a `WaitGroup` gating the final close; and anything that needs to stop *early*, before its normal input is exhausted, answers it with `context.Context`. Once you can name which answer a piece of concurrent code is using, the code stops looking like clever plumbing and starts looking like one of five familiar shapes.

Next: what happens when one of these patterns is built slightly wrong — the deadlocks, goroutine leaks, and livelocks that are Go concurrency's actual failure modes in production, and the concrete habits that catch them before a pager does.
