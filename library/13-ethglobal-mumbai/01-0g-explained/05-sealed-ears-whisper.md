# 5. Ears: Whisper on 0G, and Why We Might Listen on the Laptop Instead

> [!STORY] The stenographer and the messenger
> In the old Bombay High Court, a stenographer sat behind a carved wooden screen and took down every word said in the room. Imagine she now works inside the glass kitchen: she hears your words, types them, and cannot repeat them to anyone because nobody can open her door.
>
> But your words still have to reach her. For some kitchens, 0G seals them in a locked tin before the messenger picks them up, so he carries something he cannot read. For the stenographer's kitchen, it doesn't, yet. The messenger carries your words in the open and swears an oath never to repeat or keep them. He is honest, and 0G publishes the oath. But it is an oath, not a lock.

That is the truth about speech on 0G today, and it matters for a project whose whole promise is privacy.

## The facts

- **Model**: `whisper-large-v3`, Private (TeeML, runs in an enclave), zero data retention, multilingual transcription and translation. One provider.
- **Price**: $0.00013 per second of audio, about $0.0078 a minute or $0.47 an hour.
- **Endpoint**: `POST https://router-api.0g.ai/v1/audio/transcriptions`, OpenAI-shaped, **multipart** (or a JSON body with `file_base64`). Because it is multipart, the verify flag goes in the URL: **`?verify_tee=true`**.
- **Formats**: only `json` (the default) or `verbose_json`. The docs page still lists text, srt and vtt, but the router now refuses them, and it refuses `stream: true` too.
- **Mainnet only.** The testnet router serves two models, and Whisper is not one of them.
- **Not end-to-end encrypted.** 0G's Encrypted Transit, launched in October 2026, covers only GLM-5.3, 0GM-1.0 and the two Qwen3 embedding models. For Whisper, laya, Vela, Z-Image and 0GM-SIA, the router reads the request in memory and keeps none of it: zero data retention as a policy, not hardware.

So "sealed Whisper" is half true. The model runs in the enclave. The audio crosses 0G's router readable.

## What 0G cannot do at all: speak

0G has six text-to-speech models, all MiniMax, and **all on the Standard tier, with no attestation**. There is no sealed voice output. So the tutor speaks on the laptop. That was always the plan ("motion stays on the device"), and now it is also the only private option.

## The design choice: where does the tutor listen?

Two honest options, and the lab measures both on Saturday 31 October.

**Option A: listen on the laptop.** A small Whisper model runs on the Mac itself, through **whisper.cpp**, a public open-source library (allowed under the Fresh rule: public libraries are fine). On an M3, a base-size model transcribes a short question in well under a second. The audio never leaves the laptop. Only the text goes to 0GM-1.0, which *is* end-to-end encrypted.

**Option B: listen on 0G.** Send the clip to Whisper Large v3 on 0G. Better accuracy, especially for Hindi or a mix of Hindi and English, and it uses a corner of 0G nobody in the corpus has touched. But the audio crosses the router readable, under a policy, and it adds a network round trip.

| | A: on the laptop | B: Whisper on 0G |
|---|---|---|
| Who can hear the audio | nobody but the laptop | the enclave, and the router in memory (no retention, by policy) |
| Speed | likely fastest (no network) | a round trip plus upload |
| Accuracy | good for clear English; weaker on accents and mixed languages | Whisper Large v3, the strongest open model |
| Judges | "privacy all the way down" (EF loves this) | "used a neglected 0G corner" (0G likes this) |

**The likely answer: A by default, B as a switch.** The tutor listens on the laptop unless the user turns on "better accuracy (uses 0G Whisper)", and the README says exactly what that switch costs in privacy. The Physical AI track asks for a 0G call in the decision loop for *vision, voice or decision*: 0GM-1.0 (vision) and laya (decision) already satisfy it, so voice can stay local without losing the track.

> [!GOTCHA] Never use the browser's built-in speech recognition
> Chrome's `webkitSpeechRecognition` sends your audio to Google's servers. It looks local and it is not. For a privacy product it is the one API that would quietly break the promise. Same caution for speech synthesis: on macOS the system voices are local, but some voices in the list are online. Pick a local one.

## What screen-tutor already taught us about voice

- **Push-to-talk beats always-listening** for a demo: no accidental triggers, no guessing when the user finished, a clean clip.
- **Apple's voice processing refuses aggregate audio devices**, so echo cancellation silently does not run and the tutor hears itself. On the built-in mic, zero self-interruptions. In a browser, Chrome's own echo cancellation handles it.
- **Measure the slowest link before optimising anything.** In screen-tutor's local cascade, the cloned voice synthesising at about 0.9 times real time was the ceiling, not the network.

> [!PROJECT]
> Hold a key, speak, release. The clip goes to whisper.cpp on the laptop (default) or to Whisper on 0G (switch). The text plus the screen outline becomes the brain's prompt. The answer is spoken by a local voice.

> [!TRY] For the lab
> Five questions, three ways: whisper.cpp base model, whisper.cpp small model, Whisper Large v3 on 0G. For each: time from key release to text, and word errors. Include two questions in Hinglish. Then decide the default with numbers.

> [!LINKS]
> [Whisper Large v3 on 0G](https://pc.0g.ai/models/whisper-large-v3) · [0G's privacy post: which models are end-to-end encrypted](https://0g.ai/blog/data-privacy-on-0g-private-computer) · [Router privacy docs](https://docs.0g.ai/developer-hub/building-on-0g/compute-network/router/privacy) · [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
