# Data Models and Query Languages

The data model you choose is arguably the single biggest lever on how you and everyone after you will think about a problem — every layer of a real application is itself a data model built on top of the layer below it (application objects, on top of a database's tables/documents/graphs, on top of bytes on disk, on top of electrical signals). Each layer hides the complexity of the one beneath it through abstraction, and each layer's design shapes what's easy or painful to express in the layer above it. This chapter is about the two layers application developers actually choose: how you shape your records, and how you query them.

## Relational vs. document

**The relational model** (SQL databases) organizes data into tables of rows, related to each other via foreign keys, queried by joining tables together. Its strength is flexibility for relationships: it doesn't force you to decide up front how data will be accessed, because joins can traverse relationships in either direction at query time. This makes it well-suited to data with many-to-many relationships and access patterns that change over time.

**The document model** (JSON/BSON-style stores like MongoDB) stores each record as a self-contained, often nested document — closer to how an application object actually looks in memory. Its main win is reducing the **impedance mismatch**: less translation code between "object in memory" and "rows across several joined tables." It also gives **locality**: if an application typically needs an entire record at once (a user profile, a resume with nested work history), a document store can fetch it in a single read, whereas the relational equivalent might need several joins. The cost is that document databases are generally weak at joins — a many-to-many relationship either has to be resolved in application code (multiple round trips) or denormalized (duplicating data, accepting the update anomalies that come with it).

**Schema-on-write vs. schema-on-read**: relational databases traditionally enforce a schema at write time (an explicit migration is required to change the shape of data). Document databases are usually **schema-on-read** — the data has an implicit structure, but it's the *application's* job to interpret it correctly, which means the database will happily store records of differing shapes side by side. Schema-on-read is more like duck typing (flexible, checked when used); schema-on-write is more like static typing (stricter, checked up front). Schema-on-read is a genuine advantage when the data itself is heterogeneous, or when structure needs to change often and you don't want an application-wide lockstep migration.

The debate between these two models isn't new — it's a recurring pendulum: hierarchical databases (IBM's IMS) came first and struggled badly with many-to-many relationships; the relational model was explicitly invented to fix that; document databases emerged decades later partly as a reaction to the impedance mismatch relational databases reintroduced. Today most relational databases support native JSON columns and most document databases have added join-like operators, so the practical distinction has blurred — but the underlying tradeoff (locality/flexibility vs. relationship-querying power) is still real and still drives the choice.

## Graph data models

When the interesting facts about your data are the *relationships themselves*, and those relationships are many-to-many and multiple degrees deep (social graphs, recommendation engines, fraud/ring detection, dependency graphs), both relational and document models get awkward — either the joins multiply out of control or the document nesting doesn't have a natural "center."

A **property graph** represents data as vertices (entities, each with a set of key-value properties) and edges (directed, labeled relationships between vertices, which can also carry properties). This is a natural fit for questions like "find people two hops away from me who like the same things I do" — a query that's a genuinely awkward number of self-joins in SQL, but a short traversal in a graph query language.

Query languages built for this shape include **Cypher** (declarative, pattern-matching syntax — Neo4j) and **SPARQL**/**Datalog** (for the closely related triple-store model, where every fact is a `(subject, predicate, object)` triple — the same expressive power as a property graph, just factored differently).

## Declarative vs. imperative query languages

- **Imperative** code tells the computer the exact steps to perform, in order (a for-loop scanning records one by one).
- **Declarative** languages (SQL, Cypher, relational algebra, SPARQL) instead specify *what* result you want, not *how* to get it — the pattern of the data you're looking for, not the traversal steps.

Declarative languages have a major practical advantage that's easy to overlook: because the query only describes the desired *result*, the database's query optimizer is free to choose the actual execution strategy (which index to use, which join order, whether to parallelize) — and can change that strategy later (a new index, a schema change) without the query itself needing to change. An imperative traversal, by contrast, hard-codes the access path; if the underlying data layout changes, the code has to change with it. Declarative languages are also inherently friendlier to automatic parallelization, since the optimizer — not hand-written control flow — decides how work is split across cores or machines.

**MapReduce** (covered fully in the batch-processing chapter) sits in between: it's a fairly low-level programming model based on `map`/`reduce` functions applied across a cluster, more flexible than SQL but requiring you to write more imperative-feeling code to express what a declarative query would say in one line — a genuine middle ground rather than a straightforward replacement for either.

## Quick reference

| Model | Natural fit | Weak point |
|---|---|---|
| Relational | Data with many, evolving many-to-many relationships; ad hoc query needs | Object-relational impedance mismatch; rigid schema changes |
| Document | Self-contained, tree-shaped records read/written as a whole (profiles, content) | Weak/no joins; denormalization creates update anomalies |
| Graph | Deeply interconnected data queried via relationships (social, fraud, recommendations) | Awkward for simple tabular/aggregate reporting |

## Takeaways

- Don't pick a data model out of habit — pick it based on the *shape of your access patterns*: how deeply nested are your records, and how many-to-many are the relationships you'll actually query?
- Schema-on-read isn't "no schema," it's "schema enforced by the reader instead of the writer" — the flexibility has to go somewhere, and it goes into more careful application code.
- Prefer declarative query languages whenever you can — they decouple your query's *meaning* from its *execution strategy*, which is what lets the database evolve underneath you for free.
