#!/usr/bin/env python
"""Render one passage with several voices and time each: pick the narrator by ear.

Usage: python tools/narrate/bench.py [out_dir]   (run inside tools/narrate/.venv)
Writes <name>.wav files plus bench.json with seconds-of-work per second-of-speech.
"""
import json, os, sys, time, traceback
import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model

OUT = sys.argv[1] if len(sys.argv) > 1 else ".tmp/voice-samples"
os.makedirs(OUT, exist_ok=True)

# Two paragraphs from library/02-books/show-your-work (same text for every voice)
TEXT = ("There are a lot of destructive myths about creativity, but one of the most dangerous is the lone genius myth. "
        "An individual with superhuman talents appears out of nowhere at certain points in history, free of influences or precedent, "
        "with a direct connection to God or The Muse. When inspiration comes, it strikes like a lightning bolt! "
        "A lightbulb switches on in his head, and then he spends the rest of his time toiling away in his studio.\n"
        "We're all terrified of being revealed as amateurs. But in fact, today it is the amateur, the enthusiast who pursues her work "
        "in the spirit of love, who often has the advantage over the professional. \"In the beginner's mind, there are many possibilities,\" "
        "said Zen monk Shunryu Suzuki. \"In the expert's mind, there are few.\"")
SENTS = [s for s in TEXT.replace("\n", " ").split(". ") if s]

def run(name, make):
    print(f"\n== {name}", flush=True)
    try:
        t0 = time.time()
        parts, sr = make()
        work = time.time() - t0
        audio = np.concatenate([np.asarray(p, dtype=np.float32).reshape(-1) for p in parts])
        secs = len(audio) / sr
        sf.write(os.path.join(OUT, name + ".wav"), audio, sr)
        r = {"name": name, "speech_s": round(secs, 1), "work_s": round(work, 1), "rtf": round(work / secs, 2), "sr": sr}
        print(r, flush=True)
        return r
    except Exception as e:
        traceback.print_exc()
        return {"name": name, "error": str(e)[:300]}

results = []

# 1. Kokoro, the current voice (baseline)
def kokoro():
    m = load_model("mlx-community/Kokoro-82M-bf16")
    out = [r.audio for r in m.generate(text=TEXT, voice="af_heart", lang_code="a")]
    return out, 24000
results.append(run("1-kokoro-heart", kokoro))

# 2/3. Qwen3-TTS 1.7B CustomVoice: preset English narrators with a style instruction
qwen = None
def qwen_custom(speaker, instruct):
    def f():
        global qwen
        if qwen is None:
            qwen = load_model("mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit")
        out = []
        for r in qwen.batch_generate(texts=[s + "." for s in SENTS], voices=[speaker] * len(SENTS),
                                     instructs=[instruct] * len(SENTS), lang_code="english"):
            out.append((r.sequence_idx, r.audio))
        out.sort(key=lambda x: x[0])
        return [a for _, a in out], qwen.sample_rate
    return f
INSTR = "Warm, calm audiobook narrator. Natural pacing, clear emphasis on key words, slight pauses at commas."
results.append(run("2-qwen3-ryan", qwen_custom("Ryan", INSTR)))
results.append(run("3-qwen3-aiden", qwen_custom("Aiden", INSTR)))
qwen = None

# 4. Qwen3-TTS VoiceDesign: a voice described in words
def qwen_design():
    m = load_model("mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit")
    out = [r.audio for r in m.generate_voice_design(
        text=TEXT.replace("\n", " "), language="English",
        instruct="A warm, mature female audiobook narrator with a gentle, expressive, unhurried delivery.")]
    return out, m.sample_rate
results.append(run("4-qwen3-design-female", qwen_design))

# 5. Chatterbox Turbo (default built-in voice)
def chatterbox():
    m = load_model("mlx-community/chatterbox-turbo-fp16")
    out = [r.audio for r in m.generate(text=TEXT.replace("\n", " "), temperature=0.5, repetition_penalty=1.5)]
    return out, m.sample_rate
results.append(run("5-chatterbox-turbo", chatterbox))

json.dump(results, open(os.path.join(OUT, "bench.json"), "w"), indent=1)
print("\nDONE", json.dumps(results, indent=1))
