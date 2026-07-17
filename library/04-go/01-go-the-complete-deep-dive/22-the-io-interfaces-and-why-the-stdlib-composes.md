# The io Interfaces and Why the Stdlib Composes

**Fast overview:** if one thing explains why Go's standard library feels like it was designed by a single disciplined team rather than accreted over a decade, it's this chapter's subject: `io.Reader` and `io.Writer`, two one-method interfaces so small they fit in a tweet, that nearly every piece of I/O code in the language — files, sockets, in-memory buffers, compressors, hashers, template renderers — implements or accepts. *Connect the dot:* this is Chapter 7's structural typing paying off at the scale of an entire standard library: no shared base class, no registration, no framework. A type satisfies `io.Reader` by having the right method, full stop, and that's the entire mechanism behind everything in this chapter.

## The contract, read precisely

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}
```

`Read` fills the caller-provided slice `p` with up to `len(p)` bytes and reports how many it actually wrote (`n`) plus an `error`. The exact contract, straight from the doc comment every Go engineer eventually reads closely, has edge cases that trip people up if they guess instead of checking:

- `Read` **may** return fewer bytes than `len(p)`, even when more data is available and no error occurred — a caller **must not** assume a short read means end-of-stream.
- When a `Read` reaches the end of the available data, it may return `(n, io.EOF)` with `n > 0` on the *same* call that delivered the last real bytes, or return `(0, io.EOF)` on a subsequent call with no more data at all — both are valid, and correct callers handle a non-zero `n` together with a non-nil `err` in the *same* call, processing the bytes first and checking the error second:

```go
for {
    n, err := r.Read(buf)
    if n > 0 {
        process(buf[:n]) // handle the data even if err is also set
    }
    if err != nil {
        if err == io.EOF {
            break // expected: normal end of stream, not a failure
        }
        return fmt.Errorf("reading: %w", err)
    }
}
```

`Write` is the simpler, stricter half of the pair: it must return an error if it writes fewer than `len(p)` bytes, so a caller checking `n == len(p) && err == nil` never has to also separately check for a short write on success. *Connect the dot:* Chapter 19 used `io.EOF` as its worked example of a sentinel error that means "expected," not "broken" — this is the interface that sentinel belongs to.

## Composability: every layer only knows about the interface below it

The payoff is that you can stack arbitrarily many pieces of infrastructure — a network connection, buffering, decompression, decoding — with zero coupling between layers, because each layer only ever depends on `io.Reader` or `io.Writer`, never on the concrete type underneath:

```go
conn, _ := net.Dial("tcp", "example.com:80")     // implements io.ReadWriteCloser
buffered := bufio.NewReader(conn)                // wraps any io.Reader
gz, _ := gzip.NewReader(buffered)                // wraps any io.Reader
dec := json.NewDecoder(gz)                       // reads from any io.Reader

var payload Response
dec.Decode(&payload)
```

`bufio.NewReader` doesn't know or care that its argument is a network connection rather than a file or an in-memory buffer. `gzip.NewReader` doesn't know its input is buffered. `json.NewDecoder` doesn't know any of the layers underneath exist at all — it just calls `Read` on whatever it was handed. This is possible with **zero shared base type**: no `Stream` superclass, no `implements io.Reader` declaration anywhere, just four independent packages that each happen to accept or produce something with a `Read(p []byte) (int, error)` method.

`io.Copy(dst Writer, src Reader) (int64, error)` is the simplest expression of the same idea: it moves bytes from any reader to any writer, chosen entirely by the caller, with an internal buffer sized sensibly and special-cased fast paths (like `ReadFrom`/`WriteTo`, described below) for types that can do the copy more efficiently than a generic loop.

## Composed interfaces, embedded

*Connect the dot:* Chapter 4 covered struct embedding for promoting fields and methods; the `io` package does the same trick with interfaces, embedding smaller interfaces inside larger ones to name common combinations without redeclaring their methods:

```go
type Closer interface {
    Close() error
}

type ReadCloser interface {
    Reader
    Closer
}

type ReadWriteCloser interface {
    Reader
    Writer
    Closer
}
```

An `os.File` satisfies `io.ReadWriteCloser` automatically, just by having `Read`, `Write`, and `Close` methods with the right signatures — nobody had to write `func (f *File) satisfiesReadWriteCloser()` anywhere. This is also why function signatures in well-written Go APIs take the *smallest* interface that actually covers what they need: a function that only ever reads should accept `io.Reader`, not `*os.File` and not `io.ReadWriteCloser`, so it can be handed a network connection, a `bytes.Buffer`, or a test's `strings.Reader` with no changes at the call site.

## Buffered and line-oriented reading: `bufio`

Raw `Read` calls against a network connection or disk file are expensive per-call, so `bufio.Reader` wraps any `io.Reader` and batches actual reads from the underlying source into a larger internal buffer, serving small `Read` calls out of memory. `bufio.Scanner` builds on this for the extremely common case of line-oriented or token-oriented input:

```go
scanner := bufio.NewScanner(file)
for scanner.Scan() {
    line := scanner.Text()
    process(line)
}
if err := scanner.Err(); err != nil {
    log.Fatal(err)
}
```

Note the loop shape: `Scan()` returns `false` both on a real error *and* on a clean end-of-input, so you check `scanner.Err()` *after* the loop to tell the two apart — `nil` means it stopped because the input ended, not because something broke.

## In-memory implementations: your tests get these for free

`bytes.Buffer` implements both `io.Reader` and `io.Writer` over an in-memory byte slice, and `strings.Reader` implements `io.Reader` (plus `io.Seeker`, `io.ReaderAt`) over an immutable string. *Connect the dot:* this is exactly what Chapter 21 leaned on for test doubles without a mocking framework — any function accepting `io.Reader` can be tested by passing `strings.NewReader("fake response body")` with zero network calls, no test server, and no mock library:

```go
func TestParseHeader(t *testing.T) {
    r := strings.NewReader("Content-Type: application/json\r\n\r\n")
    got, err := ParseHeader(r)
    // ...
}
```

Production code that writes output can similarly be pointed at a `&bytes.Buffer{}` in a test instead of a real file or `http.ResponseWriter`, then have the test assert against `buf.String()` — no filesystem, no server, and the function under test never needed to know it wasn't talking to the real thing.

## `io.Pipe`: connecting a writer to a reader in-process

Occasionally you need to hand something a reader whose bytes are actually produced by a writer somewhere else in the same process — streaming the output of one operation directly into the input of another without buffering the whole thing in memory first. `io.Pipe()` returns a connected `*PipeWriter`/`*PipeReader` pair: bytes written to one block until read from the other, making it a synchronous, in-memory analogue of a Unix pipe, typically driven from its own goroutine (*connect the dot:* Chapter 11's channels solve a similar "hand data from one goroutine to another" problem for arbitrary values; `io.Pipe` is the same idea specialized to the `io.Reader`/`io.Writer` shape specifically).

Next: Chapter 23 covers the two remaining escape hatches for dynamism in an otherwise fully static type system — runtime reflection, and its more Go-flavored alternative, code generation.
