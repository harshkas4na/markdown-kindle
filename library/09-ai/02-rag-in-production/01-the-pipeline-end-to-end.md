# The Pipeline End to End

**Fast overview:** Before optimising anything it helps to have the whole thing in one file, small enough to read in a minute. This chapter builds a complete RAG pipeline with no framework, names every stage's contract, and then points at exactly where each later chapter plugs in. Building it once without a framework is not a detour — it is what makes you able to answer "what does LangChain actually give you" with something specific.

## The minimal version

```python
import numpy as np, sqlite3, json
from openai import OpenAI

client = OpenAI()
EMBED = "text-embedding-3-small"
CHAT  = "gpt-4o-mini"

# ---------- index time ----------
def chunk(text, size=800, overlap=120):
    words, out, i = text.split(), [], 0
    while i < len(words):
        out.append(" ".join(words[i:i+size]))
        i += size - overlap
    return out

def embed(texts):
    r = client.embeddings.create(model=EMBED, input=texts)
    return [np.array(d.embedding, dtype=np.float32) for d in r.data]

def index(docs, db):
    for doc in docs:                       # doc = {"id","source","text"}
        chunks = chunk(doc["text"])
        vecs   = embed(chunks)
        for n, (c, v) in enumerate(zip(chunks, vecs)):
            db.execute(
                "INSERT INTO chunks (doc_id, source, ord, text, vec) VALUES (?,?,?,?,?)",
                (doc["id"], doc["source"], n, c, v.tobytes()))
    db.commit()

# ---------- query time ----------
def search(query, db, k=5):
    qv = embed([query])[0]
    qv /= np.linalg.norm(qv)
    rows = db.execute("SELECT doc_id, source, ord, text, vec FROM chunks").fetchall()
    scored = []
    for doc_id, source, ord_, text, blob in rows:
        v = np.frombuffer(blob, dtype=np.float32)
        scored.append((float(qv @ (v / np.linalg.norm(v))), doc_id, source, ord_, text))
    scored.sort(reverse=True)
    return scored[:k]

PROMPT = """Answer the question using only the documents below.
If they do not contain the answer, reply exactly: NOT_FOUND

<documents>
{docs}
</documents>

Question: {q}

Answer using only the documents above, and cite the ids you used."""

def answer(query, db):
    hits = search(query, db)
    docs = "\n\n".join(
        f'<document id="{i}" source="{s}">\n{t}\n</document>'
        for i, (_, _, s, _, t) in enumerate(hits))
    r = client.chat.completions.create(
        model=CHAT, temperature=0,
        messages=[{"role": "user",
                   "content": PROMPT.format(docs=docs, q=query)}])
    return r.choices[0].message.content, hits
```

That is a working RAG system. It is also wrong in about nine ways, and every one of them is a later chapter.

## The contracts, stage by stage

Naming each stage's input, output and failure mode is worth doing explicitly, because in an interview the fluent version of this list *is* the answer to "walk me through a RAG system".

**1. Ingest.** Source → raw text plus metadata. Fails by producing structurally destroyed text (Chapter 2). The linear-scan `search` above also cannot survive a real corpus, which is Chapter 5.

**2. Clean.** Raw text → normalised text. Strip navigation, headers, footers, boilerplate. Skipping this is why every chunk in some corpora is 20% cookie banner and all of them look similar to each other.

**3. Chunk.** Document → list of chunks with position metadata. The naive word-split above ignores sentence and section boundaries, which is Chapter 3.

**4. Embed.** Chunks → vectors. The code silently assumes the model's input limit exceeds the chunk size, which it may not (Chapter 4). It also does not record which model produced the vectors, which is the migration bug from Book 01.

**5. Store.** Vectors plus text plus metadata → an index supporting filtered nearest-neighbour search. Chapters 5 and 6.

**6. Transform query.** Raw query → one or more search queries. The code uses the raw query, which breaks on conversational follow-ups ("what about the second one?") and on queries phrased unlike the corpus. Chapter 9.

**7. Search.** Query → candidate chunks. Vector only here; hybrid is Chapter 7.

**8. Rerank.** Candidates → reordered, truncated. Absent above. Chapter 8, and the single most reliable quality win available.

**9. Assemble.** Chunks → prompt. The code dumps five chunks in similarity order with no token budgeting and no attention to position. Chapter 10.

**10. Generate.** Prompt → answer plus citations. This part is nearly right: temperature 0, tagged documents, an explicit escape token, citations requested.

**11. Post-process.** Verify citations resolve, check faithfulness, decide whether to show the answer at all. Absent. Chapters 10 and 11.

## What to fix first, and why not to fix it all

The temptation on reading that list is to build all eleven properly. Resist it, for a reason that is itself the lesson: **you cannot tell which stage is hurting you until you measure.** On one corpus, parsing is 80% of the problem and reranking adds nothing. On another, parsing is trivial and reranking is transformative.

So the order of work is:

1. Get the minimal pipeline running end to end on real data. A day.
2. **Write forty question/answer pairs by hand**, and for each, record which chunk should have been retrieved. An afternoon.
3. Measure recall@5 on the naive system. Write the number down.
4. Change one thing. Measure. Keep or revert.

Step 2 is the one people skip, and skipping it is what turns steps 3 and 4 into a year of vibes.

## The framework question

Every stage above has a framework abstraction. LangChain has `DocumentLoader`, `TextSplitter`, `Embeddings`, `VectorStore`, `Retriever`, `ContextualCompressionRetriever`. LlamaIndex has an even richer version aimed specifically at this pipeline.

The honest position, worth being able to argue both sides of:

**What frameworks genuinely give you:** a large catalogue of loaders and connectors that would each take a day to write; standardised interfaces so swapping a vector store is a line rather than a refactor; and implementations of patterns you would otherwise get subtly wrong the first time.

**What they cost you:** the pipeline becomes hard to see. When retrieval is bad, you need to inspect what came out of the retriever, in what order, with what scores, and how it was rendered into the prompt. Abstractions that hide that are actively harmful in exactly the moment you need them most. They also add dependency weight and version churn, and they change fast enough that code written a year ago often does not run.

**A defensible default:** own the pipeline, use libraries for the parts that are genuinely commoditised — a parser, a tokeniser, a vector client, a reranker — and keep the orchestration in your own code where you can print it. For a small team this loses very little and keeps the debugging path short. It is also the position that matches what the JobOps dossiers describe as the real difficulty of these jobs: reliability and measurement, not assembly.

Whatever you choose, **be able to say why**, because "we use LangChain" with no reasoning behind it is a weaker answer than either alternative held deliberately.

## The thing to log from day one

Every request should produce a trace containing: the raw query, the transformed query, the retrieved chunk ids with scores in order, the reranked order, the exact assembled prompt, the model and version, and the answer. Without this you cannot execute the debugging procedure from Book 01 Chapter 10, and you will spend your time guessing.

This is thirty lines of work at the start and unbuildable later once traffic exists and the questions become urgent.

*Connect the dot:* the trace described here is the input to the eval harness in Chapter 11, and to the observability chapter in Book 06. It is the same artifact serving three purposes, which is why it is worth over-investing in early.

Next: ingestion and parsing, where more RAG projects quietly die than anywhere else.
