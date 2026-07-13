Reformat the raw text I give you into a chapter-structured markdown book for my e-reader. Follow these rules EXACTLY:

1. Split the content into its natural chapters. Immediately before each chapter, output this marker on its own line:
   <!-- chapter: Chapter Title -->
2. Start each chapter's content with an H1 heading repeating the same title: # Chapter Title
3. Inside a chapter use only ## and ### headings. Never use a single # anywhere except the chapter title line — my importer splits on those.
4. If the content has larger groupings (parts/sections that contain several chapters), output this marker on its own line before the first chapter of each group:
   <!-- part: Part Name -->
5. Allowed formatting: paragraphs, **bold**, *italic*, `inline code`, fenced ``` code blocks, > blockquotes, tables, and bullet/numbered lists nested at most ONE level deep.
6. Do NOT use: images, footnotes, HTML tags (except the two marker comments above), or lists nested more than one level — my reader cannot display them.
7. Keep the original wording and order — you are restructuring, not rewriting or summarizing. Fix only broken line-wraps, OCR artifacts, hyphenation damage, and stray whitespace.
8. Output nothing before the first marker and nothing after the last chapter — no preamble, no "Here is your formatted text", no closing remarks.
9. If you run out of output space, stop cleanly at the end of a chapter. When I reply "continue", resume starting with the next chapter's marker line. (The markers make it safe for me to concatenate your replies.)

Here is the raw text:
