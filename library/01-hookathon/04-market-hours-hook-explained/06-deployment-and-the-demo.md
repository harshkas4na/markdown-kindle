# 06 — Deployment and the Demo: From `forge test` to a Clickable Opening Bell

Goal: understand everything that happens between "the tests pass" and "I'm clicking buttons against a live chain" — the deployment pipeline, the two bugs only real deployment could catch, and exactly how the demo page works and what to do in it.

## Why deployment is its own engineering problem

Tests run against an in-memory EVM where `deployCodeTo` conjures the hook at any address. Real chains grant no such favors. Three problems appear the moment you go live:

**Problem 1: address mining.** A hook's address must physically contain its permission flags in the low 14 bits. The deploy script uses `HookMiner.find(CREATE2_FACTORY, flags, creationCode, constructorArgs)` — brute-forcing salts until `CREATE2` yields a matching address — then deploys through the canonical CREATE2 factory (`0x4e59b4...`, predeployed on virtually every chain including anvil) with that salt. Our flags are `AFTER_INITIALIZE | BEFORE_SWAP | AFTER_SWAP`: 3 fixed bits among 14 → about 1 in 16k salts... but the *other* 11 flag bits must be zero too, so it's a uniform 1-in-16384 search. Seconds of CPU.

**Problem 2 (the bug tests can't see): the 24KB limit.** First real deployment attempt failed: *"`Unknown3` is above the contract size limit (29541 > 24576)"*. The hook compiled to ~30KB — over EIP-170 — because **Forge 1.0 ships with the solc optimizer OFF by default**, and `deployCodeTo` had happily etched the oversized bytecode in every test. The fix is two lines in `foundry.toml` (`optimizer = true`, `optimizer_runs = 800`), taking the hook to ~17KB. Lesson: `forge build --sizes` belongs in your pre-deploy checklist, because your tests will never tell you.

**Problem 3 (the other invisible bug): simulation-only addresses.** The v4-template's scripts auto-deploy the PoolManager/PositionManager/router on chain 31337 — but those deployments happen inside each script's *simulation*, not on the actual anvil node. Our first hook deploy succeeded yet was constructed pointing at a PoolManager that existed only in the simulation (`cast call hook "poolManager()"` returned an address with no code). The fix: run `script/testing/00_DeployV4.s.sol --broadcast` once (real deployments), then pin those addresses as `LOCAL_*` constants in `BaseScript` with overrides that use them whenever they have code. Read `DEPLOYMENT.md` for the exact addresses of the verified run.

## The pipeline, one command per line

```bash
anvil --port 8545 --chain-id 31337
forge script script/testing/00_DeployV4.s.sol   ... --broadcast  # V4 stack (once per anvil)
forge script script/testing/01_DeployTokens.s.sol ... --broadcast # tSTOCK + mUSD (CREATE2)
forge script script/00_DeployHook.s.sol         ... --broadcast  # mine + deploy the hook
forge script script/01_CreatePoolAndAddLiquidity.s.sol ... --broadcast # dynamic-fee pool + 100e18 range
forge script script/03_Swap.s.sol               ... --broadcast  # a live swap through the hook
```

Between steps you paste printed addresses into `BaseScript.sol`'s config block (tokens, then hook) — the scripts are deliberately dumb about discovery. Two script-level details that matter for *this* hook: the pool-creation and swap scripts must use `fee: LPFeeLibrary.DYNAMIC_FEE_FLAG` (a `PoolKey` with 3000 hashes to a *different pool ID* — the swap wouldn't fail against the wrong pool, it would target a nonexistent one), and the verified run happened during real NYSE hours, so the swap executed at the 0.30% base fee — the hook read the actual wall-clock Monday and said OPEN. You can verify the live phase yourself:

```bash
cast call $HOOK "phaseAt(uint256)(uint8)" $(date +%s) --rpc-url http://localhost:8545   # 0=OPEN 1=CLOSED 2=AUCTION
cast call $HOOK "closedFeeAt(uint256)(uint24)" 1783166400 --rpc-url ...                  # Saturday noon => 14800
```

## The demo page: what it is

`demo/index.html` is a **single self-contained file** — no build step, no framework, no wallet extension. Serve the repo folder (`python3 -m http.server 8080`) and open `/demo/`. Inside it:

- **ethers v6 from a CDN** (the one external dependency) speaks JSON-RPC to anvil at `localhost:8545`.
- **No MetaMask needed**: anvil's accounts are *unlocked* — `provider.getSigner(0)` returns a signer that can send transactions via plain `eth_sendTransaction`. The demo acts as anvil's account #0, which conveniently owns the hook, the tokens, and the LP position.
- **Addresses are constants at the top of the script block** (hook, tokens, router, Permit2, PoolManager) matching `DEPLOYMENT.md`. Redeploy → update those five lines.
- **ABIs are human-readable fragments** (`"function phaseAt(uint256) view returns (uint8)"`) — ethers compiles them on the fly; no JSON artifacts to copy around.

## How each panel works (and the on-chain call behind it)

**Market status card.** Every 8 seconds (and after every action) `refresh()` reads: `phaseAt(latestBlock.timestamp)` → the big OPEN/CLOSED/AUCTION word (note it passes *chain* time, not wall time — after warping, those differ); `closedFeeAt`/`baseFee` → the live fee; `upcomingEpoch` → next open; and the pool price. The price read is the fun one: there's no "getPrice" ABI — the page recomputes v4's own storage layout in JavaScript, hashing `keccak256(poolId . uint256(6))` (the pools mapping lives at slot 6) and calling `extsload` on the PoolManager, then masks the low 160 bits for `sqrtPriceX96` and squares it. The same trick `StateLibrary` does in Solidity, done client-side.

**Time machine.** Buttons call anvil's `evm_setNextBlockTimestamp` + `evm_mine`. Time only moves **forward** (anvil refuses regressions), so the buttons compute their targets from *chain-now*: "→ Saturday noon" scans up to 8 days ahead for a UTC-Saturday and warps to 16:00 UTC (= noon EDT); "→ next open + 1 min" asks the *hook itself* (`upcomingEpoch`) rather than duplicating calendar logic in JS; "+1 hour/+1 day" are relative. After every warp the status card re-renders — this is how you *watch* the phase machine flip.

**Swap panel.** A swap through the router needs the Permit2 two-step the first time: `token.approve(Permit2, max)` then `permit2.approve(token, router, max, maxExpiry)` — the demo just does both before each swap (idempotent). Then `swapExactTokensForTokens(amount, 0, zeroForOne, KEY, "0x", me, deadline)`. One trap the code comments loudly: in this pool **tSTOCK sorted as currency1**, so "sell tSTOCK" is `zeroForOne = false` — token order is decided by address sort, not by your mental model. Failures are caught and printed to the log panel with the revert reason — *a reverting swap is a feature being demonstrated*, not an error.

**Auction panel.** `placeAuctionOrder` needs a direct ERC20 approval **to the hook** (escrow pulls via `transferFrom` — no Permit2 involved). The orders table re-derives everything from view calls: `orderCount(poolId, epoch)` then `getOrder(...)` per row, with the action button chosen by state — `cancel` while unsettled, `claim` once settled, nothing when closed. `settleAuction` and `snapshotCloseReference` are one-click permissionless calls.

## The demo script — what to actually do in front of someone

1. **Open during OPEN** (or warp to a weekday 11:00 ET). Status: green OPEN, fee 0.30%. Swap 0.5 — instant, cheap. *"Normal market hours: the hook is invisible."*
2. **→ Saturday noon.** Status flips CLOSED, fee reads 1.48%. Same swap — works, output visibly smaller. *"The pool knows Wall Street is dark, and prices the risk."* Try 2.0 — **reverts** (size cap). *"And you can't dump through a thin weekend pool — that's the circuit breaker regulators keep asking for."*
3. **Place auction orders while closed.** Sell 1 tSTOCK; also place the opposite side. Watch the orders table fill and the epoch label point at Monday 09:30.
4. **→ next open +1 min.** Status: amber AUCTION. Try to swap — **reverts**. *"Nobody trades the open. Not even you."*
5. **→ next open +11 min.** Swap still reverts (`AuctionNotSettledYet`). Press **Settle auction** — the bell. Orders flip to `claimable`; claim both; balances land. Now swap — works at 0.30%. *"The Monday-morning race is gone: everyone in the batch got one price, matched volume never even paid the pool a fee."*
6. Optional flourish: after a warp to just-past-close, hit **Snapshot close reference**, enable the band via `cast` (`setClosedBandBps`), and show a big weekend swap bouncing off the limit-up/limit-down corridor.

## Testnet path

Same scripts, zero code changes: `Deployers.sol` resolves canonical v4 addresses per chain from hookmate's `AddressConstants` (Unichain Sepolia = 1301). Supply a funded key and an RPC; deploy hook → set tokens/hook constants → create pool. The demo page then just needs its `RPC` constant changed — though on a public testnet you lose the time machine (nobody warps Sepolia) and the unlocked signer (you'd wire a wallet).

## The one sentence to keep

**Deployment taught the two lessons tests never could — turn the optimizer on or die at 24KB, and pin real artifact addresses or bind your hook to a simulation ghost — and the demo is one dependency-free HTML file that acts as anvil's unlocked account #0, reads the phase machine live (down to hand-hashing slot 6 for the price), bends time with `evm_setNextBlockTimestamp`, and walks a viewer through close → circuit breaker → frozen open → permissionless bell → uniform-price claims in six clicks.**
