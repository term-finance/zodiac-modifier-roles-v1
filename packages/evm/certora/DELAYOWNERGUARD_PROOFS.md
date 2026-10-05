# DelayOwnerSafe ConfigLockGuard Proof


## 1. High Level Conclusion

### Conclusion

```
Branch 2 (the token-vote path, whose only power is to veto)
  Governor --module--> Roles (+ SetTxNonceGuard) --target--> DelayOwnerSafe (+ ConfigLockGuard) --owner--> Delay

Signed path
  DelayOwnerSafe signers (5/11) --execTransaction--> DelayOwnerSafe --checked by--> ConfigLockGuard
```

The summation of all of the conclusions drawn from FV proofs should prove the following statements:

1. Once installed, the DelayOwnerSafe's ConfigLockGuard cannot be removed or replaced, and the DelayOwnerSafe's signers cannot enable or disable a module on it, change its fallback handler, or delegatecall.

2. The DelayOwnerSafe's signers cannot transfer or renounce ownership of the Delay, enable or disable a module on it, or change its guard, avatar or target.

3. Everything else the DelayOwnerSafe does still goes through: the veto `setTxNonce`, the Delay's cooldown and expiration, and the Safe's own owner and threshold management.

[`ConfigLockGuard`](../contracts/helpers/ConfigLockGuard.sol) is a Safe transaction guard. On the DelayOwnerSafe it is built with `lockedModifier` = the Delay. It checks what the signers sign and nothing a module sends (CL141-22), so the module path is bounded separately, by Role 1 and SetTxNonceGuard (P2.12 in [PROOFS.md](PROOFS.md)).

FV evidence comes from two new confs, plus Safe, Delay and Roles rules already cited in [PROOFS.md](PROOFS.md):

- [`confs/Safe-v141-configLockGuard.conf`](confs/Safe-v141-configLockGuard.conf) ([`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec)), code `CL141`: the real Safe v1.4.1 through `SafeV141Harness` (solc 0.7.6), the DelayOwnerSafe's version, with the real ConfigLockGuard (solc 0.8.6) in its guard slot. The guard's `lockedModifier` is left unconstrained, so these rules hold for whatever modifier it was built with, `address(0)` included.
- [`confs/Delay-delayOwnerGuard.conf`](confs/Delay-delayOwnerGuard.conf) ([`specs/Delay/delayOwnerGuard.spec`](specs/Delay/delayOwnerGuard.spec)), code `OD`: the real Delay mastercopy source ([`helpers/Delay.sol`](helpers/Delay.sol), solc 0.8.6) on its own for the Delay's half of the lock, plus the same Safe and guard, with the guard's `lockedModifier` linked to the Delay, for the witnesses that the guarded Safe can still run the Delay.

The Delay lock is proved in two halves that meet at the Safe's call into the Delay, as GV-2 and GV-3 do in P2.13. With the Safe routing arbitrary calldata into the Delay's functions, the Prover (certora-cli 7.31.0) stops with an internal error, as it does for GV-2. It does not when the calldata is one call of fixed length, which is how the `OD` witnesses are stated.

Safe v1.4.1 and Zodiac each bring their own `Enum.Operation`. They declare the same enum, so both confs remap `@gnosis.pm/safe-contracts` onto `@safe-global/safe-contracts`, which leaves one `Enum` in the scene. The two `Enum.sol` and `IERC165.sol` files differ only in comments and in `contract` versus `abstract contract`, so the guard's and the Delay's bytecode is unchanged. Rule IDs are listed in section 2.

**FV status.** All `CL141` and `OD` rules pass against ConfigLockGuard on the Prover (certora-cli 7.31.0, `--rule_sanity basic`), compiled with solc 0.7.6 and 0.8.6 as in CI. Both confs are in the CI matrix ([`.github/workflows/formal-verification.yaml`](../../../.github/workflows/formal-verification.yaml)), so every push reruns them.

**On-chain status.** ConfigLockGuard is not yet deployed or installed on the DelayOwnerSafe. At block 26080459 the DelayOwnerSafe's guard slot is zero, and the Delay's owner is still the old Roles (`0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2`, see P2.3 in PROOFS.md). The on-chain rows about the guard stay ⏳ pending until it is deployed and installed.

### Statement 1 — ConfigLockGuard stays installed and seals the DelayOwnerSafe

| # | Statement | Evidence |
| --- | --- | --- |
| DG1.1 | ConfigLockGuard is installed as the DelayOwnerSafe's guard, with the Delay as its locked modifier. | **FV — the owners can install it:** CL141-11 `ownersCanInstallConfigLockGuard` ✅ passes. With no guard set, the owners' `execTransaction` of `setGuard(ConfigLockGuard)` addressed to the Safe succeeds and the guard slot then holds ConfigLockGuard. v1.4.1's `setGuard` probes the new guard with `supportsInterface`, and the real guard answers it in the scene, so the probe passes.<br><br>**FV — only the Safe itself can change its guard:** SE141-7 `settingsOnlyChangeWhenTheSafeCallsItself`, SC141-4 `settingsOnlyChangeThroughAModuleOrOwners` ✅ pass. The guard slot is one of the Safe's settings, so it only changes when the Safe calls itself, through `execTransaction` or an enabled module.<br><br>**On-chain — the DelayOwnerSafe's guard is ConfigLockGuard:** ⏳ pending deployment. The guard slot (`0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8`) on the DelayOwnerSafe (`0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3`) must hold the deployed ConfigLockGuard. At block 26080459 it is zero.<br><br>**On-chain — the guard's locked modifier is the Delay:** ⏳ pending deployment. `lockedModifier()` on that ConfigLockGuard must return the Delay (`0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf`). CL141-6 to CL141-9 lock whatever address `lockedModifier()` holds, and the `OD` rules assume it is the Delay. So this has to be checked before the Safe calls `setGuard`. Once installed the guard cannot be replaced (DG1.3), so a wrong `lockedModifier` would leave the Delay's settings unlocked for good. With `address(0)`, for example, the guard would lock only calls to `address(0)`, which has no code. |
| DG1.2 | The guard checks every transaction the signers make, and none that a module sends. | **FV — the signed path is checked:** CL141-12 to CL141-19 ✅ pass. Every signed `execTransaction` in DG1.3 and DG1.4 reaches the real ConfigLockGuard, and its revert reverts the whole transaction.<br><br>**FV — the module path is not checked:** CL141-22 `moduleCallBypassesTheGuard` ✅ passes. With ConfigLockGuard installed, an enabled module's `execTransactionFromModule` addressed to the Safe with a `setGuard` call succeeds and moves the guard slot, which CL141-12 shows the owners cannot do.<br><br>**FV — only an enabled module can use the module path:** SE141-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes.<br><br>**On-chain — the Roles Modifier is the only module:** ✅ same as P2.7. At block 26080459, `getModulesPaginated` on the DelayOwnerSafe returns only the Roles Modifier (`0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3`).<br><br>**FV — the Roles Modifier can only send the veto:** same as P2.12. Every call the Governor completes through the Roles Modifier is `setTxNonce(uint256)` on the Delay, with zero value and as a plain `Call` (RG-2 to RG-5). |
| DG1.3 | The signers cannot remove or replace the guard, enable or disable a module, or change the fallback handler. | **FV — the guard rejects these self-calls:** CL141-2 `checkTransactionRejectsSelfSetGuard`, CL141-3 `checkTransactionRejectsSelfEnableModule`, CL141-4 `checkTransactionRejectsSelfDisableModule`, CL141-5 `checkTransactionRejectsSelfSetFallbackHandler` ✅ pass. Called by the Safe, the guard reverts on any transaction to the Safe itself whose calldata starts with `setGuard(address)` (`0xe19a9dd9`), `enableModule(address)` (`0x610b5925`), `disableModule(address,address)` (`0xe009cfde`) or `setFallbackHandler(address)` (`0xf08a0323`), whatever the argument, value or operation.<br><br>**FV — end to end, they revert:** CL141-12 `guardedSafeCannotCallSetGuard`, CL141-13 `guardedSafeCannotCallEnableModule`, CL141-14 `guardedSafeCannotCallDisableModule`, CL141-15 `guardedSafeCannotCallSetFallbackHandler` ✅ pass. With ConfigLockGuard installed, `execTransaction` addressed to the Safe with each of these calls reverts. Removing the guard (`setGuard(address(0))`) and replacing it are both the first call.<br><br>**FV — no self-call moves them:** CL141-17 `guardedSelfCallNeverChangesGuard`, CL141-18 `guardedSelfCallNeverChangesModules`, CL141-19 `guardedSelfCallNeverChangesFallbackHandler` ✅ pass. With ConfigLockGuard installed, for any calldata and operation, `execTransaction` addressed to the Safe leaves the guard slot holding ConfigLockGuard, leaves every entry of the module list as it was and leaves the handler slot unchanged. The Safe's call to itself runs its real settings functions, so this covers every settings function, not only the four above.<br><br>**FV — a self-call is the only way in:** SE141-7 `settingsOnlyChangeWhenTheSafeCallsItself` ✅ passes. These settings only change when the Safe calls itself. A call routed through another contract, such as MultiSendCallOnly, reaches the Safe with that contract as `msg.sender`.<br><br>Blocking `disableModule` also means the signers cannot take the Roles Modifier off the DelayOwnerSafe, which would cut Branch 2's veto.<br><br>**On-chain — nothing to unlock from:** ✅ at block 26080459 the DelayOwnerSafe's fallback handler slot is zero (P2.5), so the locked handler stays zero, and its only module is the Roles Modifier (DG1.2). |
| DG1.4 | The signers cannot delegatecall. | **FV — the guard rejects every delegatecall:** CL141-1 `checkTransactionRejectsDelegateCall` ✅ passes. The guard reverts on every delegate call, whatever the destination and calldata.<br><br>**FV — end to end, it reverts:** CL141-16 `guardedSafeCannotDelegateCall` ✅ passes. With ConfigLockGuard installed, `execTransaction` with `operation = DelegateCall` reverts, to any address.<br><br>A delegatecall runs someone else's code against the Safe's own storage, so it could write the guard slot or the module list directly and skip DG1.3. This also rules out batching through MultiSend, which needs a delegatecall. `simulateAndRevert` also makes a delegatecall, but always reverts afterwards (SE141-11). |

### Statement 2 — The DelayOwnerSafe cannot unlock the Delay

| # | Statement | Evidence |
| --- | --- | --- |
| DG2.1 | The Delay has one owner, which is the DelayOwnerSafe. | Same as P2.3. ⏳ pending migration. |
| DG2.2 | Only a direct call from the owner reaches the Delay's settings functions. | **FV — owner only:** DM-8 `atMostOneCallerPassesOnlyOwner` ✅ passes. Only the owner can call the Delay's ten settings functions, and there is only one owner at a time.<br>• DM-14 `onlyModulesOrOwnerCanCallDelay` ✅ passes: every other write function except `executeNextTx`, `skipExpired` and `setUp` only succeeds for the owner or an enabled module.<br><br>So a call routed through another contract, such as MultiSendCallOnly, reaches the Delay with that contract as `msg.sender` and reverts. The only calls ConfigLockGuard has to stop are the ones where `to` is the Delay. |
| DG2.3 | The signers cannot transfer or renounce the Delay, enable or disable a module on it, or change its guard, avatar or target. | **FV — the guard rejects these calls:** CL141-6 `checkTransactionRejectsModifierOwnershipChange`, CL141-7 `checkTransactionRejectsModifierModuleChange`, CL141-8 `checkTransactionRejectsModifierSetGuard`, CL141-9 `checkTransactionRejectsModifierSetAvatarOrTarget` ✅ pass. Called by the Safe, the guard reverts on any transaction to `lockedModifier()` whose calldata starts with `transferOwnership` (`0xf2fde38b`), `renounceOwnership` (`0x715018a6`), `enableModule` (`0x610b5925`), `disableModule` (`0xe009cfde`), `setGuard` (`0xe19a9dd9`), `setAvatar` (`0x086cfca8`) or `setTarget` (`0x776d1a01`).<br><br>**FV — the Safe's half, end to end:** CL141-23 `guardedSafeCannotCallLockedModifierFunctions` ✅ passes. With ConfigLockGuard installed, `execTransaction` to `lockedModifier()` carrying any of the seven selectors reverts, whatever the arguments, value and operation. The guard runs before the Safe makes its call, so the Delay is never reached. With CL141-16 (no delegate calls), every `execTransaction` to the Delay that succeeds is a plain call carrying some other selector.<br><br>**FV — the Delay's half: no other call moves them:** OD-1 `unlockedDelayCallsNeverChangeOwnerGuardAvatarOrTarget`, OD-2 `unlockedDelayCallsNeverChangeModules` ✅ pass. Over every Delay write function except the seven and `setUp`, and for any caller, the Delay's owner, guard, avatar and target read the same afterwards and no module is added or removed. The Delay has no fallback (DM-13), so a call with any other selector, or under 4 bytes, reverts. `setUp` always reverts after deployment (DM-1).<br><br>Together: every call the signers get through to the Delay is one of the calls OD-1 and OD-2 cover, so none of them changes the Delay's owner, modules, guard, avatar or target. Blocking `disableModule` also means the signers cannot take the Proposer Safe off the Delay, which would stop Branch 1.<br><br>**FV — the same holds for every other caller:**<br>• DM-6 `ownerOnlyChangesThroughOwnableTransfer` ✅ passes: the owner only changes through `transferOwnership` or `renounceOwnership`.<br>• DM-2 `modulesOnlyChangeThroughOwnerEnableOrDisable` ✅ passes: a module is only added or removed through the owner's `enableModule` or `disableModule`.<br>• DM-7 `guardOnlyChangesThroughOwnerSetGuard` ✅ passes: the guard only changes through the owner's `setGuard`, so PauseGuard stays on the Delay.<br>• OD-3 `delayAvatarAndTargetOnlyChangeThroughOwnerSetters` ✅ passes: over every Delay write function but `setUp`, the avatar only changes through the owner's `setAvatar` and the target only through the owner's `setTarget`. This closes the gap proofsContext.md records under Premise 12. |
| DG2.4 | The module path cannot reach these calls either. | Same as DG1.2. The Roles Modifier, the DelayOwnerSafe's only module, can only send `setTxNonce(uint256)` to the Delay (P2.12). |

### Statement 3 — Everything else still goes through

| # | Statement | Evidence |
| --- | --- | --- |
| DG3.1 | The veto still works. | **Signed path — FV:** OD-4 `guardedSafeCanStillVeto` ✅ passes. With ConfigLockGuard installed and the Safe owning the Delay, `execTransaction` of `setTxNonce(n)` to the Delay succeeds and `txNonce` becomes `n`, for an `n` the Delay accepts. DP-22 `ownerCanSetTxNonceWhilePaused` ✅ passes: the owner's `setTxNonce` lands even while PauseGuard is paused.<br><br>**Governor path:** the guard is never consulted on the module path (CL141-22), so the Governor's veto lands exactly as in P2.13 (GV-2, GV-3). |
| DG3.2 | The DelayOwnerSafe's signers can still manage owners and threshold. | **FV — each unblocked settings function still works:** CL141-21 `guardedOwnersCanStillChangeOtherSettings` ✅ passes. With ConfigLockGuard installed, for each of `addOwnerWithThreshold`, `removeOwner`, `swapOwner` and `changeThreshold`, an `execTransaction` addressed to the Safe with a call to it succeeds and a setting changes. |
| DG3.3 | The DelayOwnerSafe can still set the Delay's cooldown and expiration. | **FV — each unblocked Delay setting still works:** OD-5 `guardedSafeCanStillSetTxCooldown`, OD-6 `guardedSafeCanStillSetTxExpiration` ✅ pass. With ConfigLockGuard installed and the Safe owning the Delay, an `execTransaction` to the Delay of `setTxCooldown(c)` succeeds and the cooldown becomes `c`, and of `setTxExpiration(x)` succeeds and the expiration becomes `x`. |
| DG3.4 | The guard blocks nothing but the calls above. | **FV — everything else passes:** CL141-10 `checkTransactionAcceptsEverythingElse` ✅ passes. Every plain call that is not one of the locked calls in DG1.3 and DG2.3 passes the guard, whatever the destination, value and calldata, including `setTxNonce` and any call with less than 4 bytes of calldata. With CL141-1 to CL141-9, the guard blocks exactly those calls and delegate calls.<br><br>**FV — plain calls still succeed end to end:** CL141-20 `guardedOwnersCanStillCallOut` ✅ passes. With ConfigLockGuard installed, a plain `execTransaction` to an address other than the Safe and the Delay succeeds. |
| DG3.5 | Only the DelayOwnerSafe's signers can do any of this. | **FV — `execTransaction` needs the signers:** SE141-5 `execTransactionRunsOnlyAfterTheSignatureCheck`, SE141-12 `eachSignatureAcceptsANewApprovingOwner` ✅ pass: `execTransaction` acts only when as many different owners as the threshold have approved. SE141-6 `ownersCanMakeTheSafeAct` ✅ passes: once they have, it succeeds.<br><br>**On-chain — the DelayOwnerSafe is a 5-of-11 Safe:** ✅ at block 26080459, it runs Safe v1.4.1 (`VERSION`), has threshold 5 (`getThreshold`) and 11 owners (`getOwners`). |

### Not claimed

- **The lock holds against the signers, not against a full governance proposal.** The Ownerless Safe owns the Roles Modifier (G3.RolesModifier.2b). A Branch 1 proposal, which waits out the cooldown and can be vetoed or paused, could change Role 1 or remove SetTxNonceGuard. The Roles Modifier could then send the DelayOwnerSafe any call on the module path, which ConfigLockGuard never sees (CL141-22), including `setGuard(0)`.
- **A mistaken install cannot be undone.** See DG1.1: the `OD` rules assume `lockedModifier()` is the Delay, and DG1.3 means the guard can never be replaced.

### Modelling notes and limits

- The Safe's call to `to` has a symbolic target. In the `CL141` scene it is routed to the Safe's eight settings functions. That routing ignores `to`, so the "never changes" rules pin `to` to the Safe (CL141-17 to CL141-19). A call to any other address can only reach those functions by calling back in, where `msg.sender` is not the Safe (SE141-7). In the `OD` witnesses (OD-4 to OD-6) it is routed to the one Delay function each witness names, with `to` pinned to the Delay.
- In the `CL141` scene, a self-call whose selector is none of the eight leaves the Safe's storage alone. That includes the Safe calling its own `execTransaction` again. The nested call goes through the same guard, so the same rules apply to it.
- The Delay's half (OD-1 to OD-3) calls the Delay's functions directly, for any caller, so it needs no routing. The Delay's own call to its target in `executeNextTx` is summarised to change nothing. A target that called back into the Delay would do so as itself, which those rules already cover for any caller.
- `checkSignatures` is stubbed to pass. That only adds executions, so the revert and "never changes" rules are unaffected. The signature check itself is SE141-5 and SE141-12.

---

## 2. Rule IDs

Rule IDs follow PROOFS.md: the conf's code, then the rule's position in its spec. `CL141` = `Safe-v141-configLockGuard`, `OD` = `Delay-delayOwnerGuard`, `SE141` = `Safe-v141-executionPaths`, `SC141` = `Safe-v141-selfCalls`, `DM` = `Delay-moduleIntegrity`, `DP` = `Delay-pauseGuardSufficient`, `RG` = `Roles-setTxNonceGuardAndRoleConfig`, `GV` = `Governor-veto` and `Safe-v141-vetoLandsOnDelay`.

| ID | Rule | Spec |
| --- | --- | --- |
| CL141-1 | `checkTransactionRejectsDelegateCall` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-2 | `checkTransactionRejectsSelfSetGuard` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-3 | `checkTransactionRejectsSelfEnableModule` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-4 | `checkTransactionRejectsSelfDisableModule` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-5 | `checkTransactionRejectsSelfSetFallbackHandler` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-6 | `checkTransactionRejectsModifierOwnershipChange` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-7 | `checkTransactionRejectsModifierModuleChange` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-8 | `checkTransactionRejectsModifierSetGuard` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-9 | `checkTransactionRejectsModifierSetAvatarOrTarget` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-10 | `checkTransactionAcceptsEverythingElse` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-11 | `ownersCanInstallConfigLockGuard` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-12 | `guardedSafeCannotCallSetGuard` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-13 | `guardedSafeCannotCallEnableModule` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-14 | `guardedSafeCannotCallDisableModule` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-15 | `guardedSafeCannotCallSetFallbackHandler` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-16 | `guardedSafeCannotDelegateCall` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-17 | `guardedSelfCallNeverChangesGuard` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-18 | `guardedSelfCallNeverChangesModules` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-19 | `guardedSelfCallNeverChangesFallbackHandler` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-20 | `guardedOwnersCanStillCallOut` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-21 | `guardedOwnersCanStillChangeOtherSettings` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-22 | `moduleCallBypassesTheGuard` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| CL141-23 | `guardedSafeCannotCallLockedModifierFunctions` | [`specs/SafeV141/configLockGuard.spec`](specs/SafeV141/configLockGuard.spec) |
| OD-1 | `unlockedDelayCallsNeverChangeOwnerGuardAvatarOrTarget` | [`specs/Delay/delayOwnerGuard.spec`](specs/Delay/delayOwnerGuard.spec) |
| OD-2 | `unlockedDelayCallsNeverChangeModules` | [`specs/Delay/delayOwnerGuard.spec`](specs/Delay/delayOwnerGuard.spec) |
| OD-3 | `delayAvatarAndTargetOnlyChangeThroughOwnerSetters` | [`specs/Delay/delayOwnerGuard.spec`](specs/Delay/delayOwnerGuard.spec) |
| OD-4 | `guardedSafeCanStillVeto` | [`specs/Delay/delayOwnerGuard.spec`](specs/Delay/delayOwnerGuard.spec) |
| OD-5 | `guardedSafeCanStillSetTxCooldown` | [`specs/Delay/delayOwnerGuard.spec`](specs/Delay/delayOwnerGuard.spec) |
| OD-6 | `guardedSafeCanStillSetTxExpiration` | [`specs/Delay/delayOwnerGuard.spec`](specs/Delay/delayOwnerGuard.spec) |
| SE141-3 | `onlyEnabledModulesCanCallModuleExec` | [`specs/SafeV141/executionPaths.spec`](specs/SafeV141/executionPaths.spec) |
| SE141-5 | `execTransactionRunsOnlyAfterTheSignatureCheck` | [`specs/SafeV141/executionPaths.spec`](specs/SafeV141/executionPaths.spec) |
| SE141-6 | `ownersCanMakeTheSafeAct` | [`specs/SafeV141/executionPaths.spec`](specs/SafeV141/executionPaths.spec) |
| SE141-7 | `settingsOnlyChangeWhenTheSafeCallsItself` | [`specs/SafeV141/executionPaths.spec`](specs/SafeV141/executionPaths.spec) |
| SE141-11 | `simulateAndRevertAlwaysReverts` | [`specs/SafeV141/executionPaths.spec`](specs/SafeV141/executionPaths.spec) |
| SE141-12 | `eachSignatureAcceptsANewApprovingOwner` | [`specs/SafeV141/executionPaths.spec`](specs/SafeV141/executionPaths.spec) |
| SC141-4 | `settingsOnlyChangeThroughAModuleOrOwners` | [`specs/SafeV141/selfCalls.spec`](specs/SafeV141/selfCalls.spec) |
| DM-1 | `setUpAlwaysRevertsAfterDeployment` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| DM-2 | `modulesOnlyChangeThroughOwnerEnableOrDisable` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| DM-6 | `ownerOnlyChangesThroughOwnableTransfer` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| DM-7 | `guardOnlyChangesThroughOwnerSetGuard` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| DM-8 | `atMostOneCallerPassesOnlyOwner` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| DM-13 | `delayWriteFunctionsAreTheKnownFifteen` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| DM-14 | `onlyModulesOrOwnerCanCallDelay` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| DP-22 | `ownerCanSetTxNonceWhilePaused` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| RG-2 to RG-5 | see P2.12 in [PROOFS.md](PROOFS.md) | [`specs/Roles/setTxNonceGuardAndRoleConfig.spec`](specs/Roles/setTxNonceGuardAndRoleConfig.spec) |
| GV-2, GV-3 | see P2.13 in [PROOFS.md](PROOFS.md) | [`specs/Governor/veto.spec`](specs/Governor/veto.spec), [`specs/SafeV141/vetoLandsOnDelay.spec`](specs/SafeV141/vetoLandsOnDelay.spec) |
