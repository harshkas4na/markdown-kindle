# The Workshop — Building and Testing Hooks with Foundry

**Fast overview:** the practical chapter. Toolchain (Foundry + v4-template), project anatomy, the local test harness that stands up a real PoolManager, address mining in tests and deployment, and — most importantly — the testing discipline: unit, fuzz, invariant, and fork tests, in that order of increasing honesty. Nothing here is theory; this is the difference between a hook that demos and a hook that survives.

## Toolchain

**Foundry** is the standard: Solidity-native tests, fast fuzzer, invariant engine, mainnet forking, and scripting (`forge`, `anvil`, `cast`). Start every hook from the official **v4-template** (github.com/uniswapfoundation/v4-template), which arrives with v4-core/v4-periphery wired, `BaseHook` to inherit, `HookMiner` for addresses, and example tests. Get current versions — v4 tooling moved fast through 2025; pre-1.0 tutorials online will bite you with renamed types (`SwapParams` moved packages, `Deployers` evolved) — when a snippet doesn't compile, diff against the template's own tests first.

```bash
forge init my-hook --template uniswapfoundation/v4-template
cd my-hook && forge test    # green out of the box
```

## Anatomy of a hook test

The template's base test contract (`Deployers` from v4-core/test) gives you a fresh, *real* protocol per test — this is the great luxury of the singleton design (Chapter 6): the whole exchange is one contract you deploy locally in milliseconds.

```solidity
contract MyHookTest is Test, Deployers {
    MyHook hook;

    function setUp() public {
        deployFreshManagerAndRouters();          // PoolManager + swap/liquidity routers
        deployMintAndApprove2Currencies();       // two test ERC20s, funded & approved

        // 1. compute the flags your hook needs
        address flags = address(uint160(
            Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG
        ) ^ (0x4444 << 144));                    // namespace to avoid collisions

        // 2. in tests you can cheat: deploy straight to a valid address
        deployCodeTo("MyHook.sol:MyHook", abi.encode(manager), flags);
        hook = MyHook(flags);

        // 3. create a pool wired to the hook
        (key, ) = initPool(currency0, currency1, hook, 3000, SQRT_PRICE_1_1);

        // 4. seed liquidity
        modifyLiquidityRouter.modifyLiquidity(key,
            ModifyLiquidityParams(-60, 60, 10 ether, 0), ZERO_BYTES);
    }

    function test_swap_charges_fee() public {
        BalanceDelta d = swapRouter.swap(key,
            SwapParams({zeroForOne: true, amountSpecified: -1e18,
                        sqrtPriceLimitX96: MIN_PRICE_LIMIT}),
            PoolSwapTest.TestSettings(false, false), ZERO_BYTES);
        // assert on d, hook state, manager balances...
    }
}
```

The two deployment modes matter: **tests** use `deployCodeTo` (Foundry's cheatcode writes bytecode at any address — no mining needed); **real chains** need `HookMiner.find(deployer, flags, creationCode, constructorArgs)` to search salts, then CREATE2 via the canonical deterministic-deployment proxy so the address (and its permission bits — Chapter 7) comes out right. Scripts in the template show both; the classic deploy failure is mining with one deployer address and deploying from another — the computed salt is invalid and `initialize` reverts with `HookAddressNotValid`.

## The testing ladder

Climb all four rungs. Each catches what the previous can't.

**1. Unit tests — the happy paths and the sad ones.** Exercise each enabled callback through the real router (never call the hook directly — the PoolManager's context is part of the behavior). Mandatory sad paths people skip: exact-*output* swaps (Chapter 8's specified/unspecified trap), both `zeroForOne` directions, swaps that cross initialized ticks, zero-liquidity pools, and operations with unexpected `hookData` (empty, garbage, oversized).

**2. Fuzz tests — free counterexamples.** Let Foundry randomize amounts, directions, and sequences:

```solidity
function testFuzz_fee_bounded(uint128 amtIn, bool dir) public {
    vm.assume(amtIn > 1e6 && amtIn < 1e24);
    // ... swap, then:
    assertLe(hook.lastFee(), MAX_FEE);           // policy clamp holds for ALL inputs
}
```

Fuzzing is embarrassingly effective against exactly the bug class that kills hooks: rounding and boundary arithmetic. Bunni's $8.4M flaw (next chapter) was a *floor-vs-round direction* in withdrawal math — the archetypal fuzz-findable bug. When your logic divides, fuzz it; when it converts between token amounts and liquidity (Chapter 4's formulas), fuzz it twice, and assert the rounding always favors the pool.

**3. Invariant tests — the properties that define you.** Declare what must *always* hold, let the engine run random call sequences against a handler contract:

- solvency: hook's 6909 claims + reserves ≥ its obligations (for custom-accounting hooks, this IS the protocol);
- conservation: user in + user out consistent with fees taken (no value appearing from nowhere);
- monotonicity: e.g., oracle observations never move backward; cumulative fees never decrease;
- your economic promise itself (for a fixed-price hook: executed price == quoted price, always).

If you cannot write down your hook's invariants, you do not yet understand your hook — that sentence is the cheapest audit you'll ever get.

**4. Fork tests — reality.** `forge test --fork-url $RPC` against live v4 deployments: real PoolManager bytecode, real routers, real tokens (6-decimals USDC will find your decimal assumptions — Chapter 4's warning), real gas profile (`forge snapshot` per swap; remember Chapter 8's budget: observation hooks ~10–30k, custom accounting 60–150k+). Then deploy to a testnet and run the *composed* paths: multi-hop routes through your pool, aggregator-style batched unlocks — the interactions that single-pool tests never see.

## Habits that separate shipped from wrecked

- **Start from `BaseHook`, override the internal `_beforeSwap`-style functions**, and let the base handle caller checks and selector returns. Hand-rolling the interface is how selector-mismatch DoS happens (Chapter 7).
- **Reuse audited building blocks**: OpenZeppelin's `uniswap-hooks` library (BaseAsyncSwap, BaseCustomCurve, fee utilities) — inheriting a reviewed skeleton removes whole bug classes; the hookathon judges of 2025–2026 explicitly favored it.
- **Guard the money paths**: every function that moves value asks "who can call this, and can they call it *mid-unlock* of something else?" (Chapter 6's reentrancy inversion means your hook can be re-entered through a nested unlock — model it in tests, don't assume the manager saves you).
- **Events on everything** — your subgraph, your monitoring, and your incident response all read logs.
- **A pause switch and a documented admin model.** Bunni's emergency controls limited the damage. But every admin power you add is trust users must extend (Chapter 7's "immutable pool, mutable hook") — document it or expect the audit to.
- **Gas-golf last.** Correct and 20k gas heavier beats clever and wrong; you cannot patch a hook whose address encodes its behavior — you can only launch a new pool and beg liquidity to migrate.

You can now build the machine. Next chapter: the morgue — a tour of how machines exactly like yours have died, so yours doesn't.
