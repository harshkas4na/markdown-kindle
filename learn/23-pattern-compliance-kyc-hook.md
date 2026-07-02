# 23 — Code Pattern: Compliance / KYC-Gated Hook

Goal: build the pattern behind the 60-hook "Compliance, KYC & Identity" category — a hook that only allows swaps and liquidity actions from wallets that have passed some verification, which is the prerequisite every RWA-tokenization hook (article 13) needs before it's legally usable for anything beyond a demo.

## The simplest version: a whitelist mapping, gated in `beforeSwap`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {Ownable} from "openzeppelin-contracts/access/Ownable.sol";

contract WhitelistGatedHook is BaseHook, Ownable {
    mapping(address => bool) public isVerified;

    event WalletVerified(address indexed wallet);
    event WalletRevoked(address indexed wallet);

    constructor(IPoolManager _poolManager, address initialOwner)
        BaseHook(_poolManager)
        Ownable(initialOwner)
    {}

    // in practice, this would be called by a trusted off-chain KYC provider's
    // relayer wallet, or by an on-chain attestation-checking function — see below
    function setVerified(address wallet, bool verified) external onlyOwner {
        isVerified[wallet] = verified;
        if (verified) emit WalletVerified(wallet);
        else emit WalletRevoked(wallet);
    }

    function getHookPermissions() public pure override returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: false, afterInitialize: false,
            beforeAddLiquidity: true,   // <- gate who can become an LP
            afterAddLiquidity: false,
            beforeRemoveLiquidity: false, afterRemoveLiquidity: false,
            beforeSwap: true,            // <- gate who can trade
            afterSwap: false,
            beforeDonate: false, afterDonate: false,
            beforeSwapReturnDelta: false, afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false, afterRemoveLiquidityReturnDelta: false
        });
    }

    function _beforeSwap(address sender, PoolKey calldata, IPoolManager.SwapParams calldata, bytes calldata)
        internal view override returns (bytes4, BeforeSwapDelta, uint24)
    {
        require(isVerified[sender], "wallet not KYC-verified");
        return (this.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }

    function _beforeAddLiquidity(address sender, PoolKey calldata, IPoolManager.ModifyLiquidityParams calldata, bytes calldata)
        internal view override returns (bytes4)
    {
        require(isVerified[sender], "wallet not KYC-verified");
        return this.beforeAddLiquidity.selector;
    }
}
```

## The `sender` gotcha: whose address are you actually checking?

**This is the single most important, most commonly-gotten-wrong detail in a compliance hook.** The `sender` parameter your hook receives is whoever called the PoolManager directly — which, if the user went through a router contract (very common — most frontends route swaps through an aggregator or Uniswap's own router, not raw), will be **the router's address, not the end user's wallet.** Naively checking `isVerified[sender]` in that setup checks whether the *router* is whitelisted, not whether the actual trader is — a real, easy-to-ship bug that completely defeats the compliance check's purpose.

The standard fix: require the real user's address to be passed explicitly through `hookData` (the arbitrary bytes parameter every callback receives, meant exactly for this kind of "extra context the router needs to forward"), and verify it there instead:

```solidity
function _beforeSwap(address sender, PoolKey calldata, IPoolManager.SwapParams calldata, bytes calldata hookData)
    internal view override returns (bytes4, BeforeSwapDelta, uint24)
{
    address actualTrader = abi.decode(hookData, (address));
    require(isVerified[actualTrader], "wallet not KYC-verified");
    // NOTE: this alone doesn't prove `actualTrader` really is the one who
    // initiated the call — a malicious router could lie about who's calling.
    // A production system typically also requires a signature from `actualTrader`
    // authorizing this specific trade, checked here via ecrecover, rather than
    // trusting the caller's self-reported hookData at face value.
    return (this.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
}
```

## A more realistic compliance flow: on-chain attestations instead of an owner-managed mapping

A centrally-owned `setVerified()` mapping (the simple version above) is fine for a hackathon demo, but it means one admin key can arbitrarily add or remove anyone's trading rights — a real centralization/trust concern for anything claiming to be "decentralized compliance." Production-grade approaches (referenced by ERC-3643-style hooks in article 13) typically instead check a *separate*, independent identity-registry contract:

```solidity
interface IIdentityRegistry {
    function isVerified(address wallet) external view returns (bool);
}

contract AttestationGatedHook is BaseHook {
    IIdentityRegistry public immutable identityRegistry;

    constructor(IPoolManager _poolManager, IIdentityRegistry _registry) BaseHook(_poolManager) {
        identityRegistry = _registry;
    }

    function _beforeSwap(address, PoolKey calldata, IPoolManager.SwapParams calldata, bytes calldata hookData)
        internal view override returns (bytes4, BeforeSwapDelta, uint24)
    {
        address actualTrader = abi.decode(hookData, (address));
        require(identityRegistry.isVerified(actualTrader), "not KYC-verified");
        return (this.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
}
```

This separates "who runs the KYC verification process" (the identity registry, potentially run by a licensed, regulated third party) from "who runs the trading pool" (your hook) — the hook just *checks* a verification status, it doesn't own or manage the verification process itself. This division of responsibility is exactly how ERC-3643 and similar real production standards structure it.

## The one sentence to keep

**A compliance hook checks a caller's verification status in `beforeSwap`/`beforeAddLiquidity`, but naively checking `sender` is a common, serious bug because that's usually a router's address, not the actual trader's — the real trader's address needs to be passed through `hookData` (ideally with a signature proving they actually authorized the trade, not just a self-reported claim), and production systems typically check an independent identity-registry contract rather than an owner-controlled mapping baked into the hook itself.**
