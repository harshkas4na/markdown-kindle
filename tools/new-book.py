#!/usr/bin/env python3
"""Scaffold a new book in library/ following the repo's conventions.

Usage:
    python3 tools/new-book.py <section> "<Book Title>" [options]

    <section>   an existing section folder name (e.g. 02-books) or a new one;
                matching is fuzzy: "books" finds "02-books".
    options:
        --author "Name"
        --description "One paragraph shown on the book's TOC page"
        --chapters "Intro,Getting Started,Advanced"   (comma-separated titles)

Examples:
    python3 tools/new-book.py books "Deep Work" --author "Cal Newport"
    python3 tools/new-book.py 03-hld "Kafka Internals" --chapters "Overview,Log,Replication"

Creates the folder, book.json, and numbered chapter stubs (each with an H1),
then reminds you to run the build.
"""
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
LIBRARY = os.path.join(ROOT, "library")


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "untitled"


def next_prefix(dirpath):
    """Smallest unused NN- prefix among the folder's entries."""
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


def parse_args(argv):
    args, opts = [], {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            key = a[2:]
            if i + 1 >= len(argv):
                sys.exit(f"missing value for {a}")
            opts[key] = argv[i + 1]
            i += 2
        else:
            args.append(a)
            i += 1
    return args, opts


def main():
    args, opts = parse_args(sys.argv[1:])
    if len(args) != 2:
        sys.exit(__doc__)
    section_q, title = args

    section = find_section(section_q)
    if section is None:
        section = f"{next_prefix(LIBRARY)}-{slugify(section_q)}"
        sec_dir = os.path.join(LIBRARY, section)
        os.makedirs(sec_dir)
        with open(os.path.join(sec_dir, "section.json"), "w", encoding="utf-8") as fh:
            json.dump({"title": section_q.strip().title()}, fh, ensure_ascii=False, indent=2)
        print(f"Created new section library/{section}/")
    sec_dir = os.path.join(LIBRARY, section)

    book_folder = f"{next_prefix(sec_dir)}-{slugify(title)}"
    book_dir = os.path.join(sec_dir, book_folder)
    if os.path.exists(book_dir):
        sys.exit(f"{book_dir} already exists")
    os.makedirs(book_dir)

    meta = {"title": title}
    if opts.get("author"):
        meta["author"] = opts["author"]
    if opts.get("description"):
        meta["description"] = opts["description"]
    with open(os.path.join(book_dir, "book.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    chapters = [c.strip() for c in opts.get("chapters", "").split(",") if c.strip()]
    if not chapters:
        chapters = ["Start Here"]
    for i, ch in enumerate(chapters):
        fname = f"{i:02d}-{slugify(ch)}.md"
        with open(os.path.join(book_dir, fname), "w", encoding="utf-8") as fh:
            fh.write(f"# {ch}\n\n(Write this chapter.)\n")

    rel = f"library/{section}/{book_folder}"
    print(f"Created {rel}/ with {len(chapters)} chapter stub(s):")
    for i, ch in enumerate(chapters):
        print(f"  {i:02d}-{slugify(ch)}.md  — # {ch}")
    print("\nNext: write the chapters, then run  python3 tools/build-reader.py")


if __name__ == "__main__":
    main()
