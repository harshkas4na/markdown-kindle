# How Real Go Codebases Are Organized

**Fast overview:** this chapter opens Part 6 — production engineering — and deliberately revisits Chapter 9's packages and modules now that you've actually built something (Part 5). Chapter 9 gave you the mechanics: what a package is, what `internal/` enforces, how imports resolve. This chapter is about judgment: how the dominant `cmd/`/`internal/`/`pkg/` convention actually gets used, why it's contested, and how a real project's structure should evolve instead of being scaffolded whole on day one.

## The convention you'll see everywhere

Clone almost any well-known Go project and you'll find some version of this shape:

```
cmd/
  api/main.go       — one entrypoint per binary the repo builds
  worker/main.go
internal/
  order/            — application code, organized by domain
  auth/
pkg/                — code meant to be imported by other repositories (optional, contested)
go.mod
```

`cmd/<binary-name>/main.go` exists so a repo that builds more than one binary (an API server and a background worker, say) has a clear, separate entrypoint for each, and so that `main.go` itself stays thin — wiring dependencies together and calling `Run()`, not containing logic that can't be unit-tested without starting a whole process. *Connect the dot:* Chapter 26's `main.go` already followed this instinct in miniature; this is that same discipline generalized across a whole repository with several binaries.

`internal/` is Chapter 9's compiler-enforced import boundary, used here deliberately: any package under `internal/` can only be imported by code inside the same module tree, so it's structurally impossible for another team's repository to accidentally start depending on your application's internals. That matters because an accidental external dependency isn't just an inconvenience — it's a promise you didn't mean to make, and one you now can't break without breaking someone else's build. Making `internal/` the *default* home for application code, rather than an occasional opt-in, means you never have to remember to lock a package down later; you only have to remember to explicitly move something *out* of `internal/` once you actually intend to support external consumers.

## pkg/ is popular, and it is not official

This is worth being direct about, because the confusion is common: `golang-standards/project-layout`, the GitHub repository that popularized this exact `cmd/`/`internal/`/`pkg/` shape, is a community convention, not a Go team standard, and it says so in its own disclaimer. It became popular because it's a reasonable default for large, multi-binary projects with genuine public library code — Kubernetes, for instance, exposes real, versioned client libraries under a `pkg/`-shaped area other projects import. But the Go team itself has never endorsed one canonical layout, and several well-known voices in the Go community have pushed back on `pkg/` specifically as often being cargo-culted onto projects that have no external consumers at all — a folder that exists because a template had it, not because anything in the project actually needs the distinction it implies. The honest rule: if nothing outside your own module imports a package, putting it under `pkg/` instead of `internal/` buys you nothing and *removes* the compiler's protection against someone accidentally depending on it later.

## How structure should actually evolve

The mistake this chapter is most trying to prevent is scaffolding `cmd/`, `internal/`, `pkg/`, `api/`, and half a dozen other folders for a service that's currently two hundred lines of code. Structure imposed ahead of need doesn't prevent complexity — it just gives complexity somewhere to hide, and forces every contributor to guess which of five empty-feeling folders a new five-line function belongs in.

A structure that holds up in real projects tends to grow like this instead: start with everything reasonable in `main.go` and a small number of files beside it. Extract a package only when you feel *actual* pain — a second binary that needs to share the database access code the first one has, or a piece of logic you want to unit test in isolation from HTTP handling, or a file that's grown past the point where you can hold its whole contents in your head. Each extraction should be traceable to a concrete reason, not a template. This is slower to look "properly organized" in the first week and dramatically faster to actually navigate in the first year, because every folder boundary that exists, exists because someone needed it to.

## Domain-oriented vs layer-oriented boundaries

Once you are extracting packages, a second, more consequential choice appears: cut the codebase by **domain** (`package order`, `package payment`, `package shipping`, each owning its own types, logic, and data access for that concern) or by **layer** (`package models`, `package handlers`, `package repositories`, each spanning every domain concern at one architectural tier)?

Most experienced Go teams converge on domain-oriented boundaries, and the reason connects directly back to Chapter 7. A layer-oriented split tends to accumulate a central `package interfaces` or `package models` that every other package imports, which becomes a dumping ground nobody owns and a single point of merge conflicts. A domain-oriented split instead lets each package define the small interfaces *it* needs, at the point where it needs them — Chapter 7's "accept interfaces, return structs" idiom, applied at package-design scale rather than just function-signature scale. `package order` doesn't need a shared `Repository` interface defined somewhere else; it defines its own narrow `orderStore` interface with exactly the two or three methods `order`'s own logic actually calls, and any storage package that happens to implement those methods — Postgres-backed today, an in-memory fake in tests, something else entirely later — satisfies it without either package knowing the other exists at compile time beyond that one small contract.

| Split | Ownership | Common failure mode |
|---|---|---|
| Domain (`order`, `payment`) | Clear — one team, one package, one concern | Some genuinely cross-cutting logic doesn't fit neatly in either domain |
| Layer (`models`, `handlers`, `repositories`) | Diffuse — every domain touches every layer | Central packages become import magnets and bottleneck reviews |

Neither is universally correct — a small service with one clear domain barely needs the distinction at all — but as a codebase grows past a handful of contributors, domain-oriented boundaries tend to degrade more gracefully, because the blast radius of a change stays contained to the package that owns the concern being changed.

## What's next

Structure is only useful once the service is actually running somewhere real. Chapter 30 covers configuration and observability — how a Go service tells you what config it's running with, and what it's actually doing, once it's out of your terminal and into production.
