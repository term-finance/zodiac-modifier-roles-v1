# Ownerless Safe ConfigLockGuard Proof


## 1. High Level Conclusion

### Conclusion

```
Branch 1 (the slow path, for real proposals)
  Proposer Safe (5/11) --module--> Delay (+ PauseGuard) --module--> Ownerless Safe (+ ConfigLockGuard)

Signed path
  Ownerless Safe signers (9/9) --execTransaction--> Ownerless Safe --checked by--> ConfigLockGuard
```

The summation of all of the conclusions drawn from FV proofs should prove the following statements:

1. Once installed, the Ownerless Safe's signers cannot remove or replace its ConfigLockGuard.

2. Once installed, the Ownerless Safe's signers cannot enable or disable a module, change its fallback handler, or make a delegate call. So against the signers, the Delay stays the Ownerless Safe's only module and the handler stays zero.

3. Once installed, the Ownerless Safe's signers can still act on the protocol with plain calls and manage the Safe's owners and threshold.

4. Governance through the Delay is untouched: a proposal that has waited out the cooldown can still make the Ownerless Safe do anything, including change the settings the signers cannot. Nothing can change what the guard checks.

**Assumption.** This proof takes the Ownerless Safe to own no Zodiac modifier: it renounces ownership of the Roles Modifier before the guard is relied on (see S1.1). The Ownerless Safe's [`ConfigLockGuard`](../contracts/helpers/ConfigLockGuard.sol) is then built with `lockedModifier = address(0)`, and it locks only the Ownerless Safe's own settings. It also rejects the seven modifier selectors (`transferOwnership`, `renounceOwnership`, `enableModule`, `disableModule`, `setGuard`, `setAvatar`, `setTarget`) sent to `address(0)`, but `address(0)` has no code, so that locks nothing real.

That is the Proposer Safe's configuration, on the same GnosisSafe v1.3.0 code, so the signed-path locks are the `PG` rules in [PROPOSERSAFEGUARD_PROOFS.md](PROPOSERSAFEGUARD_PROOFS.md) ([`confs/Safe-proposerSafeGuard.conf`](confs/Safe-proposerSafeGuard.conf), [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec)). No rule in that spec assumes anything about the Proposer Safe beyond its Safe version, and only PG-6 assumes `lockedModifier = address(0)`. What differs is that the Ownerless Safe has a module, the Delay, and that module is the governance path. A new conf covers that, plus the guard's own entry points: [`confs/Safe-ownerlessSafeGuard.conf`](confs/Safe-ownerlessSafeGuard.conf) ([`specs/Safe/ownerlessSafeGuard.spec`](specs/Safe/ownerlessSafeGuard.spec)), code `LG`, the real GnosisSafe v1.3.0 through `GnosisSafeHarness` (solc 0.7.6) with the real ConfigLockGuard (solc 0.8.6) in its guard slot. Rule IDs are listed in section 2.

**FV status.** All `LG` and `PG` rules pass against ConfigLockGuard on the Prover (certora-cli 7.31.0, `--rule_sanity basic`), compiled with solc 0.7.6 and 0.8.6 as in CI. Both confs are in the CI matrix ([`.github/workflows/formal-verification.yaml`](../../../.github/workflows/formal-verification.yaml)), so every push reruns them.

**On-chain status.** ConfigLockGuard is not yet deployed or installed on the Ownerless Safe. Before it is installed, the old Roles must be removed as a module and the fallback handler cleared, because afterwards the signers can no longer do either and only a Branch 1 proposal could. The Roles Modifier must also be renounced before this proof applies (S1.1).

### Statement 1 — Once installed, the signers cannot remove or replace ConfigLockGuard

| # | Statement | Evidence |
| --- | --- | --- |
| S1.1 | ConfigLockGuard is installed as the Ownerless Safe's guard, built with no locked modifier, after the Ownerless Safe's module list, fallback handler and Roles ownership are in their target state. | **FV — the owners can install it:** PG-7 `ownersCanInstallConfigLockGuard` ✅ passes. With no guard set, the owners' `execTransaction` of `setGuard(ConfigLockGuard)` addressed to the Safe succeeds and the guard slot then holds ConfigLockGuard.<br><br>**On-chain — the Ownerless Safe's guard is ConfigLockGuard:** ⏳ pending deployment. The guard slot (`0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8`) on the Ownerless Safe (`0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03`) must hold the deployed ConfigLockGuard.<br><br>**On-chain — no locked modifier:** ⏳ pending deployment. `lockedModifier()` on that ConfigLockGuard must return `address(0)`. PG-6, LG-2 and LG-3 assume it.<br><br>**On-chain — first, the old Roles is removed as a module:** ⏳ pending, same as G1.5. At block 26085317 the Ownerless Safe has two modules, the old Roles (`0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2`) and the Delay. Once the guard is installed the signers cannot call `disableModule` (S2.3).<br><br>**On-chain — first, the fallback handler is cleared:** ⏳ pending, same as G1.3. At block 26085317 the handler slot holds CompatibilityFallbackHandler v1.3.0 (`0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4`), and the plan has no task that clears it. Once the guard is installed the signers cannot call `setFallbackHandler` (S2.5).<br><br>**On-chain — first, the Roles Modifier is renounced:** ⏳ pending. `owner()` on the Roles Modifier (`0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3`) must no longer be the Ownerless Safe. At block 26083996 it is the Ownerless Safe (G3.RolesModifier.2b). The guard does not block `renounceOwnership` on the Roles Modifier (PG-6), so this can also happen after installation. |
| S1.2 | The guard slot only changes when the Safe calls itself. For the signers, that is `execTransaction`'s call to the Safe. | **FV — settings only change on a self-call:** SE-7 `settingsOnlyChangeWhenTheSafeCallsItself` ✅ passes.<br><br>**FV — the Safe calls itself through three paths only:** `execTransaction`, a module's `execTransactionFromModule`, or `fallback`'s call to its handler (G1.2 in PROOFS.md).<br>• SE-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can use the module path. On the Ownerless Safe that is the Delay, which is governance (Statement 4), not the signers.<br>• SE-13 `fallbackMakesNoCallWithoutAHandler` ✅ passes: with no handler, `fallback` makes no call. The handler is cleared before installation (S1.1) and the signers cannot set one (S2.5).<br>• SE-9 `setupAlwaysRevertsAfterSetup` ✅ passes: `setup` cannot be re-run to reset the guard.<br><br>That leaves `execTransaction`'s call to the Safe itself, which S1.3 covers. |
| S1.3 | The Safe's `execTransaction` cannot call its own `setGuard`, or otherwise move the guard. | **FV — the guard rejects it:** PG-2 `checkTransactionRejectsSelfSetGuard` ✅ passes.<br><br>**FV — end to end, it reverts:** PG-8 `guardedSafeCannotCallSetGuard` ✅ passes. Removing the guard (`setGuard(address(0))`) and replacing it are both this call.<br><br>**FV — no self-call moves the guard:** PG-13 `guardedSelfCallNeverChangesGuard` ✅ passes. With ConfigLockGuard installed, for any calldata and operation, `execTransaction` addressed to the Safe leaves the guard slot holding ConfigLockGuard.<br><br>A delegate call could write the guard slot directly. It is blocked too (S2.4). |

### Statement 2 — Once installed, the signers cannot change the modules or handler, or delegate call

| # | Statement | Evidence |
| --- | --- | --- |
| S2.1 | ConfigLockGuard is installed as the Ownerless Safe's guard. | Same as S1.1. |
| S2.2 | The Delay is the Ownerless Safe's only module. | Same as G1.5. ⏳ pending the removal of the old Roles (S1.1). |
| S2.3 | The signers cannot enable or disable a module. | **FV — the guard rejects it:** PG-3 `checkTransactionRejectsSelfEnableModule`, PG-4 `checkTransactionRejectsSelfDisableModule` ✅ pass.<br><br>**FV — end to end, it reverts:** PG-9 `guardedSafeCannotCallEnableModule`, PG-10 `guardedSafeCannotCallDisableModule` ✅ pass.<br><br>**FV — no self-call changes the module list:** PG-14 `guardedSelfCallNeverChangesModules` ✅ passes. With ConfigLockGuard installed, for any calldata and operation, `execTransaction` addressed to the Safe leaves every entry of the module list as it was.<br><br>So the signers can neither add a module that would bypass the guard nor remove the Delay, which would cut Branch 1 off from the Ownerless Safe. |
| S2.4 | The signers cannot make a delegate call. | **FV — the guard rejects it:** PG-1 `checkTransactionRejectsDelegateCall` ✅ passes.<br><br>**FV — end to end, it reverts:** PG-12 `guardedSafeCannotDelegateCall` ✅ passes, to any address.<br><br>Delegated code runs as the Safe and could otherwise write the guard slot, the module list or the handler slot directly. A MultiSend batch reached by plain call makes its calls from the MultiSend contract, not the Safe, so they cannot change the Safe's settings (SE-7). `requiredTxGas` and `simulateAndRevert` always revert afterwards (SE-10, SE-11). |
| S2.5 | The signers cannot change the fallback handler. | **FV — the guard rejects it:** PG-5 `checkTransactionRejectsSelfSetFallbackHandler` ✅ passes.<br><br>**FV — end to end, it reverts:** PG-11 `guardedSafeCannotCallSetFallbackHandler` ✅ passes.<br><br>**FV — no self-call moves the handler:** PG-15 `guardedSelfCallNeverChangesFallbackHandler` ✅ passes: all 256 bits of the handler slot are unchanged.<br><br>So once cleared before installation (S1.1), the handler stays zero against the signers. |

### Statement 3 — Once installed, the signers can still act on the protocol and manage owners

| # | Statement | Evidence |
| --- | --- | --- |
| S3.1 | The guard blocks nothing but the calls above. | **FV — everything else passes:** PG-6 `checkTransactionAcceptsEverythingElse` ✅ passes. With `lockedModifier = address(0)`, every plain call that is not the Safe calling its own `setGuard`, `enableModule`, `disableModule` or `setFallbackHandler`, and not one of the seven modifier selectors (`transferOwnership`, `renounceOwnership`, `enableModule`, `disableModule`, `setGuard`, `setAvatar`, `setTarget`) sent to `address(0)`, passes the guard, whatever the destination, value and calldata. With PG-1 to PG-5, the guard blocks delegate calls and those four self-calls; the only other calls it rejects go to `address(0)`, which has no code, so they could never do anything. |
| S3.2 | The signers can still make plain calls to the protocol, such as the `DEVOPS_ROLE` calls of G1.1. | **FV — plain calls still succeed:** PG-16 `guardedOwnersCanStillCallOut` ✅ passes. With ConfigLockGuard installed and the threshold passed, a plain `execTransaction` to another contract succeeds. |
| S3.3 | The signers can still manage the Safe's owners and threshold. | **FV — each unblocked settings function still works:** PG-17 `guardedOwnersCanStillChangeOtherSettings` ✅ passes, for each of `addOwnerWithThreshold`, `removeOwner`, `swapOwner` and `changeThreshold`. |
| S3.4 | Only the Ownerless Safe's nine signers can use the signed path. | **FV — `execTransaction` needs the signers:** SE-5 `execTransactionRunsOnlyAfterTheSignatureCheck`, SE-12 `eachSignatureAcceptsANewApprovingOwner` ✅ pass. SE-6 `ownersCanMakeTheSafeAct` ✅ passes: once they have signed, it succeeds.<br><br>**On-chain — the Ownerless Safe is a 9-of-9 Safe:** ✅ same as G1.4. At block 26084853 it runs GnosisSafe v1.3.0, with threshold 9 and 9 owners. |

### Statement 4 — Governance through the Delay is untouched, and the guard cannot change

| # | Statement | Evidence |
| --- | --- | --- |
| S4.1 | The guard is never consulted on the module path, so a Delay proposal is not checked by it. | **FV — a module still does what the guard forbids the signers:** PG-18 `moduleCanDelegateCallPastTheGuard`, PG-19 `moduleCanDelegateCallPastTheGuardWithReturnData` ✅ pass: a module's delegate call succeeds, so a proposal can still batch through MultiSend. PG-20 `moduleCanRemoveTheGuard` ✅ passes: a module can move the guard out of the slot. |
| S4.2 | A Delay proposal can still change any of the Ownerless Safe's settings. | **FV — every settings function still works on the module path:** LG-2 `moduleCanStillChangeEachSetting` ✅ passes. With ConfigLockGuard installed, for each of the Safe's eight settings functions, including the four the signers cannot call, an enabled module's `execTransactionFromModule` addressed to the Safe with a call to it succeeds and a setting changes. |
| S4.3 | A Delay proposal can still act on the protocol. | **FV — plain calls still succeed on the module path:** LG-3 `moduleCanStillCallOut` ✅ passes. With ConfigLockGuard installed, an enabled module's plain `execTransactionFromModule` to another contract succeeds. |
| S4.4 | Only the Delay can use the module path, and only for proposals that waited out the cooldown. | **FV — only enabled modules:** SE-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes, and the Delay is the only module (S2.2).<br><br>**The Delay's own restrictions:** same as G1.13. A proposal comes only from the Proposer Safe, waits out the cooldown, must not have expired, and can be vetoed or paused. |
| S4.5 | Nothing can change what the guard checks. | **FV — the guard's entry points are accounted for:** LG-1 `configLockGuardFunctionsAreTheKnownFour` ✅ passes. ConfigLockGuard has no fallback, its functions are exactly `checkTransaction`, `checkAfterExecution`, `supportsInterface` and `lockedModifier`, and none of them writes state. `lockedModifier` is immutable and the guard has no admin, so what it checks is fixed at deployment. |
| S4.6 | Every entry point of the Ownerless Safe is covered. | **FV — the Safe's entry points are enumerated:** SE-1 `safeEntryPointsAreAllAccountedFor` ✅ passes, as in G1.2. The signed path is `execTransaction` (Statements 1 to 3), the module path is `execTransactionFromModule` and `execTransactionFromModuleReturnData` (this statement), the settings functions are self-calls reached only through those two (SE-7), and the rest always revert or are `fallback` and `receive`. |

### Not claimed

- **The guard does not bound governance.** A Branch 1 proposal can remove the guard, add or remove modules, set a handler or delegate call (S4.1, S4.2). That is the intended path for changing the Ownerless Safe, and it is bounded by the Delay's cooldown, the veto and the pause (G1.13), not by this guard.
- **The signers keep their protocol power.** The guard does not restrict what the signers' plain calls do to other contracts. They still hold `DEVOPS_ROLE` (G1.1).
- **Roles Modifier ownership.** The proof assumes the Ownerless Safe has renounced the Roles Modifier (S1.1). While it still owns it, the signers can change every Roles setting: `lockedModifier = address(0)` locks nothing real outside the Safe.

### Modelling notes and limits

- The `PG` scene is shared with the Proposer Safe. It assumes nothing about which Safe it is beyond GnosisSafe v1.3.0, so its rules carry over unchanged. Its modelling notes apply here (see [PROPOSERSAFEGUARD_PROOFS.md](PROPOSERSAFEGUARD_PROOFS.md)).
- In the `LG` scene the module's call to `to` is routed to the Safe's eight settings functions, so LG-2 pins `to` to the Safe. LG-3 pins `to` away from it.
- The module is any enabled module in both scenes. That it is the Delay on chain is S2.2.

---

## 2. Rule IDs

Rule IDs follow PROOFS.md: the conf's code, then the rule's position in its spec. `LG` = `Safe-ownerlessSafeGuard`, `PG` = `Safe-proposerSafeGuard`, `SE` = `Safe-executionPaths` (Safe v1.3.0).

| ID | Rule | Spec |
| --- | --- | --- |
| LG-1 | `configLockGuardFunctionsAreTheKnownFour` | [`specs/Safe/ownerlessSafeGuard.spec`](specs/Safe/ownerlessSafeGuard.spec) |
| LG-2 | `moduleCanStillChangeEachSetting` | [`specs/Safe/ownerlessSafeGuard.spec`](specs/Safe/ownerlessSafeGuard.spec) |
| LG-3 | `moduleCanStillCallOut` | [`specs/Safe/ownerlessSafeGuard.spec`](specs/Safe/ownerlessSafeGuard.spec) |
| PG-1 to PG-20 | see section 2 of [PROPOSERSAFEGUARD_PROOFS.md](PROPOSERSAFEGUARD_PROOFS.md) | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| SE-1, SE-3, SE-5, SE-6, SE-7, SE-9, SE-10, SE-11, SE-12, SE-13 | see G1.2 in [PROOFS.md](PROOFS.md) | [`specs/Safe/executionPaths.spec`](specs/Safe/executionPaths.spec) |
