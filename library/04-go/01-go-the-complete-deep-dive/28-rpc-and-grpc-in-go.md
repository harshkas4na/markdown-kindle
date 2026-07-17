# RPC and gRPC in Go

**Fast overview:** Chapters 24–27 built a JSON-over-HTTP service — the right default for anything a browser or an external client talks to. This chapter covers the other common shape of Go network code: internal, service-to-service calls where you control both ends and want strong typing, generated clients, and streaming. gRPC is the dominant answer in Go's ecosystem specifically, for reasons that trace back to how naturally its call shapes map onto the language's own concurrency primitives.

## When JSON-over-HTTP stops being the right tool

Nothing is wrong with REST-over-JSON for internal traffic — plenty of production systems use it everywhere and never regret it. But three specific pains tend to push a team toward RPC once a system grows past a handful of services: **hand-maintained API contracts drift** — a REST client and server agree on a JSON shape only by convention, and nothing stops them silently diverging; **every field needs to be parsed and validated at runtime** — even though a compiler could have caught a type mismatch if the schema were shared; and **long-lived, bidirectional communication is awkward** — HTTP/1.1's request/response model doesn't naturally express "the server keeps pushing me updates as they happen."

## Protocol Buffers: the shared, generated contract

gRPC starts from a `.proto` file — a schema, not code:

```protobuf
syntax = "proto3";

service PostService {
  rpc GetPost (GetPostRequest) returns (Post);
  rpc StreamPosts (StreamPostsRequest) returns (stream Post);
}

message GetPostRequest { string id = 1; }
message Post {
  string id = 1;
  string title = 2;
  string body = 3;
}
```

Running `protoc` with the Go plugin (`protoc-gen-go` and `protoc-gen-go-grpc`) generates real Go structs (`Post`, `GetPostRequest`) with marshal/unmarshal methods, plus client and server interfaces for `PostService`. *Connect the dot:* this is Chapter 23's `go generate` pattern at industrial scale, and it's the single most common real-world reason a Go engineer runs a code generator — the schema is the single source of truth, both sides of a call are generated from the same file, and a schema change that breaks compatibility becomes a compile error in every consuming service rather than a runtime surprise discovered in production.

The wire format itself (binary, field-numbered rather than field-named) is also considerably smaller than the equivalent JSON, which matters at the volume of internal service-to-service traffic a busy system generates.

## Four call shapes

| Shape | Proto syntax | What it's for |
|---|---|---|
| Unary | `rpc Get(Req) returns (Res)` | A single request, single response — the RPC equivalent of a normal REST call |
| Server streaming | `rpc Watch(Req) returns (stream Res)` | One request, a sequence of responses over time (e.g. "stream me every new post") |
| Client streaming | `rpc Upload(stream Req) returns (Res)` | A sequence of requests, one final response (e.g. uploading chunks) |
| Bidirectional streaming | `rpc Chat(stream Req) returns (stream Res)` | Both sides send a sequence, independently, over one long-lived call |

The generated Go code for a streaming RPC hands you a stream object with `Send` and `Recv` methods that you call in a loop:

```go
stream, err := client.StreamPosts(ctx, &pb.StreamPostsRequest{})
if err != nil {
    return err
}
for {
    post, err := stream.Recv()
    if err == io.EOF {
        break
    }
    if err != nil {
        return err
    }
    handle(post)
}
```

*Connect the dot:* this loop should feel familiar — `Send`/`Recv` in a loop is the same mental shape as sending and receiving on a channel (Chapter 11), even though a gRPC stream isn't literally a Go channel under the hood. Streaming is *natural* to write in Go specifically because the language already trained you, via channels and goroutines, to think in terms of a sequence of values arriving over time rather than one value arriving all at once — which is a large part of why gRPC and Go ended up so closely associated in practice (Kubernetes' own internal and external APIs lean heavily on this combination).

## HTTP/2 underneath

gRPC runs over HTTP/2, not HTTP/1.1, and that choice is what makes streaming and low per-call overhead both possible: HTTP/2 multiplexes many independent streams over a single long-lived TCP connection, so a service issuing hundreds of concurrent RPCs to another service doesn't pay the cost of hundreds of separate connections (or the head-of-line blocking of forcing them through too few HTTP/1.1 connections). For high-volume, low-latency internal traffic — the kind two services in the same cluster exchange constantly — this is a meaningful win over a naive HTTP/1.1 JSON API, independent of the wire-format savings Protocol Buffers already provide.

## Interceptors: middleware, renamed

gRPC's name for Chapter 25's middleware pattern is an **interceptor** — a unary interceptor wraps a single request/response call, a stream interceptor wraps a streaming call, and both do exactly the same job middleware does over HTTP: logging, authentication, metrics, panic recovery, all applied uniformly without touching individual RPC method implementations.

```go
func LoggingInterceptor(ctx context.Context, req any, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (any, error) {
    start := time.Now()
    resp, err := handler(ctx, req)
    log.Printf("%s took %v, err=%v", info.FullMethod, time.Since(start), err)
    return resp, err
}
```

The shape — take the next thing to call, do work before and after, call it in between — is identical to Chapter 25's `func(http.Handler) http.Handler`. Once you've internalized the pattern once, every framework's version of "middleware" is recognizable on sight.

## When plain HTTP/JSON still wins

gRPC is not a universal upgrade, and treating it as one is a common overcorrection. Reach for JSON-over-HTTP instead when: the client is a **browser** (browsers can't easily speak raw gRPC without a proxy layer like gRPC-Web, and REST needs none); the API is **public**, consumed by third parties who benefit from human-readable payloads, `curl`-ability, and the universal familiarity of REST over a generated `.proto` contract they'd need tooling to consume; or **debuggability during development** matters more than wire efficiency — a JSON body is readable in a browser's network tab or a raw `curl` response, a Protocol Buffers payload is not, without decoding tooling. The decision rule that holds up in practice: gRPC for internal, high-volume, service-to-service traffic where both ends are Go (or another gRPC-supported language) code you control; HTTP/JSON for anything public-facing or browser-facing. Most real systems end up running both, side by side, for exactly these two different audiences.

## What's next

Part 5 is complete — a full picture of building a Go service that takes traffic, from the router up through the database and out to other services. Part 6 turns to keeping that service alive in production, starting with Chapter 29's return to project structure, now informed by everything you've actually built.
