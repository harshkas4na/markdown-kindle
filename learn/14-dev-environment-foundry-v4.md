# 14 — Dev Environment: Foundry + Uniswap v4

Goal: get from zero to "I have a hook compiling and a test running" — the actual mechanical setup, explained like you've never opened a terminal for a Solidity project before.

**A note before we start**: Uniswap v4's exact function names and signatures have shifted a few times as it moved from testnet to mainnet (and will likely keep evolving). Every code snippet in this and the following lessons is written to match the *shape and intent* of the real v4-periphery/v4-core APIs as of writing — treat it as "this is how the pattern works and roughly how it's written," and always cross-check exact current signatures against the live `Uniswap/v4-core` and `Uniswap/v4-periphery` GitHub repos before shipping real code. That habit — pattern-match from what you've learned, then verify exact syntax against current source — is how experienced Solidity devs actually work anyway, since the ecosystem moves fast.

## What Foundry is, and why it's the standard for this

**Foundry** is a Solidity development toolkit — think of it as the whole workbench: it compiles your contracts, runs your tests (written *in Solidity itself*, not JavaScript, which is the detail that makes it feel different from older tools like Hardhat), deploys contracts, and lets you fork mainnet state locally to test against real, live contracts. It's four command-line tools bundled together:

- **`forge`** — compile, test, build, deploy. This is the one you'll type constantly.
- **`cast`** — a Swiss-army-knife for making one-off calls: "what's the current price in this pool," "send this transaction," "decode this calldata."
- **`anvil`** — spins up a local, fake Ethereum node on your machine in one second, for fast local testing.
- **`chisel`** — a Solidity REPL (a scratchpad where you can type a line of Solidity and immediately see the result), useful for quickly checking "wait, what does this expression actually evaluate to."

## Installing it

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

That second command (`foundryup`) is also how you update Foundry later — re-run it any time.

## Starting a hook project: use the official v4 template, don't start from a blank folder

Uniswap publishes a starter template specifically for hook development — `v4-template` — which already has the correct dependencies, remappings (explained below), and a working example hook wired up. Starting here saves you from hours of dependency-version mismatches, which are the single most common source of "nothing compiles" pain in this ecosystem.

```bash
forge init my-first-hook --template uniswapfoundation/v4-template
cd my-first-hook
forge install
```

## What's actually inside the project, and why

```
my-first-hook/
├── src/                  <- your hook contracts go here
│   └── Counter.sol       <- the template's example hook (a good thing to read first)
├── test/                 <- your Solidity tests go here
│   └── Counter.t.sol
├── lib/                  <- external dependencies, installed as git submodules
│   ├── v4-core/          <- the actual Uniswap v4 PoolManager contracts (article 5's singleton)
│   ├── v4-periphery/     <- helper contracts, including BaseHook (article 15)
│   └── forge-std/        <- Foundry's own standard testing library
├── foundry.toml          <- project configuration
└── remappings.txt        <- import path shortcuts (explained below)
```

Two ideas worth understanding, not just memorizing:

**Dependencies are git submodules, not an `npm install`-style package manager.** When you see `lib/v4-core`, that's a literal clone of the Uniswap v4-core GitHub repo, pinned to a specific commit, sitting inside your project. This matters because it means "what version of v4 am I building against" is answered by "what commit is checked out in `lib/v4-core`" — if a tutorial's code doesn't compile against your setup, this is almost always why: they were pinned to a different commit of v4-core than you are.

**Remappings let you write clean imports.** Solidity's `import` statement needs a real file path, but nobody wants to write `import "../../lib/v4-core/src/interfaces/IPoolManager.sol"`. A `remappings.txt` file lets you write `import "v4-core/src/interfaces/IPoolManager.sol"` instead, and Foundry silently translates it. When you open any hook's source code and see clean-looking imports like `import "v4-periphery/src/utils/BaseHook.sol"`, that cleanliness is remappings doing their job, not a different import system.

## Confirming it actually works

```bash
forge build   # compiles everything
forge test    # runs the template's example tests
```

If `forge test` shows passing tests on the template's example `Counter.sol` hook (a trivially simple hook that just counts how many times it's been called), your environment is correctly set up and you're ready for lesson 15, where we actually read and understand what that Counter hook's code is doing.

## The one sentence to keep

**Foundry is a Solidity-native toolkit (compile/test/deploy all in one, tests written in Solidity itself), the official `v4-template` gives you a working project with the right dependency versions already wired up as git submodules under `lib/`, and `forge build` + `forge test` passing on the template's example hook is your signal that you're ready to start writing real hook code.**
