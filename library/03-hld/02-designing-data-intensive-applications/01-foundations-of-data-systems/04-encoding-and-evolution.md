# Encoding and Evolution

Applications change. That means schemas change. And in any real deployment, you can never update every piece of a system atomically — servers get rolled out gradually (**rolling upgrades**), mobile clients update whenever the user feels like it (sometimes never), and old data written months ago still has to be readable today. This chapter is about the format data is encoded in, and why that format single-handedly determines how painful every future schema change will be.

## The core requirement: backward and forward compatibility

- **Backward compatibility**: newer code can read data written by older code. This one is intuitive — of course new code should handle old data.
- **Forward compatibility**: older code can read data written by newer code. This is the counterintuitive, easy-to-forget one — it matters because during a rolling upgrade, old and new code are running *simultaneously*, and old nodes will absolutely receive data written by already-upgraded nodes.

A format that only manages backward compatibility will work fine right up until your first zero-downtime rolling deploy, and then quietly break.

## In-memory representations vs. encoded bytes

Inside a running program, data lives as objects, structs, or hash maps — but the moment it needs to leave the process (written to a file, sent over the network), it must be translated into a sequence of bytes. This translation is called **encoding** (or serialization); the reverse is **decoding** (deserialization).

Language-specific serialization (Java serialization, Python's `pickle`, Ruby's `Marshal`) looks convenient because it requires no schema definition — but it should generally be avoided beyond short-lived, same-language, same-process use: it ties you to one programming language, often has serious security problems (deserializing arbitrary bytes can be made to execute arbitrary code), and typically has poor-to-no support for evolving the format over time, which is precisely the problem this chapter is about.

## Textual formats: JSON, XML, CSV

Human-readable, extremely widely supported, and the default choice for most APIs today — but they come with real limitations once you look closely: JSON doesn't distinguish integers from floating-point numbers precisely, and large numbers can silently lose precision across languages with different numeric types; neither JSON nor XML has native support for binary strings; and while optional schemas exist for both (JSON Schema, XML Schema), most usage skips them, leaving correct interpretation of a field's meaning and type up to informal agreement between producer and consumer.

## Binary encoding formats with schemas

**Protocol Buffers** and **Thrift** both take the same core approach: a schema defines each field's type and, critically, a **field tag** — a small integer identifying that field on the wire, instead of the field's name. This one design choice is what buys backward *and* forward compatibility almost for free:

- Fields are identified by number, not name, so you can freely **rename** a field without breaking anything already encoded.
- You can **add a new field** with a new tag number; old code simply doesn't recognize the tag and skips it — forward compatible.
- You can **remove a field**, as long as its tag number is never reused for something else later — as long as old code doesn't have that field marked `required` (which is why both formats push you toward `optional` fields almost everywhere; a field marked required can never safely be removed, because old code will refuse to decode a message missing it).
- Changing a field's **type** is *not* safe in general — some type changes (e.g. int32 to int64) are tolerated, but most aren't, which is the sharp edge to watch for when evolving a schema.

**Avro** takes a different approach: there are no field tags on the wire at all — a value is essentially just a sequence of encoded bytes with no embedded metadata, which makes it extremely compact but means the *reader must be told the writer's exact schema separately* in order to decode anything. Avro's schema resolution then matches fields between the writer's schema and the reader's schema **by field name**, applying rules for handling fields present in one schema but not the other (a genuinely different mechanism from Protobuf/Thrift's tag-number approach, but aimed at the same compatibility goal). Because Avro doesn't bake tag numbers into a schema by hand, it's particularly well suited to *dynamically generated* schemas — e.g. exporting a relational database with hundreds of structurally similar tables, where hand-assigning tag numbers to every column of every table would be impractical.

## Modes of dataflow: how encoded data actually travels

The encoding format matters differently depending on *how* data moves from whoever wrote it to whoever reads it:

- **Through databases**: a process writing a row today may be read by a *different version of the application*, possibly years later — a database is, in this sense, a form of message-passing through time, not just through space, which makes schema evolution a first-class database concern, not just an API concern.
- **Through service calls**: two common styles. **REST** treats the API as a set of addressable resources manipulated over HTTP with standard verbs and typically JSON bodies — simple, cacheable, and works well with the grain of the web. **RPC** frameworks (gRPC and predecessors) try to make a network call *look* like a local function call — but a network call has entire categories of failure a local call doesn't (it can time out with no way to know whether the other side actually executed it, it can be retried and accidentally executed twice, the network itself can be down). Making a remote call *look* local is a leaky abstraction: it hides real, consequential differences behind a familiar syntax, and code that forgets this (e.g. doesn't design for safe retries / idempotency) breaks in ways that are hard to diagnose precisely because the abstraction told it not to worry.
- **Through asynchronous message-passing** (message brokers / queues): a producer publishes a message without needing the consumer to be online right now; the broker durably holds it until a consumer is ready. This decouples producer and consumer in time (unlike RPC, which needs both ends up simultaneously), and naturally supports one message fanning out to multiple independent consumers — at the cost of losing RPC's direct request/response guarantee.

## Takeaways

- Compatibility is bidirectional and both directions matter the moment you do rolling deploys — "new code reads old data" alone is not enough.
- Field identity should be tag/number-based (Protobuf/Thrift) or resolved by an explicit writer's schema (Avro) — anything relying on the reader guessing a field's meaning from convention is a compatibility trap waiting to happen.
- RPC's promise of "calling a remote service is just like calling a function" is worth being actively suspicious of — the differences (partial failure, retries, latency) are exactly the things that cause outages when developers trust the abstraction too literally.
