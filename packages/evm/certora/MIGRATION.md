# Certora 8.19.2 migration

40 of 41 existing configurations now select Certora 8.19.2 in CI and the local runner. The [second batch](migration/8.19.2-second-batch.md) validates 32 additional configurations after the eight below. The CI matrix still runs the same 34 configurations: 33 on 8.19.2 and 1 on 7.31.0. All seven manual configurations use 8.19.2.

## First verified batch

The baseline is the passing [main CI run](https://github.com/term-finance/zodiac-modifier-roles-v1/actions/runs/37650684284) at `b78b57ea6e37c3eee48e265acb3c3dca4f76d5ff`. The uncached candidate cloud jobs below match the Solidity, dependency, configuration and CVL bytes in `2309fd508494e83dc22e014e3d5a2aa88937be8d`. Archive hashes, source hashes and all 41 CLI selections are retained in [the migration record](migration/8.19.2-first-batch.json).

| Configuration | Solidity | Verified leaves: 7 → 8 | Baseline | Candidate |
| --- | --- | --- | --- | --- |
| [MultiSend-shortBatch.conf](https://github.com/term-finance/zodiac-modifier-roles-v1/blob/2309fd508494e83dc22e014e3d5a2aa88937be8d/packages/evm/certora/confs/MultiSend-shortBatch.conf#L1) | 0.8.6 | 8 → 11 | [7.31.0](https://prover.certora.com/output/563174/54aff7d431914f9d9108c9b946d364d3) | [8.19.2](https://prover.certora.com/output/99679/c59261b04e144defb5dc22342371f6ff) |
| [PauseGuard-deployment.conf](https://github.com/term-finance/zodiac-modifier-roles-v1/blob/2309fd508494e83dc22e014e3d5a2aa88937be8d/packages/evm/certora/confs/PauseGuard-deployment.conf#L1) | 0.8.6 | 50 → 54 | [7.31.0](https://prover.certora.com/output/563174/1c2f584e95be46b2bbea6d494f28271d) | [8.19.2](https://prover.certora.com/output/99679/ad0df019c50d49e281be69f9899956e6) |
| [Safe-fallbackStorage.conf](https://github.com/term-finance/zodiac-modifier-roles-v1/blob/2309fd508494e83dc22e014e3d5a2aa88937be8d/packages/evm/certora/confs/Safe-fallbackStorage.conf#L1) | 0.7.6 | 4 → 5 | [7.31.0](https://prover.certora.com/output/563174/b16dd7f8c9514260b6418dd722d4e81e) | [8.19.2](https://prover.certora.com/output/99679/60f109b25ea64e5f93f96458d8acc778) |
| [Safe-noStateChange.conf](https://github.com/term-finance/zodiac-modifier-roles-v1/blob/2309fd508494e83dc22e014e3d5a2aa88937be8d/packages/evm/certora/confs/Safe-noStateChange.conf#L1) | 0.7.6 | 12 → 16 | [7.31.0](https://prover.certora.com/output/563174/b442cde714ab40b684cc9252efb0920f) | [8.19.2](https://prover.certora.com/output/99679/fcb7c8ae65744358a2bdb20a12550579) |
| [Safe-receive.conf](https://github.com/term-finance/zodiac-modifier-roles-v1/blob/2309fd508494e83dc22e014e3d5a2aa88937be8d/packages/evm/certora/confs/Safe-receive.conf#L1) | 0.7.6 | 3 → 4 | [7.31.0](https://prover.certora.com/output/563174/d5ebb527b7814e89af382357024a9e3b) | [8.19.2](https://prover.certora.com/output/99679/6a7b03d1033b462a8cfa194302dda846) |
| [Safe-v141-fallbackStorage.conf](https://github.com/term-finance/zodiac-modifier-roles-v1/blob/2309fd508494e83dc22e014e3d5a2aa88937be8d/packages/evm/certora/confs/Safe-v141-fallbackStorage.conf#L1) | 0.7.6 | 4 → 5 | [7.31.0](https://prover.certora.com/output/563174/7f0c02bae90f44caa5758dfb05ad25ef) | [8.19.2](https://prover.certora.com/output/99679/f9cef6e16d714103a6b94e9bf323fbb8) |
| [Safe-v141-noStateChange.conf](https://github.com/term-finance/zodiac-modifier-roles-v1/blob/2309fd508494e83dc22e014e3d5a2aa88937be8d/packages/evm/certora/confs/Safe-v141-noStateChange.conf#L1) | 0.7.6 | 12 → 16 | [7.31.0](https://prover.certora.com/output/563174/44e2c8f13a48489a8a08d8a96746150e) | [8.19.2](https://prover.certora.com/output/99679/8899abbdaa6e478d9d1491e59425c130) |
| [Safe-v141-receive.conf](https://github.com/term-finance/zodiac-modifier-roles-v1/blob/2309fd508494e83dc22e014e3d5a2aa88937be8d/packages/evm/certora/confs/Safe-v141-receive.conf#L1) | 0.7.6 | 3 → 4 | [7.31.0](https://prover.certora.com/output/563174/665f5dc346d648c9a088d70d4292e852) | [8.19.2](https://prover.certora.com/output/99679/79dce1567a1943f4b945f0e58e9ec75e) |

All eight jobs ended with every result node verified, including basic sanity and existential witnesses. The archived backend versions are 7.31.0 and 8.19.2 respectively. The comparison retains all 180 baseline rule/method/sanity groups, normalizing only source-line offsets introduced by the companion assertions; 8.x has 203 groups and 115 verified leaves, versus 96 leaves in the baseline. Compiler versions, settings, compiled method inventories, configuration bytes and reported call-resolution inventories are unchanged.

Fifteen existing `satisfy` statements gain `assert true` companions. This makes the prover check implicit pessimistic assertions alongside each existential witness and retains its rule sanity. The assertion introduces no precondition. Certora documents this behavior in [the CVL statements reference](https://docs.certora.com/en/latest/docs/cvl/statements.html#satisfy-statements). The other additional results are constructor sanity checks for the PauseGuard invariants.

## Scope and assumptions

No contract, harness, property assertion, witness predicate, precondition, method filter, summary, scene link, compiler setting or loop bound was removed or weakened. No new assumption was added. These remain the existing bounded, conditional claims:

- **PauseGuard:** the four constructor-based invariants and rejection of a zero pauser, in the single-contract scene. The membership ghost starts at zero and tracks the real role map; preserved invariants rely on the other proved role invariants. Loop bound 1 and optimistic loop handling remain.
- **MultiSend:** short inputs execute no call; the existing witnesses exercise the no-op, longer input, threshold boundary and CALL hook; the entry-point rule remains. The short-input bound is at most 32 transaction bytes, with an existing 33-byte boundary witness. Loop bound 2 and optimistic loop/fallback handling remain.
- **Safe 1.3.0 and 1.4.1:** receive logging, fallback storage effects, and state effects with no handler, plus the existing hook/path witnesses. Method filters still select receive/fallback and, where applicable, `approveHash`. External handlers are outside the scene; the existing non-self-handler and empty-handler preconditions retain their scope. Loop bound 1, optimistic loop/fallback/hashing, hashing length 1024 and disabled storage splitting remain. Ghost resets measure effects during the selected call.

This first batch does not prove arbitrary external-handler behavior, all Safe execution paths, unbounded loops, or a deployment configuration. The separate inventory check accounts for all 41 specs/contexts and issues **zero semantic dependency-closure certificates**. Specification completeness, abstraction refinement and deployment bindings remain separate obligations; upgrading the prover does not discharge them. No contract flaw was identified by these compatibility runs.

## Diagnostics retained for review

The six Safe candidate archives report a points-to call-graph diagnostic for `execTransaction` and a storage-analysis diagnostic for `getStorageAt`. Their actual method instances are receive/fallback and, in the hook-witness suites, `approveHash`; neither diagnostic method occurs in the selected CVL or resolved-call reports. No method selection was changed to exclude them. The full compiled scene remains identical to the baseline.

The pinned prover source [reports call-graph analysis failure as a warning and falls back to heuristics](https://github.com/Certora/CertoraProver/blob/8.19.2/src/main/kotlin/analysis/icfg/CallGraphBuilder.kt#L4485-L4523); [storage-analysis failure is retained as a failure result if subsequently consumed](https://github.com/Certora/CertoraProver/blob/8.19.2/src/main/kotlin/analysis/storage/StorageAnalysis.kt#L4195-L4203). These diagnostics are recorded in the migration evidence rather than described as clean logs. They must be reassessed when migrating suites that exercise those methods. The older baseline also has display-annotation warnings; the candidate has none of those.

## Run a proof

From `packages/evm`, activate a Python environment, install the selected pin, and provide `CERTORAKEY` through the environment or that directory’s `.env`:

```sh
conf=Safe-receive.conf
pip install -r "$(python3 certora/toolchain.py "$conf" --field requirements)"
solc-select install 0.7.6 0.8.6
./run-certora.sh "$conf" "Certora migration check"
```

The local runner checks the installed CLI before submission, runs from the package directory, and selects the same default compiler as CI. Existing mixed-compiler configurations still require CI’s `solc7.6`, `solc8.6` and `solc8.20` aliases. The runner uses the active environment; it no longer implicitly activates `.venv`.

`python3 certora/toolchain_test.py` checks every configuration’s pin and default compiler, rejects outside/missing configurations and malformed pins, and exercises both successful and wrong-version local-runner paths with a stub (no cloud submission).

## Remaining

One configuration remains on 7.31.0: `Roles-setTxNonceGuardAndRoleConfig.conf`. The [packed-key investigation](migration/8.19.2-packed-keys.md) adds native EVM regression checks and reproducible cloud diagnostics: precise settings pass the isolated packing checks, but the full suite still lacks an accepted result. No additional configuration is promoted. Historical records retain the selections as they stood for each batch; the [second record](migration/8.19.2-second-batch.json) contains the current selection for all 41 configurations.
