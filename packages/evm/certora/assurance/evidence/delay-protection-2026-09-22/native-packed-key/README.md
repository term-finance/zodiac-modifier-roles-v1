# Native replay of the packed-key counterexample

The Certora `bitwise-memory-diagnostic` job gives the same function-scope key to
the two-byte payload `0x46ba` (selector `0x46ba0000`) and the allowed veto selector
`0x46ba2307`. An earlier diagnostic aliases the empty payload. In the compiled
EVM, both denied keys remain zero while the veto key is nonzero.

`PackedKey.t.sol` repeats those configuration operations with the reported target
and role, 10001. `forge.log` is the original successful replay with Foundry 1.7.1,
solc 0.8.30 and optimizer runs 1. The original build configuration is retained;
the replay command overrides its machine-specific compiler path.

From this directory, with Foundry installed:

```sh
python3 replay.py 0.8.30
```

An existing solc 0.8.30 executable path may replace the version argument. The
script checks the submitted archive's manifest hash and extracts only original
contract, harness and dependency sources into a temporary directory. Certora's
instrumented `.pre_autofinders` and `.post_autofinders` copies are excluded.

This is a concrete counterexample replay, not a proof for all inputs. It does
not establish forwarding safety, historical reachability, deployment bindings,
Delay correctness or semantic dependency closure. The more precise byte-memory
solver attempts report an internal prover error and remain unproved.
