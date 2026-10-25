# TODO

Things worth doing later. Not started unless a box is ticked.

---

## Local AI for "Ask AI" (offline, no rate limits)

**Status: not started.** The reader already has the *slot* for this — ⚙ in the Ask AI
panel lists "Ollama (this machine)" and "LM Studio (this machine)" as providers, and
the failover logic treats them like any other. What's missing is the actual model on
the machine: as of this writing Ollama is **not installed** here, so picking that
provider just errors with a connection failure.

**Why bother**, given Gemini + OpenRouter already solve the rate-limit problem: a
local model never rate-limits, works on a plane (the reader is already an offline
PWA — this is the last piece that isn't), and never sends the book you're reading
to anyone else's server.

### Steps

```sh
brew install ollama
OLLAMA_ORIGINS='*' ollama serve     # leave running
ollama pull qwen2.5:7b              # in another terminal; ~4.7 GB
```

Then in the reader: ✦ Ask → ⚙ → provider **Ollama (this machine)** → ↻ to load the
model list → pick `qwen2.5:7b` → Save.

### Gotchas found while building this

- **`OLLAMA_ORIGINS='*'` is not optional.** Ollama's default CORS policy rejects the
  reader page, and the failure looks like a generic network error. The panel's error
  message for local providers names this specifically.
- **Deployed vs local doesn't matter — the *device* does.** The request is made by the
  browser, and Chrome exempts `http://localhost` from mixed-content blocking, so even
  the GitHub Pages build can reach a local Ollama. But opening the deployed reader on
  a *phone* means `localhost` is the phone. Local models only work on machines that
  are both running Ollama and viewing the page.
- Model sizing: 7B is the sweet spot for a 16 GB machine. Below ~3B the answers get
  too vague to be useful for "explain this passage"; above 13B it will swap.

### Model candidates

| Model | Pull | Notes |
|---|---|---|
| `qwen2.5:7b` | ~4.7 GB | Best default — strong at explanation and summarising |
| `llama3.2:3b` | ~2.0 GB | For a weaker machine; noticeably shallower |
| `gemma3:4b` | ~3.3 GB | Good middle ground |
| `phi4-mini` | ~2.5 GB | Punches above its size on reasoning |

---

## Fine-tune a model for this reader's voice

**Status: not started.** No dataset, no training run, no model. This is a genuinely
separate project from the local-AI setup above, and it should be done *after* it —
running a stock local model for a few weeks is what tells you whether fine-tuning is
even worth it.

**Do it only if** the stock model is consistently wrong in a *specific, repeatable*
way — e.g. it ignores the "don't spoil later chapters" instruction, or won't stay in
the 2–6 sentence house style that `aiSystemPrompt()` asks for. If the complaint is
"the answers aren't smart enough", fine-tuning will not fix that; a bigger model or a
better prompt will.

### Steps

1. **Collect data.** Aim for 300–1000 example pairs. The cheapest source is this repo
   itself: run the existing Ask AI against real chapters with a strong model (Gemini
   2.5 Pro), keep the answers you'd have wanted, and edit the rest by hand. Match the
   real prompt shape — system prompt from `aiSystemPrompt()`, the selected passage,
   the question — so training input looks like production input.
2. **Train a LoRA** on the same base you're already running locally (`Qwen2.5-7B-Instruct`),
   so the merged result drops straight into Ollama. Unsloth or Axolotl on a rented
   A100 — a few hours, roughly $5–15. A full fine-tune is not warranted here.
3. **Export to GGUF** and register it:
   ```sh
   ollama create my-reader -f Modelfile   # Modelfile: FROM ./my-reader-q4.gguf
   ```
   It then shows up in the ⚙ model list like any other, no reader code changes.
4. **Evaluate honestly.** Hold out ~50 examples from step 1 and compare the fine-tune
   against the stock model on them before switching over. Fine-tunes routinely come
   out *worse* on a small dataset — be ready to bin it.

---

## Listen: background sound that follows the chapter's mood

**Status: not started** (idea #10 from the audiobook brainstorm, 2026-10-25 — parked
for later on purpose). Under the Kokoro voice, play a quiet ambient bed — rain, a café,
a fire, wind — chosen from the chapter's tone, ducked under the speech.

- **Picking the mood:** ask the Ask AI provider once per chapter for one word from a
  fixed list (`rain | cafe | fire | night | wind | none`) and cache it per chapter id,
  or let the reader pick it in the Listen bar.
- **Sound:** a few loopable files (CC0, ~30–60 s each, small Opus/AAC) in `public/ambient/`,
  played through a second `<audio>` at ~10–15% volume. A Web Audio gain node would let it
  duck while a sentence plays, but iOS only allows Web Audio after a tap — start it on the
  same tap as Play.
- **Gotchas to check first:** the page is cross-origin isolated now (COEP require-corp),
  so the sound files must be same-origin; two `<audio>` elements on iOS share one audio
  session, so test that the bed keeps going between sentences and with the screen locked.

---

## Smaller ideas

- Curated model ids in `AI_PROVIDERS` (`tools/reader-template.html`) go stale as
  providers retire models. The ↻ button covers this at runtime, but the defaults are
  worth a re-check every few months.
- No provider is verified against its live API — the failover logic was tested against
  a mock server, and Gemini/Groq/OpenRouter/etc. were wired from their documented
  OpenAI-compatible endpoints. Confirm each one the first time you put a real key in.
