# Performance: Profiling, Benchmarking, and the GC

**Fast overview:** Go performance work has a shape, and it's almost always the same shape: measure first, find where the time or memory actually goes with `pprof`, fix the highest-leverage thing (which is very often "stop allocating"), and re-measure with a benchmark that can't lie to you. This chapter covers the tools in that order — profiling, benchmarking methodology, escape analysis, and just enough of the garbage collector's internals to know when it's genuinely your bottleneck versus a convenient scapegoat for a bug you haven't found yet.

## Profiling: find out where the time actually goes

Guessing where a Go program spends its time is a bad habit the standard library actively discourages by making the correct habit almost as easy. `runtime/pprof` lets any program write CPU and memory profiles to a file; `net/http/pprof` goes further and, for a running server, exposes them live over HTTP — import it for its side effect and a handful of `/debug/pprof/*` endpoints appear on your mux for free:

```go
import (
    "net/http"
    _ "net/http/pprof" // registers /debug/pprof/* on http.DefaultServeMux
)

func main() {
    go func() { http.ListenAndServe("localhost:6060", nil) }()
    // ... the rest of your server
}
```

With that running, `go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30` captures 30 seconds of CPU samples from a live process and drops you into an interactive shell (`top` for the hottest functions, `list funcName` for line-by-line cost, `web`/`png` for a call graph). For a one-off CLI tool or a test, `runtime/pprof.StartCPUProfile`/`StopCPUProfile` does the same thing without a server. Memory profiles work the same way but sample allocations rather than CPU time, and `pprof` gives you a choice of view: `-inuse_space` (what's live on the heap right now — good for finding leaks) versus `-alloc_objects` (everything ever allocated, including garbage already collected — good for finding a hot loop that's allocating too much per iteration, even if none of it lingers).

The output that matters most day to day is the flat/cumulative `top` table and the flame graph it implies: a wide bar means a function (or everything it calls) is eating a large fraction of the profiled time; a tall stack means deep call chains. You don't need to become a `pprof` expert to get 90% of the value — `top10` and `list` on whatever shows up at the top of it will point you at the actual line almost every time.

## Benchmarks that don't lie to you

*Connect the dot:* Chapter 21 introduced `testing.B` and the `func BenchmarkX(b *testing.B)` shape. The deeper truth is that a single run of `go test -bench=.` is noisy — CPU frequency scaling, other processes, GC timing all jitter the number by a meaningful percentage, and comparing one before-run to one after-run is a common way to convince yourself an optimization worked when it didn't (or vice versa). The fix is statistical, not clever: run each version multiple times with `-count=10`, and compare the two sets with `benchstat` (`go install golang.org/x/perf/cmd/benchstat@latest`), which reports whether the difference is actually significant or just noise:

```bash
go test -bench=Encode -count=10 ./... > old.txt
# make your change
go test -bench=Encode -count=10 ./... > new.txt
benchstat old.txt new.txt
```

Two mistakes wreck benchmark numbers even when the methodology above is followed. First, letting the compiler notice your benchmark's result is never used and optimizing the whole loop away — the fix is assigning to a package-level variable so the result has an observable effect the compiler can't discard:

```go
var sink int

func BenchmarkParse(b *testing.B) {
    for i := 0; i < b.N; i++ {
        sink = parse(input)
    }
}
```

Second, measuring setup cost inside the loop — `b.ResetTimer()` after any expensive one-time setup, or `b.StopTimer()`/`b.StartTimer()` bracketing per-iteration setup you don't want counted, keeps the number honest.

## Escape analysis, properly this time

*Connect the dot:* Chapter 5 mentioned in passing that the compiler decides whether a value lives on the stack or the heap. Here's the mechanism and why it's the single highest-leverage thing to understand for Go performance.

`go build -gcflags="-m"` (repeat `-m -m` for more detail) prints the compiler's escape decisions for every value in a file:

```bash
go build -gcflags="-m" ./...
# ./main.go:12:9: &user escapes to heap
# ./main.go:20:6: n does not escape
```

A value **escapes to the heap** when the compiler can't prove its lifetime is bounded by the function that created it — the classic triggers are returning a pointer to a local variable, storing a value in an interface (the interface's internal representation needs a stable address for anything larger than a word), sending a value on a channel, or passing it to a function the compiler can't fully see through (an interface method call, or anything across a package boundary the inliner gives up on). A stack-allocated value costs nothing beyond the function call itself — it's reclaimed automatically when the frame pops, no GC involved. A heap-allocated value costs an actual allocation *and* becomes the garbage collector's problem to eventually reclaim.

This is why "reduce allocations" is the refrain you'll hear from every experienced Go engineer doing performance work, more than "reduce CPU work": a hot path doing one unnecessary heap allocation per call, called a million times a second, is doing a million unnecessary allocations a second, and every one of those is both a direct cost (the allocator's work) and an indirect one (more garbage for the next section's collector to walk). Common, fixable offenders: building a `[]byte` from a `string` (and back) in a loop instead of once outside it, `fmt.Sprintf` in a hot path instead of `strconv` or a preallocated `bytes.Buffer`, and passing large structs by value into an interface parameter where a pointer would do.

## The garbage collector: concurrent, tri-color, and usually not your problem

Go's GC is a **concurrent, tri-color mark-and-sweep** collector: it runs its mark phase *alongside* your goroutines rather than freezing the whole program, using a write barrier to stay correct while your code keeps mutating the heap underneath it. "Tri-color" describes the bookkeeping — every object is white (not yet visited), grey (visited, but its children not yet scanned), or black (visited and fully scanned); the collector repeatedly promotes grey objects to black until nothing grey remains, at which point everything still white is garbage. There are brief stop-the-world pauses (for setting up the mark phase and finishing it), but they're measured in microseconds, not milliseconds, on modern Go — this has been a headline design goal since the GC was substantially rewritten around Go 1.5–1.8, when pause times dropped from tens of milliseconds to sub-millisecond even on multi-gigabyte heaps.

Two environment variables are the actual tuning surface, and both are worth knowing exist even if you rarely touch them:

| Variable | What it controls | Default |
|---|---|---|
| `GOGC` | Target heap growth before triggering the next collection, as a percentage of live heap size after the last one | `100` (heap can double before the next GC) |
| `GOMEMLIMIT` | A soft cap (added in Go 1.19) on total memory the runtime will use, letting the GC collect *more aggressively* as it approaches the limit instead of the process OOMing | unset |

`GOMEMLIMIT` exists specifically because `GOGC` alone is a bad fit for containers: `GOGC=100` says "double the heap before collecting," which is fine on a machine with headroom but can OOM-kill a process running in a 512MB Kubernetes pod (*connect the dot:* Chapter 34) long before the collector would have chosen to run on its own. Setting `GOMEMLIMIT` close to (but a little under) the container's memory limit lets the runtime trade some CPU for staying inside its box.

The honest closing advice, and the one worth remembering over every flag above: measure before tuning. The GC is very rarely the actual bottleneck in a Go service that feels slow — an allocation-heavy hot path (fixable with the escape-analysis techniques above), a lock held too long (Chapter 13), or a synchronous call to a slow downstream dependency (no amount of `GOGC` tuning fixes that) is the far more common culprit, and `pprof`'s CPU and heap profiles will show you which one you actually have instead of leaving you guessing.

Next: none of this matters if you can't get the binary onto the machine that needs it. Chapter 32 is Go's other headline production property — shipping a single static binary anywhere, with nothing else to install.
