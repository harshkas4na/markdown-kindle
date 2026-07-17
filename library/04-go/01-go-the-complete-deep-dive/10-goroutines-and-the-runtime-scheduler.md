# Goroutines and the Runtime Scheduler

**Fast overview:** this chapter opens Part 2 — concurrency, the feature that gets most people to try Go in the first place. A goroutine is a function running concurrently with every other goroutine in the program, started with the `go` keyword, and costing so little to create and hold that "a goroutine per incoming request" or "a goroutine per unit of work" is the default Go architecture, not an optimization you reach for later. This chapter is the machine underneath that sentence: how goroutines are scheduled onto real OS threads, why the scheduler can multiplex hundreds of thousands of them onto a handful of cores, and what changed in 2020 to close the one real gap in that story.

## Starting one, and what it actually costs

```go
func main() {
    go doWork("first")   // starts a goroutine, returns immediately
    go doWork("second")  // starts another, also returns immediately
    time.Sleep(time.Second) // crude, but keeps main alive to let them finish
}

func doWork(label string) {
    fmt.Println(label, "running")
}
```

`go f()` schedules `f` to run concurrently and returns control to the calling goroutine immediately — it does not wait, and it does not hand you anything back to observe when `f` finishes (that coordination problem is Chapter 11 and Chapter 13's `sync.WaitGroup`). `main()` itself runs as goroutine #1; when it returns, the program exits immediately, whether or not other goroutines are still running — there's no implicit "wait for everyone" at the end, which is exactly why the crude `time.Sleep` above is a bug waiting to happen in real code and never appears in it.

The reason "just start a goroutine for everything" is viable Go architecture, and would be reckless advice for OS threads, is the cost per unit. An OS thread typically reserves a fixed stack — often 1–8MB — allocated up front, because the OS can't predict how deep the thread's call stack will grow and has to commit to a size. A goroutine starts with a stack of roughly **2KB**, and that stack **grows and shrinks dynamically** as the call stack actually deepens and unwinds, managed entirely by the Go runtime rather than the OS. Ten thousand OS threads would exhaust gigabytes of memory before doing any real work; ten thousand goroutines cost a few tens of megabytes. This is the single fact that makes "goroutine per connection" a reasonable default for a server handling tens of thousands of concurrent clients — the architecture Chapter 24's `net/http` server relies on without saying so explicitly.

## The GMP model

The Go runtime doesn't hand goroutines to the OS scheduler one-to-one. It runs its own scheduler on top, multiplexing many goroutines onto far fewer OS threads, using three kinds of entities usually just called by their letters:

| Letter | Stands for | What it is |
|---|---|---|
| **G** | Goroutine | A single `go f()` call: a function, its stack, and its scheduling state |
| **M** | Machine | An actual OS thread — what the operating system schedules |
| **P** | Processor | A logical execution context; there are `GOMAXPROCS` of them, default = number of CPU cores |

A **P** is the key indirection: an M can only execute Go code while holding a P, and each P has its own **local run queue** of goroutines ready to run, plus access to a **global run queue** shared by all Ps. When a goroutine yields (blocks, calls `runtime.Gosched`, or hits a preemption point), the M running it pulls the next ready goroutine off its P's local queue — no OS involvement, no thread context switch, just the Go runtime picking the next G, which is roughly an order of magnitude cheaper than an OS-level context switch. If a P's local queue runs empty, it **work-steals**: it checks the global queue, and failing that, steals *half* of another P's local queue — this is what keeps a `GOMAXPROCS=8` program from stalling seven cores because one P happened to get eight goroutines queued onto it. `runtime.GOMAXPROCS(n)` reads or sets the number of Ps (and therefore the ceiling on how many goroutines can run truly *simultaneously*, as opposed to merely *concurrently*); `runtime.NumGoroutine()` reports the live goroutine count, a common health-check and leak-detection signal (Chapter 15).

## Cooperative, then preemptive: the 2020 turning point

For Go's first six years, the scheduler was fundamentally **cooperative**: a goroutine only yielded the P it was running on at specific points — a function call, a channel operation, a `select`, garbage-collection safepoints. This had one sharp edge: a **tight loop with no function calls and no channel operations** — a pure numeric computation, say — could run forever without ever hitting a yield point, starving every other goroutine assigned to that P, including the goroutine that runs the garbage collector's own coordination. Real production code hit this: a JSON-parsing loop or a hand-unrolled numeric kernel could stall an entire program.

**Go 1.14 (February 2020)** fixed this with **asynchronous preemption**: the runtime now uses OS signals (`SIGURG` on Unix) to interrupt a goroutine that has been running too long — around 10ms — and force a yield at essentially any point in its execution, not just at the old cooperative checkpoints. This closed the gap without changing anything about how you write goroutines; the mental model "the scheduler will give everyone a fair turn" only became fully true in 2020, and it's worth knowing the date because any Go concurrency advice written before it (some of which still circulates) may be more cautious about tight loops than modern Go actually requires.

## Blocking syscalls: the mechanic that makes I/O-bound servers scale

Not every block looks like a channel operation — a goroutine that calls `os.ReadFile` or does a blocking network read is asking the *operating system* to block it, and the Go scheduler has no visibility into or control over that. If the runtime did nothing special here, one goroutine stuck in a slow syscall would freeze its entire M — and since an M can't run Go code without a P, that P would sit idle even though other goroutines are ready to run on it.

The runtime's actual behavior: when a goroutine enters a blocking syscall, the runtime **detaches the P from that M** and hands the P to a different M (spinning one up if none is idle) so other goroutines keep making progress. When the syscall returns, the original goroutine tries to reacquire a P — grabbing an idle one if available, or going onto a queue to wait for one, occasionally causing the runtime to spin up yet another M. This is precisely the mechanic behind "goroutine per connection" scaling for I/O-bound work despite `GOMAXPROCS` capping how many goroutines run *CPU* work simultaneously: thousands of goroutines can be blocked in network reads at once, each one only briefly needing a real P when it has actual computation to do, and the P/M split absorbs the rest.

*Connect the dot:* this whole chapter is the machinery underneath two things you'll build later — Chapter 14's worker pools and pipelines, which are really just disciplined patterns for keeping a bounded number of goroutines fed with work instead of launching an unbounded number, and Chapter 24's HTTP server, which spins up a new goroutine per accepted connection and relies on exactly the blocking-syscall handoff described above to make that affordable at scale. And Chapter 15 is the other side of this coin: a goroutine that blocks *forever* — waiting on a channel nobody will ever write to, say — never returns its resources, and "hundreds of thousands of goroutines" stops being a strength and starts being a leak.

Goroutines run concurrently, but they don't yet talk to each other — a goroutine that computes a result has no way, so far, to hand it back. That's the channel's entire job, and it's the next chapter.
