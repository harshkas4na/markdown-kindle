# Talking to Databases

**Fast overview:** `database/sql` is another case of the standard library defining an interface and letting third parties implement it — your application code depends only on `database/sql`, never on a specific driver. This chapter covers the parts of that package that are genuinely easy to get subtly wrong (lazy connections, silent row-iteration errors, connection pool tuning) and closes with the real, ongoing debate between hand-written SQL, code-generated SQL, and full ORMs.

## An interface, not a database

*Connect the dot:* this is the same shape as Chapter 24's `net/http` — the standard library owns the interface (`database/sql`), and third-party packages (`lib/pq` or `jackc/pgx` for Postgres, `go-sql-driver/mysql` for MySQL) implement `driver.Driver` underneath it. Your application code imports `database/sql` and, purely for its side effect of registering itself, the driver package — and then never calls the driver directly again:

```go
import (
    "database/sql"
    _ "github.com/lib/pq"
)

db, err := sql.Open("postgres", dsn)
```

That underscore import matters: `lib/pq`'s `init()` function registers itself with `database/sql` under the name `"postgres"`, and nothing else about the package is used directly. Swap the driver, and — so long as you're not relying on database-specific SQL syntax — the rest of your code doesn't change.

## sql.Open is lazy — and that trips people up

`sql.Open` does **not** connect to the database. It validates the DSN's format and returns a `*sql.DB` (which is really a connection *pool*, not a single connection) — but the pool is empty until something actually needs a connection. This means a typo'd password or an unreachable host produces **no error at all** from `sql.Open`; the error only surfaces on the first real query, which is a common source of confused bug reports ("the app started fine, but every request 500s"). If you want to fail fast at startup instead — almost always what you want for a service — call `db.Ping()` (or `db.PingContext(ctx)`) explicitly right after `Open`:

```go
db, err := sql.Open("postgres", dsn)
if err != nil {
    return fmt.Errorf("invalid dsn: %w", err)
}
if err := db.PingContext(ctx); err != nil {
    return fmt.Errorf("database unreachable: %w", err)
}
```

## Tuning the pool

`*sql.DB` manages a pool of underlying connections for you, and three settings are worth setting explicitly rather than trusting the defaults (which include an *unbounded* max-open-connections count — fine for a script, dangerous for a service under real load, where an unbounded pool can exhaust the database's own connection limit during a traffic spike):

| Method | What it bounds | Why you'd tune it |
|---|---|---|
| `SetMaxOpenConns(n)` | Total connections (in use + idle) | Cap concurrent load on the database; match it to the database's own connection limit divided across your service's replicas |
| `SetMaxIdleConns(n)` | Idle connections kept warm between queries | Too low and you pay reconnect overhead constantly; too high wastes database-side resources for connections doing nothing |
| `SetConnMaxLifetime(d)` | Maximum age of any connection before it's closed and replaced | Plays nicely with load balancers or database proxies that silently drop long-lived connections; also spreads reconnects out instead of a thundering herd if the database is ever restarted |

None of these have a universally correct value — they depend on your database's own limits and your service's traffic shape — but leaving all three at their zero-value defaults on a production service is a common, avoidable mistake.

## Querying: Query, QueryRow, Exec — and the two idioms that prevent silent bugs

```go
rows, err := db.QueryContext(ctx, "SELECT id, title FROM posts WHERE author = $1", authorID)
if err != nil {
    return nil, err
}
defer rows.Close()

var posts []Post
for rows.Next() {
    var p Post
    if err := rows.Scan(&p.ID, &p.Title); err != nil {
        return nil, err
    }
    posts = append(posts, p)
}
if err := rows.Err(); err != nil {
    return nil, err
}
return posts, nil
```

Two idioms here are load-bearing, not stylistic. **Always `defer rows.Close()`** — forgetting it leaks the underlying connection back into a "still in use" state instead of returning it to the pool, and enough leaked connections eventually exhausts `MaxOpenConns` and starts hanging every future query. **Always check `rows.Err()` after the loop, not just each `Scan`'s error.** `rows.Next()` returns `false` both when it's genuinely done *and* when an error occurred while streaming the result set from the database — the loop can't tell you which, and it's `rows.Err()`, called only after the loop exits, that reveals whether the iteration actually finished cleanly. Skipping this check is how a connection dropped halfway through a large result set silently becomes "we got 40 of the 200 rows and nobody noticed."

`QueryRow` is the single-row convenience form — its returned error is deferred until you call `.Scan()`, so `sql.ErrNoRows` (the sentinel for "no matching row," *connect the dot* to Chapter 17's sentinel-error pattern) shows up there. `Exec` is for statements that don't return rows (`INSERT`, `UPDATE`, `DELETE`), returning a `Result` you can query for `LastInsertId()` or `RowsAffected()`.

## Parameterized queries are not optional

Every example above uses a placeholder (`$1` for Postgres, `?` for MySQL/SQLite) rather than building the query string by concatenation. This is not a style preference — string-concatenating user input into SQL is the textbook SQL injection vulnerability, and `database/sql`'s placeholder mechanism sends the query text and the parameter values to the database *separately*, so a malicious value like `'; DROP TABLE posts; --` is treated as inert data, never as SQL syntax. There is no legitimate reason to build a query by `fmt.Sprintf`-ing a user-supplied value into it, and any code review that finds one should treat it as a security bug, not a nitpick.

## The ORM debate

Go's ecosystem has never settled on one answer here, and it's worth understanding the real tradeoff rather than picking a side by reputation.

**Hand-written `database/sql`**, as above, is fully explicit — you see exactly what SQL runs, with no surprise queries generated behind your back — but every query is boilerplate: write the SQL, write the struct, write the `Scan` call, keep all three in sync by hand as the schema evolves.

**`sqlc`** takes a different path that fits Go's broader taste for generated code over runtime magic: you write real `.sql` files (schema and queries), and it generates fully type-safe Go functions and structs from them at build time. *Connect the dot:* this is Chapter 23's code-generation philosophy applied directly — "generate real, readable, debuggable code once, don't do it dynamically at runtime" — and it's the option most idiomatic-Go-leaning teams reach for when hand-writing every `Scan` call starts to hurt.

**Full ORMs** like GORM trade that explicitness for convenience: struct tags describe your schema, and the library generates SQL for you at runtime, including relationship loading, migrations, and query building via method chaining. The real cost is that the SQL actually executed is one layer removed from what you wrote, which can hide N+1 query patterns and make performance debugging harder — but for CRUD-heavy applications where query complexity is genuinely low, that cost is often worth the productivity.

There's no universally correct choice; the honest guidance is that `sqlc` or hand-written SQL wins when query correctness and performance transparency matter most (which is most services with real traffic), and a full ORM wins when development speed on straightforward CRUD matters more than that transparency.

## Migrations, briefly

Schema changes need to be versioned and applied in order, the same way code changes are versioned by git — `golang-migrate` and `goose` are the two dominant tools, both working from numbered up/down `.sql` files applied against a tracked schema-version table, run either as a startup step or as an explicit deploy-pipeline stage before the new binary goes live.

## What's next

The service can now talk to a database safely. Chapter 28 covers the other common way Go services talk to *each other* — RPC and gRPC — for the internal, service-to-service traffic where JSON-over-HTTP starts to show its limits.
