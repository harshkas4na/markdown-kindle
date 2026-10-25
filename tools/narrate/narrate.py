#!/usr/bin/env python
"""Studio narration: make a book's audio on this Mac, so the phone only plays.

For every chapter of a book this writes, next to index.html:

    audio/<section>-<book>/NN-<slug>.m4a    the chapter, AAC mono (iPhone-safe)
    audio/<section>-<book>/NN-<slug>.json   timing map: which words play when
    audio/<section>-<book>/index.json       what was made from which text

The words come from the built reader itself (tools/podcast/plan.mjs runs the
same tokenizer Listen uses), so the highlight on screen follows the voice.
Only chapters whose text, voice or model changed are made again.

Setup once:   cd tools/narrate && uv venv --python 3.12 .venv
              source .venv/bin/activate && uv pip install mlx-audio soundfile
              (also needs: ffmpeg, Chrome, and `npm install` in tools/podcast)
Build first:  python3 tools/build-reader.py
Run:          tools/narrate/.venv/bin/python tools/narrate/narrate.py 02-books/show-your-work
              ... --voice ryan            a preset (see VOICES below)
              ... --chapters 1,3-5        only some chapters (1-based)
              ... --engine chatterbox     the other model
Then:         python3 tools/build-reader.py   (picks up audio/) and push.

A book can opt in for good with  "narrate": true  (optional "narrateVoice":
"ryan") in its book.json; then plain `narrate.py` makes every opted-in book.
"""
import argparse, hashlib, json, os, re, subprocess, sys, time, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LIB = os.path.join(ROOT, "library")
OUT = os.path.join(ROOT, "audio")
PLAN = os.path.join(ROOT, "tools", "podcast", "plan.mjs")

# Voices. qwen presets are Qwen3-TTS CustomVoice speakers plus a style line;
# "design:" voices are Qwen3-TTS VoiceDesign descriptions; chatterbox uses
# its built-in voice or a reference .wav you put in tools/narrate/voices/.
NARRATOR_STYLE = ("Warm, calm audiobook narrator. Natural, unhurried pacing; clear emphasis on the "
                  "important words; brief pauses at commas and between sentences. Read every word "
                  "exactly as written, with no added sounds, sighs or filler.")
VOICES = {
    "ryan":  {"engine": "qwen", "speaker": "Ryan",  "instruct": NARRATOR_STYLE, "label": "Ryan"},
    "aiden": {"engine": "qwen", "speaker": "Aiden", "instruct": NARRATOR_STYLE, "label": "Aiden"},
    "nora":  {"engine": "qwen-design", "label": "Nora",
              "instruct": "A warm, mature female audiobook narrator with a gentle, expressive, unhurried delivery."},
    "chatterbox": {"engine": "chatterbox", "label": "Chatterbox", "ref": None},
}
MODELS = {
    "qwen": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
    "qwen-design": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",
    "chatterbox": "mlx-community/chatterbox-turbo-fp16",
}
BATCH = 6            # chunks per forward pass (Qwen batch_generate scales almost linearly)
GAP = {2: 0.55, 1: 0.22, 0: 0.08}   # silence after a chunk: paragraph end / sentence end / none
# Every chunk is listened back to with Whisper and compared with its text; a
# chunk whose words differ too much (a dropped clause, an added "ahem" — the
# big models do this now and then) is made again, up to RETRIES times.
STT = "mlx-community/whisper-large-v3-turbo-asr-fp16"
RETRIES = 2
VERBOSE = False


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s))[:60] or "chapter"


def read_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def opted_in():
    out = []
    for sec in sorted(os.listdir(LIB)):
        sdir = os.path.join(LIB, sec)
        if not os.path.isdir(sdir):
            continue
        for book in sorted(os.listdir(sdir)):
            meta = read_json(os.path.join(sdir, book, "book.json"), {})
            if meta.get("narrate") is True:
                out.append((f"{sec}/{book}", meta.get("narrateVoice")))
    return out


def plan_of(book_id):
    r = subprocess.run(["node", PLAN, book_id], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr.strip() or f"plan.mjs failed for {book_id}")
    return json.loads(r.stdout)


class Engine:
    """Lazily loads the model; speak(texts) -> list of float32 arrays at self.sr."""
    def __init__(self, voice):
        self.v = VOICES[voice]
        self.name = voice
        self.model = None
        self.sr = 24000

    def load(self):
        if self.model:
            return
        from mlx_audio.tts.utils import load_model
        print(f"  loading {MODELS[self.v['engine']]} …", flush=True)
        self.model = load_model(MODELS[self.v["engine"]])
        self.sr = int(getattr(self.model, "sample_rate", 24000))

    def speak(self, texts, temperature=None):
        import numpy as np
        self.load()
        m, v = self.model, self.v
        out = [None] * len(texts)
        kw = {"temperature": temperature} if temperature is not None else {}
        if v["engine"] == "qwen":
            for r in m.batch_generate(texts=texts, voices=[v["speaker"]] * len(texts),
                                      instructs=[v["instruct"]] * len(texts), lang_code="english", **kw):
                out[r.sequence_idx] = np.asarray(r.audio, dtype=np.float32).reshape(-1)
        elif v["engine"] == "qwen-design":
            for i, t in enumerate(texts):
                rs = list(m.generate_voice_design(text=t, language="English", instruct=v["instruct"], **kw))
                out[i] = np.concatenate([np.asarray(r.audio, dtype=np.float32).reshape(-1) for r in rs])
        else:  # chatterbox
            for i, t in enumerate(texts):
                ref = {"ref_audio": v["ref"]} if v.get("ref") else {}
                rs = list(m.generate(text=t, temperature=temperature or 0.5, repetition_penalty=1.5, **ref))
                out[i] = np.concatenate([np.asarray(r.audio, dtype=np.float32).reshape(-1) for r in rs])
        return out


def norm_words(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower().replace("’", "'")).split()


class Checker:
    """Whisper listens to a chunk; errors(text, audio) -> number of words that differ."""
    def __init__(self):
        self.model = None

    def errors(self, text, audio, sr):
        import difflib, tempfile, soundfile as sf
        if self.model is None:
            from mlx_audio.stt.utils import load_model
            self.model = load_model(STT)
        path = os.path.join(tempfile.gettempdir(), f"narrate-check-{os.getpid()}.wav")
        sf.write(path, audio, sr)
        heard = self.model.generate(path, language="en").text
        r, h = norm_words(text), norm_words(heard)
        sm = difflib.SequenceMatcher(None, r, h, autojunk=False)
        n = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")
        return n, len(r), heard

    def ok(self, n, total):
        # one homophone or a name is fine; a missing clause or added sound is not
        return n <= max(1, round(0.08 * total))


def trim(a, sr, thresh=0.004, keep=0.06):
    """Cut leading/trailing silence, keeping `keep` seconds on each side."""
    import numpy as np
    idx = np.nonzero(np.abs(a) > thresh)[0]
    if not len(idx):
        return a[: int(sr * 0.2)]
    k = int(sr * keep)
    return a[max(0, idx[0] - k): min(len(a), idx[-1] + k)]


def render_chapter(eng, ch, m4a, tmap, checker):
    import numpy as np, soundfile as sf
    chunks = [c for c in ch["chunks"] if c["text"]]
    pieces, times, t = [], [], 0.0
    t0 = time.time()
    remade = doubtful = 0
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        audios = [trim(a, eng.sr) for a in eng.speak([c["text"] for c in batch])]
        if checker:
            for k, (c, a) in enumerate(zip(batch, audios)):
                n, total, heard = checker.errors(c["text"], a, eng.sr)
                if VERBOSE:
                    print(f"\n    [{n}/{total}] {c['text'][:60]!r} -> {heard.strip()[:60]!r}")
                best = (n, a)
                tries = 0
                while not checker.ok(n, total) and tries < RETRIES:
                    tries += 1
                    a2 = trim(eng.speak([c["text"]], temperature=0.6)[0], eng.sr)
                    n, total, heard2 = checker.errors(c["text"], a2, eng.sr)
                    if VERBOSE:
                        print(f"    retry {tries}: [{n}/{total}] -> {heard2.strip()[:60]!r}")
                    if n < best[0]:
                        best = (n, a2)
                if tries:
                    remade += 1
                    if not checker.ok(best[0], total):
                        doubtful += 1
                        print(f"\n    ? still off after {tries} retries: {c['text'][:70]!r}")
                audios[k] = best[1]
        for c, a in zip(batch, audios):
            gap = np.zeros(int(eng.sr * GAP.get(c["brk"], 0.08)), dtype=np.float32)
            times.append([c["s"], c["e"], round(t, 3), round(t + len(a) / eng.sr, 3)])
            pieces += [a, gap]
            t += (len(a) + len(gap)) / eng.sr
        done = min(i + BATCH, len(chunks))
        print(f"\r    {done}/{len(chunks)} chunks · {t/60:.1f} min of audio · {time.time()-t0:.0f} s"
              + (f" · {remade} remade" if remade else ""), end="", flush=True)
    print()
    if doubtful:
        print(f"    ! {doubtful} chunk(s) still didn't match their text — listen to this chapter")
    audio = np.concatenate(pieces) if pieces else np.zeros(eng.sr, dtype=np.float32)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio * min(1.0, 0.89 / peak)
    wav = m4a + ".tmp.wav"
    sf.write(wav, audio, eng.sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-ar", str(eng.sr),
                    "-c:a", "aac", "-b:a", "56k", "-movflags", "+faststart", m4a], check=True)
    os.unlink(wav)
    dur = len(audio) / eng.sr
    with open(tmap, "w", encoding="utf-8") as fh:
        json.dump({"v": 1, "dur": round(dur, 3), "words": ch["words"], "chunks": times}, fh, separators=(",", ":"))
    return dur, time.time() - t0


def parse_range(spec, n):
    if not spec:
        return set(range(1, n + 1))
    out = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("books", nargs="*", help="<section>/<book> ids; default: books with \"narrate\": true")
    ap.add_argument("--voice", default=None, help=" | ".join(VOICES))
    ap.add_argument("--chapters", default=None, help="e.g. 1,3-5 (1-based)")
    ap.add_argument("--force", action="store_true", help="make everything again")
    ap.add_argument("--no-check", action="store_true", help="skip the Whisper listen-back check (faster, riskier)")
    ap.add_argument("--verbose", action="store_true", help="print what Whisper heard for every chunk")
    args = ap.parse_args()
    global VERBOSE
    VERBOSE = args.verbose
    checker = None if args.no_check else Checker()

    todo = [(b, args.voice) for b in args.books] if args.books else opted_in()
    if not todo:
        print('Nothing to narrate. Pass a book id or add "narrate": true to a book.json.')
        return
    if not os.path.exists(os.path.join(ROOT, "index.html")):
        sys.exit("Build the reader first: python3 tools/build-reader.py")

    for book_id, voice in todo:
        voice = args.voice or voice or "ryan"
        if voice not in VOICES:
            sys.exit(f"unknown voice {voice!r}; choose from {', '.join(VOICES)}")
        eng = Engine(voice)
        book = plan_of(book_id)
        slug = book_id.replace("/", "-")
        d = os.path.join(OUT, slug)
        os.makedirs(d, exist_ok=True)
        idx = read_json(os.path.join(d, "index.json"), {}) or {}
        prev = {c["id"]: c for c in idx.get("chapters", [])}
        want = parse_range(args.chapters, len(book["chapters"]))
        label = VOICES[voice]["label"]
        print(f"\n{book['title']} — {len(book['chapters'])} chapters · voice {label} → audio/{slug}/")
        entries, keep = [], {"index.json"}
        for k, ch in enumerate(book["chapters"], 1):
            base = f"{k:02d}-{slugify(ch['title'])}"
            m4a, tmap = os.path.join(d, base + ".m4a"), os.path.join(d, base + ".json")
            h = hashlib.sha256((MODELS[VOICES[voice]["engine"]] + "|" + voice + "|v2\n" +
                                "\n".join(c["text"] for c in ch["chunks"])).encode()).hexdigest()[:16]
            old = prev.get(ch["id"])
            have = old and os.path.exists(os.path.join(d, old["file"])) and os.path.exists(os.path.join(d, old["map"]))
            fresh = have and old["hash"] == h
            if k not in want:
                if have:  # not asked for this run: keep what exists, even if its text has changed since
                    keep.update([old["file"], old["map"]])
                    entries.append({**old, "n": k, "title": ch["title"]})
                    print(f"  {'=' if fresh else '~'} {old['file']}" + ("" if fresh else "  (text changed — re-run for this chapter)"))
                continue  # never made: Kokoro reads it live
            keep.update([base + ".m4a", base + ".json"])
            if fresh and not args.force:
                entries.append({**old, "n": k, "title": ch["title"]})
                print(f"  = {base}.m4a")
                continue
            print(f"  + {base}  ({ch['words']} words)")
            dur, work = render_chapter(eng, ch, m4a, tmap, checker)
            entries.append({"id": ch["id"], "n": k, "title": ch["title"], "file": base + ".m4a", "map": base + ".json",
                            "dur": round(dur, 1), "hash": h, "voice": voice, "label": label,
                            "bytes": os.path.getsize(m4a)})
            print(f"    {dur/60:.1f} min of audio in {work/60:.1f} min  ({work/max(dur,1):.2f}× real time, "
                  f"{os.path.getsize(m4a)//1024} KB)")
        for f in os.listdir(d):
            if f not in keep:
                os.unlink(os.path.join(d, f))
        with open(os.path.join(d, "index.json"), "w", encoding="utf-8") as fh:
            json.dump({"book": book_id, "chapters": entries}, fh, indent=1)
        total = sum(e["dur"] for e in entries)
        print(f"  audio/{slug}/index.json — {len(entries)} chapters, {total/3600:.1f} h, "
              f"{sum(e.get('bytes',0) for e in entries)/1048576:.0f} MB. Now: python3 tools/build-reader.py")


if __name__ == "__main__":
    main()
