# 11. The Ones That Did Not Place, and Why

> [!STORY] The best-engineered loser
> Somewhere in the Lisbon judging pile sat dMemo: private long-term memory for coding agents, encrypted to your wallet, stored on 0G, portable across machines. Its engineering was the best in the whole corpus. It recomputed every blob's fingerprint before decrypting because the SDK's proof flag was a no-op. It measured cold restores at 3 seconds. It wrapped a popular memory library so nothing changed for the user. It did not place.
>
> The reason is one sentence long. Nothing in dMemo **decided** anything. It remembered beautifully, and a judge watching a demo saw a memory being remembered.

Losers teach more than winners, because they show the idea the room keeps building. This chapter is the ban list.

## Memory as the pitch

- **dMemo** (above): superb plumbing, no decision, no live link.
- **Kimayyy**: one persistent public AI that everyone talks to in the same shared context, with snapshots on Storage and a registry on the chain. A thought experiment with no user job.
- **BetterHalf.ai** (New Delhi): a personal agent with user-controlled memory, spread across three networks.

**Lesson:** our tutor has memory ("last time you got stuck on the Contract tab"), and it stays a supporting detail. It is never the first sentence.

## A layer for "agents" with no person in it

- **Rerun**: AI guard agents stake on their verdicts, and anyone who re-runs the check and disagrees takes the stake. Clever, solo, no end user, and its attestation did not verify on testnet.
- **Agent Router**: a layer to pick a model route by cost, latency and privacy. Partly a copy of what 0G's own router already does.
- **Recomputable Agents** and **Mithra**: 0G was one of three or four networks, a "second commitment".

**Lesson:** a person with a problem, named, in the first ten seconds of the demo.

## The closest neighbours to our idea

These three matter most, because they are near what we are building.

**Reboleira** (Lisbon) is a **Chrome extension that rebuilds any web page around the reader**: simplified, translated, re-levelled, with every link and button still wired to the real element. It extracts a semantic graph of the page, sends it to a TEE-sealed model on 0G, and draws the answer in an overlay. The reader's profile is encrypted and stored on 0G Storage. **It did not place.** It was built by the same GitHub account that won 1st with 0run. The coach won and the extension did not.

> [!PROJECT] How we differ from Reboleira
> Reboleira changes the page. The tutor leaves the page alone and **teaches you to use it**: it hears a question, points at the real button, explains while you click, and refuses to guess when unsure. Reboleira has no decision checkpoint, no voice, no episode log of decisions and no live link. The tutor's sealed decision (laya's act or hold) is visible in every turn. And our demo uses a real, private-looking screen, so the reason for sealing is felt rather than explained.

**DoomTax** (Lisbon) is a personal focus app: state what you will do, stake a little, submit evidence, and a sealed AI coach decides whether you kept your word. Sealed verdict, money moves, still no place. It ran as a World mini-app with no access to the computer, so its "evidence" was something the user pasted. **A tutor that actually sees the screen has the evidence DoomTax lacked.**

**Goggles** (New Delhi) is the only desktop screen-watcher in the corpus: a Mac service that looks at every screenshot and renames the file sensibly, "privately". Its write-up was two paragraphs and named no 0G model. It placed nowhere.

**Shrimpy** (Lisbon) is the cousin to watch. A private AI journal: write or speak, three agents reflect on the entry inside a TEE using Private mode on 0G, and the entry is encrypted and stored. Voice came from a small Whisper running in the browser, not sealed Whisper on 0G. **It won Sui's prize, not 0G's.** Its honest line about the TEE is the best sentence in the corpus: it protects you from the provider, not from physics. We will borrow that honesty.

## Doing everything right and still losing

- **BlindSample**: a buyer asks questions about a private dataset and gets scored answers without seeing the rows. One sealed router call, with the request id and TEE proof recorded, and **no fallback: if 0G fails, no score is published.** That is exactly the fail-closed behaviour Mumbai asks for. It did not place.
- **Overlap**: a sealed two-party negotiation room that tells each side only "workable" or "not workable". Fails closed. Did not place.
- **Sekaigent**: used all four 0G components, on mainnet. Did not place.

**Lesson:** fail-closed, sealed verdicts, breadth, honesty: all necessary, none sufficient. What decides it is a product a judge feels in one sentence, demoed live.

## The five ways 0G entries fail

1. **Memory as the pitch** (dMemo, Kimayyy, BetterHalf).
2. **A generic layer with no user** (Agent Router, Rerun, Recomputable Agents, Mithra).
3. **Attestation that never verified on testnet.** Chat ids returning `chat_id_not_found` through the testnet router (AEGIS), the router "never yields a verifiable signature" (Overlap), `processResponse` returning no valid signature (Rerun), no TeeML chat model live on the testnet router (dMemo). Winners worked around it with the Direct broker. Chapter 9 is the fix list.
4. **Storage on the hot path.** Uploads unreadable for 22 minutes (0run), a wait function that retries forever (dMemo), 10 to 15 seconds to finalise (Recomputable Agents).
5. **0G as a plan or a spike.** "Prepares for Storage", "can route to Compute", "planned migration". In 2026, the auditor-style code review catches it.

> [!LINKS]
> [dMemo](https://ethglobal.com/showcase/dmemo-0d378) · [Reboleira](https://ethglobal.com/showcase/reboleira-ew70c) · [DoomTax](https://ethglobal.com/showcase/doomtax-1dxh4) · [Shrimpy](https://ethglobal.com/showcase/shrimpy-c3mdz) · [Goggles](https://ethglobal.com/showcase/goggles-3qrtf) · [BlindSample](https://ethglobal.com/showcase/blindsample-07ci5) · [Overlap](https://ethglobal.com/showcase/overlap-7ninc) · [Rerun](https://ethglobal.com/showcase/rerun-q5ypt) · [Mithra](https://ethglobal.com/showcase/mithra-c5q9f) · [Sekaigent](https://ethglobal.com/showcase/sekaigent-opxax)
