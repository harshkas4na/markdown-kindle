# 20. The Field Guide: Every Gotcha in One Place

> [!STORY] The pilot's checklist
> Pilots with ten thousand hours still read a checklist before every take-off. Not because they forget, but because the one thing that goes wrong is never the thing you were thinking about. Read this chapter the night before kickoff, and again at 03:00 on Saturday.

Each line says what goes wrong and what to do. The source is in brackets.

## Compute and the router

- **Private is opt-in.** Send `X-0G-Provider-Trust-Mode: private` on every call, or the router may not pin a TEE provider. (0G model pages)
- **Private mode with no TEE provider returns 503** `no_provider_for_trust_mode` and does not fall back. Treat it as a safe-stop. (0G docs, via the brief)
- **Most "Verified" models are TeeTLS**: the route is attested, not the execution. Never call them sealed. (0G docs)
- **Only one Private model takes images**: 0GM-1.0-35B-A3B. (pc.0g.ai/models, 30 October)
- **0GM-1.0 has thinking on by default**, and non-streaming requests must finish within about 10 minutes. Stream long outputs; measure thinking on and off. (model page)
- **A tiny `max_tokens` on a reasoning model can return empty text.** (0run)
- **Rate limits** come back as 429 with `Retry-After`; read the `X-RateLimit-*` headers. Zero-In was rate-limited live during onboarding. (brief, Zero-In)
- **`tee_verified` is the router's boolean, not a proof.** Fetch the signature when it matters. (0G docs)
- **Whisper is multipart**: pass `verify_tee=true` as a query parameter. Only `json` and `verbose_json` formats work; no streaming. (0G docs, router changelog)
- **Only four models are end-to-end encrypted** (0GM-1.0, GLM-5.3, two Qwen3 embeddings). Whisper and laya run in a TEE but the router reads them in memory under a no-retention policy. Send them nothing private. (0G privacy post)
- **On an E2EE request, `tee_verified` is absent**, even with `verify_tee`. Check the attested gateway and the `X-Provider` header instead. (router changelog)
- **The testnet router has two models.** Whisper, laya and GLM-5.3 are mainnet-only. Fund a mainnet key. (measured 30 October)
- **Never ship 0G keys in code.** The user brings their own key. (0G docs)
- **laya reads only 512 tokens** of English state; longer is cut off. (model page)
- **Testnet and mainnet are separate worlds**: separate endpoints, keys and balances. A mainnet key does not work on testnet. (0G router docs, via the brief)

## Verification

- **Signatures expire after about 20 minutes** at the provider. Fetch and store them right after each decision. (0G serving broker config)
- `processResponse` checks the signature, not that the signed text matches your content. (SDK source)
- Chat id from the **`ZG-Res-Key` header**, not the body. (Mithra)
- The signature covers a hash of the **raw** response body. Don't re-serialise before hashing. (Mithra)
- The signer is **`teeSignerAddress`**, not the provider address. (Overlap)
- Check **`teeSignerAcknowledged`**. Try recovery values 27 and 28 on a 64-byte signature. (Mithra)
- On testnet in July, router signatures often failed to verify; winners used the Direct broker for the decision they needed to prove. Re-test on our setup. (AEGIS, Overlap, Rerun)

## Storage

- **Use the Turbo indexers**; the Standard ones returned 503 or nothing on 30 October. **KV reads need your own KV node**; the documented one timed out. (measured)
- **Uploads are slow and can hang.** 0run saw 22+ minutes before a file was readable, and an upload call that never returned. **Never put Storage on the decision path.** Upload in the background, cache locally, compute the Merkle root yourself. (0run)
- **Put a timeout on every SDK call**: 120 s upload, 30 s download. `waitForLogEntry` retries forever otherwise. (0run, dMemo)
- **The TypeScript SDK returns `[value, error]` pairs**; it does not throw. Check the error every time. (Hands Unchained)
- **`upload()` returns an object**; unwrap `.rootHash`. Download refuses to overwrite an existing file. (Rerun)
- **A wrong decryption key does not throw**: it silently returns ciphertext. Call `indexer.peekHeader(rootHash)` first. Lose the AES key and there is no server-side recovery. (brief)
- **The SDK's `with_proof` flag was a no-op** for dMemo, and AES-CTR has no authentication tag. Recompute the blob's Merkle root from the raw ciphertext and compare before decrypting. (dMemo)
- **Downloads use `fs`** and do not work in a browser. Do Storage from a Node process, not the extension page. (brief)
- **The Storage SDK's old axios breaks inside Cloudflare Workers.** Use a Node sidecar. (MASS)

## Chain

- **Galileo's chain id is 16602 (hex 0x40DA)**; mainnet is 16661 (0x4115). The Builder Hub's hex values are wrong. (measured)
- **WebSocket is refused on Galileo** and works on mainnet. (measured)
- **Deploy with `--legacy`** and a fixed gas price; the default EIP-1559 tip is rejected. Pin `evmVersion: cancun`. (Rerun, brief)
- **Receipts take about 10 seconds**, and log subscriptions on the public Galileo RPC delivered nothing. Poll, don't subscribe. (zerobot notes, via the brief)
- **The faucet gives 0.1 0G a day**, while the Direct broker's ledger needs a 3 0G minimum deposit. Use the router with team credits; claim the faucet daily before the event; Lortnoc Tahc got a top-up at the 0G booth. (brief, Lortnoc Tahc)
- **0G's reference agent-token contract is 24.6 KB**, over the contract-size limit. Write a minimal one if you need ERC-7857. (0run)

## The browser extension

- **Chrome kills an idle service worker after about 30 seconds.** Don't keep state in it between turns. (Chrome docs, Anon-RPC harness notes)
- **One offscreen document per extension.** Put the mic and any sandbox there. (Chrome docs)
- **Anon-RPC's extension harness fails silently** on hand-copied static files, a missing `blob:` in `script-src`, or a port in a host permission. (Anon-RPC README)
- **Anon-RPC's tor gateway is demonstration-only** and may be exhausted at the venue. Have Nym as a backup or leave it off. (Anon-RPC docs)

## The desktop

- **Accessibility and Screen Recording permissions** are per app and can be silently ignored after a code-signing change. Grant them Thursday afternoon and rehearse after a reboot. (velocity notes, edge notes)
- **Aggregate audio devices break echo cancellation** on macOS: the tutor hears itself. Use the built-in mic. (screen-tutor)
- **Chrome's built-in speech recognition sends audio to Google.** Never use it; transcribe with whisper.cpp on the laptop. Pick a local speech-synthesis voice, not an online one. (Chrome docs)

## The submission

- **Video 2:00 to 2:59**, 720p or better, no speed-up, no AI voice, not on a phone. (ETHGlobal, 0G)
- **Fresh repo after 21:00 Thursday**, small commits, AI use documented, spec files committed. (ETHGlobal rules)
- **No third-party trackers in the client**, self-hosted fonts. (EF CROPS)
- **One EF prize per project.** (EF)
- **Submit by 08:00**, select 0G and the Ethereum Foundation, opt into finalist judging. (ETHGlobal)
