# Personal Kindle — a markdown reading library

This repo is a personal, Kindle-style e-reader. All content lives as plain markdown
files under `library/`, and a build script compiles everything into **one
self-contained `index.html`** (no server, no dependencies) that works offline, on
phones, and via GitHub Pages.

**The core idea (Next.js-style folder routing):** the folder structure *is* the
library structure. You never configure anything — you drop folders and `.md` files
into `library/` in the shape described below, re-run the build, and the book shows
up on the shelf with its own cover, table of contents, and reading progress.

## Quick start

```bash
python3 tools/build-reader.py   # rebuild index.html from library/
open index.html                 # or serve it, or push to GitHub Pages
```

That is the entire workflow. There are no other build steps or dependencies
(Python 3 stdlib only).

## How content is structured (READ THIS BEFORE ADDING ANYTHING)

```
library/
├── 01-hookathon/                    ← 1st-level folder = a SECTION (a shelf)
│   ├── section.json                 ← optional: {"title": "Hookathon — Uniswap v4"}
│   ├── 01-research/                 ← 2nd-level folder = a BOOK
│   │   ├── book.json                ← optional: {"title", "author", "description"}
│   │   ├── 00-START-HERE.md         ← .md files = CHAPTERS, ordered by filename
│   │   └── 01-....md
│   └── 03-hook-directory/
│       ├── 00-README.md
│       └── categories/              ← 3rd-level+ folder = a PART (TOC group heading)
│           └── mev-lvr-protection.md
└── 02-books/
    └── show-your-work/              ← the demo book — copy this pattern
        ├── book.json
        ├── 00-about-these-notes.md
        └── 01-you-dont-have-to-be-a-genius.md … 10-stick-around.md
```

### The rules

| Level | Meaning | Notes |
|---|---|---|
| `library/<folder>/` | **Section** — a shelf heading on the home screen | Title from `section.json` `"title"`, else prettified folder name |
| `library/<section>/<folder>/` | **Book** — one cover on the shelf | Metadata from `book.json`, else prettified folder name, no author |
| `.md` files inside a book | **Chapters** — natural-sorted by filename | Title = first `# H1` in the file, else prettified filename |
| Folders inside a book | **Parts** — group headings inside the book's TOC | e.g. `categories/` renders as a "Categories" heading; nesting deeper joins names with " / " |
| Loose `.md` directly in a section | A **one-chapter book** of its own | Handy for standalone notes/articles |

- **Ordering** is natural sort of names: use a numeric prefix (`01-`, `02-`, … also
  works for section/book folders) to control order. The prefix is stripped from
  display titles (`03-defi-trends-2026.md` → "Defi Trends 2026" if it had no H1).
- **Every chapter file should start with a `# Title` line** — that becomes its
  display name everywhere.
- `book.json` schema (all keys optional):
  `{"title": "...", "author": "...", "description": "one paragraph shown on the book's TOC page"}`
- Loose `.md` files at `library/` root are ignored (a warning is printed).
- Non-`.md` files and dot-files are ignored, so images/json can live alongside.

### Adding a new book (recipe for agents)

1. Pick (or create) a section folder under `library/`.
2. Create a book folder inside it; add `book.json` with title/author/description.
3. Add chapters as `NN-slug.md` files, each starting with a `# Chapter Title` H1.
   Optional: group chapters into part subfolders.
4. Run `python3 tools/build-reader.py` and confirm the printed
   section/book/chapter counts.
5. Never edit `index.html` by hand — it is generated output and any edit will be
   overwritten by the next build.

## Where the code lives

Only two source files matter:

### `tools/build-reader.py` — the compiler (~170 lines)

Walks `library/`, applies the routing rules above, and injects two JSON blobs into
the template, replacing these placeholders:

- `__LIB_DATA__` → sections → books (with `chapters` as indices into the flat list)
- `__CHAPTER_DATA__` → flat chapter list `{id, file, book, part, num, title, md}`;
  `id` is the repo-relative file path and is also the **localStorage progress key**
  and the **URL hash**, so renaming a file resets that chapter's reading progress.

Key functions: `natural_key` (sort), `prettify` (name → title), `title_of`
(H1 extraction), `collect_book_chapters` (recursive walk, builds part labels),
`build` (assembles everything, writes `index.html`).

### `tools/reader-template.html` — the entire reader app (single file: CSS + HTML + JS)

Top-to-bottom map:

| Block | What it does |
|---|---|
| `<style>` themes | Light/sepia/dark via CSS variables on `html[data-theme]` |
| `<style>` home/toc/reader/md/bars/panel | Shelf grid + covers, TOC list, paginated reader, markdown styles, toolbar chrome, Aa settings panel |
| `#home`, `#toc`, `#reader` divs | The three views; exactly one visible at a time (`showView`) |
| `mdToHtml` + helpers | Tiny built-in markdown renderer (headings, bold/italic, code, tables, lists, quotes). No external libs — keep it that way |
| `store` / `S` / `progress` / `last` | localStorage state under `hkr.*` keys: settings, per-chapter `{pct}` progress, last-read chapter |
| **Routing** (`nav`, `route`, `showView`) | Hash-based: `""` = shelves, `#b/<bookId>` = book TOC, `#c/<chapterId>` = reader. Browser/phone back button works between views |
| `renderHome` / `coverHtml` | Shelf view; covers are deterministic gradients hashed from the book title |
| `renderToc` | Book page: hero, description, Start/Continue button, chapter list grouped by parts, per-chapter % |
| Reader core (`renderChapter`, `paginate`, `goTo…`, `next/prev`) | CSS-columns pagination, swipe/tap/keys/wheel, scroll mode, progress save/restore. Chapter prev/next is **constrained to the current book** |
| Aa panel + events | Font/size/spacing/margins/theme/page-turn/layout settings |

### Everything else

- `index.html` — **generated**; never hand-edit (see above).
- `library/` — all content (structure above).
- Reading progress lives in the *browser's* localStorage, not in this repo —
  clearing site data or switching devices resets it.

## Reader UI cheat-sheet

- **Home** → tap a cover → **book TOC** → tap a chapter → **reader**.
- In the reader: tap center = toolbars, tap/swipe edges = turn page,
  `←/→`/space = pages, `T` = theme, `+/-` = font size, `Esc`/☰ = back to TOC.
- "Continue reading" card on Home jumps to the last-read chapter across all books.

## Note on book content & copyright

`library/02-books/show-your-work/` contains **original chapter-by-chapter study
notes** on Austin Kleon's *Show Your Work!* — summaries in our own words, not the
book's text. When adding "real books," follow the same rule: notes/summaries of
copyrighted works, or full text only for public-domain/openly-licensed material.
