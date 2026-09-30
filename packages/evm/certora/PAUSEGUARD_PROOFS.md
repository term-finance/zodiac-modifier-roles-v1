# PauseGuard Proof


## 1. High Level Conclusion

### Conclusion

```
Branch 1 (the slow path, for real proposals)
  Proposer Safe (5/11) --module--> Delay (+ PauseGuard) --module--> Ownerless Safe

Pause controls
  PauseSafe (2/9)  --pause-->               PauseGuard
  Admin Safe (4/10) --unpause / setPauser--> PauseGuard
```

The summation of all of the conclusions drawn from FV proofs should prove the following statements:

1. PauseGuard pauses when called by the pauser, and once paused no queued Delay transaction can execute.

2. The PauseGuard admin successfully unpauses, and once unpaused queued Delay transactions can execute again.

3. The PauseGuard admin successfully sets the pauser to another pauser, and from then on only the new pauser can pause.

Pausing and unpausing are deliberately asymmetric: the low-threshold PauseSafe can pause, but only an `ADMIN_ROLE` holder, the Admin Safe, can unpause or replace the pauser. That way the party being paused cannot unpause itself.

FV evidence comes from two confs, plus the Safe rules already cited in [PROOFS.md](PROOFS.md):

- [`confs/Delay-pauseGuardSufficient.conf`](confs/Delay-pauseGuardSufficient.conf) ([`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec)): the real Delay mastercopy with the real [`PauseGuard`](../contracts/helpers/PauseGuard.sol) installed through `Guardable.setGuard`. The rules leave role membership unconstrained apart from the caller under test, so they hold for any admin and pauser, including Safes.
- [`confs/PauseGuard-deployment.conf`](confs/PauseGuard-deployment.conf) ([`specs/PauseGuard/deployment.spec`](specs/PauseGuard/deployment.spec)): PauseGuard alone. Its invariants' base case runs the real constructor with any arguments it accepts, so what the constructor sets up is checked by the Prover, not read off source.

Rule IDs are listed in section 2.

**On-chain status.** PauseGuard is not yet installed on the Delay. At block 26080440, `guard()` on the Delay (`0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf`) returns `0x0000000000000000000000000000000000000000`, and the Delay's owner is still the old Roles (`0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2`, see G2.3 in PROOFS.md). The on-chain rows about PauseGuard's own state stay ⏳ pending until the migration installs it.

### Statement 1 — PauseGuard pauses when called by the pauser

| # | Statement | Evidence |
| --- | --- | --- |
| P1.1 | PauseGuard is installed as the Delay's guard. | **FV — the Delay's owner can install it:** DP-1 `setGuardInstallsPauseGuard` ✅ passes. The owner's `setGuard(PauseGuard)` succeeds and the Delay's `guard` slot then holds PauseGuard.<br>• DP-2 `pauseGuardAnswersIGuardInterfaceId` ✅ passes: PauseGuard reports IGuard (`0xe6d7a83a`) and ERC-165 (`0x01ffc9a7`), which is the only check `Guardable.setGuard` makes.<br><br>**FV — only the owner can remove it:** DM-7 `guardOnlyChangesThroughOwnerSetGuard` ✅ passes. The Delay's `guard` slot moves only through the owner's `setGuard`, so nothing else can detach PauseGuard.<br><br>**On-chain — the Delay's guard is PauseGuard:** ⏳ pending migration. `guard()` on the Delay must return the deployed PauseGuard. At block 26080440 it returns `0x0`. |
| P1.2 | The pauser is the PauseSafe. | **On-chain — pauser is the PauseSafe:** ⏳ pending deployment. `pauser()` on PauseGuard must return the PauseSafe (`0x74f3F3dEfdC563bbFC8637BaB2d30596D2817472`).<br><br>**FV — there is always exactly one pauser, and it is never zero:** PD-4 `pauserNeverZero` ✅ passes. From the constructor on, `pauser()` is never the zero address. `pauser` is a single address slot, so the on-chain read above names the one account that can pause.<br><br>**On-chain — the PauseSafe is a 2-of-9 Safe that only its signers can drive:** ✅ at block 26080440, the PauseSafe runs Safe v1.4.1 (`VERSION`), has threshold 2 (`getThreshold`) and 9 owners (`getOwners`), no enabled modules (`getModulesPaginated` returns an empty list), and a zero guard slot (`0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8`) and fallback handler slot (`0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5`).<br><br>**FV — with no modules and no handler, only its signers can make it call `pause`:** the rules of G2.4 in PROOFS.md, run on Safe v1.4.1.<br>• SE141-6 `ownersCanMakeTheSafeAct` ✅ passes: once the threshold is passed, `execTransaction` succeeds and the Safe acts.<br>• SE141-5 `execTransactionRunsOnlyAfterTheSignatureCheck`, SE141-12 `eachSignatureAcceptsANewApprovingOwner` ✅ pass: `execTransaction` acts only when as many different owners as the threshold have approved.<br>• SE141-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can use the module path, and the PauseSafe has none.<br>• SE141-13 `fallbackMakesNoCallWithoutAHandler` ✅ passes: with no handler set, `fallback` makes no call at all. |
| P1.3 | The pauser can successfully pause. | **FV — the pauser always can:** DP-5 `pauseSucceedsForThePauser` ✅ passes. From an unpaused state, the pauser's `pause()` succeeds and `paused` is then true. Stated against whatever address `pauser()` holds, so it holds for the PauseSafe (P1.2). |
| P1.4 | Only the pauser can pause. | **FV — every other caller reverts:** DP-3 `pauseRevertsForAnyoneButThePauser` ✅ passes. Any caller other than `pauser()` reverts on `pause()`.<br>• DP-4 `adminAloneCannotPause` ✅ passes: holding `ADMIN_ROLE` does not let a caller pause. The admin can unpause and replace the pauser, not pause.<br><br>**FV — `pause` is the only way to set the flag:** DP-9 `pausedOnlyChangesThroughPauseOrUnpause` ✅ passes. Over every write function of both the Delay and PauseGuard, if `paused` changed, the function was `pause` or `unpause`.<br><br>**FV — the pauser cannot be changed another way:** DP-14 `pauserOnlyChangesThroughSetPauser` ✅ passes. Over every write function of both contracts, `pauser` only changes through `setPauser`, which is admin-only (P3.3). The pauser cannot hand the power on itself. |
| P1.5 | Once paused, no queued transaction executes. | **FV — paused blocks execution end to end:** DP-18 `pausedBlocksExecuteNextTx` ✅ passes. With PauseGuard installed and paused, `executeNextTx` reverts and nothing reaches the Delay's target (the Ownerless Safe), for any transaction arguments and any queue state.<br>• DP-19 `checkTransactionRevertsWhilePaused` ✅ passes: called directly, a paused PauseGuard rejects every transaction from every caller.<br><br>**FV — `executeNextTx` is the only way out of the Delay:** DP-34 `onlyExecuteNextTxReachesTheTarget` ✅ passes. Over every write function of both the Delay and PauseGuard, if a transaction reached the Delay's target, the function was `executeNextTx`. Queueing, the owner's settings functions, `skipExpired` and PauseGuard's own functions never forward anything. With DP-18, a pause stops every transaction the Delay can send.<br><br>**FV — the guard is what blocks it:** DP-26 `withoutPauseGuardExecuteNextTxForwardsUnchecked` ✅ passes. With no guard installed, `executeNextTx` forwards without any check, so P1.5 is not achieved by nothing working. |

### Statement 2 — PauseGuard admin successfully unpauses

| # | Statement | Evidence |
| --- | --- | --- |
| P2.1 | The Admin Safe is the only `ADMIN_ROLE` holder, and that cannot change. | **On-chain — Admin Safe holds `ADMIN_ROLE`:** ⏳ pending deployment. `hasRole(ADMIN_ROLE, 0x73d1C7dc9CEb14660Cf1E9BB29F80ECF9E97D774)` on PauseGuard must return true, where `ADMIN_ROLE` = `keccak256("ADMIN_ROLE")` = `0xa49807205ce4d355092ef5a8a18f56e8913cf4a201fbe287825b095693c21775`.<br><br>**FV — there is exactly one `ADMIN_ROLE` holder, ever:** PD-3 `exactlyOneAdminRoleHolder` ✅ passes. From the constructor on, `ADMIN_ROLE` has exactly one holder. So once the on-chain read above shows the Admin Safe holds it, nobody else does or can.<br><br>**FV — membership is fixed at deployment:** DP-15 `adminRoleNeverChanges` ✅ passes. Over every write function of both contracts, `ADMIN_ROLE` membership never changes for any account.<br>• DP-13 `inheritedGrantAndRevokeAlwaysRevert` ✅ passes: the inherited `grantRole` and `revokeRole` revert for every role and every caller, admins included, because both roles are administered by `DEFAULT_ADMIN_ROLE`, which nobody holds.<br>• DP-12 `renounceRoleAlwaysReverts` ✅ passes: no holder can drop a role, so the last admin cannot strand the guard with nobody able to unpause.<br>• DP-16 `defaultAdminRoleNeverGranted` ✅ passes: an unheld `DEFAULT_ADMIN_ROLE` stays unheld.<br>• PD-1 `defaultAdminRoleNeverHeld` ✅ passes: the base case DP-16 leaves open. From the constructor on, nobody holds `DEFAULT_ADMIN_ROLE`.<br>• DP-17 `roleAdminWiringNeverChanges` ✅ passes: nothing re-points the admin of `ADMIN_ROLE` or `DEFAULT_ADMIN_ROLE`.<br>• PD-2 `roleAdminWiringIsFixed` ✅ passes: the wiring DP-13 and DP-15 assume. From the constructor on, both `ADMIN_ROLE` and `DEFAULT_ADMIN_ROLE` are administered by `DEFAULT_ADMIN_ROLE`.<br><br>**On-chain — the Admin Safe is a 4-of-10 Safe that only its signers can drive:** ✅ at block 26080440, the Admin Safe runs Safe v1.3.0 (`VERSION`), has threshold 4 (`getThreshold`) and 10 owners (`getOwners`), no enabled modules (`getModulesPaginated` returns an empty list), and a zero guard slot. Unlike the Safes in PROOFS.md, its fallback handler slot is set, to `0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4`.<br><br>**FV — only its signers can make it call `unpause` or `setPauser`:** the rules of G1.2 in PROOFS.md, run on Safe v1.3.0.<br>• SE-6 `ownersCanMakeTheSafeAct` ✅ passes: once the threshold is passed, `execTransaction` succeeds and the Safe acts.<br>• SE-5 `execTransactionRunsOnlyAfterTheSignatureCheck`, SE-12 `eachSignatureAcceptsANewApprovingOwner` ✅ pass: `execTransaction` acts only when as many different owners as the threshold have approved.<br>• SE-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can use the module path, and the Admin Safe has none.<br>• SE-14 `fallbackOnlyCallsItsHandler`, SE-15 `fallbackHandlerCallsComeFromTheHandler` ✅ pass: with a handler set, `fallback` only makes a plain call to the handler, and any call the handler makes onward has the handler, not the Safe, as `msg.sender`. The handler therefore cannot call `unpause` or `setPauser` as the Admin Safe. |
| P2.2 | The admin can successfully unpause. | **FV — `ADMIN_ROLE` is enough:** DP-8 `unpauseSucceedsForAdminRole` ✅ passes. From a paused state, an `ADMIN_ROLE` holder's `unpause()` succeeds and `paused` is then false. |
| P2.3 | Only the admin can unpause. | **FV — every caller without `ADMIN_ROLE` reverts:** DP-6 `unpauseRevertsWithoutAdminRole` ✅ passes.<br>• DP-7 `pauserAloneCannotUnpause` ✅ passes: being the pauser does not let a caller lift a pause. This is the asymmetry the design depends on.<br><br>**FV — `unpause` is the only way to clear the flag:** DP-9 `pausedOnlyChangesThroughPauseOrUnpause` ✅ passes. |
| P2.4 | Once unpaused, queued transactions can execute again. | **FV — unpause reopens execution end to end:** DP-20 `unpauseReopensExecuteNextTx` ✅ passes. With PauseGuard installed and paused, after an `ADMIN_ROLE` holder unpauses, a following `executeNextTx` can succeed and reach the Delay's target.<br>• DP-21 `checkTransactionAcceptsWhileNotPaused` ✅ passes: while not paused, PauseGuard accepts any transaction from any caller, so it adds no revert of its own to `executeNextTx`. Whether an entry then runs depends only on the Delay's cooldown, expiration and `txNonce` (DP-29 to DP-31 in PROOFS.md G1.13). |

### Statement 3 — PauseGuard admin successfully sets the pauser to another pauser

| # | Statement | Evidence |
| --- | --- | --- |
| P3.1 | The Admin Safe is the only `ADMIN_ROLE` holder, and that cannot change. | Same as P2.1. |
| P3.2 | The admin can successfully replace the pauser, and the old pauser is displaced. | **FV — `ADMIN_ROLE` replaces the pauser:** DP-11 `setPauserSetsThePauser` ✅ passes. For any nonzero `account`, an `ADMIN_ROLE` holder's `setPauser(account)` succeeds, `pauser()` then returns `account`, and if `account` differs from the previous pauser, the previous pauser no longer holds the slot. There is only ever one pauser.<br><br>**FV — the pauser can never be left unset:** PD-5 `setPauserRevertsOnZeroAddress` ✅ passes. `setPauser(address(0))` reverts for every caller, admins included. PD-4 `pauserNeverZero` ✅ passes: the pauser is never zero. To stand the pauser down, the admin points it at an account that cannot act. |
| P3.3 | Only the admin can replace the pauser. | **FV — every caller without `ADMIN_ROLE` reverts:** DP-10 `setPauserRevertsWithoutAdminRole` ✅ passes. The pauser included, nobody without `ADMIN_ROLE` can hand out or take away the right to pause.<br><br>**FV — `setPauser` is the only way to change the pauser:** DP-14 `pauserOnlyChangesThroughSetPauser` ✅ passes. |
| P3.4 | After the change, only the new pauser can pause. | **FV — follows from P3.2 and Statement 1:** DP-3 `pauseRevertsForAnyoneButThePauser` and DP-5 `pauseSucceedsForThePauser` ✅ pass, and both are stated against whatever address `pauser()` holds, not a fixed one. Once DP-11 has moved `pauser()` to the new account, DP-5 says the new pauser can pause and DP-3 says the old pauser, now any other caller, reverts. |

---

## 2. Rule IDs

Rule IDs follow PROOFS.md: the conf's code, then the rule's position in its spec (invariants included). `DP` = `Delay-pauseGuardSufficient`, `PD` = `PauseGuard-deployment`, `DM` = `Delay-moduleIntegrity`, `SE` = `Safe-executionPaths` (Safe v1.3.0), `SE141` = the same rules on Safe v1.4.1 through the `Safe-v141-*` confs.

| ID | Rule | Spec |
| --- | --- | --- |
| DP-1 | `setGuardInstallsPauseGuard` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-2 | `pauseGuardAnswersIGuardInterfaceId` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-3 | `pauseRevertsForAnyoneButThePauser` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-4 | `adminAloneCannotPause` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-5 | `pauseSucceedsForThePauser` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-6 | `unpauseRevertsWithoutAdminRole` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-7 | `pauserAloneCannotUnpause` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-8 | `unpauseSucceedsForAdminRole` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-9 | `pausedOnlyChangesThroughPauseOrUnpause` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-10 | `setPauserRevertsWithoutAdminRole` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-11 | `setPauserSetsThePauser` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-12 | `renounceRoleAlwaysReverts` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-13 | `inheritedGrantAndRevokeAlwaysRevert` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-14 | `pauserOnlyChangesThroughSetPauser` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-15 | `adminRoleNeverChanges` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-16 | `defaultAdminRoleNeverGranted` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-17 | `roleAdminWiringNeverChanges` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-18 | `pausedBlocksExecuteNextTx` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-19 | `checkTransactionRevertsWhilePaused` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-20 | `unpauseReopensExecuteNextTx` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-21 | `checkTransactionAcceptsWhileNotPaused` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-26 | `withoutPauseGuardExecuteNextTxForwardsUnchecked` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| DP-34 | `onlyExecuteNextTxReachesTheTarget` | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) |
| PD-1 | `defaultAdminRoleNeverHeld` | [`specs/PauseGuard/deployment.spec`](specs/PauseGuard/deployment.spec) |
| PD-2 | `roleAdminWiringIsFixed` | [`specs/PauseGuard/deployment.spec`](specs/PauseGuard/deployment.spec) |
| PD-3 | `exactlyOneAdminRoleHolder` | [`specs/PauseGuard/deployment.spec`](specs/PauseGuard/deployment.spec) |
| PD-4 | `pauserNeverZero` | [`specs/PauseGuard/deployment.spec`](specs/PauseGuard/deployment.spec) |
| PD-5 | `setPauserRevertsOnZeroAddress` | [`specs/PauseGuard/deployment.spec`](specs/PauseGuard/deployment.spec) |
| DM-7 | `guardOnlyChangesThroughOwnerSetGuard` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| SE-3, SE-5, SE-6, SE-12, SE-14, SE-15 | see G1.2 in [PROOFS.md](PROOFS.md) | [`specs/Safe/executionPaths.spec`](specs/Safe/executionPaths.spec) (SE-15: [`specs/Safe/fallbackHandler.spec`](specs/Safe/fallbackHandler.spec)) |
| SE141-3, SE141-5, SE141-6, SE141-12, SE141-13 | see G2.4 in [PROOFS.md](PROOFS.md) | [`specs/SafeV141/executionPaths.spec`](specs/SafeV141/executionPaths.spec) |
