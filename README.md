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
python3 tools/build-reader.py --serve --lan   # same, reachable from your phone
                                              # on the local network

python3 tools/new-book.py books "Deep Work" --author "Cal Newport" \
    --chapters "Intro,Focus,Rituals"    # scaffold a new book with chapter stubs

python3 tools/import-book.py --serve    # import UI on :8081 — paste text or drop
                                        # files, preview chapters, add to library

cp mybook.epub public/epub/             # drop an .epub you own in the folder...
python3 tools/epub-import.py            # ...and it becomes a book in the reader
```

That is the entire workflow. There are no other build steps or dependencies
(Python 3 stdlib only). A GitHub Action (`.github/workflows/build.yml`) also
rebuilds `index.html` on every push to `main` and commits it back if it drifted,
so GitHub Pages never serves a stale build.

The build prints `!` warnings for content the reader can't display well:
chapters missing a `# Title` H1, duplicate `NN-` prefixes in one folder,
missing image files, lists nested deeper than one level, and an oversized
`index.html` (>8 MB). Images in the markdown *do* render; footnotes render as
superscripts. The Python EPUB path still drops images — import on the Home
screen (or a phone) keeps small figures.

**Figures, diagrams and callouts** (for books that teach):

```markdown
![alt text](img/diagram.svg "Figure 2. This becomes the caption")

> [!STORY] The dabbawala
> A labelled box. Types: STORY, PROJECT ("In our project"), GOTCHA, NOTE,
> TIP, TRY, WHY, LINKS (anything else shows its own name).
```

- An image alone on its line is a figure; its quoted title becomes the caption
  (captions are not read aloud). Keep images in a folder next to the chapters
  (e.g. `img/`); folders with no `.md` are ignored as assets.
- **Tap a figure** for a full-screen view; tap again or ＋ for 2× and 3×, ✕ or
  Esc to close. Diagrams stay readable at phone width.
- Diagrams work best as SVG with their own light background, so they read the
  same in every theme. `library/13-ethglobal-mumbai/01-0g-explained/img/` has
  examples.
- A callout's label is a paragraph, so Listen and studio narration read it
  ("Story: The dabbawala") before the body.
- **Save whole library for offline** caches every chapter's figures, not only
  the ones on screen.

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

## Importing content (paste or upload)

`tools/import-book.py` turns raw text into a properly structured book — no manual
file-splitting or renaming:

```bash
python3 tools/import-book.py --serve                # web UI at http://127.0.0.1:8081
python3 tools/import-book.py books "Deep Work" dump.md            # one bulk file
python3 tools/import-book.py books "Deep Work" ch1.md ch2.md ...  # one file per chapter
cat dump.md | python3 tools/import-book.py books "Deep Work"      # pipe / paste (stdin)
```

Extra flags: `--author "..."`, `--description "..."`, `--dry-run` (print the
detected chapter plan without writing anything), `--no-build`. The web UI does the
same thing with a paste box, drag-and-drop multi-file upload, and a live chapter
preview; it also serves the reader at `/index.html` so you can check the result
immediately.

**How chapters are detected** (priority order):

1. **Explicit markers** — a line `<!-- chapter: The Title -->` starts a new chapter
   (`=== chapter: The Title ===` also works). A line `<!-- part: Part Name -->`
   groups the chapters after it into a part subfolder. Markers inside ``` code
   fences are ignored.
2. **H1 fallback** — no markers but two or more `# Heading` lines: the text is
   split on H1s.
3. **Single chapter** — otherwise the whole text becomes a one-chapter book.

Multiple files import in natural filename order (`ch1, ch2, … ch10`), one chapter
per file — and any file that itself contains markers/H1s is split further, so a
mix of bulk and per-chapter files works. Content before the first chapter becomes
a "Front Matter" chapter, and every written chapter gets a `# Title` H1 if it
lacks one.

## Importing EPUBs

There are two paths. The recommended one on a phone is the in-browser importer.

**On your iPhone or any browser (no computer, no upload):** open the live reader
→ **📥 Import a book** → pick a DRM-free `.epub` from Files or iCloud Drive.
Conversion happens on the device and the book appears on the **On this device**
shelf (IndexedDB). Apple Books / Kindle store files are DRM-locked and will
fail with a clear error. This book stays on that browser — use **Back up my
data** before switching phones, or **Export as Markdown** on the book's TOC
page to drop it into the repo later.

Android / desktop PWAs can also **Share → Library** or drag-drop onto the
shelves. iOS has no Web Share Target, so the Files picker is the path.

**On a computer (writes into `library/` for every device):** drop the `.epub`
into `public/epub/` and run the converter:

```bash
python3 tools/epub-import.py            # convert everything new in public/epub/
python3 tools/epub-import.py --watch    # keep watching: converts on drop
python3 tools/epub-import.py --dry-run  # print the chapter plan, write nothing
python3 tools/epub-import.py book.epub  # convert one file, wherever it lives
```

For each file it reads the epub's own metadata (title, author, description) and
spine order, splits it into chapters using the table of contents — including
books that ship as one giant XHTML file whose chapters are only `#anchor`
targets — converts each chapter to markdown, writes
`library/NN-epub/NN-<book>/` with a `book.json`, then rebuilds `index.html`.
Cover pages, blank pages and nav documents are dropped (`--min-words`, default
30), and so are images, which the reader does not render.

Converted books land on their own **EPUB** shelf (`library/NN-epub/`, created on
first import), so a drop is never skipped because you already have that title
somewhere else in the library — it just gets its own folder. Use
`--section <name>` to file them elsewhere (fuzzy-matched, created if missing).

Other flags: `--force` (import a file again), `--interval <secs>` (poll rate for
`--watch`), `--dir <path>` (watch a different folder), `--no-build`.

Imported files — and files that failed to convert — are remembered in
`public/epub/.imported.json`, so re-running only picks up what is new and
`--watch` never retries the same file in a loop. The `.epub` files and that log
are gitignored; only the converted markdown in `library/` is committed.

To convert a *single chapter* out of an epub instead, `tools/epub-to-markdown.py`
takes one XHTML item and writes one markdown file.

**Formatting raw text with an LLM:** `tools/FORMAT-PROMPT.md` is a ready-made
prompt (also behind the 🪄 box in the import UI, with a copy button). Paste it
into any AI model together with your raw text — book dump, article, lecture
notes — and it returns the text restructured with the chapter/part markers above.
If the model's output gets cut off, say "continue" and simply concatenate the
replies before uploading; the markers make the seams harmless.

## Where the code lives

Only two source files matter for the reader app itself:

### `tools/build-reader.py` — the compiler

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
| Text-to-speech (`ttsBuildWords`, `ttsSpeakFrom`, `ttsSpokenWord`, `#ttsBar`) | Wraps the chapter's words in `<span class="tts-w">` (skipping `pre`), speaks sentence-aligned utterances via `speechSynthesis`, tracks the spoken word via `onboundary` (with a timer-estimated fallback for voices that fire none) to drive the highlight + tracker + page/scroll follow. Pause = cancel + remember word (engine `pause()` is unreliable). `ttsSpokenWord` is the pronunciation layer: user dictionary (`hkr.ttsDict`) → expansions → acronym spell-out. Voice picker ranks `getVoices()` quality-first. Click any word to jump the voice there |

### Everything else

- `index.html` — **generated**; never hand-edit (see above).
- `library/` — all content (structure above).
- Content helpers in `tools/`: `new-book.py` (scaffold stubs), `import-book.py` +
  `importer.html` + `FORMAT-PROMPT.md` (import pasted/uploaded text — see
  "Importing content"), `epub-import.py` (convert whole EPUBs dropped in
  `public/epub/` — see "Importing EPUBs"), `epub-to-markdown.py` (one chapter of
  an EPUB you own).
- Reading progress lives in the *browser's* localStorage, not in this repo —
  clearing site data or switching devices resets it.

## Reader UI cheat-sheet

- **Home** → tap a cover → **book TOC** → tap a chapter → **reader**.
- In the reader: tap center = toolbars, tap/swipe edges = turn page (the page
  follows the finger), `←/→`/space = pages, `T` = theme, `+/-` = font size,
  `B`/⚑ = bookmark this page, `Esc`/‹ = back to wherever you came from.
- Changing chapter: swipe past the last/first page (page mode), swipe sideways
  or pull up past the end (scroll mode), the **Up next** card under every
  chapter's last line, or tap the title in the top bar for the chapter list.
  Chapter-to-chapter moves replace the history entry, so ‹ always leaves the
  reader in one step. Library ↔ book ↔ reader slide like an iOS navigation
  stack (View Transitions); on book/search/notebook/stats pages, swipe in from
  the left edge to go back.
- "Continue reading" card on Home jumps to the last-read chapter across all books;
  each book's TOC additionally remembers its own last-read chapter.
- **Search** (box on Home, or press `/`): full-text search across every chapter,
  with matched snippets; tap a result to open the chapter.
- **Quick open** (`⌘K`/`Ctrl-K`, or the ⌘ button on Home/TOC/reader): a command
  palette that jumps straight to any book or chapter by title from any view —
  arrow keys + Enter to pick. Empty query shows "Continue reading", the open
  chapter's section headings (¶ — jump within the chapter), then all books.
  Owner-only: it never appears on `#s/...` share links or the lock screen.
- **Reading stats**: forward reading progress is tallied per day (words read),
  shown on Home as a 🔥 day-streak and "min today"; each book records the date
  you finished it on its TOC page. Included in backups.
- **Vocabulary book**: every word/short phrase you look up with "Meaning" (`D`)
  is logged with its AI definition — the 🔤 Vocabulary button at the bottom of
  Home reviews and prunes the list.
- **Export highlights**: the ⬇ button on a book's Highlights page downloads all
  of its highlights + notes as a Markdown file (for Obsidian etc.).
- **Highlights & notes**: select text in the reader → tap "Highlight" or "＋ Note".
  Tap an existing highlight to view/edit its note or remove it. Each book's TOC
  links to a per-book "Highlights" page listing them all.
- **Bookmarks**: the ⚑ button (or `B`) marks the current page; bookmarks are
  listed on the book's TOC and jump back to the exact spot.
- **Listen (read aloud)**: the 🔊 button starts **Kokoro Heart**, the same neural
  voice the screen tutor uses — not the robotic iPhone voice. The model downloads
  once (~170 MB, `uint8`) into this browser and then works offline. The page is
  served cross-origin isolated by `sw.js` so the voice runs on several threads —
  on the first visit it runs on one, from the second visit on it's ~3× faster. Bella, Nicole, Michael,
  Emma and George are in the same download. The phone's own voices stay in the
  picker under "This device" (☁ marks online system voices). Books tagged with a
  non-English language start on the device voice, because Kokoro here is English.
  A bottom bar gives play/pause, a tracker, speed (0.5×–2.5×) and the voice
  picker. The word being spoken is highlighted and the page follows it; tap a
  word to jump there. Sentences are spoken whole; several chunks are made ahead
  of the one playing, and with the bar open the rest of the chapter and the start
  of the next one are made in the background. Made audio is kept in Cache Storage
  (`kokoro-audio-v1`, oldest chapters dropped past 600 MB), so seeking back,
  listening again and the next chapter are instant. Kokoro extras in the bar:
  **⬇ Save chapter** (make it all now — gapless and offline; when saved it becomes
  **Share audio**, one .wav for Files/AirDrop/any player), **Quotes** (read
  “dialogue” of 4+ words in a second voice), **🎙 Ask** (ask out loud; Ask AI's
  answer is spoken, then reading continues), **⟲ Recap** (also automatic when a
  book is picked up again after 6+ hours, if Ask AI is set up) and **🚗 Car mode**
  (big buttons, screen kept awake, spoken commands: pause, play, back, next,
  faster, slower, recap, next chapter — anything else is asked as a question). Code blocks are skipped. A pronunciation layer
  speaks acronyms letter-by-letter ("UHI" → "U H I"), expands e.g./i.e./etc.,
  and the 🗣 button adds custom fixes (e.g. "Uniswap" → "you-nee-swap") to a
  per-browser dictionary that's included in backups. Reading continues into the
  next chapter. A ⏾ **sleep timer** (5/15/30/60 min) pauses the voice, and
  lock-screen controls use the audio element (this is real audio, so iOS can
  keep it going with the screen off — the old Web Speech path could not).
  **About voices** explains the one-time download and, if you prefer them, how
  to install a Premium system voice.
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
- **Ask AI** (✦ in the reader, or select text → ✦ Ask / `A`, meanings via `D`):
  a chat panel answers questions about the selection or the chapter using any
  OpenAI-compatible API. ⚙ picks a **provider** — Hugging Face, Google Gemini,
  Groq, OpenRouter (free `:free` models incl. Grok and Kimi), Cerebras, xAI,
  Mistral, Together, a local **Ollama**/**LM Studio** server, or a custom base
  URL — plus a model from a curated list, from the provider's live `/models`
  list (↻), or typed by hand. Keys are stored per provider in this browser only,
  so several can be set up at once: with "auto-switch" on, a rate-limited or
  failed provider silently rolls over to the next one that is configured, and
  the answer notes which one served it. The local options are wired up but
  nothing is installed yet — see [TODO.md](TODO.md) for the local-model and
  fine-tuning setup.
  The prompt is grounded in your position in the book, your
  highlights in the chapter, and a keyword-retrieved excerpt from other chapters
  of the same book ("ask the book"). With no selection the chips offer
  chapter-level actions (Summarize / Key takeaways / Quiz me / Connect to
  earlier). Every answer has "📌 Save as note", which files it into the book's
  highlights; conversations are kept per chapter while the app is open.
- **Backup**: "⬇ Back up my data" at the bottom of Home downloads progress,
  highlights, bookmarks, vocabulary, reading stats and settings as JSON;
  "⬆ Restore backup" imports it — use this before clearing site data or when
  switching devices.

## Mobile UI system

The phone layout follows two references: **Kindle's paper-first reading surface**
(one warm accent, covers as the only colour, progress everywhere, chrome that
disappears) and **Apple Books' thumb-zone navigation** (bottom tabs, cover
detail, reading goals). The important pieces:

- **Library** — 3-up cover grid on iPhone (more on iPad/desktop) with an amber
  reading bar on every cover; a large *Continue reading* card with a Resume
  pill; All / Reading / Unread / Finished filter pills; horizontal
  "Currently reading" shelf.
- **Bottom tabs** — Library · Search · Notebook · Stats. Fixed above the home
  indicator, 48px targets, hidden in the reader and on share links so a shared
  book stays clean.
- **Book page** — a full-bleed blurred cover hero, title/author/section,
  book-progress rail, one primary *Continue reading* action, and a grouped
  chapter list with per-chapter progress and part headings.
- **Reader** — chrome-free page by default. Tap the edges (or swipe) to turn,
  centre-tap for the bars. The top bar keeps only Back, the chapter title (tap
  for the chapter list), Listen, Aa and a `⋯` menu on phones; Library,
  Bookmark, Ask AI, Share and theme live in that menu. The Listen bar is a mini
  player (⏮ ▶ ⏭ + position) — swipe it up or tap ⌃ for speed, voice and the
  rest. A thin
  amber rail and "page · min left" whisper stay at the bottom, and a one-time
  gesture tip appears on the first read.
- **Aa panel** — a true bottom sheet with a grabber, 44px controls and Kindle's
  six reading themes (Light, Sepia, Green, Gray, Dark, Black) as round swatches.
- **Search** — a dedicated full-screen search tab, plus the quick search box on
  the Library screen.
- **Notebook** — every highlight, bookmark and looked-up word in one place,
  grouped by book, with delete and jump-back.
- **Stats** — Apple Books-style daily goal ring ("N min today", adjustable
  1–240 min), streak, heatmap, finished books.
- **Foundations** — safe-area insets everywhere, 44pt minimum touch targets,
  16px inputs (no iOS zoom), `prefers-reduced-motion` respected, labelled
  controls, and system light/dark for chrome while the page theme stays
  independent.

## Offline mode (PWA)

The whole library is embedded inside `index.html`, so once the page has loaded it
already reads with no connection. The only thing that needs the network is
*opening the live-link URL itself* — so the build turns the site into a small PWA
that fixes exactly that:

- **`sw.js`** — a service worker (network-first, cache fallback; studio audio under
  `audio/` is cache-first and answers the phone's byte-range requests from the
  cached file). Online you always get fresh content; offline it serves the cached
  page. It's regenerated on every build and only runs over http(s) — a harmless
  no-op when you open `index.html` as a `file://`.
- **`manifest.webmanifest`** — makes the app installable ("Add to Home Screen")
  with an icon; also regenerated each build.

**How to use it:** open the live link once with internet. On the Home screen tap
**"Save whole library for offline"** — it caches the app and the pill flips to
**"✓ Available offline"**. After that the same URL opens and every book reads with
no connection (e.g. on a plane). Tap the pill again any time to refresh the cached
copy. On phones you can also "Add to Home Screen" to launch it like a native app.

That saves text and figures, not studio audio (a few MB a chapter). A book with a
studio audiobook gets **⬇ Save audio** on its contents page, next to Listen: it
downloads every chapter's `.m4a` and timing map into the same offline cache, two
at a time, and flips to **✓ Audio saved**. Audio links carry `?v=<hash+bytes>`, so a
re-recorded chapter is fetched fresh, and Save audio clears the book's older copies.

When you rebuild after changing content, online visitors get the fresh page
automatically (network-first). If you ever change `sw.js` itself, bump
`OFFLINE_CACHE` in `tools/build-reader.py` so stale caches are discarded on the
next visit.

All three files (`index.html`, `sw.js`, `manifest.webmanifest`) must be deployed
together at the same path (GitHub Pages serves the repo root, so this is automatic).

## Archiving and deleting books from the phone

The ⋯ button on a book's page opens its menu:

- **Archive on this device** hides the book from the shelves (an *Archived* filter
  chip appears). Nothing is deleted; unarchive from the same menu.
- **Archive in the repo** moves the book's folder (and its studio audio / podcast)
  to `library-archive/`, `audio-archive/`, `podcast-archive/` in one commit. The
  build ignores those folders, so the book disappears from the site once the
  GitHub Action has rebuilt it (a minute or two). Move the folder back to bring
  it back.
- **Delete from the library** removes those files from the repo for good (git
  history still has them).
- Imported books get **Remove from device** instead of the repo actions.

The repo actions need a GitHub token, asked for the first time and kept in the
browser only: a *fine-grained personal access token* scoped to this repo with
**Contents: read and write**. The commit is made with the Git Data API directly
from the page, so it works from the phone with no server.

Two more habit helpers on the Home screen: the *Continue reading* card has a
🎧 button that opens the chapter straight into Listen, and when the app is
launched from the home screen it opens on the page you were reading (toggle
*Open where I left off* in the tools row).

## Studio narration (the good audiobook voice)

Listen's live voices (Kokoro Heart, the phone's own voices) are made *on the
phone*, sentence by sentence, which is why they stall: an iPhone's CPU makes
Kokoro about as fast as it speaks, and nothing bigger fits in a browser at all.
Studio narration moves the work to the Mac. `tools/narrate/narrate.py` renders a
book's chapters with a large narration model (Qwen3-TTS 1.7B or Chatterbox
Turbo, via Apple's MLX) and writes, next to `index.html`:

```
audio/<section>-<book>/NN-<slug>.m4a    the chapter — AAC mono, ~0.4 MB a minute
audio/<section>-<book>/NN-<slug>.json   timing map: which words play when
audio/<section>-<book>/index.json       what was made from which text (skips unchanged chapters)
```

The build embeds a chapter → audio table in `index.html`; in the reader a
**Studio** entry appears at the top of the Voice menu and is the default for
any chapter that has it. The phone then only *plays*: it starts at once, skipping
or dragging the seek bar is instant, highlights follow the voice from the timing
map, and the service worker keeps heard chapters (plus the next one) for offline.
Chapters that have no studio audio yet are read live by Heart as before.

```bash
# once
cd tools/narrate && uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install mlx-audio soundfile && cd ../..          # also: ffmpeg, Chrome, tools/podcast `npm install`

python3 tools/build-reader.py                            # the plan is read from the built reader
tools/narrate/.venv/bin/python tools/narrate/narrate.py 02-books/show-your-work --voice ryan
tools/narrate/.venv/bin/python tools/narrate/narrate.py 02-books/show-your-work --chapters 1-3
python3 tools/build-reader.py && git add audio index.html && git commit && git push
```

Voices: `ryan`, `aiden` (Qwen3-TTS presets with a narrator style line), `nora`
(a Qwen3-TTS VoiceDesign description), `chatterbox`. Add your own in `VOICES` at
the top of `narrate.py`. A book can opt in for good with `"narrate": true` (and
`"narrateVoice": "ryan"`) in its `book.json`; then plain `narrate.py` does every
opted-in book. Rendering runs at roughly real time on an M3 (a 20-minute chapter
takes 20–30 minutes), so narrate a book overnight and only re-run for chapters you
change — unchanged ones are skipped by text hash. `tools/narrate/bench.py` renders
one passage in every candidate voice to pick by ear.

**Hosting:** audio is committed to the repo and served by GitHub Pages like
everything else. Pages wants the site under 1 GB and single files under 100 MB;
at ~25 MB per hour of speech that is roughly 40 hours of narration. Past that,
move `audio/` to Cloudflare R2 (10 GB free, no egress fees) and point the URLs
in `NARRATED` at it — the player only needs a URL that supports range requests.

## Podcast feeds (public)

A book can also be published as a podcast — every chapter an episode, read by
the same Kokoro voice as Listen, followable in Apple Podcasts (lock screen,
CarPlay, downloads) or any podcast app.

```bash
# once: npm deps for the generator (and ffmpeg: brew install ffmpeg)
cd tools/podcast && npm install && cd ../..

# opt a book in: "podcast": true in its book.json (optional "podcastVoice": "af_bella")
node tools/podcast/podcast.mjs                 # every opted-in book (only changed chapters are re-made)
node tools/podcast/podcast.mjs 01-hookathon/01-research   # just one
python3 tools/build-reader.py                  # adds the 🎙 Podcast button to the book page
git add podcast library && git commit && git push
```

The feed lands at `podcast/<section>-<book>/feed.xml` on GitHub Pages
(`https://<user>.github.io/<repo>/podcast/…/feed.xml`; set `PODCAST_BASE` to
override). Episodes are 48 kbps mono MP3 (~0.35 MB a minute), committed to the
repo. Words come from the built reader itself (headless Chrome runs Listen's
`ttsPlanFor`), so an episode says exactly what Listen says.

**Feeds are public.** Only opt in books you have the right to publish as audio —
your own notes. Never the bought/EPUB books in `02-books/` or `07-epub/`.

## Note on book content & copyright

`library/02-books/show-your-work/` contains **original chapter-by-chapter study
notes** on Austin Kleon's *Show Your Work!* — summaries in our own words, not the
book's text. When adding "real books," follow the same rule: notes/summaries of
copyrighted works, or full text only for public-domain/openly-licensed material.
