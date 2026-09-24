# Configuration Proof


## 1. High Level Conclusion

### Conclusion 

```
Branch 1 (the slow path, for real proposals)
  Proposer Safe (5/11) --module--> Delay (+ PauseGuard) --module--> Ownerless Safe

Branch 2 (the token-vote path, whose only power is to veto)
  Governor --module--> Roles (+ SetTxNonceGuard) --target--> DelayOwnerSafe --owner--> Delay

Pause controls
  PauseSafe (2/9) --pause-->               PauseGuard
  Admin Safe     --unpause / setPauser-->  PauseGuard
```


The summation of all of the conclusions drawn from FV proofs should prove the following generalizations: 

* ProposerSafe configuration changes must go through 5/11 multi sig approval from its owners.

* AdminSafe configuration changes must go through 4/10 multi sig approval its owners.

* OwnerlessSafe configuration changes must either go through 9/9 multi sig approval or be proposed thru 5/11 ProposerSafe.

* DelayOwnerSafe configuration changes must go through a 5/11 multisig approval, but 2 different multisigs are possible. First one is direct owner sign/execution from DelayOwner Multisig. Second one is execution from Roles Modifier with DelayOwnerSafe as target, possible only after 5/11 Proposer safe has proposed to Delay Modifier the removal of SetTxNonce and reconfiguration of roles scope on Roles modifier to allow for.

* Delay Modifier configuration changes, besides setTxNonce, must go through a 5/11 multisig approval. 2 paths are possible. First one is direct owner sign/execution from DelayOwner Multisig. Second one is execution from Roles Modifier with DelayOwner as target, only after 5/11 Proposer safe has proposed to Delay Modifier the removal of SetTxNonce and reconfiguration of roles scope on Roles modifier.

* Roles Modifier configuration changes must be initiated by the 5/11 proposer multisig safe.

* Governor configuration changes are not possible.

*  Every write function on every contract in the governance system above executes successfully when called by the intended address.

*  Every write function on every contract in the governance system above fails to execute when not called by the intended address.

* Governor module successfully executes `Delay.setTxNonce(uint256)` through Roles Modifier. 

* A transaction queued by the Proposer Safe executes on the Ownerless Safe once the cooldown has passed, if it hasn't expired and the system isn't paused.

* A Governor proposal to call `Delay.setTxNonce(uint256)` through the Roles Modifier can be successfully proposed and, once it passes vote, successfully executed.

* Any Governor proposal that calls the Roles Modifier with anything other than `Delay.setTxNonce(uint256)` can pass the vote but fails on execution.

Following conclusions must be covered by the premises proved:

1. Governor module successfully executes `Delay.setTxNonce(uint256)` through Roles Modifier execution entry points. 
2. Permission to execute governance vetos (`Delay.setTxNonce(uint256)`) is exclusive to the Governor contract.
3. The Governor contract in turn is completely restricted to execute only governance vetos and no other call.
4. PauseGuard's permissioned pause prevents further execution of queued transactions without disarming the governance vetos.
5. PauseSafe holds exclusive permission to successfully execute pause on PauseGuard.
6. AdminSafe holds exclusive permission to successfully unpause and setPauser to new wallet on PauseGuard.
7. DelayOwnerSafe holds exclusive permission to sucessfully execute all onlyOwner functions of Delay Modifier besides `setTxNonce(uint256)`.
8. OwnerlessSafe holds exclusive permission to successfully execute all onlyOwner functions of Roles Modifier
9. Proposer Safe is only address that can successfully propose transactions to Delay Modifier queue.
10. Delay Module is the only address that can use Ownerless Safe as target to execute transactions.
11. Roles Module is the only address that can use DelayOwnerSafe as target to execute transactions.
12. Nobody can manage PauseGuard's roles outside of `setPauser`: `grantRole`, `revokeRole` and `renounceRole` always revert, `ADMIN_ROLE` membership is fixed at deployment, and the role-admin wiring cannot be re-pointed.
13. A transaction queued by the Proposer Safe executes on the Ownerless Safe once the cooldown has passed, if it hasn't expired and the system isn't paused.
14. A Governor proposal to call `Delay.setTxNonce(uint256)` through the Roles Modifier can be successfully proposed and, once it passes, successfully executed.
15. Any Governor proposal that calls the Roles Modifier with anything other than `Delay.setTxNonce(uint256)` can pass the vote but fails on execution.
 

This conclusion is the sum of sixteen premises, each established below:

- **Premise 1** — Setting Roles Modifier's guard to `SetTxNonceGuard` ensures `Delay.setTxNonce(uint256)` is the only call that can be executed through the Roles modifier, regardless of the Roles Scope Configuration being set.
- **Premise 2** — Without the guard set, the Roles Scope Configuration successfully restricts the Governor to executing `Delay.setTxNonce(uint256)`
in every case except in the multisend case.
- **Premise 3** — In the multisend case, the Roles Scope Configuration restricts every call
  inside the batch to `Delay.setTxNonce(uint256)`. However, there exists an edge case where it allows  ETH to be transferred from the DelayOwnerSafe to ONLY the multisend address and no further.
  `SetTxNonceGuard` is needed to shut off the ETH transfer edge case.
- **Premise 4** — With both gates applied, the Governor's authority over the Delay module is exactly one
  function, `setTxNonce(uint256)`.
- **Premise 5** — The Governor cannot widen its authority over the Delay module on its own initiative. Any change that increases the governor's power requires the participation of protocol multisig safes through the standard proposer/delayCooldown pipeline or the DelayOwnerSafe.
- **Premise 6** — Only the Governor and DelayOwnerSafe can initiate a `Delay.setTxNonce(uint256)` execution.
- **Premise 7** — The PauseGuard blocks all transaction hashes in Delay Modifier's queue from `executeNextTx` without freezing the veto mechanism `setTxNonce`.
- **Premise 8** - The PauseGuard is pausable by the pauser. Only the admin may unpause and change the pauser.
- **Premise 9** — The Governor can successfully execute `Delay.setTxNonce(uint256)` through the Roles Modifier's execution entry points, and the new nonce lands on the Delay.
- **Premise 10** — Only the PauseGuard's `pauser` can successfully pause, and the pauser always can.
- **Premise 11** — Only an `ADMIN_ROLE` holder can successfully unpause or replace the pauser, and the set of `ADMIN_ROLE` holders is fixed at deployment.
- **Premise 12** — Only the Delay's owner, the DelayOwnerSafe, can successfully call the Delay's `onlyOwner` functions other than `setTxNonce(uint256)`.
- **Premise 13** — Only the Roles Modifier's owner, the Ownerless Safe, can successfully call the Roles Modifier's `onlyOwner` functions.
- **Premise 14** — Only an enabled module can queue on the Delay, only the DelayOwnerSafe can change which modules are enabled, and the Proposer Safe is the only enabled module.
- **Premise 15** — Only an enabled module can make the Ownerless Safe execute, and the Delay is its only enabled module.
- **Premise 16** — Only an enabled module can make the DelayOwnerSafe execute through its module path, and the Roles Modifier is its only enabled module.

Below is a breakdown of each premise with attached proofs.

### Premise 1 — Setting Roles Modifier's guard to `SetTxNonceGuard` ensures `Delay.setTxNonce(uint256)` is the only call that can be executed through the Roles modifier, regardless of the Roles Scope Configuration being set.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **2.1** — `setTxNonceGuardLimitsExecTransactionWithRoleToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionFromModuleToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` | Every execution the Roles modifier completes is `setTxNonce(uint256)` on the Delay, zero value, plain `Call`, on all four entry points — for **any caller, any role and any Roles configuration**. The guard works per modifier, not per role, so this bounds every module on the modifier, present and future. | `SetTxNonceGuard` is installed and pointed at the Delay. Nothing about the caller, the role or the Roles configuration. |
| **2.2** — `setTxNonceGuardLimitsToDelaySetTxNonceUnderMaximallyPermissiveRoles` | The same holds under the worst-case configuration: blanket `Clearance.Target` with `ExecutionOptions.Both` on the destination. | As 2.1, plus the caller is an enabled module in that role with that clearance (narrows 2.1 to the worst case). |
| **2.3** — `setTxNonceGuardRejectsMultisendTarget` | A transaction addressed to the MultiSend address always reverts: the guard inspects the outer transaction, not the calldata. | As 2.1, plus the MultiSend address is not the Delay. |
| **2.4** — `withoutSetTxNonceGuardPermissiveRolesAllowNonDelayCall` (witness) | The guard is what does the work: with no guard and the same permissive configuration, a call to something other than the Delay succeeds. | No guard; an enabled-module member with `Target`/`Both` clearance on a non-Delay, non-MultiSend destination. |

Across all four: the guard stays installed, and Roles' `target` is a stand-in avatar that accepts and forwards nothing, so these rules bound what leaves Roles, not what the DelayOwnerSafe then does with it.

### Premise 2 — Without the guard set, the Roles Scope Configuration successfully restricts the Governor to executing `Delay.setTxNonce(uint256)` in every case except in the multisend case.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **3.1** — `roleConfigLimitsExecTransactionWithRoleToDelaySetTxNonce`, `roleConfigLimitsExecTransactionFromModuleToDelaySetTxNonce`, `roleConfigLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, `roleConfigLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` | The Roles Scope Config admits only `setTxNonce(uint256)` on the Delay, zero value, plain `Call`, on all four entry points. | No guard. The destination is **not** the MultiSend address. |
| **3.2** — `nonMemberExecTransactionWithRoleAlwaysReverts` | A caller that is not a member of the role it names can execute nothing at all, whatever it sends. | No guard; the caller is not a member of the named role. Stated on `execTransactionWithRole`. |
| **3.7** — `optionsSendLetsValueThrough`, `optionsDelegateCallLetsDelegateCallThrough`, `optionsBothLetsValueAndDelegateCallThrough` (witnesses) | The zero-value and plain-`Call` halves rest on the options staying `None`: raised to `Send`, `DelegateCall` or `Both`, a call outside the restriction completes. | As 3.1, but with the scoped function's options raised; destination is the Delay. |

### Premise 3 — In the multisend case, the Roles Scope Configuration restricts every call inside the batch to `Delay.setTxNonce(uint256)`. However, there exists an edge case where it allows  ETH to be transferred from the DelayOwnerSafe to ONLY the multisend address and no further. `SetTxNonceGuard` is needed to shut off the ETH transfer edge case.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **3.3** — `withoutSetTxNonceGuardMultisendTargetEscapesRoleConfig` (witness) | A transaction addressed to the MultiSend address completes although it is not the Delay: `Permissions.check` routes it down a separate path that never checks the outer destination. | No guard; Roles Scope Config; the MultiSend address is set and is not the Delay. |
| **3.5** *(not yet run)* — `checkTransactionAdmitsOnlyDelaySetTxNonce`, `checkTransactionStillAdmitsDelaySetTxNonce` (witness) | Every entry inside a batch is `setTxNonce` on the Delay, zero value, plain `Call`, **for any number of entries** — stated on `checkTransaction` itself, with no loop. | Roles Scope Config, with the scoped function wildcarded. |
| **3.2a** — `roleConfigLimitsSingleEntryMultisendToDelaySetTxNonce` | For a one-entry batch, the loop hands `checkTransaction` the real entry, so it is restricted as above. | No guard; Roles Scope Config on the entry; the calldata holds exactly one entry. |
| **3.2b** *(not yet run)* — `roleConfigLimitsTwoEntryMultisendToDelaySetTxNonce` | The same for a two-entry batch. | As 3.2a, with exactly two entries. |
| **3.4** *(not yet run)* — `shortMultisendBlobSkipsEveryEntryCheck` (witness) | Calldata of 100 bytes or fewer never enters the entry loop: only role membership is checked, and the outer value and operation are not checked at all. | No guard; Roles Scope Config; calldata ≤ 100 bytes; `DelegateCall` with a non-zero value. |
| **7.1** — `shortBatchExecutesNothing` | With `multiSend(bytes)` and at most 32 bytes of payload, MultiSendCallOnly makes no call. | `transactions` ≤ 32 bytes (what ≤ 100 bytes of calldata decodes to). |
| **7.2** — `shortBatchCompletesAsNoOp` (witness) | That short call returns cleanly rather than reverting. | As 7.1. |
| **7.3** — `longerBatchCanExecute` (witness) | A longer batch does make a call, so 7.1's call hook is live. | `transactions` > 32 bytes. |
| **7.4** — `oneByteAboveTheHoleExecutes` (witness) | One byte past the cutoff an entry executes, so 32 is the exact boundary. | `transactions` = 33 bytes. |
| **7.5** *(not yet run)* — `multiSendIsTheOnlyEntryPoint` (parametric) | `multiSend(bytes)` is MultiSendCallOnly's only function and there is no fallback, so any other selector reverts. | None. |
| **7.6** *(not yet run)* — `noEntryPointWritesStorage` (parametric) | No MultiSendCallOnly function writes storage, at any input length — what matters under `DelegateCall`. | None. Has no witness that its storage hook fires. |
| **3.6** *(not yet run)* — `roleConfigDoesNotStopValueLeavingOnMultisendBranch` (witness) | **The ETH loss.** With `Operation.Call` and a non-zero value, the Roles configuration lets the DelayOwnerSafe's ETH go to MultiSendCallOnly, which has no way to return it. No configuration can prevent it. | No guard; Roles Scope Config; the MultiSend address is set and is not the Delay; non-zero value. That the ETH is then unrecoverable is read off MultiSendCallOnly's source. |

The entries are confined either way; it is the envelope around them that is not. **Losing the guard loses the restriction; losing the configuration does not.**

### Premise 4 — With both gates applied, the Governor's authority over the Delay module is exactly one function, `setTxNonce(uint256)`.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **1.1** — `governorExecTransactionWithRoleLimitedToDelaySetTxNonce`, `governorExecTransactionFromModuleLimitedToDelaySetTxNonce`, `governorExecTransactionWithRoleReturnDataLimitedToDelaySetTxNonce`, `governorExecTransactionFromModuleReturnDataLimitedToDelaySetTxNonce` | Every call the Governor completes through Roles is `setTxNonce(uint256)` on the Delay, zero value, plain `Call`, on all four entry points. | `SetTxNonceGuard` installed and pointed at the Delay; Roles Scope Config; the Governor is an enabled module, a member of role 1 only, with default role 1, and not the owner; the Roles module list is set up; Roles' `target` is neither the Delay nor Roles' owner. |
| **1.2** — `governorSucceedsOnlyThroughRolesExecEntryPoints` | The Governor cannot successfully call any Roles function other than those four; everything else is `onlyOwner`. | As 1.1. |
| **1.3** — `governorCanStillCallDelaySetTxNonce` (witness) | The intended `setTxNonce` call really is reachable, so the restriction is not achieved by nothing working. | As 1.1, with `setTxNonce` scoped wildcarded with options `None`. |

### Premise 5 — The Governor cannot widen its authority over the Delay module on its own initiative. Any change that increases the governor's power requires the participation of protocol multisig safes through the standard proposer/delayCooldown pipeline or the DelayOwnerSafe.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **6.2** — `rolesConfigOnlyChangesThroughOwner` (parametric), `ownerCanStillReconfigure` (witness) | Over every Roles function and every caller: if the guard, `multisend`, `avatar`, `target`, owner, module list, default roles, role membership or target clearance moved, the caller was the owner. So the Governor cannot remove `SetTxNonceGuard` or change its own permissions. | Any starting state. `setUp` is excluded here and covered by 6.1. |
| **6.3** — `ownerOnlyChangesThroughOwnableTransfer` (parametric) | Roles ownership moves only through `transferOwnership` or `renounceOwnership`, and only for the current owner, so the restriction cannot be sidestepped by first becoming the owner. | As 6.2. |
| **5.2** — `modulesOnlyChangeThroughOwnerEnableOrDisable` (parametric), `ownerCanEnableModule` (witness) | The Delay's module list moves only under `enableModule` or `disableModule`, and only for its owner. | Any starting state, `setUp` excluded (5.1); the Delay's `target` is not its owner. |
| **5.3** — `queueOnlyGrowsThroughEnabledModules` (parametric), `enabledModuleCanQueue` (witness) | Only an address already in the Delay's module list can leave a queue entry behind. | Any starting state, `setUp` excluded. |
| **5.5** — `guardOnlyChangesThroughOwnerSetGuard` (parametric) | The Delay's guard slot moves only for its owner, so nothing else can detach PauseGuard. | Any starting state, `setUp` excluded. |
| **1.1 + 5.2** | **The Governor can never enable a module on the Delay.** The only call the Governor can make the DelayOwnerSafe emit is `setTxNonce`, and the module list moves only for that same DelayOwnerSafe. | Those of 1.1 and 5.2. |
| **5.6** — `executeNextTxCannotEnableModuleThroughTheAvatar`, `avatarEnableModuleAttemptIsReachable` (witness) | An execution forwarded through the target and bounced back does not become a module grant: the return path's caller is the target, not the owner. | Module list set up; the target re-enters `enableModule` on every forward; no guard; the target is not the owner. |
| **5.1**, **6.1** — `setUpAlwaysRevertsAfterDeployment` (one per contract) | `setUp` is spent and always reverts on both the Delay and Roles. | The module list has already been set up. |

### Premise 6 — Only the Governor and DelayOwnerSafe can initiate a `Delay.setTxNonce(uint256)` execution.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **1.6** — `setTxNonceDoesNotLandUnlessTargetOwnsDelay` | Roles only borrows the DelayOwnerSafe's authority: if Roles' `target` does not own the Delay, nothing the Governor sends moves `txNonce`. | Both gates and the Governor wired as in 1.1; `target` forwards the way the DelayOwnerSafe's module path does, with Roles enabled as its module; the Delay is **not** owned by `target`. |
| **1.4** — `governorSetTxNonceLandsWhenDelayAccepts` | When `target` does own the Delay, the Governor's in-range `setTxNonce(n)` completes and the Delay holds `txNonce == n`. | As 1.6, but the Delay **is** owned by `target`; `n` is in the Delay's accepted range. The forward of `setTxNonce` is modelled as a typed call. |
| **3.2** — `nonMemberExecTransactionWithRoleAlwaysReverts` | Through Roles, a caller that is not a member of the role it names is rejected, whatever it sends. | No guard; the caller is not a member of the named role. Stated on `execTransactionWithRole` only. |
| **6.2** — `rolesConfigOnlyChangesThroughOwner` (parametric) | Role membership, default roles and the module list move only for the Roles owner. | Any starting state, `setUp` excluded. |

Not proved here: that the Delay's owner is the DelayOwnerSafe, that Roles is its only module and that the Governor is a member — deployment facts checked in the verification plan — nor that the Governor is the *only* member or the only enabled module on Roles, which nothing checks.

### Premise 7 — The PauseGuard blocks all transaction hashes in Delay Modifier's queue from `executeNextTx` without freezing the veto mechanism `setTxNonce`.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **4.15** — `pausedBlocksExecuteNextTx`, `checkTransactionRevertsWhilePaused` | While paused, `executeNextTx` reverts and nothing reaches the target, for any arguments and queue state. | PauseGuard installed on the Delay and paused. |
| **4.18** — `ownerCanSetTxNonceWhilePaused` | While paused, the Delay's owner can still call `setTxNonce` and the new nonce lands. | PauseGuard installed on the Delay and paused; the caller is the Delay's owner; the nonce is in `setTxNonce`'s accepted range. |
| **4.19** — `pausedBlocksExecuteNextTxWhileOwnerCanStillSetTxNonce` | Both halves in the same state: with an entry queued, `executeNextTx` is blocked *and* the owner can cancel it. | As 4.18, with the queue non-empty. |
| **4.20** — `executeNextTxStillBlockedAfterSetTxNonceDuringPause` | Cancelling does not clear the pause: afterwards `executeNextTx` is still blocked. | As 4.19. |
| **4.22** — `txNonceNeverDecreases` (parametric), `executeNextTxConsumesOnlyTheEntryAtTxNonce` | A cancelled entry stays cancelled: `txNonce` never moves back, and `executeNextTx` only runs the entry at the current `txNonce`. | None about the guard or pause state. An identical transaction queued again later is a new entry. |
| **4.16**, **4.21** — `unpauseReopensExecuteNextTx`, `checkTransactionAcceptsWhileNotPaused`, `executeNextTxAfterSetTxNonceReopensOnUnpause` (witnesses) | The pause is reversible: once an admin unpauses, an entry can execute again, including after a cancel during the pause. | PauseGuard installed; the unpauser holds `ADMIN_ROLE`. |

### Premise 8 — The PauseGuard is pausable by the pauser. Only the admin may unpause and change the pauser.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **4.3**, **4.4** — `pauseRevertsForAnyoneButThePauser`, `adminAloneCannotPause`, `pauseSucceedsForThePauser` | Only the `pauser` can pause, and the pauser always can. | Role holders unconstrained apart from the caller under test. |
| **4.5**, **4.6** — `unpauseRevertsWithoutAdminRole`, `pauserAloneCannotUnpause`, `unpauseSucceedsForAdminRole` | Only an `ADMIN_ROLE` holder can unpause, and it always can. | As 4.3. |
| **4.7** — `pausedOnlyChangesThroughPauseOrUnpause` (parametric) | No other function on the Delay or PauseGuard can move the `paused` flag, so pause and unpause are the only routes. | None. |
| **4.8**, **4.9** — `setPauserRevertsWithoutAdminRole`, `setPauserSetsThePauser`, `pauserOnlyChangesThroughSetPauser` (parametric) | The `pauser` can be replaced, but only by an `ADMIN_ROLE` holder. | As 4.3. |
| **4.10**–**4.14** — `inheritedGrantAndRevokeAlwaysRevert`, `renounceRoleAlwaysReverts`, `adminRoleNeverChanges`, `defaultAdminRoleNeverGranted`, `roleAdminWiringNeverChanges` (parametric) | `ADMIN_ROLE` membership is fixed at deployment and the inherited `grantRole`, `revokeRole` and `renounceRole` are dead, so the party being paused cannot give itself the power to unpause. | The constructor's role-admin wiring, and that it grants `DEFAULT_ADMIN_ROLE` to nobody (read off source). |

### Premise 9 — The Governor can successfully execute `Delay.setTxNonce(uint256)` through the Roles Modifier's execution entry points, and the new nonce lands on the Delay.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **1.3** — `governorCanStillCallDelaySetTxNonce` (witness) | With both gates and the Roles Scope Config in place, the Governor's `setTxNonce` call through Roles is reachable and completes. | As 1.1, with `setTxNonce` scoped wildcarded with options `None`. Stated on `execTransactionWithRole`; `target` is `DummyAvatar`, so nothing downstream is observed. |
| **1.4** — `governorSetTxNonceLandsWhenDelayAccepts` | For **every** in-range `n`, the Governor's `setTxNonce(n)` completes with `shouldRevert` set and the Delay then holds `txNonce == n`. | Both gates and the Governor wired as in 1.1; `target` is `ForwardingAvatar` with Roles enabled as its module, and owns the Delay; `txNonce < n <= queueNonce`. Stated on `execTransactionWithRole`. |
| **1.5** — `governorSetTxNonceOutsideDelayBoundsDoesNotLand` | An out-of-range `n` does not land, and the failure is visible: a revert with `shouldRevert`, otherwise `false`. A refused veto is never reported as successful. | As 1.4, with `n` out of range. |
| **1.2** — `governorSucceedsOnlyThroughRolesExecEntryPoints` | The four exec entry points are the only Roles functions the Governor can succeed on, so these are the routes a veto takes. | As 1.1. |
| **4.18** — `ownerCanSetTxNonceWhilePaused` | The call still lands while PauseGuard is paused. The Governor's route reaches the Delay with `msg.sender == owner()`, so this covers it (see the note under 4f). | PauseGuard installed and paused; the caller is the Delay's owner; `n` in range. |

Not proved here: success on `execTransactionFromModule`, `execTransactionWithRoleReturnData` and `execTransactionFromModuleReturnData`. 1.1 bounds all four entry points, but 1.3–1.5 exhibit success on `execTransactionWithRole` only. Also not proved: that the Delay's owner is the DelayOwnerSafe and that Roles is enabled on it. Those are deployment facts. `ForwardingAvatar` models Safe 1.3.0's module path, while the DelayOwnerSafe runs v1.4.1 (see section 7).

### Premise 10 — Only the PauseGuard's `pauser` can successfully pause, and the pauser always can.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **4.3** — `pauseRevertsForAnyoneButThePauser`, `adminAloneCannotPause` | Every caller other than the `pauser` reverts on `pause()`, and holding `ADMIN_ROLE` does not help. | Role holders unconstrained apart from the caller under test. |
| **4.4** — `pauseSucceedsForThePauser` (witness) | From an unpaused state, the `pauser`'s `pause()` succeeds and sets the flag. | As 4.3, starting unpaused. |
| **4.7** — `pausedOnlyChangesThroughPauseOrUnpause` (parametric) | No other function on the Delay or PauseGuard sets `paused`, so `pause()` is the only way in. | None. |
| **4.8**, **4.9** — `setPauserRevertsWithoutAdminRole`, `setPauserSetsThePauser`, `pauserOnlyChangesThroughSetPauser` (parametric) | The `pauser` slot only moves through `setPauser`, only for an `ADMIN_ROLE` holder, and there is only ever one pauser. The pauser cannot hand the power on, and nobody else can take it. | As 4.3. |

Not proved here: that the `pauser` is the PauseSafe (a deployment fact). Exclusivity lasts only until an admin replaces the pauser (Premise 11).

### Premise 11 — Only an `ADMIN_ROLE` holder can successfully unpause or replace the pauser, and the set of `ADMIN_ROLE` holders is fixed at deployment.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **4.5** — `unpauseRevertsWithoutAdminRole`, `pauserAloneCannotUnpause` | Every caller without `ADMIN_ROLE` reverts on `unpause()`, and being the `pauser` does not help. | Role holders unconstrained apart from the caller under test. |
| **4.6** — `unpauseSucceedsForAdminRole` (witness) | From a paused state, an `ADMIN_ROLE` holder's `unpause()` succeeds and clears the flag. | As 4.5, starting paused. |
| **4.8** — `setPauserRevertsWithoutAdminRole`, `setPauserSetsThePauser` | `setPauser` reverts without `ADMIN_ROLE`. With it, the new pauser is recorded and the old one is displaced. | As 4.5. |
| **4.7**, **4.9** — `pausedOnlyChangesThroughPauseOrUnpause`, `pauserOnlyChangesThroughSetPauser` (parametric) | `unpause()` and `setPauser` are the only routes to those two pieces of state. | None. |
| **4.10**–**4.14** — `inheritedGrantAndRevokeAlwaysRevert`, `renounceRoleAlwaysReverts`, `adminRoleNeverChanges`, `defaultAdminRoleNeverGranted`, `roleAdminWiringNeverChanges` (parametric) | Nobody can be added to or removed from `ADMIN_ROLE`, and the role-admin wiring cannot be re-pointed. So the admin set at deployment is the admin set for good. | The constructor grants `DEFAULT_ADMIN_ROLE` to nobody (read off source; base case for 4.13). |

Not proved here: that the Admin Safe is the only `ADMIN_ROLE` holder (a deployment fact).

### Premise 12 — Only the Delay's owner, the DelayOwnerSafe, can successfully call the Delay's `onlyOwner` functions other than `setTxNonce(uint256)`.

The Delay's `onlyOwner` surface: `setTxCooldown`, `setTxExpiration`, `setTxNonce`, `enableModule`, `disableModule`, `setGuard`, `setAvatar`, `setTarget`, `transferOwnership`, `renounceOwnership`.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **5.2** — `modulesOnlyChangeThroughOwnerEnableOrDisable` (parametric), `ownerCanEnableModule` (witness) | Covers `enableModule` / `disableModule`. The module list moves only through these, only for the owner, and the owner can do it. | Any starting state, `setUp` excluded; `target() != owner()`. |
| **5.4** — `ownerOnlyChangesThroughOwnableTransfer` (parametric) | Covers `transferOwnership` / `renounceOwnership`. Ownership moves only through these and only for the current owner, so exclusivity cannot be sidestepped by first becoming the owner. | Any starting state, `setUp` excluded. |
| **5.5** — `guardOnlyChangesThroughOwnerSetGuard` (parametric) | Covers `setGuard`. The guard slot moves only for the owner. | Any starting state, `setUp` excluded. |
| **4.1** — `setGuardInstallsPauseGuard` | The owner's `setGuard(PauseGuard)` succeeds and the slot holds it. | Caller is the Delay's owner. |
| **5.1** — `setUpAlwaysRevertsAfterDeployment` | `setUp` cannot be re-run to reset the owner. | Module list already set up. |
| **1.1 + 5.2** | The Governor's route through the DelayOwnerSafe can emit only `setTxNonce`, so every other owner-only call reaching the Delay comes from the DelayOwnerSafe's own signers. | Those of 1.1 and 5.2. |

Not proved here: `setTxCooldown`, `setTxExpiration`, `setAvatar` and `setTarget`. No rule observes cooldown, expiration, `avatar` or `target`, so their `onlyOwner` is read off source (`Delay.sol:117`, `:125`; zodiac `core/Module.sol`). Also not proved: that the owner is the DelayOwnerSafe (a deployment fact), and that no module other than Roles can drive the DelayOwnerSafe (Premise 16).

### Premise 13 — Only the Roles Modifier's owner, the Ownerless Safe, can successfully call the Roles Modifier's `onlyOwner` functions.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **6.2** — `rolesConfigOnlyChangesThroughOwner` (parametric), `ownerCanStillReconfigure` (witness) | For every function and every caller: if `guard`, `multisend`, `avatar`, `target`, `owner`, the module list, `defaultRoles`, role membership or target clearance changed, the caller was the owner. The owner can still reconfigure. | Any starting state, `setUp` excluded. `compValues` ≤ 1024 bytes and `scopeParameterAsOneOf` with exactly 2 values (section 6). |
| **6.3** — `ownerOnlyChangesThroughOwnableTransfer` (parametric) | Ownership moves only through `transferOwnership` / `renounceOwnership` and only for the current owner. | As 6.2. |
| **6.1** — `setUpAlwaysRevertsAfterDeployment` | `setUp` cannot be re-run to reset the owner or module list. | Module list already set up. |
| **1.2** — `governorSucceedsOnlyThroughRolesExecEntryPoints` | For the Governor, this covers every `onlyOwner` function, including the function- and parameter-scoping ones that 6.2 does not observe. | As 1.1. |

Not proved here: that callers other than the Governor cannot move function-level or parameter-level scope (`scopeAllowFunction`, `scopeRevokeFunction`, `scopeFunction`, `scopeFunctionExecutionOptions`, `scopeParameter*`, `unscopeParameter`). 6.2 does not observe that storage, so for those callers `onlyOwner` is read off source. Also not proved: that the owner is the Ownerless Safe (a deployment fact).

### Premise 14 — Only an enabled module can queue on the Delay, only the DelayOwnerSafe can change which modules are enabled, and the Proposer Safe is the only enabled module.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| **5.3** — `queueOnlyGrowsThroughEnabledModules` (parametric), `enabledModuleCanQueue` (witness) | `queueNonce` and `txHash[n]` only move for a caller already in the module list, and an enabled module can queue. | Any starting state, `setUp` excluded. |
| **5.2** — `modulesOnlyChangeThroughOwnerEnableOrDisable` (parametric) | The module list moves only for the Delay's owner. | As Premise 12. |
| **5.4** — `ownerOnlyChangesThroughOwnableTransfer` (parametric) | Nobody can become the owner to get around 5.2. | Any starting state, `setUp` excluded. |
| **5.6** — `executeNextTxCannotEnableModuleThroughTheAvatar`, `avatarEnableModuleAttemptIsReachable` (witness) | A queued entry that bounces back from the avatar into `enableModule` does not add a module. | Module list set up; `target` re-enters `enableModule`; no guard; `target` is not the owner. |
| **1.1 + 5.2** | The Governor can never enable a module on the Delay, so it can never become a proposer. | Those of 1.1 and 5.2. |
| **5.1** — `setUpAlwaysRevertsAfterDeployment` | `setUp` cannot reset the module list. | Module list already set up. |

Not proved here: that the Proposer Safe is the Delay's **only** enabled module (a deployment fact). The DelayOwnerSafe's own signers can still enable another. That is by design, as noted under [Where the boundary is](#where-the-boundary-is).

### Premise 15 — Only an enabled module can make the Ownerless Safe execute, and the Delay is its only enabled module.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| *(no rule)* | No Safe is in any Certora scene, so the Ownerless Safe's module list is not checked by the Prover. | — |
| Read off source | `execTransactionFromModule` requires the caller to be an enabled module, and `enableModule` is `authorized` (callable only by the Safe itself). With no reachable signer quorum, the Safe can only enable a new module by running a transaction sent by a module it already has. | `@gnosis.pm/safe-contracts` `base/ModuleManager.sol`, `common/SelfAuthorized.sol`. |
| **Premise 14 + Premise 7** | While the Delay is the only module, any new module has to arrive as a Delay queue entry. That entry can only be written by the Proposer Safe and has to pass the cooldown, the veto and the pause. | Those of Premises 7 and 14. |

Not proved here: that the Delay is the Ownerless Safe's **only** enabled module, and that the Safe has no reachable signer quorum. Both are deployment facts, checked in the verification plan.

### Premise 16 — Only an enabled module can make the DelayOwnerSafe execute through its module path, and the Roles Modifier is its only enabled module.

| Rule(s) | What it proves | Assumptions |
| --- | --- | --- |
| *(no rule)* | The DelayOwnerSafe is not in any Certora scene. 1.4–1.6 use `ForwardingAvatar`, a model of its module path. | — |
| **1.6** — `setTxNonceDoesNotLandUnlessTargetOwnsDelay` | What Roles can do to the Delay comes entirely from its `target` owning the Delay. It is the DelayOwnerSafe's authority, borrowed. | As in Premise 6. |
| **6.2** — `rolesConfigOnlyChangesThroughOwner` (parametric) | Only the Roles owner can change which Safe Roles uses as `target`. | Any starting state, `setUp` excluded. |
| Read off source | `execTransactionFromModule` requires the caller to be an enabled module. | `@gnosis.pm/safe-contracts` `base/ModuleManager.sol`. |

Not proved here: that Roles is the DelayOwnerSafe's **only** enabled module (a deployment fact). Unlike the Ownerless Safe, the DelayOwnerSafe has a 5-of-11 signer quorum. Those signers can enable further modules and can execute directly through `execTransaction`, which does not go through the module path.

### What the evidence looks like

- **78 rules, 56 lemmas, 9 confs.** The Delay and Roles scenes use the real mastercopies, not
  models. The two harnesses ([`DelayHarness`](harness/DelayHarness.sol),
  [`RolesHarness`](harness/RolesHarness.sol)) add view getters over internal storage and no logic.
- **The bounding lemmas are stated four times each**, once per execution entry point.
- **The integrity lemmas are parametric** (4.7, 4.9, 4.12–4.14, 5.2–5.5, 6.2, 6.3): they quantify
  over every state-changing entry point and every caller. 5.2–5.5 and 6.2–6.3 additionally assume
  *nothing* about the pre-state, so they hold from any storage the Prover can construct. That is
  what makes them survive someone later adding an entry point.
- **Non-vacuity is discharged explicitly**, not assumed: a witness rule per restriction, plus
  `rule_sanity: basic` on every conf.

### Where the boundary is

There are two kinds of residue, both enumerated in
[Explicitly not proved](#6-explicitly-not-proved) rather than left implicit.

*Deployment facts* the rules depend on but do not establish — who the owners are, that the Delay's
`target` is not its `owner`, that the Ownerless Safe and the DelayOwnerSafe are distinct
addresses. These are checked in the verification plan, not here.

*Bounded-scope assumptions* where the Prover needs a finite model — hashing length bounds, loop
unrolling limits, single-entry multisend batches. These limit the range of a claim rather than
its validity.

And one thing that is not residue but design: **none of this constrains the owners themselves.**
An Ownerless Safe quorum can rewrite the Roles configuration, and a DelayOwnerSafe quorum can
enable a module on the Delay. Every lemma here says only that nothing *else* can.

---

## 2. The deployment being verified

Two paths reach the Ownerless Safe that holds the protocol's privileges:

```
Branch 1 (the slow path, for real proposals)
  Proposer Safe (5/11) --module--> Delay (+ PauseGuard) --module--> Ownerless Safe

Branch 2 (the token-vote path, whose only power is to veto)
  Governor --module--> Roles (+ SetTxNonceGuard) --target--> DelayOwnerSafe --owner--> Delay

Pause controls
  PauseSafe (2/9) --pause-->               PauseGuard
  Admin Safe     --unpause / setPauser-->  PauseGuard
```

Branch 1 is how changes actually get made: a 5-of-11 Proposer Safe queues a transaction on the
Delay, it waits a day in the open, then anyone may execute it against the Ownerless Safe.

Branch 2 exists so token holders can *stop* branch 1. An on-chain Governor vote drives the Roles
modifier, which forwards to the DelayOwnerSafe, which owns the Delay. The only thing that
combination is supposed to be able to do is call `Delay.setTxNonce` — i.e. invalidate whatever is
sitting in the queue. It must not be able to do anything else, and in particular it must not be
able to enable a module on the Delay, because a module on the Delay can queue anything.

Two purpose-built guards enforce this:

- **[`SetTxNonceGuard`](../contracts/helpers/SetTxNonceGuard.sol)** is installed on Roles. It
  holds one Delay address as an immutable and rejects any transaction that is not
  `setTxNonce(uint256)` on that address, with zero ETH value, as a plain `Call` (not
  `delegatecall`), with calldata of exactly 36 bytes so nothing extra can ride along.
- **[`PauseGuard`](../contracts/helpers/PauseGuard.sol)** is installed on the Delay. While it is
  paused, every `executeNextTx` reverts, which freezes the queue. Pausing and unpausing are
  deliberately asymmetric: a low-threshold PauseSafe can pause, but only an `ADMIN_ROLE` holder
  can unpause. That way the party being paused cannot unpause itself.

---

## 3. Where each lemma lives

Roles exposes **four** execution entry points — the 2x2 of {caller-named `role`,
`defaultRoles[msg.sender]`} x {`exec`, `execAndReturnData`}
([`Roles.sol:314`](../contracts/Roles.sol#L314), [`:337`](../contracts/Roles.sol#L337),
[`:357`](../contracts/Roles.sol#L357), [`:380`](../contracts/Roles.sol#L380)). Each of the three
bounding lemmas below (1.1, 2.1, 3.1) — the three that state the restriction, under the specs'
own name for them — is carried by four rules, one per entry point, asserted separately so that a
future divergence between the `exec` and `execAndReturnData` paths — or
between the named-role and default-role paths — cannot hide behind a single passing rule.

Sources:

| Conf | Spec | Scene | Rules | Lemmas |
| --- | --- | --- | --- | --- |
| [`confs/Roles-setTxNonceGuardAndRoleConfig.conf`](confs/Roles-setTxNonceGuardAndRoleConfig.conf) | [`specs/Roles/setTxNonceGuardAndRoleConfig.spec`](specs/Roles/setTxNonceGuardAndRoleConfig.spec) | Roles + SetTxNonceGuard + role clearance and membership pinned | 6 | 1.1–1.3 |
| [`confs/Roles-setTxNonceLands.conf`](confs/Roles-setTxNonceLands.conf) | [`specs/Roles/setTxNonceLands.spec`](specs/Roles/setTxNonceLands.spec) | Roles + SetTxNonceGuard + Roles Scope Config, `target` linked to `ForwardingAvatar`, Delay in scene | 3 | 1.4–1.6 |
| [`confs/Roles-setTxNonceGuardSufficient.conf`](confs/Roles-setTxNonceGuardSufficient.conf) | [`specs/Roles/setTxNonceGuardSufficient.spec`](specs/Roles/setTxNonceGuardSufficient.spec) | Roles + SetTxNonceGuard, Roles configuration left unconstrained | 7 | 2.1–2.4 |
| [`confs/Roles-setTxNonceRoleConfigSufficient.conf`](confs/Roles-setTxNonceRoleConfigSufficient.conf) | [`specs/Roles/setTxNonceRoleConfigSufficient.spec`](specs/Roles/setTxNonceRoleConfigSufficient.spec) | Roles + setTxNonce Roles configuration, no guard installed | 15 (5 not yet run) | 3.1–3.7 |
| [`confs/Delay-pauseGuardSufficient.conf`](confs/Delay-pauseGuardSufficient.conf) | [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec) | Delay + PauseGuard installed via `Guardable.setGuard` | 28 | 4.1–4.22 |
| [`confs/Delay-moduleIntegrity.conf`](confs/Delay-moduleIntegrity.conf) | [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec) | Delay via `DelayHarness`, `target` linked to `ReenteringAvatar` | 9 | 5.1–5.6 |
| [`confs/Roles-configIntegrity.conf`](confs/Roles-configIntegrity.conf) | [`specs/Roles/configIntegrity.spec`](specs/Roles/configIntegrity.spec) | Roles + SetTxNonceGuard, configuration left unconstrained | 4 | 6.1–6.3 |
| [`confs/MultiSend-shortBatch.conf`](confs/MultiSend-shortBatch.conf) | [`specs/MultiSend/shortBatchExecutesNothing.spec`](specs/MultiSend/shortBatchExecutesNothing.spec) | MultiSendCallOnly alone, vendored verbatim from `@gnosis.pm/safe-contracts` | 5 (1 not yet run) | 7.1–7.5 |
| [`confs/MultiSend-noStorageWrite.conf`](confs/MultiSend-noStorageWrite.conf) | [`specs/MultiSend/shortBatchWritesNoStorage.spec`](specs/MultiSend/shortBatchWritesNoStorage.spec) | MultiSendCallOnly, storage splitting disabled | 1 (not yet run) | 7.6 |
| | | **total** | **78** | **56** |

---

## 4. A Prover limitation the specs work around

This section documents a CVL/harness interaction that shaped how the specs are written. It does
not affect the contracts.

`RolesHarness` exposes the per-function scope configuration two ways: `functionScopeConfigForData`
(taking the calldata `bytes` blob) and `functionScopeConfigForSelector` (taking a `uint32`
selector). They read the same storage slot — the `bytes` form just does `bytes4(data)` on
entry — but **the setup predicates shared by the bounding rules must use the selector form.**

Calling the `bytes` form inside a `require` makes the *other* `require`s in the same predicate
stop constraining anything. The four bounding rules of Properties 1 and 3 then report
counterexamples in which `to`, `value`, `operation` and the selector are all simultaneously
unconstrained — not one conjunct broken, but the gate behaving as though it checked nothing
at all.

That is not possible for a sound `require`: adding one can only ever remove states, never add
them. It was isolated by bisecting Property 1's spec, whose preconditions are a strict superset of
Property 2's, yet which failed the same four conclusions until the `bytes`-form call was removed.
Property 2, which never calls either getter, passed throughout. Both properties verify once the
call is gone (Property 1) or restated through the selector form (Property 3).

The contracts are not implicated: the same counterexample appears against the audited
`Permissions.sol` and against this repo's later one, and the deployed bytecode is unaffected by
any of it. Treat it as a harness/CVL interaction. The `bytes` form is still used in a `require`
inside Property 1's witness rule 1.3, which verifies — that rule constrains one concrete
configuration rather than sharing a predicate with the bounding rules, and does not exhibit
the behaviour. The rule to follow is that no predicate feeding a bounding rule may call it.

---

## 5. The properties

### Property 1 — SetTxNonceGuard *and* the Roles configuration

Spec: [`specs/Roles/setTxNonceGuardAndRoleConfig.spec`](specs/Roles/setTxNonceGuardAndRoleConfig.spec)

This scene has both gates in place, matching the intended deployment.

The configuration half pins role 1's **clearance on the Delay and the Governor's membership in
that role**, but deliberately **not** the per-function scope (`scopeAllowFunction`). Stating that
last pin triggered the Prover limitation described in section 4, and the four bounding rules
verify without it — so what 1.1 establishes is strictly stronger than "both gates fully pinned".
The function-scope pin only does real work in the scene where no guard is installed, which is
Property 3.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 1.1 | With the guard installed and role 1 pinned as above, every call the Governor completes through the Roles module is `setTxNonce(uint256)` on the Delay, with zero value and as a plain `Call` — on **all four** execution entry points. | `governorExecTransactionWithRoleLimitedToDelaySetTxNonce`, `governorExecTransactionFromModuleLimitedToDelaySetTxNonce`, `governorExecTransactionWithRoleReturnDataLimitedToDelaySetTxNonce`, `governorExecTransactionFromModuleReturnDataLimitedToDelaySetTxNonce` |
| 1.2 | The Governor cannot successfully call any Roles entry point other than those four. Everything else is `onlyOwner`, and `setUp` is spent once the module has been set up. | `governorSucceedsOnlyThroughRolesExecEntryPoints` |
| 1.3 | The restriction above is non-vacuous: the intended `setTxNonce` call really is reachable under the same wiring and configuration. | `governorCanStillCallDelaySetTxNonce` (witness) |

1.1–1.3 are stated at the Roles boundary: they bound what the Governor can *attempt*. In that scene
`target` is `DummyAvatar`, which returns `true` and forwards nothing, so nothing downstream is
observed. 1.4–1.6 follow the call the rest of the way, in their own scene
([`specs/Roles/setTxNonceLands.spec`](specs/Roles/setTxNonceLands.spec)): `target` is
[`ForwardingAvatar`](helpers/ForwardingAvatar.sol), which forwards the way the DelayOwnerSafe's
module path does, and the Delay is in scene, so the rules read the Delay's own state after the
Governor's call. `Delay.setTxNonce` accepts only from its owner, and only a nonce `n` with
`txNonce < n <= queueNonce`.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 1.4 | **The call lands when the Delay would accept it.** With both gates, the Roles Scope Config and the DelayOwnerSafe as the Delay's owner, for every `n` in range the Governor's `setTxNonce(n)` completes and the Delay then holds `txNonce == n`. The queue does not move. Stated with `shouldRevert` set, so "completes" means the inner call really succeeded, not that a failure was swallowed as `false`. | `governorSetTxNonceLandsWhenDelayAccepts` |
| 1.5 | **A nonce the Delay would refuse does not land, and the refusal is visible.** For `n` out of range, `txNonce` is unchanged; the Governor's call reverts if it set `shouldRevert`, and otherwise returns `false`. A refused cancel is never reported as done. | `governorSetTxNonceOutsideDelayBoundsDoesNotLand` |
| 1.6 | **The cancel power is the target's ownership of the Delay.** If the contract at Roles' `target` does not own the Delay, nothing the Governor sends moves `txNonce`, in range or not. Roles only lets the Governor borrow the DelayOwnerSafe's authority. | `setTxNonceDoesNotLandUnlessTargetOwnsDelay` |

---

### Property 2 — SetTxNonceGuard alone is sufficient

Spec: [`specs/Roles/setTxNonceGuardSufficient.spec`](specs/Roles/setTxNonceGuardSufficient.spec)

This scene asks what the guard gives you if the Roles configuration is worthless. No `require`
touches role storage at all, so the Prover is free to pick the most permissive configuration
that could exist.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 2.1 | With SetTxNonceGuard installed and pointed at the Delay, and **no assumption at all** about the Roles configuration, every completed execution is `setTxNonce(uint256)` on the Delay with zero value and as a plain `Call` — on **all four** execution entry points. | `setTxNonceGuardLimitsExecTransactionWithRoleToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionFromModuleToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, `setTxNonceGuardLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` |
| 2.2 | The same restriction holds under an explicitly worst-case configuration: the caller is an enabled module, is a member of the role it names, and that role holds blanket `Clearance.Target` with `ExecutionOptions.Both` on an arbitrary address. | `setTxNonceGuardLimitsToDelaySetTxNonceUnderMaximallyPermissiveRoles` |
| 2.3 | Transactions sent to the MultiSend address — the one destination where the role layer does not bound the outer destination, value or operation — are closed by the guard: a transaction addressed to the configured MultiSend always reverts. | `setTxNonceGuardRejectsMultisendTarget` |
| 2.4 | The guard is what imposes the restriction, rather than the restriction being an artefact of how the scene is set up: with no guard installed and the same permissive configuration, a call to a non-Delay address succeeds. | `withoutSetTxNonceGuardPermissiveRolesAllowNonDelayCall` (witness) |

---

### Property 3 — the Roles configuration alone is sufficient

Spec: [`specs/Roles/setTxNonceRoleConfigSufficient.spec`](specs/Roles/setTxNonceRoleConfigSufficient.spec)

The mirror image of Property 2: no guard is installed (`guard() == 0` throughout), so the Roles
permission check is the only gate.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 3.1 | With no guard installed, the Roles Scope Config (`scopeTarget` → `Clearance.Function` on the Delay, `scopeAllowFunction(setTxNonce, Options.None)`, `assignRoles(governor, [1])`) admits only `setTxNonce(uint256)` on the Delay with zero value and as a plain `Call`, **provided the destination is not the MultiSend address** — on **all four** execution entry points. | `roleConfigLimitsExecTransactionWithRoleToDelaySetTxNonce`, `roleConfigLimitsExecTransactionFromModuleToDelaySetTxNonce`, `roleConfigLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, `roleConfigLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` |
| 3.2 | A caller that is not a member of the named role can execute nothing at all, whatever it sends. This isolates the `assignRoles` half of the configuration from the scoping half. | `nonMemberExecTransactionWithRoleAlwaysReverts` |
| 3.2a | For a MultiSend destination, a **single-entry** batch is still restricted: if it completes, that entry is `setTxNonce` on the Delay with zero value and as a plain `Call`. `checkMultisendTransaction` forwards each entry to the same `checkTransaction` the direct path uses ([`Permissions.sol:236`](../contracts/Permissions.sol#L236)). **Scope: one entry only.** `optimistic_loop` means batches needing more iterations than `loop_iter` are assumed away rather than checked, so the rule requires the single-entry shape explicitly instead of leaning on that assumption. | `roleConfigLimitsSingleEntryMultisendToDelaySetTxNonce` |
| 3.2b *(not yet run)* | The same for a **two-entry** batch: if it completes, both entries are `setTxNonce` on the Delay with zero value and as a plain `Call`. Exercises a second iteration of the entry loop rather than assuming it away, so the single-entry result cannot be an artefact of the one-entry shape. **Scope: two entries**, pinned explicitly; the conf's `loop_iter` is raised to 2 for it. | `roleConfigLimitsTwoEntryMultisendToDelaySetTxNonce` |
| 3.3 | The MultiSend caveat in 3.1 is real, not merely conservative: without the guard, a transaction addressed to the configured MultiSend completes even though its destination is not the Delay, because the permission check unpacks the calldata before it consults clearance for that destination. | `withoutSetTxNonceGuardMultisendTargetEscapesRoleConfig` (witness) |
| 3.5 *(not yet run)* | **The per-entry restriction, with no loop involved.** `checkMultisendTransaction` decides nothing itself: it parses the calldata and hands each entry to `checkTransaction` ([`Permissions.sol:236`](../contracts/Permissions.sol#L236)), the same function the direct path calls ([`:190`](../contracts/Permissions.sol#L190)). This rule states the restriction on `checkTransaction` directly, with `to`, `value`, `data` and `operation` universally quantified and nothing driving the batch loop — `to` ranging over every address including the MultiSend one. Composed with 3.2a/3.2b it gives: **every entry the loop visits is `setTxNonce` on the Delay, for any number of entries.** `loop_iter` then bounds only how many entries the Prover walks, not what is true of them. Requires `isWildcarded`, which the Roles Scope Config sets and which keeps `checkParameters` — the one loop reachable from `checkTransaction` — off the path; the conclusion does not depend on it, since parameter scoping only narrows. | `checkTransactionAdmitsOnlyDelaySetTxNonce`, `checkTransactionStillAdmitsDelaySetTxNonce` (witness) |
| 3.4 *(not yet run)* | The sharper form of 3.3, isolating the one shape in which **no entry is checked at all**: with calldata of 100 bytes or fewer, `checkMultisendTransaction`'s entry loop never runs ([`Permissions.sol:216`](../contracts/Permissions.sol#L216)), so `check()` returns having verified role membership only. The rule exhibits such a call completing with the outer destination at `Clearance.None`, as a `DelegateCall`, carrying a **non-zero** value — all three pinned, so the witness cannot degenerate into a harmless one. A witness: it proves the hole is reachable **through Roles**, and nothing in Property 3 closes it. What happens downstream is out of scene — `target` is linked to `DummyAvatar`, which returns `true` and calls nothing — and is covered by **Property 7**, which verifies that nothing executes at the other end. | `shortMultisendBlobSkipsEveryEntryCheck` (witness) |
| 3.6 *(not yet run)* | **The exception that is not empty.** `Permissions.check` is handed `value` but does not forward it when the destination is the MultiSend address ([`Permissions.sol:186-191`](../contracts/Permissions.sol#L186)) — `checkMultisendTransaction` takes `data` alone — so no configuration constrains the outer value. With `Operation.Call` the `Executor` of the contract at Roles' `target` slot — the DelayOwnerSafe — passes it straight to the `call` (delegatecall takes no value argument, which is why 3.4's witness moves nothing), and `MultiSendCallOnly.multiSend` is `payable` with no withdrawal function. **So the Roles configuration alone cannot stop ETH leaving the DelayOwnerSafe**, bounded by that Safe's own balance, and this is not closed by Property 7: unlike the 100-byte hole, the surface here is not empty. `SetTxNonceGuard` closes it by requiring both `to == delay` and `value == 0`. Demonstrated end to end against the real contracts in [`test/MultisendShortBlob.spec.ts`](../test/MultisendShortBlob.spec.ts), where 1 ETH leaves the `target` contract and lands permanently in MultiSendCallOnly. | `roleConfigDoesNotStopValueLeavingOnMultisendBranch` (witness) |
| 3.7 | **The options pin is load-bearing.** Every bounding rule above pins the scoped function's `ExecutionOptions` to `None`. With the guard absent and the same configuration except for the options, a call outside the restriction completes on the direct path: `Send` lets a non-zero value reach `setTxNonce` on the Delay, `DelegateCall` lets `Operation.DelegateCall` through, and `Both` lets both through at once ([`Permissions.sol:284-306`](../contracts/Permissions.sol#L284)). So the zero-value and plain-`Call` halves of the restriction rest on the options staying `None`, and nothing else in the Roles configuration supplies them. With the guard installed this does not arise: 2.1 leaves the options unconstrained. | `optionsSendLetsValueThrough`, `optionsDelegateCallLetsDelegateCallThrough`, `optionsBothLetsValueAndDelegateCallThrough` (witnesses) |

> **Why both gates are kept.** 3.3 and 2.3 are the same transaction: without the guard it
> succeeds, with the guard it reverts.
>
> **3.6 is the sharper form of that argument, and the one that matters.** The 100-byte hole (3.4)
> is a bypass with nothing behind it — Property 7 proves nothing executes through it. The outer
> *value* is different: it is equally unchecked, but it is not empty, because `Operation.Call`
> with a non-zero value moves ETH out of the avatar into a `payable` contract that cannot return
> it. That is a loss the role configuration cannot prevent at any setting, which is what makes
> `SetTxNonceGuard` load-bearing rather than defence in depth.

> **What 3.4 does not reach, and where it is covered.** 3.4 proves Roles *permits* calldata of 100
> bytes or fewer. It says nothing about whether anything then happens, because the Roles scenes
> link `target` to `DummyAvatar`, which returns `true` and calls nothing — the real
> `MultiSendCallOnly` is not in any Certora scene. That half is covered by
> [`test/MultisendShortBlob.spec.ts`](../test/MultisendShortBlob.spec.ts) against the real
> contracts, which establishes that such calldata executes **nothing at all**, whatever its selector:
>
> - **Wrong selector** — `MultiSendCallOnly` declares no `fallback` or `receive`, so the inner
>   call reverts. The avatar returns `success == false` rather than propagating, so
>   `execTransactionFromModule` returns `false` and no state moves.
> - **Right selector** — the ABI decoder caps the declared `transactions` length at what the
>   calldata holds, so at most `100 - 68 = 32` bytes. `MultiSendCallOnly`'s own loop starts at
>   `i = 0x20` and runs while `i < length`, so a declared length of 32 or less executes zero
>   entries.
> - **Either way** the arithmetic is the reason: 68 bytes of ABI header plus an 85-byte entry
>   header is 153, so no payload of 100 bytes can carry even one entry.
>
> The permission bypass is real; the surface behind it is empty. That is why this is recorded as a
> bounded non-claim rather than a finding.

---

### Property 4 — PauseGuard on the Delay

Spec: [`specs/Delay/pauseGuardSufficient.spec`](specs/Delay/pauseGuardSufficient.spec). The scene
uses the real Delay mastercopy, not a model.

#### 4a. Can the guard be installed at all

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.1 | The Delay's owner can install PauseGuard with `Guardable.setGuard`, and the Delay's `guard` slot then holds it. | `setGuardInstallsPauseGuard` |
| 4.2 | PauseGuard answers `supportsInterface` for `IGuard` (`0xe6d7a83a`) and ERC-165 (`0x01ffc9a7`), which is the only thing `Guardable.setGuard` checks. | `pauseGuardAnswersIGuardInterfaceId` |

#### 4b. Who may pause

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.3 | Only the `pauser` can pause. Every other caller reverts, and holding `ADMIN_ROLE` does not confer the right. | `pauseRevertsForAnyoneButThePauser`, `adminAloneCannotPause` |
| 4.4 | The `pauser` always can: from an unpaused state, `pause()` succeeds and sets the flag. (This is also the non-vacuity witness for 4.3.) | `pauseSucceedsForThePauser` |

#### 4c. Who may unpause

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.5 | Unpausing requires `ADMIN_ROLE`. Callers without it revert, and being the `pauser` is not sufficient. This is the pause/unpause asymmetry the design depends on. | `unpauseRevertsWithoutAdminRole`, `pauserAloneCannotUnpause` |
| 4.6 | `ADMIN_ROLE` is sufficient: from a paused state, a holder unpauses and the flag is cleared. (Also the non-vacuity witness for 4.5.) | `unpauseSucceedsForAdminRole` |
| 4.7 | No other entry point on either contract can move the `paused` flag. | `pausedOnlyChangesThroughPauseOrUnpause` (parametric) |

#### 4d. Role and membership integrity

These lemmas together establish that the party being paused cannot acquire the ability to unpause
itself.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.8 | Replacing the pauser requires `ADMIN_ROLE`. A holder can do it, the new account is recorded, and the outgoing pauser is displaced — there are never two pausers at once. | `setPauserRevertsWithoutAdminRole`, `setPauserSetsThePauser` |
| 4.9 | `setPauser` is the only entry point that can change the `pauser`. | `pauserOnlyChangesThroughSetPauser` (parametric) |
| 4.10 | The `grantRole` and `revokeRole` functions inherited from AccessControl are dead for every role and every caller, because `DEFAULT_ADMIN_ROLE` administers both roles and nobody holds it. | `inheritedGrantAndRevokeAlwaysRevert` |
| 4.11 | `renounceRole` is explicitly disabled, so no holder can drop a role. This is what stops the last admin from stranding the guard with nobody able to unpause. | `renounceRoleAlwaysReverts` |
| 4.12 | `ADMIN_ROLE` membership is fixed at deployment: no entry point changes it. | `adminRoleNeverChanges` (parametric) |
| 4.13 | `DEFAULT_ADMIN_ROLE`, unheld in the starting state, stays unheld. This is the induction step that freezes `ADMIN_ROLE`; the base case is the constructor, which grants it to nobody (assumed from source, not proved). | `defaultAdminRoleNeverGranted` (parametric) |
| 4.14 | The role-admin wiring cannot be re-pointed: `_setRoleAdmin` is never reached, so `getRoleAdmin` of both roles is invariant. | `roleAdminWiringNeverChanges` (parametric) |

#### 4e. Pausing blocks execution

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.15 | While PauseGuard is paused, `Delay.executeNextTx` reverts and nothing reaches the Delay's target — for any transaction arguments and any queue state. Stated end to end, and again on the guard half called directly. | `pausedBlocksExecuteNextTx`, `checkTransactionRevertsWhilePaused` |
| 4.16 | The pause is reversible: after an `ADMIN_ROLE` holder unpauses, a queue entry can execute again, and the unpaused guard rejects nothing on its own. Stated end to end, and again on the guard half called directly. | `unpauseReopensExecuteNextTx` (witness), `checkTransactionAcceptsWhileNotPaused` |
| 4.17 | The guard is what does the blocking: with no guard installed, `executeNextTx` forwards to the target with no check at all. | `withoutPauseGuardExecuteNextTxForwardsUnchecked` (witness) |

#### 4f. A pause does not disarm the owner

This is the subtle part of the design. A pause must freeze execution without also freezing the
owner's ability to cancel what is queued — otherwise pausing would trap the bad entry in place
rather than allow it to be removed.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 4.18 | While PauseGuard is installed **and paused**, the Delay's owner (the DelayOwnerSafe) can still call `setTxNonce` and the new nonce lands. `setTxNonce` is `onlyOwner`, never reaches `Module.exec`, and so never consults the guard. | `ownerCanSetTxNonceWhilePaused` |
| 4.19 | Both halves of the veto hold in the **same** state: with an entry queued and the guard paused, `executeNextTx` reverts with nothing reaching the target, *and* in that same state the owner can bump `txNonce` past the pending entry. | `pausedBlocksExecuteNextTxWhileOwnerCanStillSetTxNonce` |
| 4.20 | And in the other order: **after** the owner's `setTxNonce` succeeds during a pause, the pause is still standing (`setTxNonce` does not clear it) and `executeNextTx` still reverts with nothing reaching the target. The queue is left deliberately non-empty, so the revert cannot be the empty-queue check. Bumping `txNonce` is not a way to slip the next entry past a paused guard. | `executeNextTxStillBlockedAfterSetTxNonceDuringPause` |
| 4.21 | That block really is the pause: from the same bump-during-pause state, once the admin unpauses, an entry can execute. | `executeNextTxAfterSetTxNonceReopensOnUnpause` (witness) |
| 4.22 | **A skipped entry stays skipped.** Over every entry point of the Delay and PauseGuard, `txNonce` never decreases. And a successful `executeNextTx` runs exactly the entry stored at the current `txNonce` — the executed transaction's hash equals `txHash[txNonce]` — and advances `txNonce` by one. Together: once `setTxNonce` moves `txNonce` past entry *k*, `txNonce` never returns to *k*, so entry *k* is never the one executed. An identical transaction queued again later is a new entry and can execute; that is a fresh proposal through the queue, cooldown and pause, not the skipped entry returning. | `txNonceNeverDecreases` (parametric), `executeNextTxConsumesOnlyTheEntryAtTxNonce` |

> **On `msg.sender == owner()` covering both routes.** There are two ways `Delay.setTxNonce` gets
> called in this design: a transaction signed by the DelayOwnerSafe's own owners, and
> the Governor path (`Governor → Roles → Module.exec → IAvatar(target).execTransactionFromModule`,
> where `target` *is* the DelayOwnerSafe). Both arrive at the Delay as an ordinary external call
> whose `msg.sender` is `owner()`. The Delay cannot tell them apart, so requiring
> `e.msg.sender == owner()` covers both.
>
> What happens upstream of the Safe on the second route is Property 1's subject. That a paused
> PauseGuard cannot interfere with it is immediate: PauseGuard is installed on the Delay and
> SetTxNonceGuard on the Roles module, and neither reads the other's storage.

> **On 4.20's "still fails *because of* the pause".** `setTxNonce` moves `txNonce`, so a later
> `executeNextTx` could in principle revert on the empty-queue check
> ([`Delay.sol:206`](../certora/helpers/Delay.sol#L206)) rather than on the guard — which would
> make 4.20 true for the wrong reason. 4.20 therefore requires `nonce < queueNonce()`, strictly
> less, where `setTxNonce` itself only needs `<=`. That leaves something still queued. 4.21 then
> exhibits that same state executing successfully once unpaused. Together they pin the revert on
> the pause rather than on the state `setTxNonce` left behind.

---

### Property 5 — the Delay's module list, owner and guard

Spec: [`specs/Delay/moduleIntegrity.spec`](specs/Delay/moduleIntegrity.spec). The scene is the
real Delay mastercopy, inherited unmodified by [`harness/DelayHarness.sol`](harness/DelayHarness.sol),
which adds one view getter and no logic. `target` is linked to
[`helpers/ReenteringAvatar.sol`](helpers/ReenteringAvatar.sol) rather than `DummyAvatar` — see the
note after the table for why.

This property covers the attack the whole integration exists to rule out: an unauthorized party
gets an address into the Delay's module list, that address queues a transaction, and after the
cooldown anyone executes it against the Ownerless Safe. Everything downstream — cooldown, veto,
pause — is moot once a hostile module is enabled, because the queue entry it writes is
indistinguishable from a legitimate one.

> **The claim that matters here is a composition, and neither half states it.** Property 1 proves
> that with both gates in place, the only call the Governor can make the DelayOwnerSafe emit is
> `Delay.setTxNonce`. Lemma 5.2 proves that the Delay's module list only moves for its `owner`,
> which is that same DelayOwnerSafe. Together — and only together — they give:
>
> **the Governor can never enable a module on the Delay.**
>
> Weakening either half gives that up silently, which is why it is written out here rather than
> left to the reader to assemble.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 5.1 | `setUp` is spent: given a module list that has already been set up, the `public` and otherwise unmodified `setUp` ([`Delay.sol:76`](../certora/helpers/Delay.sol#L76)) always reverts. It is protected only by `__Ownable_init()`'s `initializer` modifier ([`Delay.sol:87`](../certora/helpers/Delay.sol#L87)) and by `setupModules()` requiring an empty sentinel slot ([`Delay.sol:106`](../certora/helpers/Delay.sol#L106)). A second `setUp` would run `transferOwnership` **and** reset the module list, which breaks every claim below at once. | `setUpAlwaysRevertsAfterDeployment` |
| 5.2 | Over every state-changing entry point and every caller — including `executeNextTx`, whose avatar tries `enableModule` on the way through — the module list only moves under `enableModule` or `disableModule`, and only for the `owner`. **This is the formal statement of the goal "no party other than the DelayOwnerSafe quorum can add a module to the Delay".** | `modulesOnlyChangeThroughOwnerEnableOrDisable` (parametric), `ownerCanEnableModule` (witness, reachability only — see below) |
| 5.3 | The second half of the same attack: only an address already in the module list can leave a queue entry behind. Over every entry point, both `queueNonce` and `txHash[n]` only move for a caller whose raw list entry is non-zero. That is the predicate `moduleOnly` actually reads (`@gnosis.pm/zodiac` 1.0.1 `core/Modifier.sol:58-61`), rather than `isModuleEnabled`, which diverges at the self-linked sentinel. | `queueOnlyGrowsThroughEnabledModules` (parametric), `enabledModuleCanQueue` (witness) |
| 5.4 | Ownership cannot be seized, so 5.2 cannot be sidestepped by first becoming the owner: `owner` only moves through `transferOwnership` or `renounceOwnership`, and only for the current owner. | `ownerOnlyChangesThroughOwnableTransfer` (parametric) |
| 5.5 | The guard over execution is owner-only too, so nothing can detach PauseGuard on its way past. | `guardOnlyChangesThroughOwnerSetGuard` (parametric) |
| 5.6 | An execution is not a module grant. With an avatar that answers every forwarded queue entry by calling `enableModule` straight back on the Delay, `executeNextTx` completes and the attacker is still not in the list, because the return path's `msg.sender` is the avatar, not the owner. | `executeNextTxCannotEnableModuleThroughTheAvatar`, `avatarEnableModuleAttemptIsReachable` (witness) |

> **On 5.6's scene, and why it is not `DummyAvatar`.** `DummyAvatar.execTransactionFromModule`
> returns `true` and calls nothing ([`DummyAvatar.sol:19`](../certora/helpers/DummyAvatar.sol#L19)).
> That is deliberate for the specs it serves, but under it *every* claim about what the avatar's
> call can do back to the Delay would hold vacuously. `ReenteringAvatar` instead tries
> `enableModule` on every forward and records that it tried, and
> `avatarEnableModuleAttemptIsReachable` is what shows the path was actually exercised rather than
> assumed away.
>
> The `enableModule` attempt is swallowed with `try`/`catch` and the avatar reports success
> regardless. Without that, the revert would propagate through `Module.exec` and roll the whole
> transaction back, leaving no post-state in which to observe that the attempt was made and
> refused — the same vacuity problem one layer down.

> **On `setUp`, and why 5.2–5.5 exclude it.** `setUp` is the one entry point that can legitimately
> rewrite both the module list and the owner, so leaving it in the parametric `f` would make it a
> counterexample to every claim here. Pinning the starting state instead — requiring the list
> already set up — is worse than useless: in that state `setUp` *always* reverts, and a parametric
> `f(e, args)` without `@withrevert` discards reverting paths, so the `setUp` instance would pass
> with an unreachable body. Vacuous, not proved.
>
> So 5.2–5.5 filter `setUp` out of `f` and assume nothing about the starting state, which makes
> them strictly stronger: they hold from any storage. 5.1 states the `setUp` case directly, as a
> revert claim where the revert is asserted rather than assumed away. The two together cover every
> entry point of the deployed contract. The witness rules and 5.6 do still require the list set up,
> because they are about behaviour in the deployed configuration rather than about every reachable
> state.
>
> **The one exception is 5.2's `target() != owner()` requirement.** Its `msg.sender == owner`
> assertion reads the *outermost* caller, which is a stronger statement than "only the owner can
> change the list", and equivalent to it only while no nested caller can be the owner. If `target`
> were the `owner`, `executeNextTx` would forward to an avatar that is itself the owner, its
> `enableModule` would legitimately succeed, and the list would move under an outer caller who is
> not the owner — a counterexample to the assertion, but not to the property. Ruling that wiring
> out is what makes the two readings coincide. In the deployment they are two distinct addresses;
> see [Explicitly not proved](#6-explicitly-not-proved).

---

### Property 6 — Roles configuration integrity

Spec: [`specs/Roles/configIntegrity.spec`](specs/Roles/configIntegrity.spec)

Properties 1–3 all establish the restriction *given* a Roles configuration, and every part of
that configuration is mutable storage. If the Governor could reach any of it, the restriction
would hold right up until the Governor chose to remove it. This property closes that loop, and is
Conclusion 5's Roles half.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 6.1 | `setUp` is spent: given a module list that has already been set up, `Roles.setUp` ([`Roles.sol:44`](../contracts/Roles.sol#L44)) always reverts. This is the lemma that **discharges** what the assumptions table used to carry unproved for 1.1–1.3. | `setUpAlwaysRevertsAfterDeployment` |
| 6.2 | Over every state-changing entry point and every caller: if any of `guard`, `multisend`, `avatar`, `target`, `owner`, the module list, `defaultRoles`, role membership or target clearance moved, then the caller was the `owner`. The Governor is an enabled module and never the owner, so **the Governor can never widen its own restriction.** | `rolesConfigOnlyChangesThroughOwner` (parametric), `ownerCanStillReconfigure` (witness) |
| 6.3 | Ownership only moves through `transferOwnership` or `renounceOwnership`, and only for the current owner — so 6.2 cannot be sidestepped by first becoming the owner. | `ownerOnlyChangesThroughOwnableTransfer` (parametric) |

> 6.2 is the general form of 1.2. `governorSucceedsOnlyThroughRolesExecEntryPoints` states it for
> the Governor and for that scene's specific wiring; 6.2 states it for every caller and every piece
> of configuration at once, which is the form that survives someone later adding an entry point.
>
> 6.2 and 6.3 exclude `setUp` from `f` and assume nothing about the starting state, for the reason
> spelled out under Property 5; 6.1 carries that entry point on its own.

---

### Property 7 — MultiSendCallOnly, the downstream half

Spec: [`specs/MultiSend/shortBatchExecutesNothing.spec`](specs/MultiSend/shortBatchExecutesNothing.spec)

A different contract, and the only property here whose scene is not Roles or the Delay. It
answers what 3.4 deliberately leaves open: 3.4 shows Roles *permits* calldata of 100 bytes or
fewer, but the Roles scenes link `target` to `DummyAvatar`, which returns `true` and calls
nothing, so nothing downstream is modelled there.

The scene is `MultiSendCallOnly` on its own,
[vendored verbatim](../contracts/test/MultiSendCallOnly.sol) from
`@gnosis.pm/safe-contracts` so Hardhat and the Prover both have an artifact for it. The
deployment's `multisend` slot points at the canonical Safe deployment of that same source.

The threshold is written as `MULTISEND_HOLE_MAX()`, defined in the spec as `100 - (4 + 32 + 32)`, so
the `32` carries its provenance: ≤100 bytes of calldata is 68 bytes of ABI header plus at most 32 of
payload, and the decoder caps the declared length at what the calldata holds. It is the exact
image of the hole under decoding, not a number chosen for convenience.

**No loop is involved.** `MultiSendCallOnly`'s entry loop starts at `i := 0x20` and runs while
`i < length`, using the same pointer-frame/content-length convention Roles does. A declared
length of 32 or less makes that condition false *on entry*, so there are zero iterations and
`loop_iter` does no work in 7.1 — unlike the batch-length lemmas on the Roles side, this claim
does not inherit a bound from it.

| # | Lemma proved | Rule(s) |
| --- | --- | --- |
| 7.1 | With at most 32 bytes of `transactions` — less than one 85-byte entry header — no entry executes: no `CALL` opcode is reached, on completing and reverting paths alike. Observed through a `CALL` opcode hook, since `MultiSendCallOnly` performs each entry with raw assembly rather than a typed call. | `shortBatchExecutesNothing` |
| 7.2 | The no-op is clean — it returns rather than reverting. Without this, 7.1 would be equally satisfied by `multiSend` reverting on every short input, which is a different fact about the same threshold. | `shortBatchCompletesAsNoOp` (witness) |
| 7.3 | **The non-vacuity guard that matters most here.** 7.1 asserts that a ghost stays `false`, and would pass just as green if the `CALL` hook never fired at all — a wrong hook signature, or the Prover not modelling the opcode — in which case it would prove nothing. This exhibits a batch that *does* set the ghost, so the observable is live. | `longerBatchCanExecute` (witness) |
| 7.5 *(not yet run)* | **The entire external surface is `multiSend(bytes)`.** The hole lets a caller put *arbitrary* bytes in front of this contract — Roles never checks the selector, only the offset word ([`Permissions.sol:209-213`](../contracts/Permissions.sol#L209)) — so "what can 100 arbitrary bytes reach?" has two halves. If the selector matches `multiSend`, 7.1 covers it; this covers the other half by showing there is nothing else to reach, and no fallback. **It is a claim about shape, not behaviour:** it establishes that a fallback does not *exist*, not that one would be harmless. The exhaustiveness of 7.1's case analysis is what rests on it — see the obligation note below. | `multiSendIsTheOnlyEntryPoint` (parametric) |
| 7.6 *(not yet run)* | **No entry point writes storage, at any input length.** The claim that matters under `DelegateCall`, where this code runs in the **avatar's** storage context: a single `SSTORE` reached here would land on the Safe's own slots (owners, threshold, modules, nonce), so "executes no calls" alone would be cold comfort. `multiSend` performs only `call`s and has no storage access at any length, so unlike 7.1 this needs **no bound on the input** — which is why it is stated parametrically over every entry point and every argument, and why it would cover a future fallback automatically. Observed through an `ALL_SSTORE` hook, which requires storage splitting disabled — a global Prover setting, so this lemma lives in its **own conf** rather than changing the settings 7.1–7.5 verified under. | `noEntryPointWritesStorage` (parametric) |
| 7.4 | **The cutoff is exactly where the arithmetic puts it.** One byte past the threshold — a declared length of 33, i.e. 101 bytes of calldata — and an entry does execute. Without this, 7.1 would be equally true of a threshold picked far too high, with nothing tying it to the real boundary. 33 is also the first calldata length that enters *Roles'* loop (`i < data.length`, `i` starting at 100), so the two contracts share this cutoff — which is why the hole below it is empty on both sides rather than on only one. | `oneByteAboveTheHoleExecutes` (witness) |

> **If 7.5 ever fails, what must be proved.** 7.5 says the external surface is exactly
> `multiSend` and contains no fallback. That is what makes 7.1's case analysis exhaustive:
> arbitrary calldata either matches `multiSend`, where 7.1 applies, or matches nothing. It does
> **not** say a fallback would be safe.
>
> So if a function or fallback is ever added to the vendored copy, 7.5 fails, and the obligation
> is to prove the new entry point cannot violate the restriction either — specifically, that it
> executes no call on an input of at most 32 bytes, the way 7.1 does for `multiSend`. Half of that
> obligation is already discharged in advance: 7.6 is parametric over every entry point, so a new
> one would have to write no storage to pass. The no-call half is length-bounded and cannot be
> generalised the same way, so it is the part that would need new work.

> **What Property 7 does not cover, and why.** Two steps in the chain are compiler-generated and
> are left to source and test rather than the Prover:
>
> - **That calldata of at most 100 bytes yields a declared `transactions` length of at most 32.**
>   That is the ABI decoder's calldata bounds check. This spec receives `transactions` already
>   decoded and states the threshold on its length directly.
> - **That calldata whose selector is not `multiSend(bytes)` reverts.** The *premise* is now proved
>   rather than read off source: 7.5 establishes that every external entry point is `multiSend`
>   and that none is a fallback. What remains assumed is only the Solidity dispatcher's behaviour
>   on unmatched calldata, which the Prover abstracts — CVL's `method f` ranges over *declared*
>   functions, so an undeclared selector cannot be invoked from a rule at all.
>
> Both are covered against the real contracts by
> [`test/MultisendShortBlob.spec.ts`](../test/MultisendShortBlob.spec.ts), together with the
> avatar returning `success == false` rather than propagating the inner revert.

---

## 6. Explicitly not proved

Carried over from the "Deliberately NOT claimed" sections of each spec, so that the tables above
are not read as broader than they are.

| Not claimed | Where it would have gone |
| --- | --- |
| `compValues` entries longer than that same 1024-byte bound on Property 6's conf. `compressCompValue` hashes a symbolic-length `bytes calldata` ([`Permissions.sol:1080`](../contracts/Permissions.sol#L1080)), which is unbounded hashing. Without `optimistic_hashing` the Prover leaves keccak injectivity unenforced and manufactures counterexamples in which a `role.compValues` slot aliases the `_owner` slot. Turning it on is what makes 6.2 and 6.3 provable at all — at the cost of assuming no hashed `compValue` exceeds 1024 bytes. | Property 6 |
| `scopeParameterAsOneOf` with a `compValues` array whose length is not exactly 2. The function reverts below length 2 ([`Permissions.sol:685`](../contracts/Permissions.sol#L685)), while `optimistic_loop` assumes the loop exited after `loop_iter` unrollings. With `loop_iter: 1` that left every non-reverting path pruned and that instance of 6.2/6.3 **vacuous** — a sanity failure, not a pass. Property 6's conf therefore raises `loop_iter` to 2, which pins the length at exactly 2. Ownership and configuration ownership do not depend on the array's length, but the claim as stated is bounded. | Property 6 |
| That the avatar can do no harm anywhere else. `ReenteringAvatar` models one return path — back into the Delay's own owner-only surface. What a real avatar does with the rest of a queue entry is that entry's business, and is what the cooldown is for. | Property 5 |
| That `enableModule` leaves the module list in the expected shape. 5.2's witness asserts only that the owner's call does not revert. The resulting state is not observable in this scene: the Prover scalarizes the constant-key `modules[SENTINEL_MODULES]` that `Modifier`'s own code writes — visible in counterexamples as a scalar going `SENTINEL` → `m` across the call — while every getter reachable from CVL takes the key as a parameter and reads the storage wordmap, which never sees that write. Asserting the list afterwards, whether via `isModuleEnabled`, via `moduleEntry`, or via a dedicated constant-key harness getter, fails against a model where `enableModule` reports success and the list reads unchanged. The write demonstrably happens; the storage view cannot see it. Worth raising with Certora rather than working around further. | Property 5 |
| The Roles-side equivalent of 5.6. `target` is linked to `DummyAvatar` in Property 6's scene, which calls nothing, so the avatar's return path is not explored there. On that side the avatar is the DelayOwnerSafe, and what the Governor can make it emit is Property 1's subject. | Property 6 |
| That calldata of at most 100 bytes decodes to a `transactions` length of at most 32. That is the ABI decoder's bounds check, which is compiler-generated; 7.1 starts from the decoded length. Covered by [`test/MultisendShortBlob.spec.ts`](../test/MultisendShortBlob.spec.ts), not by the Prover. | Property 7 |
| That calldata with any selector other than `multiSend(bytes)` reverts. 7.5 proves no other function or fallback exists; the Solidity dispatcher's revert on an unmatched selector is abstracted by the Prover and covered by test. | Property 7 |
| That 7.6's `ALL_SSTORE` hook fires. 7.6 asserts a ghost stays `false` and has no witness showing the hook can set it, so a green result is consistent with the hook never firing. MultiSendCallOnly writes no storage at any length, so no witness is available from within that contract. | Property 7 |
| Anything about MultiSendCallOnly's calls on calldata longer than 100 bytes. 7.1 is bounded to the hole below Roles' loop start; 7.4 shows an entry does execute one byte past it. What longer batches may contain is Property 3's subject, on the Roles side. | Property 7 |

---

## 7. Assumptions read off source rather than checked by the Prover

| Assumption | Source | Used by |
| --- | --- | --- |
| `ForwardingAvatar` forwards as the DelayOwnerSafe does on the module path: the Safe's module check (`ModuleManager.sol:68`, over a flat mapping rather than the linked list) and `Executor.execute` — the inner call's success returned rather than propagated. One deviation: a plain `Call` of `setTxNonce` to the linked Delay is made as a typed call instead of `Executor`'s low-level `call`, with the same callee, selector, argument and zero value. Through the low-level path the Prover handed the callee a calldatasize of 0, so the Delay's dispatcher reverted before reaching `setTxNonce`. The model follows `@gnosis.pm/safe-contracts` 1.3.0; the DelayOwnerSafe is Safe v1.4.1, whose module path the governance plan records as identical (`new_governance_plan_ownerless_safe.md:30`) but which is not itself in scene. | `@gnosis.pm/safe-contracts` `base/ModuleManager.sol:61-73`, `base/Executor.sol:8-25` | 1.4–1.6 |
| `Module.exec` calls `IGuard(guard).checkTransaction(...)` — i.e. the address in the Delay's `guard` slot. | `@gnosis.pm/zodiac` 1.0.1 `core/Module.sol:43-77` | 4.15, 4.16 |
| `Module.exec` forwards to `IAvatar(target).execTransactionFromModule(...)`, so an avatar linked at `target` really is on the path a queue entry takes. | same, `core/Module.sol:66-72` | 5.6 |
| That call is a plain external call with no `try`/`catch`, so a revert inside `checkTransaction` reverts `executeNextTx`. | same | 4.15 |
| The Roles module has been set up on chain, i.e. `moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES()`. The consequence that used to be read off source alongside it — *so `setUp` is not callable by anyone* — is now proved: 6.1 for Roles, 5.1 for the Delay. What remains assumed is only the deployment fact, which the verification plan checks. 5.2–5.5 and 6.2–6.3 no longer need it at all: they exclude `setUp` from `f` and hold from any starting state. | `Roles.sol:56-59`, `Delay.sol:106-112` | 1.1–1.3, 5.1, 5.6, 6.1, and the witness rules of 5.2, 5.3 and 6.2 |
| PauseGuard's constructor grants `DEFAULT_ADMIN_ROLE` to nobody — the base case for 4.13. | `PauseGuard` constructor | 4.12, 4.13 |

---

## 8. Reproducing

CI runs every conf on every push
([`.github/workflows/formal-verification.yaml`](../../../.github/workflows/formal-verification.yaml)),
one matrix job per conf, with `--wait_for_results all` so a failing rule fails the build.

`certoraRun` typechecks the spec locally *before* it needs `CERTORAKEY`, so running it without a
key set is a free syntax and type check — it compiles the scene, typechecks the CVL, and only
then stops on the missing key. Worth doing on every spec edit before submitting.

Locally, `certoraRun` takes **one** conf per invocation (it rejects multiple), and by default
submits the job without waiting for results. Prerequisites: `CERTORAKEY` exported, and solc 0.8.6
selected — the confs pin no `solc` key, so they use whatever is on `PATH`:

```bash
pip3 install -r ../requirements.txt && solc-select install 0.8.6 && solc-select use 0.8.6
```

All five Roles rulesets, submitted back to back:

```bash
cd packages/evm && for c in Roles-setTxNonceGuardAndRoleConfig Roles-setTxNonceLands Roles-setTxNonceGuardSufficient Roles-setTxNonceRoleConfigSufficient Roles-configIntegrity; do certoraRun "./certora/confs/$c.conf" --msg "$c - $(git rev-parse --short HEAD)"; done
```

Both Delay rulesets:

```bash
cd packages/evm && for c in Delay-pauseGuardSufficient Delay-moduleIntegrity; do certoraRun "./certora/confs/$c.conf" --msg "$c - $(git rev-parse --short HEAD)"; done
```

Property 7, whose scene is MultiSendCallOnly alone:

```bash
cd packages/evm && certoraRun ./certora/confs/MultiSend-shortBatch.conf --msg "MultiSend-shortBatch - $(git rev-parse --short HEAD)"
```

A single lemma's rules, via `--rule` (space-separated list, wildcards allowed) — here 4.18–4.21:

```bash
cd packages/evm && certoraRun ./certora/confs/Delay-pauseGuardSufficient.conf --rule '*SetTxNonce*' --msg "section 7 - pause vs owner setTxNonce"
```

`rule_sanity: basic` is set inside every conf, so it does not need to be passed on the command
line. It is what catches a rule that passes because its body is unreachable: in the Prover's output,
a red **rule not vacuous** node is a failure, however green the rule's own assertions look.
