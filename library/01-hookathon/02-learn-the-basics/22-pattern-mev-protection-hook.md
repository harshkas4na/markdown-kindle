# 22 — Code Pattern: MEV / Anti-Sandwich Hook

Goal: build two of the real approaches from article 7 as actual code — priority-fee-aware fee bumping (cheap, imperfect, honest about its limits) and a commit-reveal pattern (stronger, more involved). Understanding exactly what each one can and can't stop matters more than the code itself here.

## Approach A: tax high priority fees (a real but limited heuristic)

Recall article 7: a sandwiching bot needs its front-run transaction to land *before* yours in the same block, which it typically achieves by paying an unusually high priority fee (the tip that incentivizes a block builder to include and order it favorably). This gives us an imperfect but genuinely useful signal.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {LPFeeLibrary} from "v4-core/src/libraries/LPFeeLibrary.sol";

contract PriorityFeeAwareHook is BaseHook {
    uint24 public constant BASE_FEE = 3000;      // 0.30%
    uint24 public constant PENALTY_FEE = 10000;  // 1.00%, applied to suspiciously high-priority swaps
    uint256 public constant SUSPICIOUS_TIP_THRESHOLD = 5 gwei;

    constructor(IPoolManager _poolManager) BaseHook(_poolManager) {}

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false, afterInitialize: false,
            beforeAddLiquidity: false, afterAddLiquidity: false,
            beforeRemoveLiquidity: false, afterRemoveLiquidity: false,
            beforeSwap: true, afterSwap: false,
            beforeDonate: false, afterDonate: false,
            beforeSwapReturnDelta: false, afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false, afterRemoveLiquidityReturnDelta: false
        });
    }

    function _beforeSwap(address, PoolKey calldata, IPoolManager.SwapParams calldata, bytes calldata)
        internal override returns (bytes4, BeforeSwapDelta, uint24)
    {
        // tx.gasprice includes the priority fee the caller chose to pay;
        // block.basefee is the network-wide minimum required this block —
        // the DIFFERENCE is roughly "how much extra is this transaction paying to get prioritized"
        uint256 priorityTip = tx.gasprice > block.basefee ? tx.gasprice - block.basefee : 0;

        uint24 fee = priorityTip > SUSPICIOUS_TIP_THRESHOLD ? PENALTY_FEE : BASE_FEE;

        return (this.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, fee | LPFeeLibrary.OVERRIDE_FEE_FLAG);
    }
}
```

**Be honest with yourself about what this does and doesn't stop.** This penalizes *any* transaction with a high tip, including a legitimate trader who's simply in a hurry, or a sandwiching bot that's smart enough to use a moderate tip and win block placement through other means (private order-flow deals with a block builder, for instance, which bypass the public tip-auction entirely). This is a real, used technique, but it's a blunt heuristic, not a guarantee — worth stating plainly in your own project's docs rather than overselling it, and worth knowing this limitation before you build your pitch around it.

## Approach B: commit-reveal (stronger, more machinery)

The more robust idea: don't let anyone see your trade's actual parameters *at all* until it's already too late to front-run. This requires two separate transactions instead of one.

```solidity
contract CommitRevealHook is BaseHook {
    struct Commitment {
        bytes32 commitHash;
        uint256 commitBlock;
    }

    mapping(address => Commitment) public commitments;
    uint256 public constant REVEAL_DELAY_BLOCKS = 2;

    // step 1: user submits ONLY a hash of their intended trade + a secret salt,
    // revealing nothing about direction or size
    function commitSwap(bytes32 commitHash) external {
        commitments[msg.sender] = Commitment({
            commitHash: commitHash,
            commitBlock: block.number
        });
    }

    // step 2: a few blocks later, user reveals the actual parameters, which
    // must hash to exactly what they committed earlier
    function revealAndSwap(
        PoolKey calldata key,
        IPoolManager.SwapParams calldata params,
        bytes32 salt
    ) external {
        Commitment memory c = commitments[msg.sender];
        require(block.number >= c.commitBlock + REVEAL_DELAY_BLOCKS, "reveal too early");
        require(
            keccak256(abi.encode(params, salt)) == c.commitHash,
            "revealed params don't match commitment"
        );

        delete commitments[msg.sender];
        // ... now actually execute the swap through the PoolManager
    }
}
```

**How this actually defeats front-running, and what it costs you.** During the "commit" transaction, a bot watching the mempool sees only a meaningless hash — no direction, no size, nothing actionable. By the time the real parameters are revealed (and could theoretically be front-run), the trade executes in the *same* revealing transaction, leaving no gap for a bot to react within. The cost: this requires two separate user transactions instead of one (worse UX, more gas overall), and a mandatory delay between them (worse latency) — which is exactly why commit-reveal shows up far less often in the directory than the cheaper, imperfect heuristics like priority-fee penalties. It's a real tradeoff between protection strength and usability, not a strictly-better option.

## A third, cheaper mitigation worth knowing: slippage bounds as your own baseline defense

Before reaching for either hook pattern above, remember the simplest available defense already lives in `SwapParams.sqrtPriceLimitX96` (lesson 17) — a tight, correctly-set slippage limit already caps how much a sandwich attack can extract from any individual trade, because the trade simply reverts if the price has moved past what the user was willing to accept. Most real-world sandwich losses happen specifically because a wallet/frontend sets an overly loose default slippage tolerance (some interfaces default to 0.5%-1%, or worse, "auto" settings that pick something generous) — a huge amount of MEV-protection hook complexity in this directory is arguably compensating for that one upstream UX default, more than it's solving something unfixable at the protocol level.

## The one sentence to keep

**A priority-fee-penalty hook is cheap and easy to build but only a blunt heuristic (it can't distinguish an impatient honest trader from a bot, and doesn't stop private order-flow deals), a commit-reveal hook genuinely hides trade parameters until it's too late to front-run but costs two transactions and a mandatory delay, and neither replaces the far simpler, already-available defense of a correctly tight slippage bound — which is worth understanding before building something more elaborate to solve a problem tighter defaults would have mostly prevented.**
