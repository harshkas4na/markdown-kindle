# The epub drop folder

Put an `.epub` you own in this folder and run:

    python3 tools/epub-import.py

Each new file is converted into a proper book on its own **EPUB** shelf
(`library/NN-epub/`) — chapters split from the epub's table of contents,
title/author/description from its metadata — and `index.html` is rebuilt, so the
book shows up in the reader. Titles you already have elsewhere in the library are
imported anyway; nothing is skipped as a duplicate.

To have it happen the moment you drop a file in, leave this running:

    python3 tools/epub-import.py --watch

Useful flags: `--dry-run` (print the chapter plan, write nothing),
`--section <name>` (file it under a different shelf), `--force` (import a file
again). `python3 tools/epub-import.py --help` lists them all.

The `.epub` files themselves and `.imported.json` (which remembers what has
already been converted) stay out of git — only the converted markdown in
`library/` is committed.
