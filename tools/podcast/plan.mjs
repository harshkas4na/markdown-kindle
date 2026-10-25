#!/usr/bin/env node
/* Print the Listen "plan" of a book as JSON — the exact chunks of words the
   reader would speak, with their word indices — so tools/narrate/narrate.py
   can make audio whose timing map lines up with the words on screen.

   Usage: node tools/podcast/plan.mjs <section>/<book>   (needs index.html built)
   Output: {title, author, chapters:[{id, title, words, chunks:[{s,e,text,brk}]}]}
   s/e: [start,end) word index; brk: break after the chunk's last word
   (2 = paragraph/heading end, 1 = sentence end, 0 = none). Headings are
   included (ttsSkipHead off) and there is no dialogue voice, so the word
   numbering is the one the reader uses when it plays studio audio. */
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const bookId = process.argv[2];
if (!bookId) { console.error("usage: plan.mjs <section>/<book>"); process.exit(2); }

const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.join(ROOT, "index.html")).href);
  const data = await page.evaluate((bookId) => {
    S.ttsVoice = "kokoro:af_heart"; S.ttsDlg = ""; S.ttsSkipHead = false;
    const b = Array.isArray(BOOKS) ? BOOKS.find(x => x.id === bookId) : BOOKS[bookId];
    if (!b) return null;
    return {
      id: b.id, title: b.title, author: b.author || "", lang: b.lang || "en",
      chapters: b.chapters.map(i => {
        const c = CHAPTERS[i];
        const div = document.createElement("div");
        div.innerHTML = htmlCache[c.id] || (htmlCache[c.id] = mdToHtml(c.md));
        const T = ttsTokenize(div, false);
        const plan = ttsMakePlan(T);
        return {
          id: c.id, title: c.title, words: T.texts.length,
          chunks: plan.map(c => ({ s: c.start, e: c.end, text: c.text, brk: T.breaks[c.end - 1] || 0 })),
        };
      }),
    };
  }, bookId);
  if (!data) { console.error(`${bookId} is not in index.html — run python3 tools/build-reader.py first`); process.exit(1); }
  process.stdout.write(JSON.stringify(data));
} finally {
  await browser.close();
}
