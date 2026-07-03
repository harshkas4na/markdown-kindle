# 16 — Address Mining & Deployment

Goal: actually do the thing article 6 described in the abstract — get a hook deployed to an address whose bits match its declared permissions, and get a pool created that uses it. This is the step that trips up almost every first-time hook builder, so we'll go slow.

## Quick recap of the problem

From article 6 and lesson 15: your hook's deployed *address* must have specific bits set (in its lowest bits) matching exactly the callbacks it declared `true` in `getHookPermissions()`. You don't get to choose your deployed address freely under a normal deployment — Ethereum derives it automatically from your deployer's address and a nonce. So how do you land on an address with a *specific* bit pattern?

## `CREATE2`: the deployment opcode that makes this possible

Normally (`CREATE`), a contract's deployed address is `hash(deployer_address, deployer's_transaction_count)` — you have no control over it beyond deploying at a different time.

`CREATE2` is a different deployment opcode that computes the address differently: `hash(deployer_address, salt, contract_bytecode)`, where **`salt`** is an arbitrary 32-byte value *you* choose. Change the salt, get a completely different resulting address — deterministically, computable in advance, without actually deploying anything yet.

**Analogy: imagine a vending machine that dispenses a uniquely-shaped keychain based on a code you type in before it makes anything.** Type in code "4471", get keychain shape A. Type in "4472", get a totally different shape B. You can compute in advance, on paper, exactly which shape any given code will produce, without spending a single token to actually manufacture it — you're just doing the math. "Mining" a hook address is exactly this: trying thousands of different salt values, computing (off-chain, for free) what address each one *would* produce, and stopping the instant you find one whose resulting address has the exact bit pattern your `getHookPermissions()` needs.

## `HookMiner`: the actual tool that does this search for you

Uniswap provides a helper library, `HookMiner`, that does this brute-force search efficiently:

```solidity
import {HookMiner} from "v4-periphery/src/utils/HookMiner.sol";

// figure out which permission bits we need, based on our hook's declared permissions
uint160 flags = uint160(
    Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG
);

// this searches (off-chain, in your deploy script) for a salt producing
// a matching address, using CREATE2's deterministic address formula
(address hookAddress, bytes32 salt) = HookMiner.find(
    CREATE2_DEPLOYER,                          // the standard CREATE2 factory address
    flags,                                     // the bit pattern we need
    type(Counter).creationCode,                // our hook's compiled bytecode
    abi.encode(poolManagerAddress)             // constructor arguments (encoded)
);

// now actually deploy, using that exact salt, through the CREATE2 factory
Counter counter = new Counter{salt: salt}(IPoolManager(poolManagerAddress));

// sanity check: the address we actually got had better match what we mined for
require(address(counter) == hookAddress, "address mismatch");
```

Notice this whole process happens in your *deployment script*, not inside any on-chain contract — the "mining" (trying many salts) is just a local, off-chain loop searching for a match, which typically takes a fraction of a second to a few seconds depending on how many flag bits you need to match.

## Doing this in a Foundry test/script, end to end

In practice, for local testing, Foundry's test utilities (from `v4-core`'s `Deployers.sol`, which the template already gives you) wrap most of this for you:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Deployers} from "v4-core/test/utils/Deployers.sol";
import {Counter} from "../src/Counter.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";

contract CounterTest is Test, Deployers {
    Counter hook;

    function setUp() public {
        // Deployers.sol spins up a real local PoolManager + standard test routers
        deployFreshManagerAndRouters();
        // it also deploys two test ERC20 tokens for us to use in a pool
        deployMintAndApprove2Currencies();

        // mine + deploy our hook to the correct flagged address
        uint160 flags = uint160(Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG);
        (address hookAddress, bytes32 salt) =
            HookMiner.find(address(this), flags, type(Counter).creationCode, abi.encode(manager));

        hook = new Counter{salt: salt}(manager);
        require(address(hook) == hookAddress, "hook address mismatch");

        // NOW create an actual pool that uses this hook
        (key, ) = initPool(
            currency0,
            currency1,
            hook,
            3000,          // 0.30% fee (or the dynamic-fee flag, see lesson 18)
            SQRT_PRICE_1_1 // starting price = 1:1
        );
    }
}
```

Walk through what just happened: we deployed a *real*, local copy of the PoolManager (article 5's singleton), mined and deployed our hook to a correctly-flagged address, and then created a brand-new pool whose `PoolKey.hooks` field points at our hook. From this point on, every swap or liquidity action against this specific pool will trigger our hook's callbacks — which is exactly what lesson 17 tests.

## What actually happens if the address doesn't match

If you try to initialize a pool with a hook address whose bits *don't* match what the hook's own `getHookPermissions()` declares, the PoolManager reverts the pool creation transaction outright, with an error like `HookAddressNotValid`. This is a deliberate, hard guardrail — there's no way to accidentally end up with a hook silently not being called for a permission it claims to have, or being called for one it doesn't.

## The one sentence to keep

**`CREATE2` lets you choose a `salt` that determines your contract's deployed address in advance, `HookMiner` brute-forces (off-chain, for free) a salt that produces an address with the exact permission bits your hook declared, and Foundry's `Deployers.sol` test utilities wrap the whole "deploy PoolManager, mine hook address, deploy hook, initialize pool" sequence into a few lines you'll copy into essentially every hook test you ever write.**
