#!/usr/bin/env python3
"""Import pasted text or uploaded files as a new, properly structured book.

Two ways to use it:

    python3 tools/import-book.py --serve [port]
        Local web UI (default http://127.0.0.1:8081): paste text or drop
        .md/.txt files, preview the detected chapters, click "Add to library".
        The reader is served at /index.html on the same port.

    python3 tools/import-book.py <section> "<Book Title>" [files...] [options]
        CLI. <section> matches like new-book.py (fuzzy, created if missing).
        With no files (or --paste) the text is read from stdin, so you can
        pipe or paste directly. Options:
            --author "Name"          --description "One paragraph"
            --dry-run   print the detected chapter plan without writing
            --no-build  skip rebuilding index.html afterwards

How chapters are detected, in priority order:

    1. Explicit markers — a line `<!-- chapter: The Title -->` starts a new
       chapter (also accepted: `=== chapter: The Title ===`). A line
       `<!-- part: Part Name -->` groups the chapters after it into a part
       subfolder. Markers inside ``` code fences are ignored.
    2. H1 fallback — no chapter markers but 2+ `# Heading` lines: split on H1s.
    3. Single chapter — otherwise the whole text becomes one chapter.

Multiple files are imported in natural filename order (ch1, ch2, ... ch10),
one chapter per file — unless a file itself contains markers/H1s, in which
case it is split too. Content before the first chapter becomes a "Front
Matter" chapter. Every written chapter starts with a `# Title` H1.

tools/FORMAT-PROMPT.md is a ready-made prompt for getting an LLM to convert
raw text into the marker format above.
"""
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
LIBRARY = os.path.join(ROOT, "library")
PROMPT_FILE = os.path.join(TOOLS, "FORMAT-PROMPT.md")
TEMPLATE = os.path.join(TOOLS, "importer.html")

H1_RE = re.compile(r"^#(?!#)\s+(.*\S)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
MARKER_RES = [
    re.compile(r"^\s*<!--\s*(chapter|part)\s*:\s*(.+?)\s*-->\s*$", re.I),
    re.compile(r"^\s*={3,}\s*(chapter|part)\s*:\s*(.+?)\s*=*\s*$", re.I),
]


class ImportError_(Exception):
    """A user-facing problem with the requested import (bad input, clash...)."""


# ---------------------------------------------------------------- shared helpers
# (same conventions as build-reader.py / new-book.py)

def natural_key(name):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def prettify(name):
    name = re.sub(r"^\d+[-_. ]+", "", name)
    words = re.split(r"[-_]+", name)
    return " ".join(w[:1].upper() + w[1:] for w in words if w)


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "untitled"


def next_prefix(dirpath):
    used = set()
    if os.path.isdir(dirpath):
        for name in os.listdir(dirpath):
            m = re.match(r"^(\d+)[-_. ]", name)
            if m:
                used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return f"{n:02d}"


def find_section(query):
    if not os.path.isdir(LIBRARY):
        return None
    q = query.lower()
    for name in sorted(os.listdir(LIBRARY)):
        full = os.path.join(LIBRARY, name)
        if not os.path.isdir(full) or name.startswith("."):
            continue
        if name.lower() == q or q in name.lower():
            return name
    return None


def create_section(title):
    folder = f"{next_prefix(LIBRARY)}-{slugify(title)}"
    sec_dir = os.path.join(LIBRARY, folder)
    os.makedirs(sec_dir)
    with open(os.path.join(sec_dir, "section.json"), "w", encoding="utf-8") as fh:
        json.dump({"title": title.strip()}, fh, ensure_ascii=False, indent=2)
    return folder


def list_sections():
    out = []
    if not os.path.isdir(LIBRARY):
        return out
    for name in sorted(os.listdir(LIBRARY), key=natural_key):
        full = os.path.join(LIBRARY, name)
        if name.startswith(".") or not os.path.isdir(full):
            continue
        meta = {}
        try:
            with open(os.path.join(full, "section.json"), encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            pass
        out.append({"id": name, "title": meta.get("title", prettify(name))})
    return out


# ---------------------------------------------------------------- chapter splitting

def marker_of(line):
    for rx in MARKER_RES:
        m = rx.match(line)
        if m:
            return m.group(1).lower(), m.group(2).strip()
    return None


def scan(lines):
    """(line_index, kind, title) for every marker/H1 outside code fences."""
    events, fence = [], None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if fence:
            if s.startswith(fence):
                fence = None
            continue
        m = FENCE_RE.match(ln)
        if m:
            fence = m.group(1)[:3]
            continue
        mk = marker_of(ln)
        if mk:
            events.append((i, mk[0], mk[1]))
            continue
        h = H1_RE.match(ln)
        if h:
            events.append((i, "h1", h.group(1).strip()))
    return events


def leading_h1(md):
    for ln in md.splitlines():
        if ln.strip():
            m = H1_RE.match(ln)
            return m.group(1).strip() if m else None
    return None


def ensure_h1(body, title):
    if leading_h1(body):
        return body
    return f"# {title}\n\n{body}" if body else f"# {title}\n"


def split_text(text, fallback_title):
    """-> (entries, warnings); entries = [{"part", "title", "md"}] in order."""
    text = text.lstrip("﻿")
    lines = text.splitlines()
    events = scan(lines)
    warnings = []

    if any(k == "chapter" for _, k, _ in events):
        boundary = "chapter"
    elif sum(1 for _, k, _ in events if k == "h1") >= 2:
        boundary = "h1"
    else:  # single chapter
        title = next((t for _, k, t in events if k == "h1"), None) or fallback_title
        drop = {i for i, k, _ in events if k == "part"}
        body = "\n".join(ln for i, ln in enumerate(lines) if i not in drop).strip()
        return [{"part": "", "title": title, "md": ensure_h1(body, title)}], warnings

    evmap = {i: (k, t) for i, k, t in events}
    raw, pre, cur, part = [], [], None, ""
    for i, ln in enumerate(lines):
        ev = evmap.get(i)
        if ev:
            k, t = ev
            if k == "part":
                part = t
                continue
            if k == boundary:
                if cur is not None:
                    raw.append(cur)
                cur = {"part": part, "title": t, "lines": []}
                if boundary == "h1":
                    cur["lines"].append(ln)  # the H1 stays in the chapter body
                continue
            # an H1 while splitting on markers is ordinary content
        (pre if cur is None else cur["lines"]).append(ln)
    if cur is not None:
        raw.append(cur)

    entries = []
    pre_text = "\n".join(pre).strip()
    if pre_text:
        entries.append({"part": "", "title": "Front Matter",
                        "md": ensure_h1(pre_text, "Front Matter")})
        warnings.append("content before the first chapter was kept as a 'Front Matter' chapter")
    for c in raw:
        body = "\n".join(c["lines"]).strip()
        if not body:
            warnings.append(f"chapter {c['title']!r} has no content")
        md = ensure_h1(body, c["title"])
        entries.append({"part": c["part"], "title": leading_h1(md) or c["title"], "md": md})
    return entries, warnings


def split_files(files, book_title):
    """files = [(name, text)] in final order -> (entries, warnings)."""
    entries, warnings = [], []
    for name, text in files:
        stem = os.path.splitext(os.path.basename(name))[0]
        fallback = book_title if len(files) == 1 else prettify(stem)
        e, w = split_text(text, fallback)
        entries.extend(e)
        warnings.extend(w if len(files) == 1 else [f"{name}: {x}" for x in w])
    return entries, warnings


def plan_files(entries):
    """Assign NN-slug.md paths (part folders included) -> [(relpath, entry)]."""
    out, top, i = [], 0, 0
    while i < len(entries):
        part = entries[i]["part"]
        top += 1
        if not part:
            e = entries[i]
            out.append((f"{top:02d}-{slugify(e['title'])}.md", e))
            i += 1
        else:  # consecutive chapters of the same part share one numbered folder
            j = i
            while j < len(entries) and entries[j]["part"] == part:
                j += 1
            pdir = f"{top:02d}-{slugify(part)}"
            for n, e in enumerate(entries[i:j], 1):
                out.append((f"{pdir}/{n:02d}-{slugify(e['title'])}.md", e))
            i = j
    return out


# ---------------------------------------------------------------- writing + building

def write_book(section, title, plan, author="", description=""):
    sec_dir = os.path.join(LIBRARY, section)
    book_folder = f"{next_prefix(sec_dir)}-{slugify(title)}"
    book_dir = os.path.join(sec_dir, book_folder)
    if os.path.exists(book_dir):
        raise ImportError_(f"library/{section}/{book_folder} already exists")
    os.makedirs(book_dir)

    meta = {"title": title}
    if author:
        meta["author"] = author
    if description:
        meta["description"] = description
    with open(os.path.join(book_dir, "book.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    for rel, e in plan:
        full = os.path.join(book_dir, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(e["md"].rstrip() + "\n")
    return book_folder


def run_build():
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "build-reader.py")],
                       capture_output=True, text=True, cwd=ROOT)
    return (r.stdout + r.stderr).strip()


# ---------------------------------------------------------------- web UI (--serve)

def payload_files(body):
    files = [(str(f.get("name") or "pasted-text.md"), str(f.get("text") or ""))
             for f in (body.get("files") or [])]
    if len(files) > 1:
        files.sort(key=lambda nf: natural_key(os.path.basename(nf[0])))
    return [f for f in files if f[1].strip()]


def api_preview(body):
    files = payload_files(body)
    if not files:
        return {"chapters": [], "warnings": [], "suggested_title": ""}
    title = (body.get("title") or "").strip() or "Untitled"
    entries, warnings = split_files(files, title)
    plan = plan_files(entries)
    chapters = [{"n": n, "file": rel, "part": e["part"], "title": e["title"],
                 "words": len(re.findall(r"\S+", e["md"]))}
                for n, (rel, e) in enumerate(plan, 1)]
    suggested = entries[0]["title"] if entries and entries[0]["title"] != "Untitled" else ""
    return {"chapters": chapters, "warnings": warnings, "suggested_title": suggested}


def api_import(body):
    title = (body.get("title") or "").strip()
    if not title:
        raise ImportError_("a book title is required")
    files = payload_files(body)
    if not files:
        raise ImportError_("no content — paste text or add files first")

    new_name = (body.get("section_new") or "").strip()
    if new_name:
        section = create_section(new_name)
    else:
        section = (body.get("section") or "").strip()
        if not section or not os.path.isdir(os.path.join(LIBRARY, section)):
            raise ImportError_("pick a section (or name a new one)")

    entries, warnings = split_files(files, title)
    plan = plan_files(entries)
    book_folder = write_book(section, title, plan,
                             (body.get("author") or "").strip(),
                             (body.get("description") or "").strip())
    return {"ok": True,
            "book_id": f"{section}/{book_folder}",
            "folder": f"library/{section}/{book_folder}",
            "chapters": len(plan),
            "files": [rel for rel, _ in plan],
            "warnings": warnings,
            "build": run_build()}


def serve(port):
    import http.server

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=ROOT, **kw)

        def log_message(self, *a):
            pass

        def _json(self, obj, status=200):
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/import"):
                with open(TEMPLATE, encoding="utf-8") as fh:
                    data = fh.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/sections":
                return self._json(list_sections())
            if path == "/api/prompt":
                try:
                    with open(PROMPT_FILE, encoding="utf-8") as fh:
                        return self._json({"prompt": fh.read()})
                except OSError:
                    return self._json({"prompt": ""})
            return super().do_GET()

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                return self._json({"error": "bad request body"}, 400)
            try:
                if self.path == "/api/preview":
                    return self._json(api_preview(body))
                if self.path == "/api/import":
                    return self._json(api_import(body))
                return self._json({"error": "unknown endpoint"}, 404)
            except ImportError_ as e:
                return self._json({"error": str(e)}, 400)
            except Exception as e:  # keep the server alive; surface the cause
                return self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Import UI:  http://127.0.0.1:{port}")
    print(f"Reader:     http://127.0.0.1:{port}/index.html   (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


# ---------------------------------------------------------------- CLI

BOOL_FLAGS = {"paste", "dry-run", "no-build"}


def parse_args(argv):
    args, opts = [], {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            key = a[2:]
            if key in BOOL_FLAGS:
                opts[key] = True
                i += 1
            else:
                if i + 1 >= len(argv):
                    sys.exit(f"missing value for {a}")
                opts[key] = argv[i + 1]
                i += 2
        else:
            args.append(a)
            i += 1
    return args, opts


def print_plan(plan, warnings):
    print(f"Detected {len(plan)} chapter(s):")
    for rel, e in plan:
        part = f"  [{e['part']}]" if e["part"] else ""
        words = len(re.findall(r"\S+", e["md"]))
        print(f"  {rel:<44} # {e['title']} ({words} words){part}")
    for w in warnings:
        print(f"  ! {w}")


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        sys.exit(__doc__)
    if argv[0] == "--serve":
        port = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 8081
        serve(port)
        return

    args, opts = parse_args(argv)
    if len(args) < 2:
        sys.exit(__doc__)
    section_q, title, paths = args[0], args[1], args[2:]

    if opts.get("paste") or not paths:
        if sys.stdin.isatty():
            print("Paste your text, then press Ctrl-D on an empty line:", file=sys.stderr)
        text = sys.stdin.read()
        if not text.strip():
            sys.exit("no input received")
        files = [("pasted-text.md", text)]
    else:
        files = []
        for p in sorted(paths, key=lambda p: natural_key(os.path.basename(p))):
            if not os.path.isfile(p):
                sys.exit(f"file not found: {p}")
            with open(p, encoding="utf-8", errors="replace") as fh:
                files.append((os.path.basename(p), fh.read()))

    entries, warnings = split_files(files, title)
    plan = plan_files(entries)
    print_plan(plan, warnings)
    if opts.get("dry-run"):
        print("\n(dry run — nothing written)")
        return

    section = find_section(section_q)
    if section is None:
        section = create_section(section_q.strip().title())
        print(f"Created new section library/{section}/")

    book_folder = write_book(section, title, plan,
                             opts.get("author", ""), opts.get("description", ""))
    print(f"\nWrote library/{section}/{book_folder}/ ({len(plan)} chapters)")
    if opts.get("no-build"):
        print("Skipped build — run  python3 tools/build-reader.py  when ready.")
    else:
        print(run_build())


if __name__ == "__main__":
    try:
        main()
    except ImportError_ as e:
        sys.exit(f"error: {e}")
