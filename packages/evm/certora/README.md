# Certora proofs

One folder per release, named after its git tag, holding that release's confs, specs and proof documents. Every release shares the same contract sources (`packages/evm/contracts`, and `harness/`, `helpers/` and `vendor/` here) except the three guards: ConfigLockGuard, PauseGuard and SetTxNonceGuard.

| Folder | Proves | Guards | Proof documents |
| --- | --- | --- | --- |
| [`2.0.0`](2.0.0) | Release `2.0.0`, the live mainnet configuration | Pulled from tag `2.0.0` into `2.0.0/contracts/` | [`liveMainnetGovernanceConfigurationProof.md`](2.0.0/liveMainnetGovernanceConfigurationProof.md) |

[`pull_guards.py`](pull_guards.py) writes a tagged release's guards, and the files they import relatively, from its tag to `<release>/contracts/` (gitignored), so they compile next to the shared sources. At most one folder is untagged at a time.

## Running

From `packages/evm`:

```bash
./run-certora.sh 2.0.0/PauseGuard-deployment.conf
```

`run-certora.sh` pulls the guards first. CI runs each folder in its own workflow: `formal-verification-2.0.0.yaml` pulls the guards before running, and runs on every push except one that changes only the guards.

## Cutting a release

1. Tag the release, and add it to `TAGGED` in `pull_guards.py`.
2. Point its confs' guard paths at `certora/<tag>/contracts/helpers/`, and give its workflow the tag fetch, guard pull and path filters of `formal-verification-2.0.0.yaml`.
3. To prove the next release, copy the folder's `confs/` and `specs/` to a new folder named after the next tag, point the guards back at `contracts/helpers/`, and add it to `RELEASES` in `toolchain.py`.
