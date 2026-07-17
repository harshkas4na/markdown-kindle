# Effective Go: Naming, Formatting, and Docs

**Fast overview:** Part 4 turns from language mechanics to culture — the conventions that make any two Go codebases on Earth look recognizably similar, even written by strangers who never talked to each other. None of this is enforced by the compiler the way the type system is, but it's enforced almost as hard by tooling (`gofmt`, `go vet`, `staticcheck`) and by review culture, and skipping it is the fastest way to mark code as "not idiomatic Go" on sight. This chapter covers the three pillars: formatting, naming, and documentation.

## `gofmt`: there is no style debate

Every other language community argues about tabs versus spaces, brace placement, import ordering. Go's answer was to remove the argument entirely: `gofmt` (or `go fmt`, which runs it per-package) parses your source and re-emits it in one canonical layout — tabs for indentation, consistent spacing around operators, aligned struct fields and comments, sorted and grouped imports (with `goimports`, a common superset that also adds/removes import lines automatically). The philosophy, straight from the language's own guidance: *let the machine take care of formatting issues.* If `gofmt`'s answer to some layout question feels wrong, the fix is to restructure the code, not to fight the formatter — there's no configuration file, no `.gofmtrc`, nothing to bikeshed. Nearly every editor and IDE runs `gofmt` on save, and CI in most real projects fails a pull request whose diff isn't already formatted. The practical payoff shows up in code review: diffs stay minimal (nobody's editor silently reformatting untouched lines), and reading a stranger's Go code never has an adjustment period the way reading someone else's C++ or JavaScript often does.

## Naming: length proportional to distance and scope

Go's naming convention starts from a genuinely useful heuristic: **a name's length should be proportional to how far it lives from its declaration, and how big its scope is.** A loop index that exists for three lines is `i`, not `currentIndexInLoop` — abbreviating it isn't laziness, it's optimizing for how a *reader* scans code: a long name in a five-line scope adds noise without adding information, because the reader can see the whole lifetime of the variable in one glance. An exported package-level function called from a hundred other files earns a fuller name, `ParseConfigFromEnv`, because its declaration is far from most of its call sites and the reader has no surrounding context to lean on.

Multi-word identifiers use **MixedCaps** (`userAccountBalance`, `ParseConfig`) — never `snake_case` and never a leading underscore for anything except deliberately-unused names. Capitalization is not cosmetic in Go: it *is* the exported/unexported boundary from Chapter 9 — `Config` is visible outside its package, `config` is not — so a naming convention and a visibility rule are the same rule, enforced by the compiler.

**Package names** get the strictest rule of all: short, all-lowercase, no underscores, and — this is the one beginners miss most — never a "utils," "common," or "helpers" grab-bag. The reason is mechanical: every call into an exported identifier is qualified by its package name (`bytes.Buffer`, `json.Marshal`), so the package name is effectively a prefix on every single thing it exports. `bytesutil.Buffer` is worse than `bytes.Buffer` in every call site, forever — the package name already tells the reader the domain, so the type inside it doesn't need to repeat it. When you're tempted to write a package called `utils`, that's usually a sign the code inside it belongs distributed across the packages that actually use it, or under a name specific enough to describe what it actually does (`ratelimit`, not `utils`).

**Getters skip the `Get` prefix.** If a struct has an unexported field `owner`, its exported accessor is `Owner()`, not `GetOwner()` — the method name alone already tells you it's returning something, and Go's convention treats `Get` as pure noise:

```go
type Account struct {
    owner string
}

func (a *Account) Owner() string     { return a.owner }
func (a *Account) SetOwner(s string) { a.owner = s } // setters DO keep "Set"
```

**Single-method interfaces are named agent-noun `-er`.** `Reader` has `Read`, `Writer` has `Write`, `Stringer` has `String() string`, `Closer` has `Close() error` — and when you define your own single-method interface, matching this pattern (`Validator` with `Validate()`, `Fetcher` with `Fetch()`) instantly tells a reader what kind of thing it is before they've read the method signature. *Connect the dot:* this convention is what makes Chapter 7's implicit interface satisfaction and Chapter 22's `io.Reader`/`io.Writer` composability actually pleasant to read — you can often guess an unfamiliar interface's single method just from its name.

## Doc comments: comments the compiler actually understands the shape of

A **doc comment** is a `//`-comment placed directly above a top-level declaration — `package`, `func`, `type`, `const`, `var` — with no blank line between the comment and the declaration. Every exported identifier should have one; `go doc` and pkg.go.dev render these directly as your package's documentation, so the comment *is* the documentation, not a separate artifact you maintain in parallel.

The one hard rule: a doc comment should be written as complete sentences and **begin with the name of the thing it documents**, so tools and readers can extract a one-line summary mechanically:

```go
// Quote returns a double-quoted Go string literal representing s.
func Quote(s string) string { ... }

// HasPrefix reports whether the string s begins with prefix.
func HasPrefix(s, prefix string) bool { ... }

// A Reader serves content from a ZIP archive.
type Reader struct { ... }

// The zero value for Buffer is an empty buffer ready to use.
type Buffer struct { ... }
```

Booleans get the "reports whether" phrasing (as `HasPrefix` shows above) rather than an imperative — it reads as a description of what the function tells you, not a command. Since Go 1.19, doc comments support a small amount of real markup, handled by `go/doc/comment`: headings (`# A Heading`, on their own line, blank lines around it), bullet lists (`//   - item one`, two-space indent before the marker), numbered lists (`//  1. step one`), and links — either bare URLs, or **doc links** in square brackets referencing another exported identifier, which pkg.go.dev turns into a real hyperlink: `// See [io.Reader] for the read contract.` A paragraph that starts with the literal word `Deprecated:` marks the identifier as deprecated in a way tools can detect and surface as a warning.

Package-level doc comments go directly above the `package` clause in any file of the package (by convention, often a dedicated `doc.go` for packages whose overview doesn't belong attached to any one file), and — the one place the "start with the name" rule looks slightly different — begin with the literal words `Package <name>`:

```go
// Package path implements utility routines for manipulating slash-separated
// paths.
//
// The path package should only be used for paths separated by forward
// slashes, such as the paths in URLs. This package does not deal with
// Windows paths with drive letters or backslashes; to manipulate operating
// system paths, use the [path/filepath] package.
package path
```

## Tools that enforce the rest

`gofmt` handles layout; `go vet` (built into the toolchain, run automatically by `go test`) catches a set of correctness-adjacent mistakes that compile fine but are almost always bugs — a `Printf` format verb that doesn't match its argument's type, a struct copied by value that contains a `sync.Mutex` (silently breaking the lock), an unreachable code path. `staticcheck`, the most widely adopted third-party linter, goes further: unused code, deprecated API usage, style issues like error strings that shouldn't be capitalized or end in punctuation (the convention: `errors.New("connection failed")`, not `errors.New("Connection failed.")`, because wrapped errors — Chapter 17 — get concatenated into sentences and a stray capital or period in the middle reads wrong). Most real Go projects run `gofmt -l` (list unformatted files), `go vet`, and `staticcheck` in CI as a hard gate, which is why idiomatic formatting, naming, and doc-comment style tend to be self-enforcing in any codebase that's been through a few code reviews.

Next: Chapter 21 covers testing — where a lot of these same naming and documentation habits (test names, table-driven test case names) show up again, this time backed by the `testing` package itself.
