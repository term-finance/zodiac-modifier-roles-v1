# Proposer Safe ConfigLockGuard Proof


## 1. High Level Conclusion

### Conclusion

```
Branch 1 (the slow path, for real proposals)
  Proposer Safe (5/11, + ConfigLockGuard) --module--> Delay (+ PauseGuard) --module--> Ownerless Safe
```

The summation of all of the conclusions drawn from FV proofs should prove the following statements:

1. Once installed, the Proposer Safe cannot remove or replace its ConfigLockGuard.

2. Once installed, the Proposer Safe cannot enable or disable a module, change its fallback handler, or make a delegate call, so nothing can run as the Proposer Safe without passing through the guard.

3. Once installed, the Proposer Safe can still propose to the Delay and manage its own owners and threshold.

Why these locks are needed: Safe v1.3.0 consults its guard in `execTransaction` (PG-8 to PG-12) but not on the module path. With the guard installed, an enabled module can still delegate call and remove the guard (PG-18 to PG-20). And a delegate call could write the guard, module or handler slots directly. [`ConfigLockGuard`](../contracts/helpers/ConfigLockGuard.sol) blocks any delegate call, and the Safe calling its own `setGuard`, `enableModule`, `disableModule` or `setFallbackHandler`. It takes the Safe from `msg.sender`, so it has no Safe address to pin and no admin. Its one piece of state is the immutable `lockedModifier`, the Zodiac modifier whose settings it also locks. The Proposer Safe owns no modifier, so its ConfigLockGuard is built with `lockedModifier = address(0)`. The guard then also rejects the seven modifier selectors (`transferOwnership`, `renounceOwnership`, `enableModule`, `disableModule`, `setGuard`, `setAvatar`, `setTarget`) sent to `address(0)`, but `address(0)` has no code, so it locks nothing real outside the Safe.

FV evidence comes from a new conf, [`confs/Safe-proposerSafeGuard.conf`](confs/Safe-proposerSafeGuard.conf) ([`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec)), plus Safe and Delay rules already cited in [PROOFS.md](PROOFS.md). The scene is the real GnosisSafe v1.3.0 through `GnosisSafeHarness` (solc 0.7.6), the Proposer Safe's version, with the real ConfigLockGuard (solc 0.8.6) in its guard slot. The rules that the guard rejects a call hold for any `lockedModifier`, since the guard checks calls to the Safe itself first. Only PG-6 assumes `lockedModifier = address(0)`. Rule IDs are listed in section 2.

**FV status.** All `PG` rules pass against ConfigLockGuard on the Prover (certora-cli 7.31.0, `--rule_sanity basic`), compiled with solc 0.7.6 and 0.8.6 as in CI. The conf is in the CI matrix ([`.github/workflows/formal-verification.yaml`](../../../.github/workflows/formal-verification.yaml)), so every push reruns it.

**On-chain status.** ConfigLockGuard is not yet deployed or installed on the Proposer Safe. At block 26080484, the Proposer Safe's guard slot (`0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8`) is zero. The on-chain rows about the guard stay ⏳ pending until a ConfigLockGuard built with `address(0)` is deployed and the Proposer Safe calls `setGuard(<ConfigLockGuard>)` on itself.

### Statement 1 — Once installed, the Proposer Safe cannot remove or replace ConfigLockGuard

| # | Statement | Evidence |
| --- | --- | --- |
| S1.1 | ConfigLockGuard is installed as the Proposer Safe's guard, built with no locked modifier. | **FV — the owners can install it:** PG-7 `ownersCanInstallConfigLockGuard` ✅ passes. With no guard set, the owners' `execTransaction` of `setGuard(ConfigLockGuard)` addressed to the Safe succeeds and the guard slot then holds ConfigLockGuard.<br><br>**On-chain — the Proposer Safe's guard is ConfigLockGuard:** ⏳ pending deployment. The guard slot (`0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8`) on the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`) must hold the deployed ConfigLockGuard. At block 26080484 it is zero.<br><br>**On-chain — no locked modifier:** ⏳ pending deployment. `lockedModifier()` on that ConfigLockGuard must return `address(0)`. PG-6 assumes it. Any other value would block some calls to that address as well, and the guard cannot be replaced once installed (S1.3). |
| S1.2 | The guard slot only changes when the Safe calls itself, and with no modules the Safe only calls itself through `execTransaction`. | **FV — settings only change on a self-call:** SE-7 `settingsOnlyChangeWhenTheSafeCallsItself` ✅ passes. The guard slot, like every other setting, only changes when the caller is the Safe itself.<br><br>**FV — the Safe calls itself through three paths only:** `execTransaction`, a module's `execTransactionFromModule`, or `fallback`'s call to its handler (P1.2 in PROOFS.md).<br>• SE-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can use the module path, and the Proposer Safe has none (S2.2).<br>• SE-13 `fallbackMakesNoCallWithoutAHandler` ✅ passes: with no handler, `fallback` makes no call. The Proposer Safe has none (P1.10), and cannot set one (S2.5).<br>• SE-9 `setupAlwaysRevertsAfterSetup` ✅ passes: `setup` cannot be re-run to reset the guard.<br><br>That leaves `execTransaction`'s call to the Safe itself, which S1.3 covers. |
| S1.3 | The Safe's `execTransaction` cannot call its own `setGuard`, or otherwise move the guard. | **FV — the guard rejects it:** PG-2 `checkTransactionRejectsSelfSetGuard` ✅ passes. Called by the Safe, the guard reverts on any transaction to the Safe itself whose calldata starts with `setGuard(address)` (`0xe19a9dd9`), whatever the new guard, value or operation.<br><br>**FV — end to end, it reverts:** PG-8 `guardedSafeCannotCallSetGuard` ✅ passes. With ConfigLockGuard installed, `execTransaction` addressed to the Safe with a `setGuard` call reverts. Removing the guard (`setGuard(address(0))`) and replacing it are both this call.<br><br>**FV — no self-call moves the guard:** PG-13 `guardedSelfCallNeverChangesGuard` ✅ passes. With ConfigLockGuard installed, for any calldata and operation, `execTransaction` addressed to the Safe leaves the guard slot holding ConfigLockGuard. The Safe's call to itself runs its real settings functions, so this covers every settings function, not only `setGuard`.<br><br>A delegate call could write the guard slot directly. It is blocked too (S2.4). |

### Statement 2 — Once installed, the Proposer Safe cannot change its modules or handler, or delegate call

| # | Statement | Evidence |
| --- | --- | --- |
| S2.1 | ConfigLockGuard is installed as the Proposer Safe's guard. | Same as S1.1. |
| S2.2 | The Proposer Safe has no enabled modules. Any module would bypass the guard. | **FV — the module path does not consult the guard:** with ConfigLockGuard installed, an enabled module still does exactly what the guard forbids.<br>• PG-18 `moduleCanDelegateCallPastTheGuard`, PG-19 `moduleCanDelegateCallPastTheGuardWithReturnData` ✅ pass: a module's delegate call through `execTransactionFromModule`, and through `execTransactionFromModuleReturnData`, succeeds. The guard rejects every delegate call (PG-1), so it was not consulted.<br>• PG-20 `moduleCanRemoveTheGuard` ✅ passes: a module can have the Safe call its own `setGuard` and move ConfigLockGuard out of the guard slot, which `execTransaction` never can (PG-13).<br><br>**On-chain — no modules:** ✅ `getModulesPaginated` on the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`) returns an empty list at block 26080484 (P1.12 in PROOFS.md, re-read). |
| S2.3 | The Safe cannot enable or disable a module. | **FV — the guard rejects it:** PG-3 `checkTransactionRejectsSelfEnableModule`, PG-4 `checkTransactionRejectsSelfDisableModule` ✅ pass. Called by the Safe, the guard reverts on any transaction to the Safe itself whose calldata starts with `enableModule(address)` (`0x610b5925`) or `disableModule(address,address)` (`0xe009cfde`), whatever the module.<br><br>**FV — end to end, it reverts:** PG-9 `guardedSafeCannotCallEnableModule`, PG-10 `guardedSafeCannotCallDisableModule` ✅ pass. With ConfigLockGuard installed, `execTransaction` addressed to the Safe with an `enableModule` or `disableModule` call reverts.<br><br>**FV — no self-call changes the module list:** PG-14 `guardedSelfCallNeverChangesModules` ✅ passes. With ConfigLockGuard installed, for any calldata and operation, `execTransaction` addressed to the Safe leaves every entry of the module list as it was.<br><br>**FV — no other route:** the module list only changes on a self-call (SE-7), and S1.2 shows `execTransaction` is the only self-call path while there are no modules. So the Proposer Safe stays module-free, and S2.2 keeps holding. |
| S2.4 | The Safe cannot make a delegate call. | **FV — the guard rejects it:** PG-1 `checkTransactionRejectsDelegateCall` ✅ passes. The guard reverts on every delegate call, whatever the destination and calldata.<br><br>**FV — end to end, it reverts:** PG-12 `guardedSafeCannotDelegateCall` ✅ passes. With ConfigLockGuard installed, `execTransaction` with `operation = DelegateCall` reverts, to any address.<br><br>This closes the direct write: delegated code runs as the Safe and could otherwise write the guard slot (S1.3), the module list (S2.3) or the handler slot (S2.5) without calling their setters. A MultiSend batch is covered too: reached by delegate call it is blocked here, and reached by a plain call its calls come from the MultiSend contract, not the Safe, so they cannot change the Safe's settings (SE-7). `requiredTxGas` and `simulateAndRevert` also execute a call or delegate call, but always revert afterwards (SE-10, SE-11). |
| S2.5 | The Safe cannot change its fallback handler. | **FV — the guard rejects it:** PG-5 `checkTransactionRejectsSelfSetFallbackHandler` ✅ passes. Called by the Safe, the guard reverts on any transaction to the Safe itself whose calldata starts with `setFallbackHandler(address)` (`0xf08a0323`), whatever the handler.<br><br>**FV — end to end, it reverts:** PG-11 `guardedSafeCannotCallSetFallbackHandler` ✅ passes.<br><br>**FV — no self-call moves the handler:** PG-15 `guardedSelfCallNeverChangesFallbackHandler` ✅ passes. With ConfigLockGuard installed, for any calldata and operation, `execTransaction` addressed to the Safe leaves all 256 bits of the handler slot unchanged.<br><br>**On-chain — the handler is zero:** ✅ at block 26080484 the Proposer Safe's fallback handler slot (`0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5`) is zero (P1.10 in PROOFS.md), so it stays zero. |

### Statement 3 — Once installed, the Proposer Safe can still propose and manage its owners

| # | Statement | Evidence |
| --- | --- | --- |
| S3.1 | The guard blocks nothing but the calls above. | **FV — everything else passes:** PG-6 `checkTransactionAcceptsEverythingElse` ✅ passes. With `lockedModifier = address(0)` (S1.1), every plain call that is not the Safe calling its own `setGuard`, `enableModule`, `disableModule` or `setFallbackHandler`, and not one of the seven modifier selectors (`transferOwnership`, `renounceOwnership`, `enableModule`, `disableModule`, `setGuard`, `setAvatar`, `setTarget`) sent to `address(0)`, passes the guard, whatever the destination, value and calldata. With PG-1 to PG-5, the guard blocks delegate calls and those four self-calls; the only other calls it rejects go to `address(0)`, which has no code, so they could never do anything. |
| S3.2 | The Proposer Safe can still propose a transaction to the Delay. | **FV — plain calls still succeed:** PG-16 `guardedOwnersCanStillCallOut` ✅ passes. With ConfigLockGuard installed and the threshold passed, a plain `execTransaction` to another contract succeeds. The Proposer Safe's proposal is one such call: `execTransactionFromModule` on the Delay.<br><br>**FV — the Delay accepts it:** DM-5 `enabledModuleCanQueue` ✅ passes. Any enabled module's `execTransactionFromModule` call succeeds and adds the transaction to the Delay's queue. The Proposer Safe is the Delay's only enabled module (P1.8 in PROOFS.md), and P1.13 follows the entry through to the Ownerless Safe. |
| S3.3 | The owners can still manage the Safe's owners and threshold. | **FV — each unblocked settings function still works:** PG-17 `guardedOwnersCanStillChangeOtherSettings` ✅ passes. With ConfigLockGuard installed, for each of `addOwnerWithThreshold`, `removeOwner`, `swapOwner` and `changeThreshold`, an `execTransaction` addressed to the Safe with a call to it succeeds and a setting changes. |
| S3.4 | Only the Proposer Safe's signers can do any of this. | **FV — `execTransaction` needs the signers:** SE-5 `execTransactionRunsOnlyAfterTheSignatureCheck`, SE-12 `eachSignatureAcceptsANewApprovingOwner` ✅ pass: `execTransaction` acts only when as many different owners as the threshold have approved. SE-6 `ownersCanMakeTheSafeAct` ✅ passes: once they have, it succeeds.<br><br>**On-chain — the Proposer Safe is a 5-of-11 Safe:** ✅ at block 26080484, it runs Safe v1.3.0 (`VERSION`), has threshold 5 (`getThreshold`) and 11 owners (`getOwners`). |

### Modelling notes and limits

- The Safe's call to `to` has a symbolic target, so the spec routes it to the Safe's eight settings functions (as in `selfCalls.spec`). That routing ignores `to`, so PG-13 to PG-15 pin `to` to the Safe itself. A call to any other address can only change the Safe's settings by calling back into it, and SE-7 shows that fails unless the caller is the Safe.
- A self-call whose selector is none of the eight leaves the Safe's storage alone in the model. That includes the Safe calling its own `execTransaction` again. The nested call goes through the same guard, so the same rules apply to it.
- `checkSignatures` is stubbed to pass. That only adds executions, so the revert and "never changes" rules are unaffected. The signature check itself is SE-5 and SE-12.
- `lockedModifier` is left unconstrained in the scene, except in PG-6. ConfigLockGuard's checks on its locked modifier are proved in the DelayOwnerSafe's scene, [DELAYOWNERGUARD_PROOFS.md](DELAYOWNERGUARD_PROOFS.md) (OG-6 to OG-10).

---

## 2. Rule IDs

Rule IDs follow PROOFS.md: the conf's code, then the rule's position in its spec. `PG` = `Safe-proposerSafeGuard`, `SE` = `Safe-executionPaths` (Safe v1.3.0), `DM` = `Delay-moduleIntegrity`.

| ID | Rule | Spec |
| --- | --- | --- |
| PG-1 | `checkTransactionRejectsDelegateCall` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-2 | `checkTransactionRejectsSelfSetGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-3 | `checkTransactionRejectsSelfEnableModule` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-4 | `checkTransactionRejectsSelfDisableModule` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-5 | `checkTransactionRejectsSelfSetFallbackHandler` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-6 | `checkTransactionAcceptsEverythingElse` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-7 | `ownersCanInstallConfigLockGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-8 | `guardedSafeCannotCallSetGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-9 | `guardedSafeCannotCallEnableModule` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-10 | `guardedSafeCannotCallDisableModule` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-11 | `guardedSafeCannotCallSetFallbackHandler` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-12 | `guardedSafeCannotDelegateCall` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-13 | `guardedSelfCallNeverChangesGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-14 | `guardedSelfCallNeverChangesModules` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-15 | `guardedSelfCallNeverChangesFallbackHandler` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-16 | `guardedOwnersCanStillCallOut` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-17 | `guardedOwnersCanStillChangeOtherSettings` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-18 | `moduleCanDelegateCallPastTheGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-19 | `moduleCanDelegateCallPastTheGuardWithReturnData` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-20 | `moduleCanRemoveTheGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| DM-5 | `enabledModuleCanQueue` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| SE-3, SE-5, SE-6, SE-7, SE-9, SE-10, SE-11, SE-12, SE-13 | see P1.2 in [PROOFS.md](PROOFS.md) | [`specs/Safe/executionPaths.spec`](specs/Safe/executionPaths.spec) |
