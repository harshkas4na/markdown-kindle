# pgvector and the Alternatives

**Fast overview:** "Which vector database" is asked far more often than it deserves and the honest answer is usually "the one you already run". This chapter makes that case concretely: what pgvector gives you, where it genuinely runs out, what the dedicated stores actually buy, and how to keep the choice reversible. It matters here for a specific reason too — one company in the corpus names pgvector directly, and it is the answer most early-stage teams should give.

## Start with the boring answer

If you already run Postgres, start with **pgvector**. Not as a compromise, as a default. The reasons are structural rather than sentimental:

- **One system to operate.** No second datastore to back up, monitor, secure, upgrade and pay for.
- **Transactional consistency.** The chunk row and its vector are written in the same transaction. With a separate vector store, a partial failure leaves the two out of sync, and reconciling them is a job somebody has to build.
- **Joins and real filters.** `WHERE tenant_id = $1 AND created_at > $2 AND status = 'published'` is a database's core competence, and metadata filtering is the thing that is awkward in most dedicated vector stores.
- **Everything else Postgres has.** Full-text search for the BM25 half of hybrid retrieval (Chapter 7), row-level security for multi-tenancy, and the entire operational ecosystem.

That last point deserves emphasis. **Postgres gives you both halves of hybrid search in one query**, which removes an entire distributed-systems problem. That is a stronger argument than any benchmark.

## Using it

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
  id          bigserial PRIMARY KEY,
  doc_id      text NOT NULL,
  tenant_id   text NOT NULL,
  section     text,
  ord         int,
  token_count int,
  updated_at  timestamptz NOT NULL DEFAULT now(),
  content     text NOT NULL,
  tsv         tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  embedding   vector(1536) NOT NULL,
  embed_model text NOT NULL
);

CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);
CREATE INDEX ON chunks USING gin (tsv);
CREATE INDEX ON chunks (tenant_id, doc_id);
```

Query, with the runtime recall dial set explicitly:

```sql
SET LOCAL hnsw.ef_search = 80;

SELECT id, content, 1 - (embedding <=> $1) AS score
FROM chunks
WHERE tenant_id = $2
ORDER BY embedding <=> $1
LIMIT 50;
```

Notes that matter:

- `<=>` is cosine distance, `<->` L2, `<#>` negative inner product. **The operator class in the index must match the operator in the query** or the index is not used and you silently fall back to a sequential scan. Check with `EXPLAIN`.
- `hnsw.ef_search` is set per session or per transaction. This is Chapter 5's dial, and it is the first thing to tune.
- `embed_model` is stored per row so a migration is survivable.
- The generated `tsv` column keeps the keyword index in sync automatically, which is exactly the kind of correctness-by-construction worth preferring over an application-managed field.

## Where pgvector runs out

Be specific rather than vague, because the vague version sounds like an excuse:

1. **Scale.** Tens of millions of vectors with a low-latency requirement starts to strain a single Postgres instance, mostly on memory for the HNSW index. The usual answers — read replicas, partitioning by tenant — work but add complexity.
2. **Index build time and memory.** Building HNSW over many millions of rows is slow and memory-hungry, and it competes with your OLTP workload on the same box. Running it on a replica or a separate instance is the standard mitigation.
3. **No built-in advanced features.** Native sparse-vector hybrid scoring, learned re-ranking, multi-vector (ColBERT-style late interaction) retrieval. Some exist via other extensions; the dedicated stores ship them.
4. **Write throughput on the index.** Very high-churn corpora degrade HNSW and need periodic rebuilds, which is more disruptive inside your primary database than beside it.

If you hit these, migrate. Hitting them is a good problem and most products never do.

## What the dedicated stores buy

Broadly, three categories:

**Managed, serverless, API-first** (Pinecone and similar). You do not operate anything, scaling is somebody else's problem, and filtering and namespaces are first-class. You pay for it, your data lives elsewhere, and you have a network hop and a vendor.

**Open-source, self-hosted or managed** (Qdrant, Weaviate, Milvus). Rich filtering, hybrid search, quantisation options, horizontal scaling. You operate a distributed system, or pay someone to.

**Libraries rather than databases** (FAISS, and its relatives). Not a service — an index you embed in your own process. Extremely fast, no server, and you own persistence, updates, filtering and distribution yourself. Correct for batch and research workloads; usually wrong as an application backend unless you enjoy rebuilding a database.

**Search engines with vector support** (Elasticsearch/OpenSearch). If you already run one for keyword search, its vector support may be the shortest path to hybrid retrieval, and its BM25 implementation is more mature than most.

## The comparison that actually matters

Not benchmarks. These:

| Question | Why it decides things |
|---|---|
| Do we already operate it? | The largest hidden cost is operational, not licence |
| Can it filter well at our selectivity? | This breaks more systems than raw search speed |
| Does it do hybrid natively, or must we fuse in the app? | Determines how much code you own |
| What happens on delete/update? | Churn-heavy corpora punish tombstoning stores |
| Can we run the golden set against it in an afternoon? | If evaluation is hard, adoption is a leap of faith |
| What does migrating *away* look like? | Ask before you enter, not after |

Raw queries-per-second is the number vendors compete on and it is rarely the constraint in an application where an LLM call downstream costs 800ms.

## Keeping the choice reversible

Put a thin interface between your pipeline and the store. Not a heavyweight abstraction — six methods:

```python
class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk]) -> None: ...
    def delete(self, doc_id: str) -> None: ...
    def search(self, vec, k: int, filters: dict) -> list[Hit]: ...
    def keyword(self, text: str, k: int, filters: dict) -> list[Hit]: ...
    def get(self, ids: list[str]) -> list[Chunk]: ...
    def count(self, filters: dict) -> int: ...
```

This is enough to swap implementations and small enough not to become its own maintenance problem. It also makes the golden-set comparison trivial: run the same eval against two implementations of the same protocol.

The failure to avoid is the opposite extreme — a framework's vector-store abstraction so general that you cannot express your store's actual filtering, so you end up post-filtering in Python and wondering why recall is bad.

## The interview answer

When asked "which vector database would you use", the answer that lands is a decision procedure, not a product name:

> Whatever we already run, until it stops working. If we have Postgres, pgvector, because I get transactional consistency between the chunk and the vector, real metadata filtering, and full-text search for the BM25 half of hybrid retrieval in the same query, and one system to operate instead of two. I would move to a dedicated store when the index stops fitting comfortably in memory or when index builds start interfering with the OLTP workload, and I would keep a six-method interface in front of it so the move is a week rather than a quarter.

*Connect the dot:* the `tsv` column in the schema above is the setup for the next chapter. Hybrid search is not an extra system; on Postgres it is a second index and one query.

Next: hybrid search, and why BM25 is not legacy technology.
