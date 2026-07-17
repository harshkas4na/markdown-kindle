# Packages, Modules, and the Build System

**Fast overview:** a Go program is built out of packages — the unit of compilation, namespacing, and visibility, one per directory — and packages are distributed and versioned as modules, declared by a single `go.mod` file. This chapter is the map from "a folder of `.go` files" to "a program that imports code from across the internet, verified and version-locked." It closes Part 1: everything about types, values, and functions from Chapters 2–8 lives *inside* the units this chapter describes.

## Packages: one directory, one namespace

Every `.go` file starts with a `package` clause, and every file in the same directory must declare the same package name — a directory is a package, full stop, and the compiler will refuse to build a directory containing files with two different package names (the sole exception is `_test.go` files, which may declare `package foo_test` for black-box testing, covered in Chapter 21). The package name and the **import path** are different things: the import path is the path other code writes to import it (`"github.com/user/project/internal/store"`), while the package name is just the identifier used inside files that import it (usually the import path's last element, but a package can name itself anything — `package store` living at that same long import path is the overwhelmingly common convention, and deviating from it without a good reason confuses readers).

## Exported vs unexported: capitalization is the access modifier

Go has no `public`, `private`, or `protected` keywords. Visibility is exactly one rule, enforced by the compiler, not a linter: an identifier — a function, type, variable, constant, struct field, or method — is **exported** (visible to importing packages) if its name starts with an uppercase letter, and **unexported** (visible only within its own package) otherwise.

```go
package store

type Record struct {
    ID    string // exported field — visible to callers
    cache map[string]any // unexported field — only this package can touch it
}

func New() *Record { ... }   // exported constructor
func (r *Record) load() { }  // unexported helper method
```

*Connect the dot:* this is the same capitalization rule Chapter 2 introduced for naming conventions, but here it's not a convention — it's load-bearing. A struct with unexported fields can still be constructed and used freely by other packages (through an exported constructor and exported fields/methods), which is how Go achieves encapsulation without a `private` keyword: hide the fields, expose the behavior.

## Modules: go.mod, versioning, and go.sum

A **module** is a collection of packages released, versioned, and distributed together, declared by a `go.mod` file at its root:

```
module github.com/harshkas4na/hookathon

go 1.23

require (
    github.com/gorilla/mux v1.8.1
    golang.org/x/sync v0.7.0 // indirect
)
```

- `module` declares the module's own import path — every package inside is addressed as `<module path>/<subdirectory>`. A `go.mod` file has exactly one `module` directive.
- `go 1.23` declares the minimum Go language version the module requires — the toolchain enforces this: an older `go` binary will refuse to build a module declaring a newer version.
- `require` lists dependency modules and their minimum versions. `// indirect` marks a dependency your code doesn't import directly — it's pulled in only because something you *do* depend on needs it.
- `replace` (not shown above) swaps one module's source for another — a local filesystem path during development, or a fork — and only takes effect in the *main* module's `go.mod`, never a dependency's; this is how you point at an unmerged patch to a library without forking your whole dependency tree.
- `exclude` and `retract` are the rarer two: `exclude` refuses a specific version outright, and `retract` (set by a module's *own* author, in its *own* `go.mod`, for a *past* published version) marks a version as "please don't depend on this" — the `go` command warns you if your build graph includes a retracted version, most often used after publishing a version with a serious bug or by accident.

`go.sum`, alongside `go.mod`, records a cryptographic checksum for every module version your build graph touches — not for trust in the usual "signing" sense, but for **reproducibility and tamper-detection**: if a module server ever serves different bytes for the same version tag than what your `go.sum` recorded the first time, the build fails loudly instead of silently linking in different code. This is Go's answer to the supply-chain class of attack where a dependency's published contents quietly change out from under you.

## The GOPATH era, briefly, because you'll still see its scars

Before modules (which arrived experimentally in Go 1.11, November 2018, and became the default in Go 1.16, February 2021), every Go workspace lived under one global tree, `$GOPATH/src`, and every project on your machine shared it — two projects needing different versions of the same dependency simply couldn't, because there was no per-project version at all, only whatever was checked out in the shared tree at that moment. Vendoring directories and third-party tools (`dep`, `glide`, `govendor`) existed purely to paper over this, and every one of them was incompatible with every other. Modules solved the problem at the language level: `go.mod` makes every module self-describing and self-versioned, `GOPATH` stopped being where your source *had* to live, and a project can be a directory anywhere on disk. If you ever read Go code with import comments like `// import "gopkg.in/yaml.v2"` or see old build scripts exporting `$GOPATH`, that's a fossil of this era — safe to ignore in code written for Go 1.16+.

## Semantic import versioning: the `/v2` rule

Go's module system encodes an opinionated stance directly into import paths: **the major version of a module (2 and above) is part of its import path.** A module's first stable release and all of its `v0.x`/`v1.x` versions import at the bare path (`github.com/user/project`), but the moment that module publishes a `v2.0.0` — a version explicitly allowed to break backward compatibility — its import path must change to `github.com/user/project/v2`.

```go
import "github.com/user/project"      // v0 or v1
import "github.com/user/project/v2"   // v2
```

This looks strange the first time you see it, but it solves a real problem: it lets **two major versions of the same module coexist in one build's dependency graph** — if package A depends on `project/v1` and package B depends on `project/v2`, both can be satisfied simultaneously, because to the module resolver they're simply different import paths, not a version conflict to reconcile. Without this rule, Go's minimum-version-selection algorithm (which picks, for every module in the build, the *highest* version any dependency requires — deliberately simpler and more predictable than the "resolve a SAT problem" approach other ecosystems use) would have no way to represent "these two requesters need incompatible major versions of literally the same thing."

## `internal/`: a visibility boundary the compiler enforces

Exported/unexported controls visibility *within* a module across every importer. `internal/` is a second, coarser mechanism: any package whose import path contains a directory literally named `internal` can only be imported by code rooted at the parent of that `internal` directory — not by any other module, and not even by unrelated packages elsewhere in the *same* module.

```
github.com/you/project/
├── api/            → importable by anyone
├── internal/
│   └── store/      → importable only from github.com/you/project/... 
└── cmd/server/     → can import .../internal/store; an outside module cannot
```

This is a real compiler-enforced boundary, not a documentation convention — an outside module attempting `import "github.com/you/project/internal/store"` fails to build. It's the tool teams reach for to expose a small public API surface (`api/`, or the module root) while keeping the actual implementation free to change without a compatibility promise. *Connect the dot:* Chapter 29 returns to this with the full `cmd/`, `internal/`, `pkg/` layout convention once you've seen enough real code to judge the tradeoffs properly.

## Workspaces: developing several modules at once

`go.work` (added in Go 1.18, the same release as generics) solves a narrower problem: when you're actively developing two or more modules together — say, a library and an application that consumes it, both changing in the same afternoon — a `go.work` file at a level above both lets your local build use the on-disk source of each, without editing either module's `go.mod` with a temporary `replace` directive you'd have to remember to revert before committing:

```
go 1.23

use (
    ./project
    ./project-plugin
)
```

`go.work` is explicitly meant to stay local — it's normal (and generally correct) to `.gitignore` it rather than commit it, since it describes your machine's working setup, not the module's actual dependency graph.

## The everyday toolbox

Three commands cover the vast majority of real work: `go get <module>[@version]` adds or upgrades a dependency and updates `go.mod`/`go.sum`; `go mod tidy` reconciles `go.mod` with what your code actually imports — adding anything missing, removing anything now unused — and is the command you run before every commit that touched imports; `go mod why <module>` answers "why is this in my dependency graph at all," tracing the shortest import chain that pulls it in, which is the fastest way to investigate an unexpected transitive dependency.

Part 1 closes here. You now have the full vocabulary for what Go code *is* — its types, its values, its functions, and the packages and modules that organize it into a buildable program. Part 2 starts with the feature that makes people choose Go in the first place: goroutines, and the runtime scheduler that makes hundreds of thousands of them practical at once.
