# net/http From First Principles

**Fast overview:** this chapter opens Part 5 — building something that takes real traffic. Go ships a production-grade HTTP server in its standard library, and the whole thing rests on one interface with one method. We build a minimal but complete server from that interface upward: the `Handler` contract, the router (`ServeMux`, dramatically upgraded in Go 1.22), and the server-level settings that separate a toy from something you'd expose to the internet. Everything in Chapters 25 and 26 is built directly on top of the server this chapter constructs.

## One interface, one method

Everything in `net/http` — the standard library router, every third-party framework, every middleware you'll ever write — ultimately reduces to this:

```go
type Handler interface {
    ServeHTTP(ResponseWriter, *Request)
}
```

*Connect the dot:* this is Chapter 7's small-interfaces idiom taken to its logical extreme. One method. Anything with a `ServeHTTP(ResponseWriter, *Request)` method satisfies `Handler` — no base class, no registration, no `implements` keyword. A struct, a closure, a whole framework's router: if it has that method, `net/http` will happily drive traffic through it.

Because writing a full type just to get one method is often more ceremony than the job needs, the standard library gives you an adapter:

```go
type HandlerFunc func(ResponseWriter, *Request)

func (f HandlerFunc) ServeHTTP(w ResponseWriter, r *Request) {
    f(w, r)
}
```

Read that twice — it's a one-line trick that's worth understanding fully rather than memorizing. `HandlerFunc` is a *function type* that has a method defined on it. So any plain function with the signature `func(ResponseWriter, *Request)` can be converted to a `HandlerFunc`, and once converted, it satisfies `Handler`, because calling its `ServeHTTP` method just calls the function itself. This is how `http.HandleFunc(pattern, myPlainFunction)` lets you write ordinary functions as handlers without ever writing `ServeHTTP` yourself. It's a small, elegant proof that Go's implicit interface satisfaction (Chapter 7) isn't a party trick — it's load-bearing in the standard library's most-used package.

## The two arguments: ResponseWriter and Request

`ResponseWriter` is how a handler produces a response. Three methods matter in practice: `Header()` returns the response header map so you can set things like `Content-Type` before writing; `Write([]byte) (int, error)` writes the response body — and satisfies `io.Writer`, so anything that writes to an `io.Writer` (`json.NewEncoder`, `fmt.Fprintf`, `io.Copy`) works directly against it, a direct payoff of Chapter 22; and `WriteHeader(statusCode int)` sends the HTTP status line and headers, and must be called *before* the first `Write` if you want anything other than an implicit `200 OK`.

`*Request` is everything about the incoming request: `Method` (`"GET"`, `"POST"`, ...), `URL` (parsed, with `.Path` and `.Query()`), `Header`, and `Body` — an `io.ReadCloser`, meaning it's Chapter 22's `io.Reader` again, which is why decoding a JSON body is just `json.NewDecoder(r.Body).Decode(&dst)` with no intermediate buffer required.

## ServeMux: the router, rebuilt in Go 1.22

For a decade, Go's built-in router (`http.ServeMux`) could only match on path prefixes and exact paths — no method matching, no path parameters — so almost every real Go web service reached for a third-party router (`gorilla/mux`, `chi`, `httprouter`) just to write `GET /users/{id}`. Go 1.22 (February 2024) closed that gap directly in the standard library, and it's worth learning the new syntax precisely because it's now genuinely production-viable for a large share of services.

Patterns can carry an HTTP method prefix and wildcard path segments:

```go
mux := http.NewServeMux()
mux.HandleFunc("GET /posts/{id}", getPost)
mux.HandleFunc("POST /posts", createPost)
mux.HandleFunc("DELETE /posts/{id}", deletePost)
mux.HandleFunc("GET /files/{path...}", serveFile)
mux.HandleFunc("GET /posts/{$}", listPostsExact)
```

`{id}` matches exactly one path segment; read it inside the handler with `r.PathValue("id")`. `{path...}` (a trailing wildcard) matches all remaining segments, useful for file-serving-style handlers. `{$}` matches only the exact path with a trailing slash — `/posts/{$}` matches `/posts/` but not `/posts` or `/posts/234`. A bare method prefix like `GET` also implicitly matches `HEAD` requests, matching HTTP semantics; every other method must match exactly. If a request's path matches no pattern at all, `ServeMux` returns `404`; if the path matches but the method doesn't, it returns `405 Method Not Allowed` with an `Allow` header listing what would have matched.

Conflict resolution follows a "most specific wins" rule: a literal segment beats a wildcard (`/posts/latest` beats `/posts/{id}`), and a method-restricted pattern beats an unrestricted one (`GET /posts/{id}` beats `/posts/{id}`). If two patterns are genuinely ambiguous — neither is strictly more specific than the other, e.g. `/posts/{id}` and `/{resource}/latest` both match `/posts/latest` — registering both **panics at startup**, not at request time, which is exactly the fail-fast behavior you want from a router: a routing conflict is a programmer error, and Go surfaces it the moment the program starts rather than the moment a user happens to hit the ambiguous path.

## Assembling the minimal server

Here is the complete, runnable spine this chapter builds toward — small enough to read in one pass, real enough that Chapters 25 and 26 extend it rather than replace it:

```go
package main

import (
    "log"
    "net/http"
    "time"
)

func listPosts(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    w.Write([]byte(`{"posts":[]}`))
}

func getPost(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")
    w.Write([]byte("post " + id))
}

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("GET /posts", listPosts)
    mux.HandleFunc("GET /posts/{id}", getPost)

    srv := &http.Server{
        Addr:         ":8080",
        Handler:      mux,
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  120 * time.Second,
    }

    log.Fatal(srv.ListenAndServe())
}
```

## Why `http.ListenAndServe` alone is a footgun

`http.ListenAndServe(":8080", mux)` — the package-level convenience function — works, and you'll see it in every five-minute tutorial. It also has no timeouts configured at all: a client can open a connection, send headers at one byte per minute, and hold a goroutine and a file descriptor open indefinitely. This is a real, named vulnerability class (Slowloris-style slow-request attacks), and it's why the example above constructs an explicit `*http.Server` instead. `ReadTimeout` bounds how long reading the entire request (headers and body) may take; `WriteTimeout` bounds how long writing the response may take; `IdleTimeout` bounds how long a keep-alive connection may sit idle between requests. None of these are optional hardening for a service that will ever be reachable from the open internet — they're the baseline. A more surgical option, `ReadHeaderTimeout`, bounds just the headers if you need slow, legitimate long-running request bodies (file uploads) without letting header-only stalls through.

## What's next

This server has no logging, no panic recovery, no request-scoped timeouts for the work it does, and no way to shut down without dropping in-flight connections. None of that belongs in the router — it belongs *around* every handler, uniformly, which is exactly what Chapter 25, middleware and the request lifecycle, builds on top of the `Handler` interface you just learned.
