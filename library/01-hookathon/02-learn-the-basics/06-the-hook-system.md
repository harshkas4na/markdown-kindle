# 06 — The Hook System Itself

Goal: this is the article. Everything before this was scaffolding so this would actually make sense. By the end, you should understand exactly what a "hook" is as a piece of code, when it runs, how the pool knows to call it, and why hook contract *addresses* are weirdly meaningful.

## What a hook actually is, mechanically

A hook is just a normal smart contract — nothing magic about its type. What makes it "a hook" is that when a pool is created, you tell the PoolManager (from article 5) "this pool has a hook, and its address is 0x1234...". From then on, at specific defined moments during that pool's lifecycle, the PoolManager will pause what it's doing and call a specific function on your hook contract, wait for it to finish (and let it optionally change what happens next), then continue.

**Analogy: think of a hook like a security checkpoint at specific doorways in a building, not a guard who watches everything all the time.** The building (PoolManager) has predefined doorways — "someone is about to enter the swap room," "someone just left the swap room," "someone is about to add liquidity," etc. At each doorway, if you've registered a checkpoint (hook) for that specific doorway, the person gets stopped there, the checkpoint's logic runs (check ID, log something, maybe deny entry), and only then are they let through to continue.

## The actual callback points

Uniswap v4 defines a fixed list of moments a hook can attach to. The main ones you'll see over and over in the directory:

- `beforeInitialize` / `afterInitialize` — runs when a brand-new pool is being created, before/after its starting price is set. Useful for things like enforcing "this pool may only be created with these specific parameters."
- `beforeAddLiquidity` / `afterAddLiquidity` — runs when an LP deposits. Useful for things like KYC-gating who's allowed to become an LP, or tracking custom reward-eligibility data.
- `beforeRemoveLiquidity` / `afterRemoveLiquidity` — runs when an LP withdraws. Useful for exit fees, or triggering a rebalance.
- `beforeSwap` / `afterSwap` — by far the most used pair in the entire directory. `beforeSwap` runs right before a trade executes — this is where dynamic-fee hooks calculate and apply a custom fee, where compliance hooks block disallowed wallets, where anti-sandwich hooks inspect the transaction. `afterSwap` runs right after — this is where hooks update volatility trackers, distribute reward points, or trigger a rebalance now that the price has moved.
- `beforeDonate` / `afterDonate` — runs around "donate" operations (directly gifting fees into a pool without swapping), a less common but real callback used by a handful of reward/insurance-style hooks.

Every single hook in the entire 556-project directory is built from some combination of these callback points — there is no other place custom logic can attach.

## The genuinely clever part: permission flags baked into the address

Here's the detail that surprises most people the first time they hear it: **a hook contract's own address encodes which callbacks it's allowed to use.**

Specifically, the *last few bits* of the hook's deployed address are read by the PoolManager as a set of yes/no flags — "does this hook implement beforeSwap? afterSwap? beforeAddLiquidity?" — one flag per callback type. Before a pool will even accept a hook, the PoolManager checks the hook's own address for these flag bits and only calls the callbacks that are flagged "on."

Why do it this way, instead of just asking the hook contract "which functions do you support" at call time? Gas efficiency and safety: checking a few bits of an address you already have is essentially free, versus making an extra external call to ask "do you support X?" before every single swap, forever. Baking the permissions into the address means the PoolManager can decide, extremely cheaply, exactly which of the (up to) 10-ish possible callbacks it needs to bother calling for this specific pool, and skip the rest entirely.

**Analogy: imagine everyone's ID badge color itself told the security system which doors they're allowed through, instead of the security system having to look each person up in a database every single time they approach a door.** Blue badge = swap-room doors only. The color is baked into the badge itself; there's no lookup, no waiting, no separate check — glance at the badge, know instantly what's permitted.

## Why hook addresses have to be "mined"

Following directly from the above: a hook developer doesn't get to just deploy their contract anywhere and have the right permission bits show up by luck — they need a deployed address whose specific trailing bits happen to match the exact set of callbacks their hook needs. Since you can't choose an Ethereum address directly (it's derived from deployment parameters like a nonce or salt), hook developers commonly use a **CREATE2 deployment** with a "salt" value they can freely choose, and then brute-force search — trying thousands or millions of possible salts — until they find one that produces a deployed address with exactly the right trailing bits set. This process is casually called **"address mining,"** and it's a genuinely distinctive, slightly weird piece of v4-hook-specific tooling you'll see referenced in some of the more technical project write-ups.

## Putting it together: a minimal example

Say you're building the simplest possible dynamic-fee hook. You'd: (1) write a hook contract that implements `beforeSwap`, containing logic like "look at recent price volatility, compute a fee percentage, override the pool's fee for this trade"; (2) mine a deployment address whose trailing bits flag "beforeSwap: yes" and everything else "no"; (3) deploy the pool itself via the PoolManager, pointing it at your hook's address. From that point on, every single swap against that pool automatically pauses right before executing, calls your `beforeSwap` function, applies whatever fee it decides, and only then continues with the trade — with zero further action needed from you, forever, for every future trade.

## The one sentence to keep

**A hook is a plain smart contract that the PoolManager calls at specific, fixed lifecycle moments (mainly before/after a swap or a liquidity change), which callbacks it's allowed to use are encoded directly into its own contract address as permission flags (requiring developers to "mine" an address with the right bits), and this is the entire mechanism — every single project in this 556-entry directory is just a different combination of "what logic do I put inside beforeSwap/afterSwap."**
