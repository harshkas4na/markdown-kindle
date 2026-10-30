# 21. Links and Glossary

## The pages to bookmark

**0G, building**
- [The model catalog](https://pc.0g.ai/models) and [the same as JSON](https://router-api.0g.ai/v1/models), the source of truth
- [Router API reference and changelog](https://0gfoundation.github.io/0g-router/)
- [Router quickstart](https://docs.0g.ai/developer-hub/building-on-0g/compute-network/router/quickstart)
- [Router privacy: what is retained](https://docs.0g.ai/developer-hub/building-on-0g/compute-network/router/privacy)
- [Verifiable execution: verify_tee and signatures](https://docs.0g.ai/developer-hub/building-on-0g/compute-network/router/features/verifiable-execution)
- [Routing headers](https://docs.0g.ai/developer-hub/building-on-0g/compute-network/router/routing)
- [laya](https://pc.0g.ai/models/laya), [0GM-1.0](https://pc.0g.ai/models/0gm-1.0-35b-a3b), [Whisper Large v3](https://pc.0g.ai/models/whisper-large-v3)
- [Which models are end-to-end encrypted](https://0g.ai/blog/data-privacy-on-0g-private-computer)
- [Why this is private, and its limits](https://github.com/0gfoundation/0g-pc-e2ee/blob/main/docs/why-this-is-private.md)
- [Storage SDK](https://docs.0g.ai/developer-hub/building-on-0g/storage/sdk)
- [Testnet overview](https://docs.0g.ai/developer-hub/testnet/testnet-overview) and [all addresses on one page](https://docs.0g.ai/ai-context)
- [Agentic ID](https://build.0g.ai/agentic-id) and [its examples](https://github.com/0gfoundation/agenticID-examples)
- [zerobot's notes](https://github.com/0gfoundation/zerobot/blob/main/AGENTS.md) and [Project Floaty](https://github.com/0gfoundation/project-floaty)
- [Builder Hub changelog](https://build.0g.ai/updates)
- [Faucet](https://faucet.0g.ai) · [Galileo explorer](https://chainscan-galileo.0g.ai) · [Private Computer dashboard](https://pc.0g.ai)

**0G, context**
- [0G home](https://0g.ai) · [Builder Hub](https://build.0g.ai) · [Docs](https://docs.0g.ai) · [Whitepaper](https://docs.0g.ai/whitepaper.pdf)
- [Lisbon recap](https://0g.ai/blog/ethglobal-lisbon-2026-recap) · [Introducing iAI](https://0g.ai/blog/introducing-infinite-ai)

**Ethereum Foundation**
- [Mumbai EF prize page](https://ethglobal.com/events/mumbai/prizes/ethereum-foundation) · [The EF Mandate](https://blog.ethereum.org/2026/03/13/ef-mandate)
- [Anon-RPC](https://ethereum.github.io/anon-rpc/) · [its wallet and app guide](https://ethereum.github.io/anon-rpc/wallets/) · [its GitHub](https://github.com/ethereum/anon-rpc)
- [Alternative mempools](https://www.altmempool.wtf/) · [EIP-8141](https://eips.ethereum.org/EIPS/eip-8141)
- [Kohaku](https://github.com/ethereum/kohaku) · [Walletbeat](https://walletbeat.eth.limo) · [Scaffold-ETH 2](https://github.com/scaffold-eth/scaffold-eth-2)

**ETHGlobal Mumbai**
- [Event home](https://ethglobal.com/events/mumbai) · [Rules and judging](https://ethglobal.com/events/mumbai/info/details) · [Hacker dashboard](https://ethglobal.com/events/mumbai/home) · [0G prize page](https://ethglobal.com/events/mumbai/prizes/0g)

**Libraries we may use (public, allowed under the Fresh rule)**
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) · [ethers](https://docs.ethers.org) · [viem](https://viem.sh) · [Chrome extension docs](https://developer.chrome.com/docs/extensions)

## Glossary

- **0G**: the network, and the name of its token.
- **0GM-1.0-35B-A3B**: 0G's own model; the only Private model that takes images; end to end encrypted.
- **Agentic ID**: ERC-7857 tokens that make an AI agent ownable, lendable and transferable.
- **Anon-RPC**: an EF standard that gives an app an anonymised fetch through Tor, Nym or Nox.
- **Attestation quote**: a report, signed by the processor's hardware, saying exactly which code an enclave runs.
- **Chat id**: the value in the `ZG-Res-Key` header, used to fetch a provider's signature.
- **CROPS**: Censorship resistant, Open source, Private, Secure; the EF's four properties.
- **Decisions API**: 0G's endpoint for models that answer typed questions with probabilities (laya, Vela).
- **Direct broker**: talking to one provider through 0G's compute SDK, paying on chain, instead of the router.
- **E2EE / Encrypted Transit**: the request crosses 0G's router as ciphertext. Only four models have it.
- **Episode log**: our record of every decision, with request ids, a Physical AI must-show.
- **Fresh (Start Fresh)**: all project work begins after kickoff; prior project code is not allowed.
- **Frame transaction (EIP-8141)**: native account abstraction; a transaction made of up to 64 frames.
- **Galileo**: 0G's testnet, chain id 16602.
- **iAI**: a token whose stakers get daily 0G compute credits.
- **laya**: a small Private decision model; 512-token context; input is free.
- **Merkle root**: a fingerprint of a file's contents; its address on 0G Storage.
- **noul / choice / score**: laya's three question types (yes-no, pick one, rate).
- **Private (TeeML)**: the model runs inside an attested enclave. The trust-mode header pins it.
- **Request id**: `x_0g_trace.request_id`, also the `X-Request-ID` header; the key of every 0G call.
- **Safe-stop**: what happens when 0G is unreachable or unsure. For us: freeze and say so; never guess.
- **TEE**: trusted execution environment; a part of a processor whose memory is encrypted even from its owner.
- **TDX**: Intel Trust Domain Extensions, the TEE technology 0G uses.
- **`tee_verified`**: the router's verdict on a signature. Absent on E2EE requests.
- **Verified (TeeTLS)**: the route is attested and signed; the provider still reads the prompt.
- **ZDR**: zero data retention; nothing kept after the answer. A policy, not hardware.
