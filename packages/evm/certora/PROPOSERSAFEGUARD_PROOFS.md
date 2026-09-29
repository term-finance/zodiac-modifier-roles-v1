# ProposerSafeGuard Proof


## 1. High Level Conclusion

### Conclusion

```
Branch 1 (the slow path, for real proposals)
  Proposer Safe (5/11, + ProposerSafeGuard) --module--> Delay (+ PauseGuard) --module--> Ownerless Safe
```

The summation of all of the conclusions drawn from FV proofs should prove the following statements:

1. Once installed, the Proposer Safe cannot remove or replace ProposerSafeGuard.

2. Once installed, the Proposer Safe cannot enable a module or make a delegate call, so nothing can run as the Proposer Safe without passing through the guard.

3. Once installed, the Proposer Safe can still propose to the Delay and manage its own owners and threshold.

Why these locks are needed: Safe v1.3.0 consults its guard in `execTransaction` (PG-6 to PG-8) but not on the module path. With the guard installed, an enabled module can still delegate call and remove the guard (PG-13 to PG-15). And a delegate call could write the guard or module slots directly. ProposerSafeGuard blocks exactly three things: any delegate call, the Safe calling its own `setGuard`, and the Safe calling its own `enableModule`. It holds no state and takes the Safe from `msg.sender`, so it has no address to pin and no admin.

FV evidence comes from a new conf, [`confs/Safe-proposerSafeGuard.conf`](confs/Safe-proposerSafeGuard.conf) ([`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec)), plus Safe and Delay rules already cited in [PROOFS.md](PROOFS.md). The scene is the real GnosisSafe v1.3.0 through `GnosisSafeHarness` (solc 0.7.6), the Proposer Safe's version, with the real [`ProposerSafeGuard`](../contracts/helpers/ProposerSafeGuard.sol) (solc 0.8.6) in its guard slot. Rule IDs are listed in section 2.

**On-chain status.** ProposerSafeGuard is not yet deployed or installed. At block 26080484, the Proposer Safe's guard slot (`0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8`) is zero. The on-chain rows about the guard stay ⏳ pending until the Proposer Safe calls `setGuard(<ProposerSafeGuard>)` on itself, as `term-finance-web3-infra/src/create-proposer-safe-guard.ts` describes.

### Statement 1 — Once installed, the Proposer Safe cannot remove or replace ProposerSafeGuard

| # | Statement | Evidence |
| --- | --- | --- |
| S1.1 | ProposerSafeGuard is installed as the Proposer Safe's guard. | **FV — the owners can install it:** PG-5 `ownersCanInstallProposerSafeGuard` ✅ passes. With no guard set, the owners' `execTransaction` of `setGuard(ProposerSafeGuard)` addressed to the Safe succeeds and the guard slot then holds ProposerSafeGuard.<br><br>**On-chain — the Proposer Safe's guard is ProposerSafeGuard:** ⏳ pending deployment. The guard slot (`0x4a204f620c8c5ccdca3fd54d003badd85ba500436a431f0cbda4f558c93c34c8`) on the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`) must hold the deployed ProposerSafeGuard. At block 26080484 it is zero. |
| S1.2 | The guard slot only changes when the Safe calls itself, and with no modules the Safe only calls itself through `execTransaction`. | **FV — settings only change on a self-call:** SE-7 `settingsOnlyChangeWhenTheSafeCallsItself` ✅ passes. The guard slot, like every other setting, only changes when the caller is the Safe itself.<br><br>**FV — the Safe calls itself through three paths only:** `execTransaction`, a module's `execTransactionFromModule`, or `fallback`'s call to its handler (G1.2 in PROOFS.md).<br>• SE-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can use the module path, and the Proposer Safe has none (S2.2).<br>• SE-13 `fallbackMakesNoCallWithoutAHandler` ✅ passes: with no handler, `fallback` makes no call. The Proposer Safe has none (G1.8).<br>• SE-15 `fallbackHandlerCallsComeFromTheHandler`, SE-16 `selfHandlerFallbackChangesNothing` ✅ pass: if the owners later set a handler (`setFallbackHandler` stays open, S3.3), its calls come from the handler, not the Safe, and a Safe set as its own handler changes nothing through `fallback`.<br>• SE-9 `setupAlwaysRevertsAfterSetup` ✅ passes: `setup` cannot be re-run to reset the guard.<br><br>That leaves `execTransaction`'s call to the Safe itself, which S1.3 covers. |
| S1.3 | The Safe's `execTransaction` cannot call its own `setGuard`, or otherwise move the guard. | **FV — the guard rejects it:** PG-2 `checkTransactionRejectsSelfSetGuard` ✅ passes. Called by the Safe, the guard reverts on any transaction to the Safe itself whose calldata starts with `setGuard(address)` (`0xe19a9dd9`), whatever the new guard, value or operation.<br><br>**FV — end to end, it reverts:** PG-6 `guardedSafeCannotCallSetGuard` ✅ passes. With ProposerSafeGuard installed, `execTransaction` addressed to the Safe with a `setGuard` call reverts. Removing the guard (`setGuard(address(0))`) and replacing it are both this call.<br><br>**FV — no self-call moves the guard:** PG-9 `guardedSelfCallNeverChangesGuard` ✅ passes. With ProposerSafeGuard installed, for any calldata and operation, `execTransaction` addressed to the Safe leaves the guard slot holding ProposerSafeGuard. The Safe's call to itself runs its real settings functions, so this covers every settings function, not only `setGuard`.<br><br>A delegate call could write the guard slot directly. It is blocked too (S2.4). |

### Statement 2 — Once installed, the Proposer Safe cannot enable a module or delegate call

| # | Statement | Evidence |
| --- | --- | --- |
| S2.1 | ProposerSafeGuard is installed as the Proposer Safe's guard. | Same as S1.1. |
| S2.2 | The Proposer Safe has no enabled modules. Any module would bypass the guard. | **FV — the module path does not consult the guard:** with ProposerSafeGuard installed, an enabled module still does exactly what the guard forbids.<br>• PG-13 `moduleCanDelegateCallPastTheGuard`, PG-14 `moduleCanDelegateCallPastTheGuardWithReturnData` ✅ pass: a module's delegate call through `execTransactionFromModule`, and through `execTransactionFromModuleReturnData`, succeeds. The guard rejects every delegate call (PG-1), so it was not consulted.<br>• PG-15 `moduleCanRemoveTheGuard` ✅ passes: a module can have the Safe call its own `setGuard` and move ProposerSafeGuard out of the guard slot, which `execTransaction` never can (PG-9).<br><br>**On-chain — no modules:** ✅ `getModulesPaginated` on the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`) returns an empty list at block 26080484 (G1.9 in PROOFS.md, re-read). |
| S2.3 | The Safe cannot enable a module. | **FV — the guard rejects it:** PG-3 `checkTransactionRejectsSelfEnableModule` ✅ passes. Called by the Safe, the guard reverts on any transaction to the Safe itself whose calldata starts with `enableModule(address)` (`0x610b5925`), whatever the module.<br><br>**FV — end to end, it reverts:** PG-7 `guardedSafeCannotCallEnableModule` ✅ passes. With ProposerSafeGuard installed, `execTransaction` addressed to the Safe with an `enableModule` call reverts.<br><br>**FV — no self-call adds a module:** PG-10 `guardedSelfCallNeverEnablesAModule` ✅ passes. With ProposerSafeGuard installed, for any calldata and operation, `execTransaction` addressed to the Safe leaves every address that was not a module still not a module. `disableModule` stays open (S3.3), but it can only remove.<br><br>**FV — no other route:** the module list only changes on a self-call (SE-7), and S1.2 shows `execTransaction` is the only self-call path while there are no modules. So the Proposer Safe stays module-free, and S2.2 keeps holding. |
| S2.4 | The Safe cannot make a delegate call. | **FV — the guard rejects it:** PG-1 `checkTransactionRejectsDelegateCall` ✅ passes. The guard reverts on every delegate call, whatever the destination and calldata.<br><br>**FV — end to end, it reverts:** PG-8 `guardedSafeCannotDelegateCall` ✅ passes. With ProposerSafeGuard installed, `execTransaction` with `operation = DelegateCall` reverts, to any address.<br><br>This closes the direct write: delegated code runs as the Safe and could otherwise write the guard slot (S1.3) or the module list (S2.3) without calling `setGuard` or `enableModule`. A MultiSend batch is covered too: reached by delegate call it is blocked here, and reached by a plain call its calls come from the MultiSend contract, not the Safe, so they cannot change the Safe's settings (SE-7). `requiredTxGas` and `simulateAndRevert` also execute a call or delegate call, but always revert afterwards (SE-10, SE-11). |

### Statement 3 — Once installed, the Proposer Safe can still propose and manage its owners

| # | Statement | Evidence |
| --- | --- | --- |
| S3.1 | The guard blocks nothing but the three calls above. | **FV — everything else passes:** PG-4 `checkTransactionAcceptsEverythingElse` ✅ passes. Every plain call that is not the Safe calling its own `setGuard` or `enableModule` passes the guard, whatever the destination, value and calldata. With PG-1 to PG-3, the guard blocks exactly delegate calls, the Safe's own `setGuard` and the Safe's own `enableModule`. |
| S3.2 | The Proposer Safe can still propose a transaction to the Delay. | **FV — plain calls still succeed:** PG-11 `guardedOwnersCanStillCallOut` ✅ passes. With ProposerSafeGuard installed and the threshold passed, a plain `execTransaction` to another contract succeeds. The Proposer Safe's proposal is one such call: `execTransactionFromModule` on the Delay.<br><br>**FV — the Delay accepts it:** DM-5 `enabledModuleCanQueue` ✅ passes. Any enabled module's `execTransactionFromModule` call succeeds and adds the transaction to the Delay's queue. The Proposer Safe is the Delay's only enabled module (G1.6 in PROOFS.md), and G1.10 follows the entry through to the Ownerless Safe. |
| S3.3 | The owners can still manage the Safe's owners, threshold and handler. | **FV — each unblocked settings function still works:** PG-12 `guardedOwnersCanStillChangeOtherSettings` ✅ passes. With ProposerSafeGuard installed, for each of `addOwnerWithThreshold`, `removeOwner`, `swapOwner`, `changeThreshold`, `disableModule` and `setFallbackHandler`, an `execTransaction` addressed to the Safe with a call to it succeeds and a setting changes. |
| S3.4 | Only the Proposer Safe's signers can do any of this. | **FV — `execTransaction` needs the signers:** SE-5 `execTransactionRunsOnlyAfterTheSignatureCheck`, SE-12 `eachSignatureAcceptsANewApprovingOwner` ✅ pass: `execTransaction` acts only when as many different owners as the threshold have approved. SE-6 `ownersCanMakeTheSafeAct` ✅ passes: once they have, it succeeds.<br><br>**On-chain — the Proposer Safe is a 5-of-11 Safe:** ✅ at block 26080484, it runs Safe v1.3.0 (`VERSION`), has threshold 5 (`getThreshold`) and 11 owners (`getOwners`), and a zero fallback handler slot (`0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5`). |

### Modelling notes and limits

- The Safe's call to `to` has a symbolic target, so the spec routes it to the Safe's eight settings functions (as in `selfCalls.spec`). That routing ignores `to`, so PG-9 and PG-10 pin `to` to the Safe itself. A call to any other address can only change the Safe's settings by calling back into it, and SE-7 shows that fails unless the caller is the Safe.
- A self-call whose selector is none of the eight leaves the Safe's storage alone in the model. That includes the Safe calling its own `execTransaction` again. The nested call goes through the same guard, so the same rules apply to it.
- `checkSignatures` is stubbed to pass. That only adds executions, so the revert and "never changes" rules are unaffected. The signature check itself is SE-5 and SE-12.
- The owners can still point the fallback handler at any contract. That does not give anyone a way around the guard (SE-14, SE-15, SE-16), but the Proposer Safe's handler would no longer be zero, which G1.8 in PROOFS.md records.

---

## 2. Rule IDs

Rule IDs follow PROOFS.md: the conf's code, then the rule's position in its spec. `PG` = `Safe-proposerSafeGuard`, `SE` = `Safe-executionPaths` (Safe v1.3.0), `DM` = `Delay-moduleIntegrity`.

| ID | Rule | Spec |
| --- | --- | --- |
| PG-1 | `checkTransactionRejectsDelegateCall` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-2 | `checkTransactionRejectsSelfSetGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-3 | `checkTransactionRejectsSelfEnableModule` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-4 | `checkTransactionAcceptsEverythingElse` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-5 | `ownersCanInstallProposerSafeGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-6 | `guardedSafeCannotCallSetGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-7 | `guardedSafeCannotCallEnableModule` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-8 | `guardedSafeCannotDelegateCall` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-9 | `guardedSelfCallNeverChangesGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-10 | `guardedSelfCallNeverEnablesAModule` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-11 | `guardedOwnersCanStillCallOut` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-12 | `guardedOwnersCanStillChangeOtherSettings` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-13 | `moduleCanDelegateCallPastTheGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-14 | `moduleCanDelegateCallPastTheGuardWithReturnData` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| PG-15 | `moduleCanRemoveTheGuard` | [`specs/Safe/proposerSafeGuard.spec`](specs/Safe/proposerSafeGuard.spec) |
| DM-5 | `enabledModuleCanQueue` | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) |
| SE-3, SE-5, SE-6, SE-7, SE-9, SE-10, SE-11, SE-12, SE-13, SE-14 | see G1.2 in [PROOFS.md](PROOFS.md) | [`specs/Safe/executionPaths.spec`](specs/Safe/executionPaths.spec) |
| SE-15 | `fallbackHandlerCallsComeFromTheHandler` | [`specs/Safe/fallbackHandler.spec`](specs/Safe/fallbackHandler.spec) |
| SE-16 | `selfHandlerFallbackChangesNothing` | [`specs/Safe/selfHandler.spec`](specs/Safe/selfHandler.spec) |
