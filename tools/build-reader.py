#!/usr/bin/env python3
"""Build index.html — a single-file Kindle-style reader for everything in library/.

Usage:  python3 tools/build-reader.py

No configuration needed. The script discovers content from the folder structure
(Next.js-style routing):

    library/
      <section>/            first-level folder  = a shelf section in the library
        section.json        optional: {"title": "..."}
        <book>/             second-level folder = one book
          book.json         optional: {"title", "author", "description"}
          01-intro.md       .md files, sorted by filename = chapters
          <part>/           deeper folders = named parts; their .md files are
                            chapters grouped under a part heading in the TOC
        loose-note.md       a loose .md directly in a section = a one-chapter book

Ordering: natural sort of file/folder names. A leading "NN-" numeric prefix
controls order and is stripped from display titles. Chapter titles come from
the first "# H1" line of the file, falling back to the prettified filename.

Re-run any time you add or edit markdown files. Output: index.html (repo root).
"""
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
LIBRARY = os.path.join(ROOT, "library")
OUT = os.path.join(ROOT, "index.html")


def natural_key(name):
    """'10-foo' sorts after '2-bar': split digit runs and compare numerically."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name)]


def prettify(name):
    """Folder/file name -> display title: strip 'NN-' prefix, dashes -> spaces, Title Case."""
    name = re.sub(r"^\d+[-_. ]+", "", name)
    words = re.split(r"[-_]+", name)
    return " ".join(w[:1].upper() + w[1:] for w in words if w)


def title_of(md, fallback):
    for line in md.splitlines():
        m = re.match(r"#\s+(.*)", line)
        if m:
            return m.group(1).strip()
    return fallback


def read_json(path):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def list_entries(dirpath):
    """(files, dirs) — visible entries, natural-sorted."""
    files, dirs = [], []
    for name in sorted(os.listdir(dirpath), key=natural_key):
        if name.startswith("."):
            continue
        full = os.path.join(dirpath, name)
        (dirs if os.path.isdir(full) else files).append(name)
    return files, dirs


def collect_book_chapters(book_dir, book_id, chapters):
    """Walk a book folder; append chapter dicts to `chapters`, return their indices.

    Files and subfolders at each level are processed in one natural-sorted pass,
    so a '05-part-two/' folder can be ordered between chapter files. Nested
    folders become part labels ('Categories', 'Part Two / Basics', ...).
    """
    indices = []

    def walk(dirpath, part_label):
        entries = sorted(os.listdir(dirpath), key=natural_key)
        for name in entries:
            if name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            if os.path.isdir(full):
                sub = prettify(name)
                walk(full, f"{part_label} / {sub}" if part_label else sub)
            elif name.endswith(".md"):
                with open(full, encoding="utf-8") as fh:
                    md = fh.read()
                indices.append(len(chapters))
                chapters.append({
                    "id": os.path.relpath(full, ROOT).replace(os.sep, "/"),
                    "file": name,
                    "book": book_id,
                    "part": part_label,
                    "num": len(indices),
                    "title": title_of(md, prettify(os.path.splitext(name)[0])),
                    "md": md,
                })

    walk(book_dir, "")
    return indices


def build():
    if not os.path.isdir(LIBRARY):
        sys.exit(f"No library/ folder found at {LIBRARY} — nothing to build.")

    sections = []
    chapters = []  # flat, global list; books reference chapters by index

    sec_files, sec_dirs = list_entries(LIBRARY)
    for stray in sec_files:
        print(f"  ! ignoring {stray} at library/ root — put .md files inside a section folder")

    for sec_name in sec_dirs:
        sec_dir = os.path.join(LIBRARY, sec_name)
        sec_meta = read_json(os.path.join(sec_dir, "section.json"))
        section = {"id": sec_name, "title": sec_meta.get("title", prettify(sec_name)), "books": []}

        files, dirs = list_entries(sec_dir)

        # loose .md files directly in a section: each becomes a one-chapter book
        for fname in files:
            if not fname.endswith(".md"):
                continue
            with open(os.path.join(sec_dir, fname), encoding="utf-8") as fh:
                md = fh.read()
            stem = os.path.splitext(fname)[0]
            book_id = f"{sec_name}/{stem}"
            idx = len(chapters)
            chapters.append({
                "id": f"library/{sec_name}/{fname}",
                "file": fname,
                "book": book_id,
                "part": "",
                "num": 1,
                "title": title_of(md, prettify(stem)),
                "md": md,
            })
            section["books"].append({
                "id": book_id,
                "title": title_of(md, prettify(stem)),
                "author": "",
                "description": "",
                "chapters": [idx],
            })

        # folders in a section: each is a book
        for book_name in dirs:
            book_dir = os.path.join(sec_dir, book_name)
            meta = read_json(os.path.join(book_dir, "book.json"))
            book_id = f"{sec_name}/{book_name}"
            ch_idx = collect_book_chapters(book_dir, book_id, chapters)
            if not ch_idx:
                print(f"  ! skipping empty book folder library/{sec_name}/{book_name}")
                continue
            section["books"].append({
                "id": book_id,
                "title": meta.get("title", prettify(book_name)),
                "author": meta.get("author", ""),
                "description": meta.get("description", ""),
                "chapters": ch_idx,
            })

        if section["books"]:
            sections.append(section)

    with open(os.path.join(TOOLS, "reader-template.html"), encoding="utf-8") as fh:
        tpl = fh.read()

    # "</" would terminate the <script> tag early; "<\/" is a safe JS escape.
    def embed(obj):
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    html = tpl.replace("__LIB_DATA__", embed(sections)).replace("__CHAPTER_DATA__", embed(chapters))

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)

    n_books = sum(len(s["books"]) for s in sections)
    print(f"Wrote {OUT}: {len(sections)} sections, {n_books} books, "
          f"{len(chapters)} chapters, {len(html) // 1024} KB")


if __name__ == "__main__":
    build()
