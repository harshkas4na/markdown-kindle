#!/usr/bin/env python
"""Listen back to studio audio with Whisper, chunk by chunk, and diff each
chunk against the text it was made from — so a dropped clause, an added
sound or a timing map that is out of step is caught without ears.

Usage (inside tools/narrate/.venv):
  python tools/narrate/check.py audio/<book>/01-foo.m4a [more chapters…]
  python tools/narrate/check.py --text "the words" sample.wav      # one file, one text
Prints every chunk that differs and the chapter's word-error estimate.
Exit 1 when a chapter is more than 5% off.
"""
import argparse, difflib, json, os, re, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STT = "mlx-community/whisper-large-v3-turbo-asr-fp16"
_model = None


def norm(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower().replace("’", "'")).split()


def transcribe(audio, sr):
    global _model
    import soundfile as sf
    if _model is None:
        from mlx_audio.stt.utils import load_model
        _model = load_model(STT)
    path = os.path.join(tempfile.gettempdir(), f"check-{os.getpid()}.wav")
    sf.write(path, audio, sr)
    return _model.generate(path, language="en").text


def diff(ref, hyp):
    r, h = norm(ref), norm(hyp)
    sm = difflib.SequenceMatcher(None, r, h, autojunk=False)
    ops = [(tag, " ".join(r[i1:i2]), " ".join(h[j1:j2])) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]
    n = sum(max(len(a.split()), len(b.split())) for _, a, b in ops)
    return n, len(r), ops


def load_audio(path):
    import numpy as np
    wav = os.path.join(tempfile.gettempdir(), f"check-in-{os.getpid()}.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "24000", wav], check=True)
    import soundfile as sf
    a, sr = sf.read(wav, dtype="float32")
    return a, sr


def chapter_chunks(m4a):
    """[(text, t0, t1)] for a chapter: the book plan's chunk texts + the timing map."""
    d = os.path.dirname(m4a)
    idx = json.load(open(os.path.join(d, "index.json"), encoding="utf-8"))
    entry = next((e for e in idx["chapters"] if e["file"] == os.path.basename(m4a)), None)
    if not entry:
        sys.exit(f"{m4a} is not in {d}/index.json")
    plan = json.loads(subprocess.run(["node", os.path.join(ROOT, "tools/podcast/plan.mjs"), idx["book"]],
                                     capture_output=True, text=True, check=True).stdout)
    ch = next(c for c in plan["chapters"] if c["id"] == entry["id"])
    tmap = json.load(open(os.path.join(d, entry["map"]), encoding="utf-8"))
    texts = {(c["s"], c["e"]): c["text"] for c in ch["chunks"] if c["text"]}
    out = []
    for s, e, t0, t1 in tmap["chunks"]:
        out.append((texts.get((s, e), ""), t0, t1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--text", help="reference text for a single file (instead of the book plan)")
    a = ap.parse_args()
    worst = 0
    for f in a.files:
        audio, sr = load_audio(f)
        parts = [(a.text, 0, len(audio) / sr)] if a.text else chapter_chunks(f)
        bad = total = 0
        for text, t0, t1 in parts:
            if not text:
                print(f"    ? no plan text for chunk at {t0:.1f}s — the book text changed since this was made")
                continue
            heard = transcribe(audio[int(t0 * sr):int(t1 * sr)], sr)
            n, words, ops = diff(text, heard)
            bad += n; total += words
            if n > max(1, round(0.12 * words)):
                print(f"    {t0:7.1f}s  {text[:80]!r}")
                for tag, r, h in ops:
                    print(f"             {tag:8} {r!r} -> {h!r}")
        rate = bad / max(1, total)
        print(f"{f}: {total} words, about {100 * rate:.1f}% differ")
        worst = max(worst, rate)
    sys.exit(1 if worst > 0.05 else 0)


if __name__ == "__main__":
    main()
