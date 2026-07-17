# Configuration, Observability, and Twelve-Factor Go

**Fast overview:** a service that's correct in your terminal and opaque in production is only half built. This chapter covers how idiomatic Go services take configuration in (flags, environment variables, config files, and the layering between them) and how they report what they're doing once they're running unattended — structured logging, metrics, and tracing, the three pillars that turn "it's slow" into "it's slow because of this specific downstream call, in this specific request." We close with the handful of Heroku's twelve-factor principles that map onto Go specifically, rather than restating all twelve.

## Configuration: three sources, one clear precedence

Real Go services almost always draw configuration from three places, layered with a consistent precedence so there's never ambiguity about which value won: **flags** (via the standard library's `flag` package, or `pflag`/`cobra` for richer CLI parsing — Chapter 36 covers that ecosystem in depth) are best for values a human operator sets per-invocation, like `--port` during local development. **Environment variables** are the twelve-factor app's preferred mechanism for anything that varies by deploy environment — database URLs, feature flags, API keys — specifically because they never risk being committed to git the way a config file can, and because every deployment platform (containers, serverless, bare metal) supports setting them uniformly without the platform needing to know anything about your application's file format. **Config files** (YAML or TOML, parsed via a library) suit larger, structured settings that would be unwieldy as individual environment variables.

The common, robust pattern layers all three with an explicit precedence — flags override environment variables, which override a config file, which override hard-coded defaults — resolved once, at startup, into a single typed config struct:

```go
type Config struct {
    Port        int
    DatabaseURL string
    LogLevel    string
}

func Load() (Config, error) {
    cfg := Config{Port: 8080, LogLevel: "info"} // defaults

    if v := os.Getenv("DATABASE_URL"); v != "" {
        cfg.DatabaseURL = v
    }
    if v := os.Getenv("LOG_LEVEL"); v != "" {
        cfg.LogLevel = v
    }
    flag.IntVar(&cfg.Port, "port", cfg.Port, "server port")
    flag.Parse()

    if cfg.DatabaseURL == "" {
        return cfg, errors.New("DATABASE_URL is required")
    }
    return cfg, nil
}
```

The point of resolving everything into one struct at startup — rather than scattering `os.Getenv` calls throughout the codebase wherever a value happens to be needed — is the same point Chapter 19 made about error design: a caller (here, the rest of the program) should depend on one clear, validated contract, not reach out to the environment ad hoc from a dozen different places, most of which then have no good way to fail loudly if a required value is missing. `Load()` failing fast at startup with a clear error is dramatically better than a nil `DatabaseURL` surfacing as a mysterious connection failure three requests into the service's life.

## Structured logging, deeper

Chapter 26 introduced `log/slog`; the piece worth adding here is handlers and levels used deliberately rather than by habit. `slog.NewTextHandler` produces human-readable output, well suited to local development; `slog.NewJSONHandler` produces one JSON object per line, well suited to production, where a log aggregator (not a human's eyes) is the first consumer. Levels exist so that verbosity is a runtime knob, not a code change — `Debug` for detail you want during an incident but not during normal operation, `Info` for routine events worth recording, `Warn` for recoverable abnormal conditions, `Error` for failures that need attention — and `LOG_LEVEL` from the config above typically drives which of them actually get emitted.

*Connect the dot:* Chapter 25's request ID, attached to the context at the edge of every request, is what makes structured logging actually useful in production rather than merely tidy — every log line a request touches, however many layers deep, can carry that same `request_id` attribute, so a support ticket about one failed request becomes one `grep` instead of an archaeology project.

## Metrics: counting what's happening, cheaply

Logs answer "what happened in this one request." Metrics answer "what's the shape of everything happening, over time" — and they need to be cheap enough to record on every single request without becoming the bottleneck themselves. The standard library's `expvar` package offers a minimal built-in mechanism for exposing counters and gauges over HTTP, but the de facto standard in the Go ecosystem is Prometheus's `client_golang`, which provides three core instrument types: **counters** (monotonically increasing — total requests served, total errors), **gauges** (a value that goes up and down — current in-flight requests, current goroutine count), and **histograms** (a distribution — request latency, bucketed, so you can ask "what's the 99th-percentile response time" rather than only an average that hides outliers).

```go
var requestDuration = prometheus.NewHistogramVec(
    prometheus.HistogramOpts{Name: "http_request_duration_seconds"},
    []string{"method", "path", "status"},
)

func init() { prometheus.MustRegister(requestDuration) }
```

Wired into the logging middleware from Chapter 25, this instrument records one observation per request, and a `/metrics` endpoint (added to the same `ServeMux` from Chapter 24) exposes the accumulated data for a Prometheus server to scrape on its own schedule — the service itself never pushes anything, it just answers "what do your counters currently say" when asked, which is a deliberately simple, pull-based design that keeps the instrumented service's own code free of any knowledge of where metrics ultimately get stored.

## Tracing: following one request across service boundaries

A single incoming request in a system built from several services (Chapter 28's gRPC world) might fan out into calls to three other services, each of which calls a database. Logs and metrics, taken separately from each service, can't reconstruct that shape — tracing exists specifically to. OpenTelemetry's Go SDK is the current standard: a **span** represents one unit of work (handling this HTTP request, making this downstream call), spans nest to form a tree, and the whole tree together is a **trace** — one request's complete path through the system, with timing for every hop.

The mechanism that makes this possible across service boundaries is the same one Chapter 25 already taught for request IDs: trace context propagates through `context.Context`, exactly like cancellation and deadlines do. A span started in the incoming HTTP handler is attached to the request's context; when that handler calls another service (over gRPC or HTTP), the trace ID and span ID are serialized into outgoing headers, and the receiving service picks them back up into its own context, continuing the same trace rather than starting a new, disconnected one. *Connect the dot:* this is the deepest payoff of Chapter 14's original claim that `context.Context` is how Go threads cross-cutting concerns through a call tree — cancellation, deadlines, request-scoped values, and now a distributed trace, all riding the same mechanism.

## The twelve-factor principles that are actually Go-specific

Heroku's twelve-factor methodology predates Go's rise to prominence, but a handful of its factors line up unusually well with idioms this book has already taught, which is worth calling out explicitly rather than restating all twelve generically:

**Stateless processes.** A goroutine-per-request model (Chapter 10) has no natural place to accumulate process-local state across requests unless you deliberately build one — which makes horizontal scaling (running more identical instances behind a load balancer) the default, not an afterthought requiring a rewrite.

**Logs as event streams.** Twelve-factor's advice to write logs to `stdout` and let the execution environment handle routing and storage is exactly what `slog.NewJSONHandler(os.Stdout, nil)` already does by default — no log file management, no rotation logic, inside the application at all.

**Fast startup, graceful shutdown.** Chapter 26's `signal.NotifyContext`/`srv.Shutdown` pairing is the direct, concrete implementation of twelve-factor's "disposability" factor — a process that can be started or stopped on a moment's notice without dropping in-flight work, which is exactly what container orchestration platforms assume every process can do.

## What's next

The service is now observable and configurable. Chapter 31 turns to what happens when observability tells you something is slow: profiling, benchmarking, and just enough of the garbage collector's internals to know whether it's actually the bottleneck or an innocent bystander.
