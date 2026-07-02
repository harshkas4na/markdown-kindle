#!/usr/bin/env python3
"""Build reader.html — a single-file Kindle-style reader with every .md file embedded.

Usage:  python3 tools/build-reader.py
Re-run any time you edit or add markdown files in research/, learn/, or hook-directory/.
"""
import json
import os
import re

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
OUT = os.path.join(ROOT, "reader.html")

SECTIONS = [
    ("Research — What To Build (2026)", "research"),
    ("Learn — The Basics", "learn"),
    ("Hook Directory — 556 Past Projects", "hook-directory"),
]


def title_of(md, fname):
    for line in md.splitlines():
        m = re.match(r"#\s+(.*)", line)
        if m:
            return m.group(1).strip()
    return os.path.splitext(fname)[0]


def collect(folder):
    base = os.path.join(ROOT, folder)
    paths = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames.sort()
        for f in sorted(filenames):
            if f.endswith(".md"):
                paths.append(os.path.join(dirpath, f))
    return paths


chapters = []
for label, folder in SECTIONS:
    n = 0
    for path in collect(folder):
        with open(path, encoding="utf-8") as fh:
            md = fh.read()
        n += 1
        chapters.append({
            "id": os.path.relpath(path, ROOT),
            "file": os.path.basename(path),
            "section": label,
            "num": n,
            "title": title_of(md, os.path.basename(path)),
            "md": md,
        })

with open(os.path.join(TOOLS, "reader-template.html"), encoding="utf-8") as fh:
    tpl = fh.read()

# "</" would terminate the <script> tag early; "<\/" is a safe JS escape.
data = json.dumps(chapters, ensure_ascii=False).replace("</", "<\\/")
html = tpl.replace("__BOOK_DATA__", data)

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(html)

print(f"Wrote {OUT}: {len(chapters)} chapters, {len(html) // 1024} KB")
