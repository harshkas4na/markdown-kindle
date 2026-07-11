# Personal Kindle — a markdown reading library

This repo is a personal, Kindle-style e-reader. All content lives as plain markdown
files under `library/`, and a build script compiles everything into **one
self-contained `index.html`** (no server, no dependencies) that works offline, on
phones, and via GitHub Pages. The build also emits two small PWA companions
(`sw.js` + `manifest.webmanifest`) so the live link can be **saved for offline
reading and installed to a home screen** — see "Offline mode" below.

**The core idea (Next.js-style folder routing):** the folder structure *is* the
library structure. You never configure anything — you drop folders and `.md` files
into `library/` in the shape described below, re-run the build, and the book shows
up on the shelf with its own cover, table of contents, and reading progress.

## Quick start

```bash
python3 tools/build-reader.py           # rebuild index.html from library/
open index.html                         # or serve it, or push to GitHub Pages

python3 tools/build-reader.py --serve   # dev mode: serve on :8080 and rebuild
                                        # automatically whenever library/ changes

python3 tools/new-book.py books "Deep Work" --author "Cal Newport" \
    --chapters "Intro,Focus,Rituals"    # scaffold a new book with chapter stubs
```

That is the entire workflow. There are no other build steps or dependencies
(Python 3 stdlib only). A GitHub Action (`.github/workflows/build.yml`) also
rebuilds `index.html` on every push to `main` and commits it back if it drifted,
so GitHub Pages never serves a stale build.

The build prints `!` warnings for content the reader can't display well:
chapters missing a `# Title` H1, duplicate `NN-` prefixes in one folder,
images/footnotes (unsupported), lists nested deeper than one level, and an
oversized `index.html` (>5 MB).

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
| **Routing** (`nav`, `route`, `showView`) | Hash-based: `""` = shelves, `#b/<bookId>` = book TOC, `#c/<chapterId>` = reader. Browser/phone back button works between views. Share routes: `#s/b/<bookId>` (book only), `#s/bc/<chapterId>` (chapter inside a shared book), `#s/c/<chapterId>` (single chapter only) — these lock the UI to that scope for recipients |
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
  `←/→`/space = pages, `T` = theme, `+/-` = font size, `B`/⚑ = bookmark this page,
  `Esc`/☰ = back to TOC.
- "Continue reading" card on Home jumps to the last-read chapter across all books;
  each book's TOC additionally remembers its own last-read chapter.
- **Search** (box on Home, or press `/`): full-text search across every chapter,
  with matched snippets; tap a result to open the chapter.
- **Highlights & notes**: select text in the reader → tap "Highlight" or "＋ Note".
  Tap an existing highlight to view/edit its note or remove it. Each book's TOC
  links to a per-book "Highlights" page listing them all.
- **Bookmarks**: the ⚑ button (or `B`) marks the current page; bookmarks are
  listed on the book's TOC and jump back to the exact spot.
- **TOC filter**: books with 10+ chapters get a filter box on their TOC page.
- **Sharing**: the ⤴ button on a book's TOC page copies a link that opens *just
  that book* (`#s/b/<bookId>`) — the recipient sees the book's TOC and chapters
  with no back button, no search, and no way to browse the rest of the library.
  The ⤴ button in the reader toolbar copies a link to *just that chapter*
  (`#s/c/<chapterId>`) — a single locked chapter with no TOC and no prev/next.
  Links only work from the live (GitHub Pages) URL, not a local `file://` open.
  Note this is a *view*, not access control: the shared page is the same public
  `index.html`, so the rest of the library is still in its source for anyone who
  looks — fine for sharing notes, not for secrets.
- **Backup**: "⬇ Back up my data" at the bottom of Home downloads progress,
  highlights, bookmarks and settings as JSON; "⬆ Restore backup" imports it —
  use this before clearing site data or when switching devices.

## Offline mode (PWA)

The whole library is embedded inside `index.html`, so once the page has loaded it
already reads with no connection. The only thing that needs the network is
*opening the live-link URL itself* — so the build turns the site into a small PWA
that fixes exactly that:

- **`sw.js`** — a service worker (network-first, cache fallback). Online you always
  get fresh content; offline it serves the cached page. It's regenerated on every
  build and only runs over http(s) — a harmless no-op when you open `index.html`
  as a `file://`.
- **`manifest.webmanifest`** — makes the app installable ("Add to Home Screen")
  with an icon; also regenerated each build.

**How to use it:** open the live link once with internet. On the Home screen tap
**"Save whole library for offline"** — it caches the app and the pill flips to
**"✓ Available offline"**. After that the same URL opens and every book reads with
no connection (e.g. on a plane). Tap the pill again any time to refresh the cached
copy. On phones you can also "Add to Home Screen" to launch it like a native app.

When you rebuild after changing content, online visitors get the fresh page
automatically (network-first). If you ever change `sw.js` itself, bump
`OFFLINE_CACHE` in `tools/build-reader.py` so stale caches are discarded on the
next visit.

All three files (`index.html`, `sw.js`, `manifest.webmanifest`) must be deployed
together at the same path (GitHub Pages serves the repo root, so this is automatic).

## Note on book content & copyright

`library/02-books/show-your-work/` contains **original chapter-by-chapter study
notes** on Austin Kleon's *Show Your Work!* — summaries in our own words, not the
book's text. When adding "real books," follow the same rule: notes/summaries of
copyrighted works, or full text only for public-domain/openly-licensed material.
