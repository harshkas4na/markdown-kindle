# Freshness, Permissions and Multi-Tenancy

**Fast overview:** The demo indexes a folder once. The product has documents changing hourly, users who may see some of them and not others, and customers whose data must never touch each other. This chapter covers incremental indexing, deletion (which is harder than it sounds), the recency problem, and the permission model — including the failure that is a security incident rather than a quality bug.

## Incremental indexing

Re-embedding an entire corpus nightly is affordable at small scale and stops being affordable exactly when the corpus becomes valuable. The correct shape is content-addressed and incremental.

```python
def sync(source_docs, store):
    seen = set()
    for doc in source_docs:
        seen.add(doc.id)
        h = sha256(doc.text)
        if store.doc_hash(doc.id) == h:
            continue                              # unchanged, skip entirely
        chunks = chunk(doc)
        for c in chunks:
            c.hash = sha256(c.text)
        existing = {c.hash: c for c in store.chunks_for(doc.id)}
        new = [c for c in chunks if c.hash not in existing]
        store.upsert(embed_chunks(new))           # embed only what changed
        store.delete_chunks(set(existing) - {c.hash for c in chunks})
        store.set_doc_hash(doc.id, h)
    store.delete_docs(store.all_doc_ids() - seen) # gone from source → gone from index
```

Three ideas doing the work:

1. **Document-level hash** short-circuits unchanged documents for the cost of a hash.
2. **Chunk-level hashes** mean an edit to page 40 of a 200-page document re-embeds two chunks, not four hundred.
3. **The final line** handles deletion at source, which is the step everyone forgets and which is how deleted documents keep getting cited for months.

This is the same content-addressed, idempotent design as `lifelog`'s content-key idempotency and git's object store. If that connection comes up in an interview it is worth making, because it reframes "I have built a RAG pipeline" as "I understand why content addressing makes sync tractable".

**Change detection at the source** matters as much as the diffing: webhooks where available, an `updated_at` watermark where not, and a full reconciliation pass on a slow schedule to catch what the incremental path missed. The reconciliation pass is not optional — every incremental sync drifts eventually.

## Deletion, which is genuinely hard

Deleting a document has four consequences, and most systems handle one:

1. **Remove the chunks** from the store. Straightforward.
2. **Remove them from the ANN index.** Most HNSW implementations tombstone rather than remove, so the vectors still occupy memory and can still be traversed until compaction. Under heavy churn, schedule rebuilds.
3. **Invalidate caches.** A semantic cache (Book 06) may hold an answer derived from the deleted document, and will keep serving it.
4. **Handle the legal case.** Under a deletion request the content must actually be gone, including from caches, backups, logs and eval datasets. Traces containing chunk text are a place personal data hides and nobody looks.

For a system handling personal or regulated data, write down where a given piece of text can end up. It is usually five places, and the answer to "have you deleted it" is only as good as that list.

## Recency and superseded content

The most common quality complaint in a mature RAG system is not a hallucination. It is a correct answer from an outdated document.

Embeddings have no notion of time. A 2023 policy and the 2026 policy that replaced it are near-identical in embedding space and the older one may well rank higher.

Mitigations, in order of effort:

- **Recency boosting at rerank time** (Chapter 8). A decay factor on the score. Cheap, effective, blunt.
- **Explicit status metadata** — `current`, `superseded`, `draft` — filtered at query time. Requires the source system to carry the status, which it usually does and nobody plumbed through.
- **Supersession links.** A document that replaces another records it, so retrieval can substitute the current version. Best quality, most ingestion work.
- **Show the date in the source tag** (Chapter 10) so the model can say "as of the 2024 policy" and the user can spot the problem.
- **Just delete the old ones.** Often correct and often blocked by a compliance requirement to retain them, which is why filtering exists.

For genuinely time-sensitive corpora, add temporal examples to the golden set: questions whose correct answer changed, where retrieving the old document is a scored failure. Without those, no metric will ever notice this problem.

## Permissions: the failure that is a security incident

If your retrieval layer can return a chunk the user is not allowed to see, you have not built a quality problem. You have built a data leak with a natural-language interface, and the LLM will happily paraphrase the confidential document so the leak is not even greppable in your logs.

**The rules:**

**1. Filter at the database, never after.** Post-filtering in application code means the vectors were read and, worse, that a bug in the filter is invisible. Push the predicate into the query.

**2. Filter before generation, never after.** Retrieving broadly and then asking the model to ignore unauthorised content is not access control. The content is in the context; the model will use it, and prompt injection can extract it directly.

**3. Prefer partitioning to filtering for hard boundaries.** Separate indexes, collections or namespaces per tenant. The isolation becomes a routing decision rather than a predicate that must be correct on every code path. This is the single most important architectural choice in a multi-tenant retrieval system.

**4. Model permissions as they are actually granted.** Copying an ACL onto each chunk works for simple cases and drifts the moment a group membership changes. The robust pattern is to store the *grant* (`group:legal`, `role:admin`) on the chunk and resolve the user's set of grants at query time:

```sql
WHERE tenant_id = $tenant
  AND acl && $user_grants::text[]     -- array overlap
```

**5. Re-check at read time.** Permissions change between indexing and querying. If the source system is authoritative, verify the final selected chunks against it before generation. A few extra milliseconds against the cost of the alternative.

**6. Test it adversarially.** Put permission cases in the eval set: a user who should get `NOT_FOUND` for a document they cannot see, and a query crafted to surface it. Assert the *negative*. This is the `learnings.md` lesson again, in the place where it matters most: a suite of cases that should pass proves nothing about the cases that should fail.

## Multi-tenancy checklist

| Concern | The answer |
|---|---|
| Isolation | Namespace or index per tenant where volume allows |
| Noisy neighbours | Per-tenant rate limits and cost caps |
| Cost attribution | Tenant id on every trace and token count |
| Per-tenant tuning | Config per tenant (k, thresholds) if the corpora differ a lot |
| Deletion / offboarding | Drop the namespace, not a filtered delete |
| Cache keys | **Tenant id in every cache key**, including semantic caches |
| Eval | Per-tenant slices if tenants differ materially |

The cache-key row is the one that produces the worst incident. A semantic cache keyed only on query text will happily serve tenant A's answer to tenant B's identical question. Put the tenant in the key, and put a test in the suite that asserts a cross-tenant hit does not happen.

## Operational health

Things worth alerting on, none of which are AI-specific and all of which are how a retrieval system actually fails in production:

- **Index/source drift** — document count in the index versus the source, checked on a schedule.
- **Indexing lag** — time from source update to searchable.
- **Failed parse rate**, trending. A source system changing its export format shows up here first.
- **NOT_FOUND rate** trending up — corpus gap, retrieval regression, or an index that stopped updating.
- **Chunk count per document distribution** — a sudden change means a parser regressed.
- **Embedding model version distribution across the index** — anything other than a single value during a migration means the migration stalled.

That last one is worth a query on a dashboard. A half-migrated index is a silent quality disaster and nothing else will tell you.

*Connect the dot:* every metric here is a *systems* metric rather than a model metric, and that is the point. Most of what makes a RAG product good or bad in month six is ordinary backend engineering — sync, deletion, permissions, staleness — which is a good thing for someone with real backend and smart-contract reps to hear.

Next: the closing chapter, on what this book earned and what it did not.
