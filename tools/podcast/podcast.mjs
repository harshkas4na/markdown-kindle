#!/usr/bin/env node
/* Public podcast feeds for books that opt in.

   A book opts in with  "podcast": true  in its book.json (optionally
   "podcastVoice": "af_bella" — any Kokoro voice id; default af_heart).
   For each such book this writes, next to index.html so GitHub Pages serves it:

     podcast/<section>-<book>/feed.xml       RSS 2.0 + Apple Podcasts tags
     podcast/<section>-<book>/cover.png      1400×1400 artwork
     podcast/<section>-<book>/NN-<slug>.mp3  one episode per chapter
     podcast/<section>-<book>/episodes.json  what was built from which text

   The words are taken from the built reader itself (headless Chrome runs the
   same ttsPlanFor() that Listen uses), so an episode says exactly what Listen
   says. The voice is Kokoro, run natively through onnxruntime-node — the same
   model and voices as Listen, ~0.4 s of work per second of speech on a Mac.
   Only chapters whose text changed are made again.

   Everything here is PUBLIC once pushed: only opt in books whose text you
   have the right to publish as audio (your own notes, not bought books).

   Setup once:  cd tools/podcast && npm install      (also needs ffmpeg)
   Run:         node tools/podcast/podcast.mjs       (all opted-in books)
                node tools/podcast/podcast.mjs 01-hookathon/01-research
   Then:        python3 tools/build-reader.py   (adds the 🎧 button) and push. */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright-core";
import { KokoroTTS } from "kokoro-js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const LIB = path.join(ROOT, "library");
const OUT = path.join(ROOT, "podcast");
const MODEL = "onnx-community/Kokoro-82M-v1.0-ONNX";

function siteBase() {
  if (process.env.PODCAST_BASE) return process.env.PODCAST_BASE.replace(/\/?$/, "/");
  const remote = execFileSync("git", ["-C", ROOT, "remote", "get-url", "origin"]).toString().trim();
  const m = remote.match(/github\.com[:/]([^/]+)\/([^/.]+)/);
  if (!m) throw new Error("Set PODCAST_BASE to the site's public URL");
  return `https://${m[1].toLowerCase()}.github.io/${m[2]}/`;
}
const readJson = f => { try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch { return null; } };
const xml = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const slugify = s => s.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "chapter";
const hms = secs => { const s = Math.round(secs); return [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60].map(n => String(n).padStart(2, "0")).join(":"); };

function optedInBooks(only) {
  const out = [];
  for (const sec of fs.readdirSync(LIB).sort()) {
    const sdir = path.join(LIB, sec);
    if (!fs.statSync(sdir).isDirectory()) continue;
    for (const book of fs.readdirSync(sdir).sort()) {
      const bdir = path.join(sdir, book);
      if (!fs.statSync(bdir).isDirectory()) continue;
      const meta = readJson(path.join(bdir, "book.json")) || {};
      const id = `${sec}/${book}`;
      if (only.length ? only.includes(id) : meta.podcast === true) out.push({ id, dir: bdir, meta });
    }
  }
  return out;
}

/* chapters + their spoken chunks, straight from the built reader */
async function chaptersFromReader(browser, bookId, voice) {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.join(ROOT, "index.html")).href);
  const data = await page.evaluate(({ bookId, voice }) => {
    S.ttsVoice = "kokoro:" + voice; S.ttsDlg = ""; S.ttsSkipHead = false;
    const b = Array.isArray(BOOKS) ? BOOKS.find(x => x.id === bookId) : BOOKS[bookId];
    if (!b) return null;
    return {
      title: b.title, author: b.author, description: b.description || "", cover: b.cover || "",
      chapters: b.chapters.map(i => ({
        title: CHAPTERS[i].title,
        chunks: ttsPlanFor(i).filter(c => c.text).map(c => c.text),
      })),
    };
  }, { bookId, voice });
  await page.close();
  if (!data) throw new Error(`${bookId} is not in index.html — run python3 tools/build-reader.py first`);
  return data;
}

async function coverPng(browser, book, file) {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1400 } });
  const art = book.cover
    ? `<img src="${xml(book.cover)}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">`
    : "";
  await page.setContent(`<!doctype html><html><body style="margin:0">
    <div style="position:relative;width:1400px;height:1400px;background:linear-gradient(160deg,#c9853a,#7a4517);
      font-family:Georgia,'Times New Roman',serif;color:#fff;overflow:hidden">${art}
      <div style="position:absolute;inset:0;padding:120px;display:flex;flex-direction:column;justify-content:flex-end;
        background:${art ? "linear-gradient(transparent 40%,rgba(0,0,0,.7))" : "none"}">
        <div style="font:600 40px -apple-system,Helvetica,sans-serif;letter-spacing:.2em;opacity:.8;margin-bottom:40px">🎧 LIBRARY · AUDIO</div>
        <div style="font-size:${book.title.length > 40 ? 104 : 136}px;line-height:1.05;font-weight:700">${xml(book.title)}</div>
        <div style="font-size:52px;margin-top:40px;opacity:.85">${xml(book.author)}</div>
      </div></div></body></html>`);
  await page.screenshot({ path: file });
  await page.close();
}

function wavFromPcm(pcm, rate) {
  const n = pcm.length, buf = Buffer.alloc(44 + n * 2);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 2, 4); buf.write("WAVE", 8); buf.write("fmt ", 12);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(rate, 24); buf.writeUInt32LE(rate * 2, 28); buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34);
  buf.write("data", 36); buf.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) { const x = Math.max(-1, Math.min(1, pcm[i])); buf.writeInt16LE(x < 0 ? x * 0x8000 : x * 0x7fff, 44 + i * 2); }
  return buf;
}

async function speak(tts, chunks, voice) {
  const parts = []; let n = 0, rate = 24000;
  for (const text of chunks) {
    const a = await tts.generate(text, { voice });
    rate = a.sampling_rate || rate;
    parts.push(a.audio); n += a.audio.length;
  }
  const pcm = new Float32Array(n); let o = 0;
  for (const p of parts) { pcm.set(p, o); o += p.length; }
  return { pcm, rate };
}

function feedXml(base, slug, book, episodes) {
  const url = `${base}podcast/${slug}/`;
  const items = episodes.map(e => `
    <item>
      <title>${xml(e.title)}</title>
      <itunes:title>${xml(e.title)}</itunes:title>
      <itunes:episode>${e.n}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <description>${xml(`Chapter ${e.n} of ${book.title}.`)}</description>
      <enclosure url="${url}${e.file}" length="${e.bytes}" type="audio/mpeg"/>
      <guid isPermaLink="false">${e.guid}</guid>
      <pubDate>${new Date(e.published).toUTCString()}</pubDate>
      <itunes:duration>${hms(e.seconds)}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>`).join("");
  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${xml(book.title)}</title>
    <link>${base}</link>
    <atom:link href="${url}feed.xml" rel="self" type="application/rss+xml"/>
    <language>en</language>
    <description>${xml(book.description || `${book.title}${book.author ? " — " + book.author : ""}, read aloud chapter by chapter.`)}</description>
    <itunes:author>${xml(book.author || "Library")}</itunes:author>
    <itunes:summary>${xml(book.description || book.title)}</itunes:summary>
    <itunes:type>serial</itunes:type>
    <itunes:image href="${url}cover.png"/>
    <image><url>${url}cover.png</url><title>${xml(book.title)}</title><link>${base}</link></image>
    <itunes:category text="Education"/>
    <itunes:explicit>false</itunes:explicit>${items}
  </channel>
</rss>
`;
}

async function main() {
  const only = process.argv.slice(2);
  const books = optedInBooks(only);
  if (!books.length) { console.log('No books opted in. Add "podcast": true to a book.json (or pass a book id).'); return; }
  const base = siteBase();
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  let tts = null;
  try {
    for (const b of books) {
      const voice = b.meta.podcastVoice || "af_heart";
      const slug = b.id.replace(/\//g, "-");
      const dir = path.join(OUT, slug);
      fs.mkdirSync(dir, { recursive: true });
      const book = await chaptersFromReader(browser, b.id, voice);
      const manifest = readJson(path.join(dir, "episodes.json")) || { episodes: [] };
      const prev = new Map(manifest.episodes.map(e => [e.file, e]));
      const episodes = [], keep = new Set(["feed.xml", "cover.png", "episodes.json"]);
      console.log(`\n${book.title} — ${book.chapters.length} chapters → podcast/${slug}/`);
      for (let k = 0; k < book.chapters.length; k++) {
        const ch = book.chapters[k];
        const file = `${String(k + 1).padStart(2, "0")}-${slugify(ch.title)}.mp3`;
        keep.add(file);
        const hash = crypto.createHash("sha256").update(voice + "\n" + ch.chunks.join("\n")).digest("hex").slice(0, 16);
        const old = prev.get(file);
        if (old && old.hash === hash && fs.existsSync(path.join(dir, file))) {
          episodes.push({ ...old, n: k + 1, title: ch.title });
          console.log(`  = ${file}`);
          continue;
        }
        if (!tts) tts = await KokoroTTS.from_pretrained(MODEL, { dtype: "fp32", device: "cpu" });
        const t0 = Date.now();
        const { pcm, rate } = await speak(tts, ch.chunks, voice);
        const wav = path.join(dir, ".tmp.wav");
        fs.writeFileSync(wav, wavFromPcm(pcm, rate));
        execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-ar", "24000", "-b:a", "48k",
          "-metadata", `title=${ch.title}`, "-metadata", `album=${book.title}`, "-metadata", `artist=${book.author || "Library"}`,
          "-metadata", `track=${k + 1}`, path.join(dir, file)]);
        fs.unlinkSync(wav);
        const seconds = pcm.length / rate;
        episodes.push({
          n: k + 1, title: ch.title, file, hash, seconds,
          bytes: fs.statSync(path.join(dir, file)).size,
          guid: old ? old.guid : `${slug}-${k + 1}-${hash}`,
          // keep the original date so podcast apps don't think every edit is a new episode
          published: old ? old.published : Date.now() - (book.chapters.length - k) * 60000,
        });
        console.log(`  + ${file}  ${hms(seconds)} of audio in ${Math.round((Date.now() - t0) / 1000)} s`);
      }
      for (const f of fs.readdirSync(dir)) if (!keep.has(f)) fs.unlinkSync(path.join(dir, f)); // removed chapters
      if (!fs.existsSync(path.join(dir, "cover.png")) || (manifest.coverFor !== book.title + book.cover.length))
        await coverPng(browser, book, path.join(dir, "cover.png"));
      fs.writeFileSync(path.join(dir, "episodes.json"), JSON.stringify({ book: b.id, voice, coverFor: book.title + book.cover.length, episodes }, null, 1));
      fs.writeFileSync(path.join(dir, "feed.xml"), feedXml(base, slug, book, episodes));
      console.log(`  feed: ${base}podcast/${slug}/feed.xml`);
    }
  } finally {
    await browser.close();
  }
}
main().catch(e => { console.error(e); process.exit(1); });
