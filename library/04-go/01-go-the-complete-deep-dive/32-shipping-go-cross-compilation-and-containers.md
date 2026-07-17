# Shipping Go: Cross-Compilation and Containers

**Fast overview:** `go build` produces one file. Not a bundle of an interpreter plus a lockfile plus a `node_modules` directory, not a JAR that still needs a JVM installed on the target — one self-contained, statically-linked executable that runs on the target machine with nothing else present. This chapter is about that fact and everything it makes possible: cross-compiling for any platform from any machine, building minimal container images around it, and embedding build metadata into the binary itself. It's also the hinge chapter of the book — everything here is the direct payoff of decisions made all the way back in Chapter 1, and it's the reason the next four chapters (Part 7) exist at all.

## The static binary

By default, `go build` links your program's Go code, the runtime, and the standard library it uses into a single executable. Add `CGO_ENABLED=0` and you also remove the one common source of a dynamic dependency — cgo, which lets Go code call C libraries and, when used, links against the target's libc — leaving a binary with *zero* runtime dependencies, not even a system C library:

```bash
CGO_ENABLED=0 go build -o myservice ./cmd/myservice
```

Compare this to the alternatives a team is usually choosing between: a Python service needs the right interpreter version and every package in `requirements.txt` present on the target, a Node service needs `node` and a populated `node_modules`, a Java service needs a matching JVM. Go needs the file. This is not a minor convenience — it's the property that made Go the default choice for infrastructure tooling that has to run reliably on machines nobody has carefully provisioned in advance, which is exactly the situation container orchestration, CLI tools, and edge agents are in.

## Cross-compilation: one laptop, every platform

Go's compiler and standard library are cross-compilation-aware by default, controlled by two environment variables: `GOOS` (target operating system) and `GOARCH` (target architecture). No separate toolchain download, no Docker-in-Docker cross-build rig — just set the variables and build:

```bash
GOOS=linux   GOARCH=amd64 go build -o myservice-linux-amd64   ./cmd/myservice
GOOS=linux   GOARCH=arm64 go build -o myservice-linux-arm64   ./cmd/myservice
GOOS=darwin  GOARCH=arm64 go build -o myservice-darwin-arm64  ./cmd/myservice
GOOS=windows GOARCH=amd64 go build -o myservice-windows.exe   ./cmd/myservice
```

`go tool dist list` prints every supported `GOOS`/`GOARCH` combination the installed toolchain knows about. The common real targets are `linux/amd64` and `linux/arm64` (the two you need for practically any container deployment across x86 and Graviton/Apple-Silicon-class ARM infrastructure), plus `darwin/amd64`/`darwin/arm64` and `windows/amd64` for tools distributed to developers directly. *Connect the dot:* Chapter 36's CLI tools lean on exactly this — a single CI job matrix-building five or six `GOOS`/`GOARCH` pairs and attaching each binary to a GitHub release is the entire distribution story for a huge share of the Go CLI ecosystem, no installer, no package-manager submission required (though many also publish to Homebrew/apt for convenience on top of the raw binaries).

## Multi-stage Docker builds

A Go binary's dependency-free nature makes it uniquely suited to the smallest possible container images. The standard pattern is a **multi-stage build**: a full `golang` image compiles the binary, then a second, minimal stage copies only the finished binary out — none of the Go toolchain, source code, or build cache ships in the final image.

```dockerfile
# ---- build stage ----
FROM golang:1.23 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w" -o /out/myservice ./cmd/myservice

# ---- final stage ----
FROM gcr.io/distroless/static-debian12
COPY --from=build /out/myservice /myservice
USER nonroot:nonroot
ENTRYPOINT ["/myservice"]
```

`distroless/static` (or, more aggressively, `FROM scratch`) contains no shell, no package manager, no libc — just enough to run a static executable and, in distroless's case, CA certificates and timezone data, which a real service usually needs for outbound TLS. This is not an option most languages have: a Python or Node "distroless-style" image still needs the interpreter and its native dependencies present, so their minimal images top out considerably larger and with more moving parts than a Go service compiled to a single static binary. The security benefit compounds the size one — no shell in the final image means a container escape that lands an attacker inside it finds no `sh`, no `curl`, no package manager to pivot with.

## Embedding build metadata with `-ldflags`

A binary that can't tell you what commit it was built from is a debugging headache waiting to happen. Go's linker lets you set the value of any package-level string variable at build time with `-X`:

```go
// package main
var (
    version   = "dev"
    commit    = "unknown"
    buildDate = "unknown"
)
```

```bash
go build -ldflags "\
  -X main.version=$(git describe --tags --always) \
  -X main.commit=$(git rev-parse --short HEAD) \
  -X main.buildDate=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -o myservice ./cmd/myservice
```

This is the mechanism behind essentially every `mytool --version` output you've ever seen print a real commit hash instead of a hand-maintained version string that inevitably drifts out of date, and it's equally valuable wired into a service's `/healthz` or startup log line for production debugging — "which build is actually running on this pod" is a question you want answered in one glance, not a git archaeology exercise.

`-ldflags "-s -w"` (shown in the Dockerfile above) strips the symbol table and DWARF debug information, typically shrinking a binary 20–30%. It's a reasonable default for a production image where you're not attaching a debugger to the shipped artifact directly; keep an unstripped build available in CI artifacts if you ever need `delve` against the exact bits that shipped.

## Why this chapter is the hinge of the book

Everything above — one file, no dependencies, cross-compiled trivially, small enough to ship in a distroless image, self-describing via embedded build metadata — is not a random grab-bag of nice features. It's the direct, compounding payoff of Chapter 1's founding complaint: a language built by engineers tired of slow, dependency-tangled builds produces, as a natural consequence, a build artifact that's fast to produce and trivial to deploy anywhere. That property is *why* Go became the default implementation language for the infrastructure the rest of the industry now runs on. The next four chapters look at exactly that, starting with the project that made "ship a static Go binary" a mainstream ops habit in the first place.
