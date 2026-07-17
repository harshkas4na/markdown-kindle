# Building a Production REST API

**Fast overview:** this chapter assembles Chapters 24 and 25 into one coherent service — the shape a real, small Go API actually takes before it grows large enough to need Chapter 29's full project-layout treatment. Four things separate a demo from something you'd put a pager rotation behind: request validation that fails predictably, structured logging you can actually query, graceful shutdown that doesn't drop in-flight work, and health endpoints your deployment platform can trust. We build all four.

## A minimal shape for the project

Full project-structure treatment is Chapter 29's job; here's just enough to place the code that follows:

```
cmd/api/main.go        — entrypoint: wiring, not logic
internal/http/         — handlers, middleware, routing
internal/store/        — data access (Chapter 27)
```

*Connect the dot:* `internal/` is doing real work here, not just convention — Chapter 9 established that the compiler enforces its boundary, and Chapter 29 explains why application code defaults to living there. `main.go` itself should stay small: it reads configuration, constructs dependencies, and calls `ListenAndServe`. Business logic that lives in `main.go` is business logic nobody can unit test without spinning up a whole process.

## Request validation that fails predictably

Decoding untrusted JSON is two steps, not one: parse it, then validate it. Skipping the second step is how a missing field becomes a nil-pointer panic three functions later instead of a clean `400` at the edge.

```go
type CreatePostRequest struct {
    Title string `json:"title"`
    Body  string `json:"body"`
}

func createPost(w http.ResponseWriter, r *http.Request) {
    var req CreatePostRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeError(w, http.StatusBadRequest, "invalid JSON body")
        return
    }
    if req.Title == "" {
        writeError(w, http.StatusBadRequest, "title is required")
        return
    }
    if len(req.Body) > 10_000 {
        writeError(w, http.StatusBadRequest, "body exceeds 10000 characters")
        return
    }
    // ... persist req
}

func writeError(w http.ResponseWriter, status int, msg string) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(map[string]string{"error": msg})
}
```

For anything beyond a handful of fields, hand-written `if` chains get unwieldy fast, and most real services reach for `go-playground/validator`, which drives validation off struct tags (`validate:"required,max=10000"`) instead. Either way, the principle is the same one Chapter 19 argued for error design in general, applied here to HTTP specifically: *the caller — here, a client application — needs a machine-parseable, specific reason a request failed*, not a generic `500` that forces someone to read server logs to find out what they did wrong. A JSON error body with a clear `error` field and the right status code (`400` for a malformed request, `404` for a missing resource, `409` for a conflict, `422` for a semantically invalid but well-formed request) is the HTTP-layer expression of "design errors for the caller."

## Structured logging with log/slog

Before Go 1.21, every team either wrote log lines by hand with `fmt.Sprintf` or picked one of several competing third-party structured-logging libraries, and no two services in the same company necessarily agreed. `log/slog`, added to the standard library in Go 1.21, ended that fragmentation: it logs structured key-value attributes instead of pre-formatted strings, at defined levels (`Debug`, `Info`, `Warn`, `Error`), through a pluggable `Handler` that decides the actual output format (text for local development, JSON for production log aggregation).

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

logger.Info("request handled",
    "method", r.Method,
    "path", r.URL.Path,
    "status", status,
    "duration_ms", time.Since(start).Milliseconds(),
    "request_id", RequestIDFrom(r.Context()),
)
```

That produces one JSON object per line — trivially parseable by any log aggregator, and trivially greppable by `request_id` to reconstruct everything one request did across every layer it touched. *Connect the dot:* the `request_id` here is exactly the value Chapter 25's `RequestID` middleware attached to the context; this is the concrete payoff of that plumbing, and Chapter 30 extends the same pattern to metrics and distributed tracing.

## Graceful shutdown

A process that just exits the moment it receives `SIGTERM` drops every in-flight request mid-response — and in any container orchestration platform (Kubernetes chief among them, Chapter 34), `SIGTERM` is exactly what a rolling deploy or a scale-down sends, routinely, as normal operation, not as an emergency. The fix is to stop *accepting new* connections immediately but give in-flight ones a bounded window to finish:

```go
func main() {
    mux := buildRoutes()
    srv := &http.Server{Addr: ":8080", Handler: mux}

    go func() {
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("server error: %v", err)
        }
    }()

    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()
    <-ctx.Done()

    shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    if err := srv.Shutdown(shutdownCtx); err != nil {
        log.Printf("forced shutdown: %v", err)
    }
}
```

`signal.NotifyContext` returns a context that's cancelled the moment the process receives `SIGINT` or `SIGTERM`, so `<-ctx.Done()` blocks the main goroutine until a shutdown signal arrives while `ListenAndServe` runs the actual server on a separate goroutine. `srv.Shutdown(shutdownCtx)` then stops the listener (no new connections accepted), waits for active requests to complete, and returns early with an error only if `shutdownCtx`'s deadline passes first — at which point you've done everything reasonable and it's fine to let the orchestrator's harder `SIGKILL` (sent automatically some seconds after `SIGTERM` if the process hasn't exited) finish the job.

## Health endpoints: liveness vs readiness

Two conceptually different questions, both commonly exposed as separate endpoints:

| Endpoint | Question it answers | Typical failure response |
|---|---|---|
| `/healthz` (liveness) | Is the process still running correctly, or should it be killed and restarted? | Deadlocked, unrecoverable internal state |
| `/readyz` (readiness) | Can this instance currently serve traffic? | Database unreachable, still warming up caches |

A liveness check should be nearly free — it exists to catch a process that's hung, not to catch a slow dependency — while a readiness check is allowed to actually ping the database or other critical dependencies, because its whole purpose is telling a load balancer "don't route to me right now." Conflating the two is a common mistake: a readiness-style dependency check wired to the *liveness* endpoint will cause an orchestrator to kill and restart a perfectly healthy process just because its database had a brief blip — restarting the process fixes nothing and makes the outage worse. Chapter 34 picks this distinction back up in the concrete context of Kubernetes probes, which consume exactly these two endpoints by name.

## What's next

The service now handles requests correctly, logs them usefully, and shuts down without dropping work — but it has nowhere real to put data yet. Chapter 27 is `database/sql`: connection pooling, the scan-and-check idioms that prevent silent data loss, and the ORM-versus-hand-written-SQL debate this ecosystem never quite settles.
