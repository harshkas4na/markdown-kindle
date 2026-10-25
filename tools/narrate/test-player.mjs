#!/usr/bin/env node
/* Drive the built reader in headless Chrome and check that a studio chapter
   plays from the shipped audio: the Studio voice is offered and default, play
   starts the m4a, the highlight follows the audio, seeking jumps the audio.
   Usage: node tools/narrate/test-player.mjs <chapter id, e.g. library/02-books/show-your-work/01-....md>
   Serves the repo on :8089 first (studio audio is fetched, so file:// won't do). */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../podcast/node_modules/playwright-core/index.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const chId = process.argv[2];
if (!chId) { console.error("usage: test-player.mjs <chapter id>"); process.exit(2); }
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".m4a": "audio/mp4", ".webmanifest": "application/manifest+json" };
const srv = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0].replace(/\/$/, "/index.html")));
  if (!fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  const st = fs.statSync(p), type = TYPES[path.extname(p)] || "application/octet-stream";
  const range = /bytes=(\d*)-(\d*)/.exec(req.headers.range || "");
  if (range) {
    const s = range[1] ? +range[1] : 0, e = range[2] ? +range[2] : st.size - 1;
    res.writeHead(206, { "Content-Type": type, "Accept-Ranges": "bytes", "Content-Range": `bytes ${s}-${e}/${st.size}`, "Content-Length": e - s + 1 });
    return fs.createReadStream(p, { start: s, end: e }).pipe(res);
  }
  res.writeHead(200, { "Content-Type": type, "Accept-Ranges": "bytes", "Content-Length": st.size });
  fs.createReadStream(p).pipe(res);
}).listen(8089);

const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--autoplay-policy=no-user-gesture-required"] });
const fails = [];
const check = (ok, what) => { console.log((ok ? "  ok  " : "  FAIL") + " " + what); if (!ok) fails.push(what); };
try {
  const page = await browser.newPage();
  page.on("pageerror", e => console.log("  page error:", e.message));
  const token = JSON.parse(fs.readFileSync(path.join(ROOT, "tools/access-config.json"), "utf8")).token;
  await page.goto(`http://127.0.0.1:8089/index.html?k=${token}#c/${encodeURIComponent(chId)}`);
  await page.waitForFunction(() => typeof ttsOpen === "function" && cur >= 0, null, { timeout: 15000 });
  const info = await page.evaluate(() => ({ narrated: !!NARRATED[CHAPTERS[cur].id], voice: ttsVoiceId(), studio: ttsUsesStudio() }));
  check(info.narrated, `chapter has studio audio in NARRATED (${JSON.stringify(info)})`);
  check(info.voice === "studio" && info.studio, "Studio is the default voice");
  await page.evaluate(() => { ttsOpen(false); });
  await page.waitForTimeout(300);
  const opt = await page.evaluate(() => [...document.querySelectorAll("#ttsVoice option")].map(o => o.value + ":" + o.textContent)[0]);
  check(/^studio:/.test(opt), `Voice menu lists Studio first (${opt})`);
  await page.evaluate(() => ttsPlay());
  await page.waitForFunction(() => { const a = document.getElementById("ttsAudio"); return a.dataset.kind === "studio" && !a.paused && a.currentTime > 0.5; }, null, { timeout: 20000 });
  const w1 = await page.evaluate(() => ({ idx: ttsIdx, t: document.getElementById("ttsAudio").currentTime, src: document.getElementById("ttsAudio").src }));
  check(/\.m4a$/.test(w1.src), `audio element plays the m4a (${w1.src.split("/").slice(-2).join("/")})`);
  await page.waitForTimeout(4000);
  const w2 = await page.evaluate(() => ({ idx: ttsIdx, t: document.getElementById("ttsAudio").currentTime, cur: document.querySelector(".tts-w.tts-cur")?.textContent }));
  check(w2.idx > w1.idx, `highlight advances with the audio (word ${w1.idx} → ${w2.idx}, now “${w2.cur}”)`);
  // seek to the middle of the chapter
  const mid = await page.evaluate(() => { const i = Math.floor(ttsWords.length * 0.6); ttsSeekTo(i); return i; });
  await page.waitForTimeout(1500);
  const w3 = await page.evaluate(() => ({ idx: ttsIdx, t: document.getElementById("ttsAudio").currentTime, dur: document.getElementById("ttsAudio").duration, paused: document.getElementById("ttsAudio").paused }));
  check(!w3.paused && Math.abs(w3.idx - mid) < 25 && w3.t > w3.dur * 0.4, `seek to word ${mid} jumps the audio (word ${w3.idx}, ${w3.t.toFixed(1)}s of ${w3.dur.toFixed(1)}s)`);
  // pause / resume keep the position
  await page.evaluate(() => ttsPause());
  await page.waitForTimeout(500);
  const p1 = await page.evaluate(() => ({ paused: document.getElementById("ttsAudio").paused, t: document.getElementById("ttsAudio").currentTime }));
  await page.evaluate(() => ttsPlay());
  await page.waitForTimeout(800);
  const p2 = await page.evaluate(() => ({ paused: document.getElementById("ttsAudio").paused, t: document.getElementById("ttsAudio").currentTime }));
  check(p1.paused && !p2.paused && p2.t >= p1.t && p2.t < p1.t + 2, `pause then play resumes in place (${p1.t.toFixed(1)}s → ${p2.t.toFixed(1)}s)`);
  // speed applies to the element
  await page.evaluate(() => { S.ttsRate = 1.5; ttsApplyRate(); });
  const rate = await page.evaluate(() => document.getElementById("ttsAudio").playbackRate);
  check(rate === 1.5, `speed slider changes playbackRate (${rate})`);
  // next sentence
  const before = await page.evaluate(() => ttsIdx);
  await page.evaluate(() => ttsSentence(1));
  await page.waitForTimeout(600);
  const after = await page.evaluate(() => ttsIdx);
  check(after > before, `next-sentence skips ahead (${before} → ${after})`);
  // end of chapter → next chapter continues with its own studio/Kokoro voice
  await page.evaluate(() => { const a = document.getElementById("ttsAudio"); a.currentTime = a.duration - 1.5; });
  await page.waitForTimeout(3500);
  const nx = await page.evaluate(() => ({ cur, active: ttsActive, speaking: ttsSpeaking, kind: document.getElementById("ttsAudio").dataset.kind, note: document.getElementById("ttsKokoroNote").textContent }));
  console.log("  after chapter end:", JSON.stringify(nx));
  check(nx.active, "Listen stays open into the next chapter");
} finally {
  await browser.close();
  srv.close();
}
console.log(fails.length ? `\n${fails.length} check(s) failed` : "\nall checks passed");
process.exit(fails.length ? 1 : 0);
