# 24 — Shared Libraries & Building Blocks

Goal: a reference sheet of the specific tools you'll see imported at the top of nearly every real hook, across every category — so when you read someone else's hook source code, the import list stops being unfamiliar noise.

## Math libraries: why you almost never use plain `+`/`-`/`*`/`/` for prices

Solidity has no native decimal/floating-point type — `5 / 2` in Solidity is `2`, not `2.5`, because integer division truncates. Financial math (prices, percentages, fees) needs precision that raw integer math can't give you, so real hooks use **fixed-point math libraries**, which represent fractional numbers as very large integers scaled by a fixed factor (commonly `1e18`, meaning "1.0" is stored as the number `1000000000000000000`), and provide safe multiply/divide operations that handle that scaling correctly without overflowing or silently losing precision.

- **`FixedPointMathLib`** (from Solmate or Solady) — the most commonly used, lightweight fixed-point math helper: `mulDivDown`, `mulDivUp`, and similar functions that correctly handle "multiply two big numbers, then divide, without overflowing partway through" — a genuinely easy mistake to make by hand (`a * b / c` can overflow at the `a * b` step even when the final answer would have fit fine).
- **`PRBMath`** — a more full-featured fixed-point and math library (natural log, exponentials, more exotic operations), reached for when a hook's logic needs something beyond basic multiply/divide (e.g. a hook computing implied volatility or an options-pricing curve).
- **`TickMath`** (from `v4-core`) — converts between a tick (article 4's discrete price step) and the actual `sqrtPriceX96` representation Uniswap uses internally for price. You'll import this constantly any time your hook logic needs to reason about "what price does tick X actually represent" or vice versa.

## Token-handling: why hooks don't just call `transfer()` directly

- **`SafeERC20`** (OpenZeppelin) — wraps standard ERC20 `transfer`/`transferFrom` calls with extra checks, because a meaningful number of real-world tokens (most infamously USDT) don't strictly follow the ERC20 standard's return-value conventions, and a naive `transfer()` call can silently "succeed" against a broken token in a way that leaves your contract's accounting wrong. `SafeERC20`'s `safeTransfer`/`safeTransferFrom` handle these edge cases so your hook doesn't have to special-case every weird token it might ever touch.
- **`CurrencyLibrary`** (from `v4-core`) — v4 represents both ERC20 tokens *and* native ETH under one unified `Currency` type (instead of the older pattern of wrapping ETH into WETH everywhere), and this library provides the helper functions (`transfer`, `balanceOf`) that work correctly across both cases. Any time you see a `Currency` type instead of a plain `address` in a hook's code, this is why.

## Access control and safety

- **`Ownable`** (OpenZeppelin) — the standard "one address (the owner) can call certain admin functions" pattern, used in lesson 23's whitelist example and in essentially any hook that needs *some* configurable parameter (fee bounds, an oracle address, pausing) without full decentralized governance.
- **`ReentrancyGuard`** (OpenZeppelin) — a modifier (`nonReentrant`) that prevents a function from being re-entered (called again) before its first execution finishes, protecting against reentrancy attacks (a malicious token or contract calling back into your hook mid-execution to exploit inconsistent intermediate state). Worth knowing where this matters specifically for hooks: the PoolManager itself already has its own reentrancy protections around the core swap/liquidity flow, but *your hook's own* external calls (to a vault in lesson 20, to an oracle in lesson 19) can still open your own contract-level reentrancy surface if you're not careful — covered properly in lesson 25.
- **`Pausable`** (OpenZeppelin) — a simple, commonly-added safety valve: an owner-controlled switch that can halt a hook's normal operation in an emergency (a discovered bug, an oracle malfunction) without needing to fully redeploy or migrate the pool. Cheap insurance to add to almost any hook holding real user funds.

## Reading pool state from inside your own hook

- **`StateLibrary`** (from `v4-core`, used constantly in lessons 17-22) — the standard way any hook reads the PoolManager's actual current state (price, tick, liquidity) for a given pool, since — recall article 5 — that state lives inside the singleton PoolManager's own storage, not inside your hook contract.

## Vaults and yield

- **`IERC4626`** (the "Tokenized Vault Standard," used in lesson 20) — the standard interface almost every "park idle capital somewhere to earn yield" hook builds on. Worth knowing the two functions you'll call constantly: `deposit(assets, receiver)` (put tokens in, get vault shares back) and `redeem(shares, receiver, owner)` (burn shares, get the underlying tokens plus accrued yield back).

## Oracles

- **`AggregatorV3Interface`** (Chainlink, used in lesson 19) — the standard interface for reading a Chainlink price feed's `latestRoundData()`. Any hook reading an external price will import this (or Pyth's equivalent SDK interfaces, for hooks integrated with Pyth instead).

## A realistic import block, now legible

Once you've met each of the above once, a real hook's import list — which looks like unreadable noise the first time you see it — becomes a straightforward checklist of "which specific concerns does this hook need to handle":

```solidity
import {BaseHook} from "v4-periphery/src/utils/BaseHook.sol";                     // hook plumbing (lesson 15)
import {Hooks} from "v4-core/src/libraries/Hooks.sol";                            // permission flags (lesson 15)
import {StateLibrary} from "v4-core/src/libraries/StateLibrary.sol";              // read pool state (lesson 17)
import {LPFeeLibrary} from "v4-core/src/libraries/LPFeeLibrary.sol";              // dynamic fee override (lesson 18)
import {TickMath} from "v4-core/src/libraries/TickMath.sol";                      // tick <-> price conversion
import {FixedPointMathLib} from "solmate/src/utils/FixedPointMathLib.sol";        // safe fee/percentage math
import {SafeERC20} from "openzeppelin-contracts/token/ERC20/utils/SafeERC20.sol"; // safe token transfers
import {IERC4626} from "openzeppelin-contracts/interfaces/IERC4626.sol";          // yield vault integration (lesson 20)
import {AggregatorV3Interface} from "chainlink/interfaces/AggregatorV3Interface.sol"; // external oracle (lesson 19)
```

That's a hook doing dynamic fees, idle-capital yield parking, *and* oracle-based safety checks all at once — a genuinely realistic, ambitious combination, and by this point in the lesson series you should be able to guess roughly what each import is there to do before even reading the contract body.

## The one sentence to keep

**Almost every real hook's import list draws from the same small toolbox — a fixed-point math library (for precision Solidity's native integers don't give you), `SafeERC20`/`CurrencyLibrary` (for tokens that don't perfectly follow the standard, and native ETH), `Ownable`/`ReentrancyGuard`/`Pausable` (for admin control and safety), `StateLibrary` (to read the PoolManager's real state), and whichever domain-specific interface (ERC-4626, Chainlink) its particular idea needs — and once you recognize each one on sight, no hook's import block will look like unfamiliar noise again.**
