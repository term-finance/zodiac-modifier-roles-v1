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

No code is changed. The repo copy in `term-finance-ops-contracts` is not the
deployed Governor: it returns `7 days` from `votingPeriod()`, while the
deployed Governor returns `22 hours`.

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
