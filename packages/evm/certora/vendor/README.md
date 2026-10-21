# Vendored deployed sources

Verified source of two deployed contracts, copied from Blockscout for
`confs/Governor-veto.conf`. Both are listed as fully verified there, so each
tree compiles to the code on chain.

| Directory | Contract | Address | Compiler |
| --- | --- | --- | --- |
| `TermFinanceGovernor/` | TermFinanceGovernor (OpenZeppelin v5.2.0) | `0x2B715634134220ffeEE9458b4e34E41A41418607` | solc 0.8.20, optimizer off, EVM paris |
| `TermToken/` | TermToken, the implementation behind the TERM proxy `0xC3d21f79C3120A4fFda7A535f8005a7c297799bF` | `0xeC222d8AfB8b4E78C418ebc1ab2cA181f19FbadC` | solc 0.8.20, optimizer 200 runs, EVM paris |

The only edit is to import paths in the two entry files, so that each tree
resolves its own copy of OpenZeppelin in a scene that also holds the Roles
Modifier's OpenZeppelin 4.3.1:

- `TermFinanceGovernor/contracts/TermFinanceGovernor.sol`: its four
  `@openzeppelin/contracts/...` imports point at `../@openzeppelin/contracts/...`.
- `TermToken/src/TermToken.sol`: its eight
  `@openzeppelin/contracts-upgradeable/...` imports point at
  `../lib/openzeppelin-contracts-upgradeable/contracts/...`.

No code is changed. TermToken's LayerZero imports are not vendored: the
confs remap `@layerzerolabs` to `node_modules`, where `package.json` pins
`@layerzerolabs/lz-evm-oapp-v2` and `@layerzerolabs/lz-evm-protocol-v2` at
2.1.3. Those releases hold the 27 files TermToken imports byte for byte as
verified, so keep that pin.

The repo copy in `term-finance-ops-contracts` is not the
deployed Governor: it returns `7 days` from `votingPeriod()`, while the
deployed Governor returns `22 hours`.

## TermToken for the TERM upgrade

`TermToken/src-triage/TermToken.sol` is not deployed yet. It is term-token's
`src/TermToken.sol` for the implementation the TERM proxy is to be upgraded
to. The Governor confs and
`confs/TermToken-supply.conf` compile it in place of `src/TermToken.sol`. It
has the same import-path edit as `TermToken/src/TermToken.sol`, so it compiles
against the same vendored OpenZeppelin in `TermToken/lib`: term-token pins
`openzeppelin-contracts` at `8b2f29ceb0db64957a49deb63af7792772bd7a5d` and
`openzeppelin-contracts-upgradeable` at
`fbdb824a735891908d5588b28e0da5852d7ed7ba`, and every `.sol` file in
`TermToken/lib` matches those commits byte for byte.

It differs from the deployed TermToken in `TermToken/src/TermToken.sol` in four
ways:

- `mint` and `burn` are `onlyRole(DEFAULT_ADMIN_ROLE)` and require their flag,
  `mintingNotPaused` or `burningNotPaused`. The deployed code admits a caller
  when the flag is on or the caller holds DEFAULT_ADMIN_ROLE.
- It no longer inherits LayerZero's OFTCore, so it has no `send`,
  `lzReceive`, peers, delegate or Ownable owner, and imports nothing from
  `@layerzerolabs`. Its constructor takes no arguments.
- It declares five private `__deprecated_` variables in slots 0 to 4, where
  OFTCore's parents kept their state, so `burningNotPaused` and
  `mintingNotPaused` stay in slot 4 on the live proxy.
- `_update` calls `ERC20VotesUpgradeable._update` directly, skipping
  `ERC20PausableUpgradeable`'s `whenNotPaused`, so a DEFAULT_ADMIN_ROLE
  holder can move, mint and burn TERM while it is paused.

## How the scene compiles them

`confs/Governor-veto.conf` compiles both for EVM paris, and TermToken with
the optimizer at 200 runs, as deployed. The Governor gets the optimizer at 1
run, like the scene's other contracts, instead of the optimizer off: once
`solc_optimize_map` names one file, certora-cli 7.31.0 enables the optimizer
for every file and has no value that turns it off. The optimizer changes the
bytecode, not what the code does.

The per-file maps are keyed by file path. certora-cli accepts contract-name
keys but drops them when it recompiles its instrumented copy of the sources,
which is how the first run compiled both contracts for Shanghai.
