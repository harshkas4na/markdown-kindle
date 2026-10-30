# 12. Creative Uses 0G Did Not Plan For

> [!STORY] The jugaad
> Every Mumbai mechanic knows jugaad: the fix nobody designed, made from what is lying around, that works better than the official part. A scooter horn wired to a bicycle. A pressure cooker whistle as a timer. The best hackathon builds are jugaad on a sponsor's stack: they use a piece for a job its makers never imagined, and the makers, watching, think "we should have thought of that."

Here are the five best pieces of 0G jugaad in the corpus, and then the ones we can do.

## The five best

**1. A 0G proof checked on another chain, with no bridge (Hands Unchained).** The enclave signs with a plain Ethereum-style signature. A contract on Hedera recomputes the digest and recovers the signer, comparing it with the signer address read from 0G's registry. The backend that relays the answer can choose which verdict to send, but cannot forge one. 0G built signatures for its own users to check. This team made them a cross-chain fact.

**2. Binding the job into the signature (Mithra).** Put a hash of the job at the top of the prompt. The model repeats it in the answer. The enclave signs a body that now contains the job's hash. Without running their own enclave, they made the signature prove *which job* was done, five out of five times, checked in their test suite.

**3. A sealed taste judge (Lortnoc Tahc).** A steganography tool needed to choose which of several cover sentences sounded most natural. They asked a 0G model to judge, and it only ever saw the public cover text. 0G sold sealed inference for secrets. They used it as an impartial referee.

**4. The customer's own proof sheet (Happy Hour).** Tap any loyalty punch and see the enclave's signature fetched live from the request id. Verification, which every other team showed to judges, was shown to the user.

**5. Seal only what someone would dispute (0run).** A small attested model produces the one contestable number; a large model writes everything else and cites it. Cheaper, faster, and the proof lands exactly where an argument would start.

Close behind: Zero-In asked a 0G vision model to name the flag in its own generated portrait and fixed it when it was wrong. Hanami made an agent pass an attested eight-scenario exam before it could be minted. Overlap's verdict was deliberately almost zero bits.

## The corners nobody has touched

The research agent searched all 2,476 projects. Three pieces of 0G have **never** been used:

1. **The Decisions API (laya and Vela).** A model that answers in calibrated probabilities. Nobody has built a gate on it.
2. **Sealed Whisper.** Nobody has sent voice to a sealed enclave on 0G. Shrimpy, the voice journal, ran Whisper in the browser instead.
3. **The Storage Key-Value layer.** Everyone used the log layer: upload a blob, download a blob.

Judges reward the corner of their own product that nobody else found. Our project uses the first two centrally and can use the third for memory.

## Our jugaad, the ones we can actually build

> [!PROJECT] The screen as a body
> The Physical AI track says "0G is the brain, not the spinal cord: motion stays on the device". Everyone reads that as robots. A pointer that moves across your screen is motion. The screen is the body. That framing is ours, and it is the line for the 0G booth.

> [!PROJECT] laya as the tutor's conscience
> Every other "safe-stop" in the corpus is a timeout or a heuristic. Ours is a calibrated probability from a sealed model, with a rule a judge can read: act above 0.8, ask between 0.5 and 0.8, hold below. The refusal is logged with its request id. A judge can watch the tutor say "I won't guess" and then open the proof.

> [!PROJECT] Vela as a redactor, before anything leaves the laptop
> Vela 2.0 answers "span" questions: it marks the characters in a text that are, say, personal information. If the screen outline contains a customer's name or an account number, a Vela pass could mark it, and the tutor could replace it with a placeholder before the brain sees it. Even the sealed model never sees the name. This is a stretch goal, and a strong sentence for the CROPS track.

> [!PROJECT] Proof sheet for the learner
> Happy Hour's move, for us: every pointer move in the session gets a small "how do I know?" link that shows the request id, the model, the provider and the re-checked signature. The learner, not just the judge, can audit their own session.

> [!LINKS]
> [Hands Unchained's code](https://github.com/grmkris/eth-global-lisbon-2026-hands-unchained) · [Mithra](https://ethglobal.com/showcase/mithra-c5q9f) · [Lortnoc Tahc](https://ethglobal.com/showcase/lortnoc-tahc-y1d3j) · [Happy Hour](https://ethglobal.com/showcase/happy-hour-v3o03) · [0run's code](https://github.com/AdCazzum/0run) · [Zero-In](https://ethglobal.com/showcase/zero-in-cwa3e) · [Hanami](https://ethglobal.com/showcase/hanami-cymnu)
