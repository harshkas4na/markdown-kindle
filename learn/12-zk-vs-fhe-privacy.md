# 12 — ZK vs FHE: The Two "Privacy" Tools

Goal: these two get lumped together constantly under "privacy tech," but they solve genuinely different problems and work in completely different ways. By the end, you should be able to tell, from a hook's description, which one it should actually be using.

## Two different questions

Before the tools, separate the *questions* each one answers:

- **"Can I prove something is true, without revealing the private information behind it?"** — that's a **Zero-Knowledge proof (ZK)** question. Example: "I have at least 5,000 USDC deposited in this pool" — proven, without revealing your exact balance or wallet address.
- **"Can a computer compute on data it never gets to see in plain form?"** — that's a **Fully Homomorphic Encryption (FHE)** question. Example: "match these two encrypted trade orders against each other and tell me if they cancel out" — computed, without the contract (or anyone watching it) ever seeing the actual order sizes or directions, even during the computation itself.

They're both "privacy" tools in a loose sense, but one is about *proving a fact*, the other is about *computing on secrets*.

## Zero-Knowledge proofs (zk-SNARKs), with an analogy

**Analogy: imagine you want to prove to a bouncer that you're over 21, without showing your ID (which also reveals your exact birthdate, address, and full legal name).** A ZK proof is like a magic slip of paper that the bouncer can verify says "TRUE: this person is over 21" — cryptographically guaranteed to be correct, generated using your real ID behind the scenes — but the slip of paper itself reveals nothing else about you. The bouncer can check the proof is valid extremely quickly, without ever needing to see your actual birthdate.

The specific flavor used most often in this directory is a **zk-SNARK** (Succinct Non-interactive ARgument of Knowledge) — "succinct" meaning the proof itself is small and fast to verify (important, since verification often happens inside a gas-costing smart contract), "non-interactive" meaning you generate the proof once and anyone can check it later without needing to have a back-and-forth conversation with you.

**Where this shows up in the directory**: proving eligibility for a reward tier without revealing your full trading history (Liquidity Rewards, via a proof provider called Brevis), or proving you're a unique human without revealing your actual identity (Proof of Personhood-style compliance hooks). The common thread: *you have private data, you want to prove one true fact derived from it, and nothing more.*

## Fully Homomorphic Encryption (FHE), with an analogy

**Analogy: imagine a locked box with built-in gloves attached to the outside — like the boxes scientists use to handle dangerous materials.** You put your ingredients inside (encrypted data), and a worker outside the box can use the attached gloves to mix, measure, and combine those ingredients — performing real operations — without ever being able to open the box or directly touch the material inside. When the process is done, the box can hand you back an encrypted result, which only you (holding the key) can open and read.

FHE lets a smart contract do this with *any* mathematical operation on encrypted numbers — add them, compare them, multiply them — while the actual values stay encrypted the entire time, including during the computation, not just during storage or transmission. This is a much heavier, more computationally expensive cryptographic tool than ZK proofs, which is why FHE-on-blockchain is a newer and less mature space (Fhenix, the provider referenced most often in this dataset, is essentially building an EVM-compatible chain specifically designed to make FHE computation practical).

**Where this shows up in the directory**: encrypted order matching, where the direction and size of a trade needs to stay hidden not just from outside observers but *during the matching computation itself*, to prevent front-running (see article 7's sandwich-attack mempool problem) — this is what ShadowSwap, CipherFlow, and similar hooks are built around.

## The key distinction, side by side

| | ZK proof | FHE |
|---|---|---|
| Answers | "Is this fact true?" | "What is the result of computing on this secret?" |
| Reveals | Nothing beyond the one proven fact | Nothing at all, even mid-computation |
| Typical use here | Prove eligibility/identity without exposing details | Hide a trade's direction/size while it's being processed |
| Maturity in this dataset | More established, faster, cheaper | Newer, heavier, still maturing |

## Why it matters to keep them separate when reading the directory

If you see a hook described as "provides privacy," check *which* problem it's actually solving before assuming it fixes MEV: a ZK-based "prove I qualify for a reward without revealing my balance" hook does nothing to stop a sandwich attack — it was never trying to. An FHE-based "encrypt trade direction until execution" hook, on the other hand, is directly attacking the mempool-visibility root cause from article 7. Same buzzword ("privacy"/"zk"), genuinely different problem being solved — worth checking which one you're actually looking at before judging whether it solves the problem you care about.

## The one sentence to keep

**ZK proofs let you prove a fact derived from private data without revealing the data itself (good for eligibility/identity checks), while FHE lets a contract actually compute on encrypted data without ever decrypting it (good for hiding a trade's contents during matching/execution) — they get bundled together as "privacy tech" in casual descriptions, but they answer different questions and you should check which one a given hook is actually using before assuming it solves MEV, or eligibility, or whichever problem you actually care about.**
