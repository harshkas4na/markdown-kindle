#!/usr/bin/env python3
"""Mechanically convert one chapter of an EPUB you own into the library's
markdown format — a small XHTML->Markdown transform in the spirit of pandoc or
Calibre, for format-shifting your own books into the reader.

It reads a single XHTML item straight out of the .epub zip and writes markdown.
Nothing is fetched or embedded from outside the file. Images are dropped because
the reader does not render them (see tools/build-reader.py).

Usage:
    python3 tools/epub-to-markdown.py \
        --epub public/raw-books/vdoc.pub_show-your-work.epub \
        --item OEBPS/chapter-1.xhtml \
        --out library/02-books/show-your-work/01-you-dont-have-to-be-a-genius.md \
        --title "You Don't Have to Be a Genius" --number 1
"""
import argparse
import html
import re
import zipfile
from pathlib import Path

BLOCK_RE = re.compile(r"<(p|h[1-6]|blockquote)\b([^>]*)>(.*?)</\1>", re.S)
CLASS_RE = re.compile(r'class="([^"]*)"')


def inline(fragment: str) -> str:
    """Reduce inline markup to markdown, keeping link/emphasis text."""
    s = re.sub(r"</?(?:em|i)\b[^>]*>", "*", fragment)
    s = re.sub(r"</?(?:strong|b)\b[^>]*>", "**", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", s, flags=re.S)  # unwrap links
    s = re.sub(r"<[^>]+>", "", s)  # drop any leftover tags (incl. images)
    return html.unescape(s).strip()


def convert(xhtml: str, title: str | None, number: int | None) -> str:
    body = re.search(r"<body[^>]*>(.*)</body>", xhtml, re.S)
    body = body.group(1) if body else xhtml

    blocks: list[tuple[str, str]] = []  # (kind, text)
    for m in BLOCK_RE.finditer(body):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        text = inline(inner)
        if not text:
            continue
        cls_m = CLASS_RE.search(attrs)
        cls = cls_m.group(1) if cls_m else ""
        if tag[0] == "h":
            blocks.append((f"h{tag[1]}", text))
        elif tag == "blockquote" or cls in ("Q", "QAtt"):
            blocks.append(("quote", text))
        else:
            blocks.append(("p", text))

    lines: list[str] = []
    if title:
        lines.append(f"# {number}. {title}" if number else f"# {title}")
        lines.append("")
    for i, (kind, text) in enumerate(blocks):
        prev = blocks[i - 1][0] if i else None
        if kind == "quote":
            if prev == "quote":  # merge consecutive quote lines into one block
                lines.append("> " + text.replace("\n", "\n> "))
                continue
            if lines and lines[-1] != "":
                lines.append("")
            lines.append("> " + text.replace("\n", "\n> "))
        elif kind.startswith("h"):
            if lines and lines[-1] != "":
                lines.append("")
            lines.append("#" * int(kind[1]) + " " + text)
        else:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(text)
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epub", required=True, type=Path)
    ap.add_argument("--item", required=True, help="path of the XHTML item inside the epub zip")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--title")
    ap.add_argument("--number", type=int)
    args = ap.parse_args()

    with zipfile.ZipFile(args.epub) as z:
        xhtml = z.read(args.item).decode("utf-8")
    md = convert(xhtml, args.title, args.number)
    args.out.write_text(md, encoding="utf-8")
    # Report metadata only — never echo the converted body.
    print(f"wrote {args.out} — {len(md.splitlines())} lines, {len(md)} chars")


if __name__ == "__main__":
    main()
