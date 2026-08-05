# Ingestion and Parsing

**Fast overview:** The least discussed stage and the most common cause of a RAG system that is mysteriously mediocre. Nothing downstream can recover information that parsing destroyed, and PDF in particular is a format designed for printing rather than for reading, which is why extracting meaning from it is genuinely hard rather than a solved library call. This chapter covers what breaks per format, the specific problem of tables, how to clean without deleting signal, and what metadata to attach while you still have it.

## Why this stage decides your ceiling

A retrieval system is a search over the text you extracted. If a table became a column of orphaned numbers, no embedding model, reranker or prompt will answer a question about that table. The information is gone.

The Patenova application in the corpus is the clean example: 60-page patent PDFs with claims, figures, citations and structured front matter. The hardest part of that product is not the LLM. It is turning those PDFs into text where a claim is still recognisably a claim.

So the first diagnostic on any RAG system you inherit is not to look at the prompt. It is to **print twenty random chunks and read them.** If they are unreadable to you, they are unreadable to the model, and you have found the problem in ten minutes.

## What breaks, by format

### PDF

PDF stores glyphs at coordinates. There is no paragraph, no reading order, no table, no heading — those are things a human infers from layout. Extraction is therefore inference, and it fails in specific ways:

- **Multi-column layouts** get read across columns, interleaving two sentences into nonsense.
- **Headers and footers** repeat into every page's text, so every chunk shares boilerplate and all chunks look similar.
- **Ligatures and hyphenation** produce `ﬁ` and words split across line breaks.
- **Tables** collapse, covered below.
- **Scanned PDFs** contain no text at all and need OCR, and nothing tells you which kind you have until you check.

Approaches, in ascending order of cost and quality: a fast text extractor (`pypdf`, `pdfplumber`) for clean digital PDFs; a layout-aware parser that models reading order and blocks; OCR (Tesseract, or a cloud document AI) for scans; and a vision-language model given the page image, which handles complex layouts and tables well and costs real money per page.

**The practical pattern** is a cascade: try fast extraction, detect failure (implausibly low character count, low dictionary-word ratio, no whitespace structure), escalate to the expensive path only for pages that fail. Most corpora are mostly fine, and the cascade means you pay for quality only where it is needed.

### HTML

Easier and still full of traps. The content is a small fraction of the document; navigation, footers, cookie banners, related-article sidebars and script tags are the rest. Include them and every chunk carries the same 200 tokens of noise, which both wastes context and pulls all your embeddings toward each other.

Use a content extractor (readability-style algorithms, `trafilatura`), convert to markdown to preserve heading structure, and keep the heading hierarchy as metadata. `<table>` converts to markdown tables cleanly, which is the one place HTML is much easier than PDF.

### Office documents

`.docx` is a zip of XML and is genuinely structured; headings, lists and tables survive if you use a real parser rather than dumping strings. `.pptx` is a set of disconnected text boxes with a reading order that may be visual rather than logical, and slide decks make terrible retrieval corpora because each slide is a fragment whose meaning lived in the speaker's mouth. `.xlsx` is not a document at all and should usually go into a database with an SQL tool rather than into a vector index.

### Code

Chunk on structural boundaries — function, class, module — not on line counts, using a real parser (tree-sitter is the standard answer). A chunk that starts mid-function is close to useless. Keep the file path, the language, and the enclosing symbol names as metadata, because those are what people actually search by.

### Email and chat

Threading matters more than content. Quoted reply chains duplicate the same text into every message, so a naive index has ten near-identical chunks of the original mail. Strip quoted sections, keep the thread id as metadata, and consider indexing the thread rather than the message.

## Tables, specifically

The single hardest sub-problem, and worth having an opinion on because it comes up in any document-heavy company.

A table's meaning lives in the relationship between a cell, its row header and its column header. Flatten it to text and that relationship is destroyed: `Q3 2025 4,120 3,880 240` means nothing.

Approaches that work:

- **Convert to markdown or HTML table syntax** and keep it intact in one chunk. Models read markdown tables well. This is the default answer.
- **Serialise row-wise into sentences**: "For Q3 2025, revenue was 4,120, costs were 3,880, and margin was 240." Verbose, and it embeds far better because each row becomes semantically complete text.
- **Keep the table out of the vector index entirely** and put it in a real database with a query tool. If the questions are analytical ("which quarter had the highest margin"), retrieval is the wrong mechanism and SQL is the right one. Recognising when a question is a query rather than a search is a genuinely senior instinct.
- **Never split a table across chunks.** If it is too big, repeat the header row in each piece.

## Cleaning without deleting signal

Do:

- Normalise whitespace and Unicode (NFKC), fix ligatures, rejoin hyphenated line breaks.
- Remove repeated headers/footers — detect them by finding lines that appear on most pages.
- Strip navigation and boilerplate from HTML.
- Drop empty and near-empty chunks.
- Deduplicate. Near-duplicate chunks waste index space and crowd out diversity in the top-k. Cheap detection: MinHash or a similarity threshold at index time.

Do not:

- Lowercase everything. Case carries signal for names, acronyms and code, and modern embedding models handle case fine.
- Strip stopwords or stem. This is advice from a pre-neural era; it damages embeddings and modern BM25 implementations handle it themselves.
- Remove punctuation. It carries structure.
- Strip numbers. Obviously, in any document that is about anything.

## Metadata is captured here or never

At parse time you know things you can never recover later. Capture them:

```python
{
  "doc_id": "patent-US1234567",
  "source_url": "...",
  "title": "...",
  "section": "Claims",         # heading hierarchy at this point
  "page": 42,
  "position": 17,              # ordinal chunk index in the document
  "created_at": "2024-06-01",
  "updated_at": "2026-02-11",
  "doc_type": "patent",
  "permissions": ["team:legal"],
  "token_count": 412,
  "embed_model": "text-embedding-3-large@2026-01",
  "parser": "layout-v2",
  "content_hash": "sha256:..."
}
```

Every field earns its place. `section` lets you prepend context to a chunk (Chapter 12) and filter by document part. `position` lets you fetch neighbouring chunks to expand a hit. `updated_at` lets you prefer recent material and detect staleness. `permissions` is the only way multi-tenancy works (Chapter 13). `token_count` makes context budgeting arithmetic. `embed_model` makes migration survivable. `content_hash` makes incremental re-indexing possible, so a document that did not change is not re-embedded.

The `content_hash` field in particular is the difference between a nightly re-index that costs money and hours, and one that processes only what changed. It is the same content-addressing idea as `lifelog`'s idempotency-by-content-key and git's object store, which is a nice thing to notice out loud if the conversation goes there.

## The parsing eval

Parsing deserves its own small evaluation, separate from retrieval:

- **Coverage:** what fraction of source documents parsed without error, and what fraction produced implausibly little text?
- **Structure retention:** on a sample of twenty documents, were headings, tables and lists preserved? Human-checked, once, per parser change.
- **Spot reading:** twenty random chunks, read by a person. This is not rigorous and it catches more real problems than anything else on this list.

Run this before believing any retrieval number, because a retrieval score computed over a mangled corpus is measuring the wrong thing precisely.

*Connect the dot:* the "print twenty random chunks and read them" diagnostic is the parsing-stage version of the debugging procedure in Book 01 Chapter 10. Check the input before blaming the model, at every stage.

Next: chunking, where the decision you make in one line caps everything downstream.
