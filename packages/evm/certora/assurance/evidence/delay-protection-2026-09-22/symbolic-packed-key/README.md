# Symbolic packed-key lemma

Halmos 0.3.3 / solc 0.8.30 proves that the actual
`Permissions.keyForFunctions(address,bytes4)` is injective in the pair of inputs.
Both addresses and both selectors are symbolic with no preconditions, dynamic
array bounds or storage assumptions. There are six paths, two successful
terminal paths, zero blocked paths and zero bounded loops. Complete compiler
input/output and the result are retained.

This supports triage of the Certora packed-key alias. It does not prove the full
permission transition, memory-model refinement in Certora, deployment equivalence
or dependency closure. The strict Certora policy job remains unproved.

To replay, reconstruct the three `input.sources` entries in `compiler.json.gz`
into an empty temporary directory, use the retained Foundry settings with a
local solc 0.8.30 executable, then run:

```
halmos --root TEMP --contract PackedKeyLemma --function check_packedKeyInjective --json-output result.json --statistics
```

Do not infer a proof from process success alone. Require the exact one method,
exitcode zero, successful paths, zero blocked paths and zero bounded loops.
