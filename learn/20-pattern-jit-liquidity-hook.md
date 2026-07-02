# 20 — Code Pattern: JIT & Idle-Liquidity Hook

Goal: build the pattern behind the 153-hook "Liquidity Management & Incentives" category — a hook that deploys liquidity from an external lending vault right before a swap and returns it right after (JIT), and the closely related pattern of parking idle capital in a yield source between swaps.

## The core idea, restated as code intent

From article 2/4: an LP's concentrated position only earns fees while the price is inside their chosen range. The "idle liquidity" pattern says: **don't let unused capital just sit there — deploy it into a lending protocol (earning interest) whenever it isn't actively needed for swaps, and pull it back the instant it is needed.**

This requires the hook to hold custody of (or have approval over) the LP's capital, moving it between "sitting in the Uniswap pool" and "deposited in a lending vault" automatically. This is exactly why so many of these hooks are `NoOp` hooks in the directory's tagging — "NoOp" here means the hook's `beforeAddLiquidity` intercepts a normal liquidity deposit and *redirects* it somewhere else entirely, rather than letting the PoolManager handle it as a standard, boring liquidity position.

## A simplified version: route idle capital into an ERC-4626 vault

**ERC-4626** is a standard interface for "tokenized yield vaults" — deposit an asset, receive a share token, the vault's underlying strategy (e.g. lending on Aave) earns yield, and your share token appreciates in value over time. Almost every "park idle liquidity somewhere" hook in the directory is really just "call `deposit()`/`withdraw()` on an ERC-4626 vault at the right moments."

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {PoolId} from "v4-core/src/types/PoolId.sol";
import {IERC4626} from "openzeppelin-contracts/interfaces/IERC4626.sol";
import {IERC20} from "openzeppelin-contracts/interfaces/IERC20.sol";

contract IdleLiquidityHook is BaseHook {
    IERC4626 public immutable yieldVault;   // e.g. an Aave-backed USDC vault
    IERC20 public immutable underlying;     // the token this vault accepts (e.g. USDC)

    // tracks how many vault shares this hook currently holds on behalf of the pool
    mapping(PoolId => uint256) public vaultShares;

    constructor(IPoolManager _poolManager, IERC4626 _vault) BaseHook(_poolManager) {
        yieldVault = _vault;
        underlying = IERC20(_vault.asset());
        underlying.approve(address(_vault), type(uint256).max);
    }

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false, afterInitialize: false,
            beforeAddLiquidity: false, afterAddLiquidity: false,
            beforeRemoveLiquidity: false, afterRemoveLiquidity: false,
            beforeSwap: true,   // <- pull capital OUT of the vault right before a swap needs it
            afterSwap: true,    // <- push capital back INTO the vault once the swap is done
            beforeDonate: false, afterDonate: false,
            beforeSwapReturnDelta: true,  // <- we need this because we're injecting our own liquidity into the swap
            afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false, afterRemoveLiquidityReturnDelta: false
        });
    }

    function _beforeSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata params, bytes calldata)
        internal override returns (bytes4, BeforeSwapDelta, uint24)
    {
        PoolId id = key.toId();
        uint256 shares = vaultShares[id];

        if (shares > 0) {
            // pull our parked capital OUT of the yield vault, back into liquid form,
            // so it's available to actually service this swap
            uint256 withdrawn = yieldVault.redeem(shares, address(this), address(this));
            vaultShares[id] = 0;

            // ... here a real implementation would call poolManager.modifyLiquidity()
            // to actually deposit `withdrawn` into the pool's active range for this
            // one transaction (the "just-in-time" part), and construct a BeforeSwapDelta
            // reflecting that injected liquidity. Simplified out here for clarity —
            // this is the single most fiddly part of a real JIT hook to get right.
        }

        return (this.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }

    function _afterSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, /* delta */ , bytes calldata)
        internal override returns (bytes4, int128)
    {
        PoolId id = key.toId();

        // ... a real implementation would first call poolManager.modifyLiquidity()
        // to WITHDRAW the just-added JIT position (now including earned swap fees)
        // back out of the pool, then:
        uint256 idleBalance = underlying.balanceOf(address(this));
        if (idleBalance > 0) {
            uint256 shares = yieldVault.deposit(idleBalance, address(this));
            vaultShares[id] += shares;
        }

        return (this.afterSwap.selector, 0);
    }
}
```

## The part deliberately left as a comment, and why it's the hard part

Actually calling `poolManager.modifyLiquidity()` *from inside a hook callback, during someone else's swap transaction* is the genuinely tricky bit of a real JIT hook — you're adding/removing liquidity in the middle of an already-in-progress swap, which means carefully constructing the `BalanceDelta`/`BeforeSwapDelta` math so the PoolManager's final accounting still nets out to zero (recall article 5's flash accounting: everything must settle by the end of the transaction, or it reverts). This is exactly why `beforeSwapReturnDelta: true` is flagged in `getHookPermissions()` above — it tells the PoolManager "expect this hook to be injecting its own balance changes into this swap, not just observing it." Getting this exactly right is genuinely one of the more advanced things you can do with a v4 hook, and it's worth building the simpler non-JIT version first (just parking/unparking capital between separate transactions, rather than mid-swap) before attempting true same-transaction JIT.

## A simpler, safer starting point: park between transactions, not mid-swap

If true JIT (same-transaction inject/withdraw) feels like too much to start with, a legitimate simpler version of this exact idea: use `afterSwap` to notice "the pool's active range now has more capital sitting idle than needed" and deposit the surplus into the vault, then use `beforeSwap` (or a separate keeper-triggered function) to pull capital back only when the price is about to cross back into a range that needs it — accepting that you might miss capturing fees on the very first swap after a withdrawal, in exchange for a much simpler, safer implementation.

## The one sentence to keep

**An idle-liquidity hook holds shares in an ERC-4626 yield vault on behalf of the pool, redeeming them back to liquid tokens in `beforeSwap` and re-depositing surplus in `afterSwap`; true same-transaction JIT liquidity additionally requires calling `poolManager.modifyLiquidity()` mid-swap with `beforeSwapReturnDelta` flagged on, which is genuinely one of the harder patterns in this whole lesson series — start with the simpler "park between transactions" version before attempting real JIT.**
