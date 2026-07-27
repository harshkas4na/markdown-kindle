#!/usr/bin/env python3
"""Turn any .epub dropped into public/epub/ into a book in the reader.

Drop-folder companion to epub-to-markdown.py (which converts one chapter at a
time). This one reads a whole .epub you own — its metadata, spine order and
table of contents — converts every chapter to the library's markdown format,
writes a proper book folder under library/, and rebuilds index.html.

    python3 tools/epub-import.py              # convert whatever is new in public/epub/
    python3 tools/epub-import.py --watch      # keep watching the folder (Ctrl-C to stop)
    python3 tools/epub-import.py --dry-run    # print the chapter plan, write nothing
    python3 tools/epub-import.py book.epub    # convert one specific file

Options:
    --section <name>    library section to file books under (fuzzy, created if
                        missing; default "epub" — its own shelf, so a title you
                        already have elsewhere is imported anyway, not skipped)
    --dir <path>        drop folder to scan (default public/epub)
    --interval <secs>   poll interval for --watch (default 3)
    --min-words <n>     skip spine documents shorter than this (default 30) —
                        drops covers, blank pages and nav documents
    --force             re-import even if the epub was imported before
    --no-build          skip rebuilding index.html

Every drop is filed under its own "EPUB" section and gets its own folder — the
same title existing elsewhere in the library is never a reason to skip it.
Already-imported files (and files that failed) are remembered in
public/epub/.imported.json, keyed by name + size + mtime, so re-running is safe,
only picks up what is new, and --watch never retries the same file in a loop.
Use --force to import a file again.

Nothing is fetched from outside the .epub. Images are dropped because the
reader does not render them (see tools/build-reader.py).
"""
import html
import importlib.util
import json
import os
import posixpath
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
DROP_DIR = os.path.join(ROOT, "public", "epub")
STATE_NAME = ".imported.json"
# Converted epubs get their own shelf, so drops never collide with hand-made books.
DEFAULT_SECTION = "epub"
DEFAULT_SECTION_TITLE = "EPUB"

XHTML_TYPES = ("application/xhtml+xml", "text/html")
NS = {
    "c": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "xhtml": "http://www.w3.org/1999/xhtml",
}


def _load(name, filename):
    """Import a sibling tool whose filename isn't a valid module name."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


e2m = _load("epub_to_markdown", "epub-to-markdown.py")
imp = _load("import_book", "import-book.py")


class EpubError(Exception):
    """A user-facing problem with one .epub (unreadable, DRM-locked, empty)."""


# ---------------------------------------------------------------- epub reading

def _text(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def _tag(el):
    return el.tag.split("}")[-1]


def opf_path(z):
    root = ET.fromstring(z.read("META-INF/container.xml"))
    for rf in root.iter():
        if _tag(rf) == "rootfile" and rf.get("full-path"):
            return rf.get("full-path")
    raise EpubError("no rootfile in META-INF/container.xml")


def resolve(base_dir, href):
    """href relative to the OPF -> path inside the zip, fragment dropped."""
    href = urllib.parse.unquote(href.split("#")[0])
    return posixpath.normpath(posixpath.join(base_dir, href)).lstrip("./")


def read_package(z):
    """-> (meta, base_dir, manifest{id: (path, media_type, properties)}, spine[ids], toc_id)."""
    opf = opf_path(z)
    base = posixpath.dirname(opf)
    pkg = ET.fromstring(z.read(opf))

    meta, manifest, spine, toc_id = {}, {}, [], None
    for node in pkg:
        kind = _tag(node)
        if kind == "metadata":
            for m in node:
                t = _tag(m)
                if t in ("title", "creator", "description") and t not in meta:
                    meta[t] = _text(m)
        elif kind == "manifest":
            for it in node:
                if _tag(it) == "item" and it.get("href"):
                    manifest[it.get("id")] = (resolve(base, it.get("href")),
                                              it.get("media-type", ""),
                                              it.get("properties", ""))
        elif kind == "spine":
            toc_id = node.get("toc")
            for ref in node:
                if _tag(ref) == "itemref" and ref.get("idref"):
                    spine.append(ref.get("idref"))
    return meta, base, manifest, spine, toc_id


def split_href(base_dir, href):
    """href -> (zip path, fragment)."""
    path, _, frag = href.partition("#")
    return resolve(base_dir, path), urllib.parse.unquote(frag)


def toc_entries(z, manifest, toc_id):
    """-> {zip path: [(fragment, title)]} from the EPUB 3 nav doc or the EPUB 2 NCX.

    Fragments matter: plenty of books ship as one giant XHTML file whose
    chapters are only `#anchor` targets in the TOC.
    """
    seen, out = set(), {}

    def add(base, href, label):
        path, frag = split_href(base, href)
        label = label.strip()
        if not label or (path, frag) in seen:
            return
        seen.add((path, frag))
        out.setdefault(path, []).append((frag, label))

    nav = next((p for p, _, props in manifest.values() if "nav" in (props or "").split()), None)
    ncx = manifest.get(toc_id, (None,))[0]
    if not ncx:
        ncx = next((p for p, mt, _ in manifest.values()
                    if mt == "application/x-dtbncx+xml" or p.endswith(".ncx")), None)

    for toc in (nav, ncx):
        if not toc:
            continue
        try:
            doc = ET.fromstring(z.read(toc))
        except (KeyError, ET.ParseError, OSError):
            continue
        base = posixpath.dirname(toc)
        if toc == nav:
            for a in doc.iter():
                if _tag(a) == "a" and a.get("href"):
                    add(base, a.get("href"), _text(a))
        else:
            for point in doc.iter():
                if _tag(point) != "navPoint":
                    continue
                label = next((_text(n) for n in point.iter() if _tag(n) == "text"), "")
                src = next((n.get("src") for n in point.iter()
                            if _tag(n) == "content" and n.get("src")), None)
                if src:
                    add(base, src, label)
    return out


def body_of(xhtml):
    m = re.search(r"<body[^>]*>(.*)</body>", xhtml, re.S)
    return m.group(1) if m else xhtml


def anchor_split(xhtml, entries):
    """Cut one XHTML document at the TOC anchors inside it.

    entries = [(fragment, title)]. -> [(title|None, html)] in document order;
    a leading piece before the first anchor gets title None.
    """
    body = body_of(xhtml)
    cuts = []
    for frag, title in entries:
        if not frag:
            continue
        m = re.search(r"""<[^>]*\b(?:id|name)\s*=\s*["']%s["']""" % re.escape(frag), body)
        if m:
            start = body.rfind("<", 0, m.end())
            cuts.append((start if start >= 0 else m.start(), title))
    cuts.sort()
    if not cuts:
        return [(None, body)]

    pieces = []
    if cuts[0][0] > 0:
        pieces.append((None, body[:cuts[0][0]]))
    for i, (pos, title) in enumerate(cuts):
        end = cuts[i + 1][0] if i + 1 < len(cuts) else len(body)
        pieces.append((title, body[pos:end]))
    return pieces


HEADING_RE = re.compile(r"^#{1,3}\s+(.*\S)\s*$")


def first_heading(md):
    for ln in md.splitlines():
        m = HEADING_RE.match(ln)
        if m:
            return m.group(1)
    return None


def plain(text):
    """Publisher blurbs are often HTML — flatten to one line of plain text."""
    s = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def first_line_title(md):
    """Fallback title for an untitled piece: its opening line, if it reads like one."""
    for ln in md.splitlines():
        s = ln.strip().strip("*_# ").strip()
        if not s:
            continue
        return s if 3 <= len(s) <= 70 and not s.endswith((".", ",", ";", ":")) else None
    return None


def words(text):
    return len(re.findall(r"\S+", text))


def strip_heading(md, title):
    """Drop a leading heading that only repeats the chapter title we add back."""
    lines = md.splitlines()
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        m = HEADING_RE.match(ln)
        if m and m.group(1).strip().lower() == title.strip().lower():
            return "\n".join(lines[i + 1:]).strip()
        break
    return md


def read_epub(path, min_words=30):
    """-> (meta, [{'title', 'md'}]) — one entry per detected chapter."""
    with zipfile.ZipFile(path) as z:
        meta, _, manifest, spine, toc_id = read_package(z)
        toc = toc_entries(z, manifest, toc_id)

        docs = []
        for idref in spine:
            item = manifest.get(idref)
            if not item:
                continue
            zip_path, media, props = item
            if media not in XHTML_TYPES or "nav" in (props or "").split():
                continue
            try:
                raw = z.read(zip_path).decode("utf-8", "replace")
            except KeyError:
                continue
            entries = toc.get(zip_path, [])
            whole_doc_title = next((t for f, t in entries if not f), None)
            stem = posixpath.splitext(posixpath.basename(zip_path))[0]

            for piece_title, html in anchor_split(raw, entries):
                md = e2m.convert(html, None, None).strip()
                if words(md) < min_words:
                    continue  # cover, blank page, copyright stub...
                title = (piece_title or whole_doc_title or first_heading(md)
                         or first_line_title(md) or imp.prettify(stem))
                docs.append({"title": title.strip(), "md": md})

    if not docs:
        raise EpubError("no readable chapters found (is it DRM-protected?)")

    # Consecutive spine documents under one TOC entry are one chapter.
    chapters = []
    for d in docs:
        if chapters and chapters[-1]["title"].lower() == d["title"].lower():
            chapters[-1]["md"] += "\n\n" + strip_heading(d["md"], d["title"])
        else:
            chapters.append(dict(d))

    for i, c in enumerate(chapters, 1):
        body = strip_heading(c["md"], c["title"])
        c["md"] = f"# {c['title']}\n\n{body}".rstrip() + "\n"
        c["part"] = ""
        c["n"] = i
    return meta, chapters


# ---------------------------------------------------------------- import state

def state_path(drop_dir):
    return os.path.join(drop_dir, STATE_NAME)


def load_state(drop_dir):
    try:
        with open(state_path(drop_dir), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_state(drop_dir, state):
    with open(state_path(drop_dir), "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)


def fingerprint(path):
    st = os.stat(path)
    return f"{os.path.basename(path)}|{st.st_size}|{int(st.st_mtime)}"


def epubs_in(drop_dir):
    if not os.path.isdir(drop_dir):
        return []
    return [os.path.join(drop_dir, n) for n in sorted(os.listdir(drop_dir), key=imp.natural_key)
            if n.lower().endswith(".epub") and not n.startswith(".")]


# ---------------------------------------------------------------- importing

def import_epub(path, section_q=DEFAULT_SECTION, min_words=30, dry_run=False):
    """Convert one .epub into a library book. -> dict describing what was written.

    Every drop gets its own folder — a title that already exists elsewhere in the
    library is not treated as a clash, it just lands beside it.
    """
    meta, chapters = read_epub(path, min_words)
    stem = os.path.splitext(os.path.basename(path))[0]
    title = plain(meta.get("title")) or imp.prettify(stem)
    plan = imp.plan_files(chapters)

    if dry_run:
        return {"title": title, "author": plain(meta.get("creator")), "plan": plan, "dry_run": True}

    section = imp.find_section(section_q) or imp.create_section(DEFAULT_SECTION_TITLE
                                                               if section_q == DEFAULT_SECTION
                                                               else section_q.strip().title())
    folder = imp.write_book(section, title, plan,
                            author=plain(meta.get("creator")),
                            description=plain(meta.get("description")))
    return {"title": title, "author": plain(meta.get("creator")), "plan": plan,
            "book_id": f"{section}/{folder}", "folder": f"library/{section}/{folder}"}


def print_plan(result):
    print(f'  "{result["title"]}"' + (f' — {result["author"]}' if result["author"] else ""))
    for rel, e in result["plan"]:
        print(f"    {rel:<48} {words(e['md'])} words")


def scan_once(drop_dir, section, min_words, force, dry_run, build, quiet=False, settle=0):
    """Import every not-yet-imported .epub in drop_dir. -> number imported."""
    files = epubs_in(drop_dir)
    if not files and not quiet:
        print(f"No .epub files in {os.path.relpath(drop_dir, ROOT)}/ — drop one in and re-run.")
    state = load_state(drop_dir)
    done = 0
    for path in files:
        # While watching, let a file finish being copied in before reading it.
        if settle and time.time() - os.stat(path).st_mtime < settle:
            continue
        fp = fingerprint(path)
        if not force and not dry_run and state.get(fp):
            continue
        name = os.path.basename(path)
        print(f"\n{name}")
        try:
            result = import_epub(path, section, min_words, dry_run)
        except (EpubError, imp.ImportError_, zipfile.BadZipFile, ET.ParseError, OSError) as e:
            why = str(e) if isinstance(e, (EpubError, imp.ImportError_)) \
                else f"unreadable epub: {type(e).__name__}: {e}"
            print(f"  ! skipped — {why}")
            if not dry_run:  # remember the failure so --watch stops retrying it
                state[fp] = {"error": why, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_state(drop_dir, state)
            continue
        print_plan(result)
        if dry_run:
            print("  (dry run — nothing written)")
            continue
        print(f"  -> {result['folder']}/  ({len(result['plan'])} chapters)")
        state[fp] = {"book": result["book_id"], "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_state(drop_dir, state)
        done += 1

    if done and build:
        print("\n" + imp.run_build())
    return done


def watch(drop_dir, interval, **kw):
    os.makedirs(drop_dir, exist_ok=True)
    sys.stdout.reconfigure(line_buffering=True)  # so `--watch | tee log` stays live
    rel = os.path.relpath(drop_dir, ROOT)
    print(f"Watching {rel}/ for new .epub files — drop one in. Ctrl-C to stop.")
    try:
        while True:
            scan_once(drop_dir, quiet=True, settle=max(interval, 2), **kw)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


# ---------------------------------------------------------------- CLI

BOOL_FLAGS = {"watch", "dry-run", "no-build", "force"}


def parse_args(argv):
    args, opts, i = [], {}, 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            key = a[2:]
            if key in BOOL_FLAGS:
                opts[key], i = True, i + 1
            elif i + 1 < len(argv):
                opts[key], i = argv[i + 1], i + 2
            else:
                sys.exit(f"missing value for {a}")
        else:
            args.append(a)
            i += 1
    return args, opts


def main():
    argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help"):
        sys.exit(__doc__)
    args, opts = parse_args(argv)

    drop_dir = os.path.abspath(opts.get("dir", DROP_DIR))
    if drop_dir == DROP_DIR:
        os.makedirs(drop_dir, exist_ok=True)
    common = {
        "section": opts.get("section", DEFAULT_SECTION),
        "min_words": int(opts.get("min-words", 30)),
        "force": bool(opts.get("force")),
        "dry_run": bool(opts.get("dry-run")),
        "build": not opts.get("no-build"),
    }

    if args:  # explicit files: convert exactly these, ignoring the drop state
        state = load_state(drop_dir) if os.path.isdir(drop_dir) else {}
        for p in args:
            if not os.path.isfile(p):
                sys.exit(f"file not found: {p}")
            print(f"\n{os.path.basename(p)}")
            try:
                result = import_epub(p, common["section"], common["min_words"],
                                     common["dry_run"])
            except (EpubError, imp.ImportError_) as e:
                sys.exit(f"  ! {e}")
            print_plan(result)
            if common["dry_run"]:
                print("  (dry run — nothing written)")
                continue
            print(f"  -> {result['folder']}/  ({len(result['plan'])} chapters)")
            if os.path.dirname(os.path.abspath(p)) == drop_dir:
                state[fingerprint(p)] = {"book": result["book_id"],
                                         "at": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_state(drop_dir, state)
        if common["build"] and not common["dry_run"]:
            print("\n" + imp.run_build())
        return

    if opts.get("watch"):
        watch(drop_dir, float(opts.get("interval", 3)), **common)
    else:
        scan_once(drop_dir, **common)


if __name__ == "__main__":
    main()
