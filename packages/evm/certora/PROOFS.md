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

1. Only the proposer safe and ownerless safe may execute DEVOPS_ROLE methods, holding the governance settings constant.

2. Only TERM token holders and Term multisig holders may veto Delay modifier transactions, holding the governance settings constant

3. Governance settings cannot be changed other than by the ownerless safe, proposer safe, or DelayModOwner safe

Only Term multisig holders can execute DEVOPS_ROLE methods subject to TERM token governance, and this can't be changed other than through Term multisig approval.

### Generalization 1 — Only the proposer safe and ownerless safe may execute DEVOPS_ROLE methods, holding the governance settings constant.

| # | Statement | Evidence |
| --- | --- | --- |
| G1.1 | Only the Ownerless Safe holds the DEVOPS_ROLE required for protocol changes. | — |
| G1.2 | Only Modules or Owners can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. | **FV — every entry point to the Safe is enumerated below:** SE-1 `safeEntryPointsAreAllAccountedFor` ✅ passes. Safe v1.3.0 has no write functions besides these seventeen entry points (the Prover checks `fallback` and `receive` as one entry), and any other call lands in `fallback`. Grouped by who can call each one:<br><br>*module gated entry points:*<br>• `execTransactionFromModule`<br>• `execTransactionFromModuleReturnData`<br><br>*owner gated entry points:*<br>• `execTransaction`<br>• `approveHash`<br><br>*Self calls — only modules and owners can reach these:*<br>• `enableModule`<br>• `disableModule`<br>• `addOwnerWithThreshold`<br>• `removeOwner`<br>• `swapOwner`<br>• `changeThreshold`<br>• `setGuard`<br>• `setFallbackHandler`<br><br>*Non-interactions — these always revert, so nothing they do stands:*<br>• `setup`<br>• `requiredTxGas`<br>• `simulateAndRevert`<br><br>*Open to anyone:*<br>• `fallback`<br>• `receive`<br><br>**FV — module-only entry points can make the Safe execute to any destination:** `execTransactionFromModule`, `execTransactionFromModuleReturnData`.<br>• SE-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can successfully call `execTransactionFromModule` or `execTransactionFromModuleReturnData`.<br>• SE-4 `enabledModuleCanMakeTheSafeAct` ✅ passes: an enabled module can call `execTransactionFromModule` and `execTransactionFromModuleReturnData` directly, with no owner signatures, and the Safe makes an outgoing call or delegatecall.<br><br>**FV — owner-only entry points can make the Safe execute to any destination:** `execTransaction`, `approveHash`.<br>• SE-6 `ownersCanMakeTheSafeAct` ✅ passes: once the threshold is passed, `execTransaction` succeeds and the Safe acts, for any threshold and any number of owners.<br>• SE-5 `execTransactionRunsOnlyAfterTheSignatureCheck` ✅ passes: `execTransaction` only runs once the signature check has passed for that exact transaction.<br>• SE-12 `eachSignatureAcceptsANewApprovingOwner` ✅ passes: every signature the check accepts is a different owner who approved it. With SE-5, the Safe acts through `execTransaction` only when as many different owners as the threshold have approved.<br>• SE-8 `onlyOwnersCanApproveHashes` ✅ passes: `approveHash` only records an owner's own approval, which then counts as that owner's signature in `execTransaction`.<br><br>**FV — settings functions are only reached through the module-only or owner-only points:**<br><br>• SE-7 `settingsOnlyChangeWhenTheSafeCallsItself` ✅ passes: these only change a setting when the caller is the Safe itself.<br>• SC-4 `settingsOnlyChangeThroughAModuleOrOwners` ✅ passes: over every write function, `fallback` included, a setting only changes through an enabled module's `execTransactionFromModule` or `execTransactionFromModuleReturnData`, or through `execTransaction`. A fallback handler is checked as if it were the Safe itself, so it cannot reach these functions even then.<br>• SC-1 `moduleCanChangeSettings`, SC-2 `moduleCanChangeSettingsWithReturnData` ✅ pass: for each function above, a module's `execTransactionFromModule`, and likewise its `execTransactionFromModuleReturnData`, addressed to the Safe with a call to that function, succeeds and changes a setting.<br>• SC-3 `ownersCanChangeSettings` ✅ passes: the same through `execTransaction`, once the threshold is passed.<br><br>**FV — setup is not a callable function after deploy:** SE-9 `setupAlwaysRevertsAfterSetup` ✅ passes. Once the Safe is set up, `setup` always reverts, so nobody can re-run it to replace the owners, threshold, modules or handler.<br><br>**FV — `requiredTxGas` and `simulateAndRevert` always revert:** SE-10 `requiredTxGasAlwaysReverts`, SE-11 `simulateAndRevertAlwaysReverts` ✅ pass. Anyone can call them, and they do execute a call (`requiredTxGas`) or delegatecall (`simulateAndRevert`), but they always revert afterwards, so nothing they do stands.<br><br>**FV — Any address can call any unsupported Safe function to initiate `fallback`, which can only make the Safe execute to Fallback Handler address if set to nonzero address:** <br>• SE-14 `fallbackOnlyCallsItsHandler` ✅ passes: with a handler set, `fallback` only makes a plain call, with no ETH, to the handler. It never delegatecalls, so the handler's code runs as its own contract, not as the Safe, and cannot write the Safe's storage. Assumes the handler is not the Safe itself: v1.3.0 allows that (v1.4.0 forbids it, GS400), and then `fallback` calls back into the Safe as the Safe. That case is covered by SE-16.<br>• SE-16 `selfHandlerFallbackChangesNothing` ✅ passes: with the Safe set as its own handler, `fallback` leaves the Safe's storage exactly as it was, and when it succeeds the Safe called nothing but itself, sent no ETH and made no delegatecall. Why: with 4+ bytes of calldata the inner call selects the same unmatched function and lands in `fallback` again, looping until it runs out and reverts; with 1–3 bytes the caller's appended address completes a new selector, but the inner call has only 21–23 bytes of calldata, so any function taking an argument fails ABI decoding and every function taking none is a view (`getThreshold`, `getOwners`, `getChainId`, `domainSeparator`, `nonce`, `VERSION`). So `fallback` either reverts or returns a view's answer. Only the Safe can set its handler (SE-7), and the Proposer Safe has none.<br>• SE-13 `fallbackMakesNoCallWithoutAHandler` ✅ passes: with no handler set (the zero address), `fallback` makes no call or delegatecall at all.<br>• SE-15 `fallbackHandlerCallsComeFromTheHandler` ✅ passes: once `fallback` calls its handler, every call the handler makes has the handler, not the Safe, as `msg.sender`. Checked with a real handler contract in the Safe's handler slot that makes a call onward, recording who it came from. The handler therefore cannot execute as the Safe to any address. Assumes the handler is not the Safe itself; that case is SE-16.<br>• A handler can only be set by the Safe itself (SE-7), and the Proposer Safe's handler slot is empty on-chain (block 26056133), so on the Proposer Safe `fallback` does nothing (SE-13).<br><br>**FV — Any address can trigger `receive` by sending Eth without calldata and it does nothing but  emits `SafeReceived`:**<br>• SE-17 `receiveOnlyEmitsSafeReceived` ✅ passes: whenever `receive` runs, it does nothing beyond the event. It emits exactly one log, `SafeReceived`, naming the caller as sender. It makes no call of any kind (call, delegatecall, staticcall or callcode) and writes no storage.<br>• SE-18 `receiveCanRun` ✅ passes: some call to the Safe succeeds and emits `SafeReceived`, so SE-17 is not vacuous. |
| G1.3 | OwnerlessSafe fallback handler is `address(0)`. | — |
| G1.4 | Delay Module is the only enabled module on OwnerlessSafe. | — |
| G1.5 | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | **FV — every entry point to the Delay Modifier is enumerated below:** DM-13 `delayWriteFunctionsAreTheKnownFifteen` ✅ passes. The Delay has no fallback and exactly fifteen write functions, each covered below:<br>• `setTxCooldown` — owner only (DM-8)<br>• `setTxExpiration` — owner only (DM-8)<br>• `setTxNonce` — owner only (DM-8)<br>• `setAvatar` — owner only (DM-8)<br>• `setTarget` — owner only (DM-8)<br>• `enableModule` — owner only (DM-8)<br>• `disableModule` — owner only (DM-8)<br>• `setGuard` — owner only (DM-8)<br>• `transferOwnership` — owner only (DM-8)<br>• `renounceOwnership` — owner only (DM-8)<br>• `execTransactionFromModule` — modules only (DM-4)<br>• `execTransactionFromModuleReturnData` — modules only (DM-4)<br>• `executeNextTx` — anyone (DM-11)<br>• `skipExpired` — anyone (DM-12)<br>• `setUp` — nobody after deployment (DM-1)<br><br>**FV — owner-only settings:** DM-8 `atMostOneCallerPassesOnlyOwner` ✅ passes. Only the owner can call the Delay's ten settings functions. There can only be one owner at a time.<br><br>**FV — module-only queueing:** DM-4 `queueOnlyGrowsThroughEnabledModules` ✅ passes. Only an enabled module can add a transaction to the queue.<br><br>**FV — setup is closed:** DM-1 `setUpAlwaysRevertsAfterDeployment` ✅ passes. Nobody can re-run the Delay's setup after deployment.<br><br>**FV — the two exceptions are open:** DM-11 `anyoneCanExecuteNextTx`, DM-12 `anyoneCanSkipExpired` ✅ pass. An address that is neither the owner nor a module can execute a queued transaction and skip an expired one.<br><br>**FV — every other function, checked all at once:** DM-14 `onlyModulesOrOwnerCanCallDelay` ✅ passes. For every write function except `executeNextTx`, `skipExpired` and `setUp`, a call that succeeds came from the owner or an enabled module. It does not rely on a list of names, so it also covers any function added later. |
| G1.6 | ProposerSafe is the only enabled module on the Delay Mod | — |
| G1.7 | Only Modules or Owners can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.2: the Proposer Safe runs the same GnosisSafe v1.3.0 code as the Ownerless Safe. |
| G1.8 | ProposerSafe fallback handler is address(0). | **On-chain:** ✅ the fallback handler slot (`0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5`, `FallbackManager.sol:12`) on the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`) is zero at block 26056133. |
| G1.9 | ProposerSafe has no enabled modules. | **On-chain:** ✅ `getModulesPaginated` on the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`) returns an empty list at block 26050570. |
| G1.10 | A transaction queued by the Proposer Safe executes on the Ownerless Safe once the cooldown has passed, if it hasn't expired, the system isn't paused, and it hasn't been vetoed. | **FV — transaction proposed by module executes after cooldown and gefore expiration:** DP-29 `queuedTransactionExecutesAfterCooldown` ✅ passes. Once a module has queued a transaction, and the cooldown has passed, it hasn't expired and the system isn't paused, anyone can execute it and it reaches the Ownerless Safe. Holds for every transaction, assuming the Ownerless Safe accepts the call.<br><br>**FV — transaction cannot execute too early or too late:** DP-30 `executeNextTxRevertsDuringCooldown`, DP-31 `executeNextTxRevertsAfterExpiration` ✅ pass. It cannot run before the cooldown has passed or after it has expired.<br><br>**FV — transaction cannot be executed while paused:** DP-18 `pausedBlocksExecuteNextTx` ✅ passes. It cannot run while PauseGuard is paused.<br><br>**FV — Only the transaction at the current txNonce executes:** DP-28 `executeNextTxConsumesOnlyTheEntryAtTxNonce` ✅ passes. What executes is exactly the transaction that was queued.<br><br>**FV — transaction cannot be executed once vetoed:** DP-32 `vetoedTransactionCannotExecute`, DP-33 `entryPassedByTxNonceNeverExecutes` ✅ pass. Once `txNonce` has moved past a proposal's nonce, it can never be executed. A proposal is vetoed by moving `txNonce` past it with `setTxNonce`. |

### Generalization 2 — Only TERM token holders and Term multisig holders may veto Delay modifier transactions, holding the governance settings constant

| # | Statement | Evidence |
| --- | --- | --- |
| G2.1 | Veto power (`Delay.setTxNonce(uint256)`) is held exclusively by the owner of the DelayMod. | **FV — `setTxNonce` is owner-only:** DM-8 `atMostOneCallerPassesOnlyOwner` ✅ passes. `setTxNonce` is one of the Delay's ten `onlyOwner` functions: only the address recorded as the owner can call it successfully, and no two different callers can both get through from the same state. |
| G2.2 | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5 |
| G2.3 | DelayMod only has one owner, which is the DelayOwnerSafe. | **FV — one owner:** DM-8 `atMostOneCallerPassesOnlyOwner` ✅ passes. The Delay has only one owner: at any moment, only one address can change the Delay's settings, and it is the address recorded as the owner. No second address can ever do it alongside it.<br><br>**On-chain — owner is DelayOwnerSafe:** ⏳ pending migration. `owner()` on the Delay must return `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3`. At block 26049693 it returns `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` (old Roles). |
| G2.4 | Only Modules or Owners can interact with DelayOwnerSafe, except fallback and receive, which anyone can call. | The same rules as G1.2, run against Safe v1.4.1 through the `Safe-v141-*` confs. Each rule keeps its G1.2 number: SE-n becomes SE141-n and SC-n becomes SC141-n.<br><br>**FV — every entry point to the Safe is enumerated below:** SE141-1 `safeEntryPointsAreAllAccountedFor` ✅ passes. Safe v1.4.1 has no write functions besides these sixteen entry points (the Prover checks `fallback` and `receive` as one entry), and any other call lands in `fallback`. These are G1.2's seventeen minus `requiredTxGas`, which Safe removed in v1.4.0. Grouped by who can call each one:<br><br>*module gated entry points:*<br>• `execTransactionFromModule`<br>• `execTransactionFromModuleReturnData`<br><br>*owner gated entry points:*<br>• `execTransaction`<br>• `approveHash`<br><br>*Self calls — only modules and owners can reach these:*<br>• `enableModule`<br>• `disableModule`<br>• `addOwnerWithThreshold`<br>• `removeOwner`<br>• `swapOwner`<br>• `changeThreshold`<br>• `setGuard`<br>• `setFallbackHandler`<br><br>*Non-interactions — these always revert, so nothing they do stands:*<br>• `setup`<br>• `simulateAndRevert`<br><br>*Open to anyone:*<br>• `fallback`<br>• `receive`<br><br>**FV — module-only entry points can make the Safe execute to any destination:** `execTransactionFromModule`, `execTransactionFromModuleReturnData`.<br>• SE141-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can successfully call `execTransactionFromModule` or `execTransactionFromModuleReturnData`.<br>• SE141-4 `enabledModuleCanMakeTheSafeAct` ✅ passes: an enabled module can call `execTransactionFromModule` and `execTransactionFromModuleReturnData` directly, with no owner signatures, and the Safe makes an outgoing call or delegatecall.<br><br>**FV — owner-only entry points can make the Safe execute to any destination:** `execTransaction`, `approveHash`.<br>• SE141-6 `ownersCanMakeTheSafeAct` ✅ passes: once the threshold is passed, `execTransaction` succeeds and the Safe acts, for any threshold and any number of owners.<br>• SE141-5 `execTransactionRunsOnlyAfterTheSignatureCheck` ✅ passes: `execTransaction` only runs once the signature check has passed for that exact transaction.<br>• SE141-12 `eachSignatureAcceptsANewApprovingOwner` ✅ passes: every signature the check accepts is a different owner who approved it. With SE141-5, the Safe acts through `execTransaction` only when as many different owners as the threshold have approved.<br>• SE141-8 `onlyOwnersCanApproveHashes` ✅ passes: `approveHash` only records an owner's own approval, which then counts as that owner's signature in `execTransaction`.<br><br>**FV — settings functions are only reached through the module-only or owner-only points:**<br><br>• SE141-7 `settingsOnlyChangeWhenTheSafeCallsItself` ✅ passes: these only change a setting when the caller is the Safe itself.<br>• SC141-4 `settingsOnlyChangeThroughAModuleOrOwners` ✅ passes: over every write function, `fallback` included, a setting only changes through an enabled module's `execTransactionFromModule` or `execTransactionFromModuleReturnData`, or through `execTransaction`. A fallback handler is checked as if it were the Safe itself, so it cannot reach these functions even then.<br>• SC141-1 `moduleCanChangeSettings`, SC141-2 `moduleCanChangeSettingsWithReturnData` ✅ pass: for each function above, a module's `execTransactionFromModule`, and likewise its `execTransactionFromModuleReturnData`, addressed to the Safe with a call to that function, succeeds and changes a setting.<br>• SC141-3 `ownersCanChangeSettings` ✅ passes: the same through `execTransaction`, once the threshold is passed.<br><br>**FV — setup is not a callable function after deploy:** SE141-9 `setupAlwaysRevertsAfterSetup` ✅ passes. Once the Safe is set up, `setup` always reverts, so nobody can re-run it to replace the owners, threshold, modules or handler.<br><br>**FV — `simulateAndRevert` always reverts:** SE141-11 `simulateAndRevertAlwaysReverts` ✅ passes. Anyone can call it, and it does make a delegatecall, but it always reverts afterwards, so nothing it does stands.<br><br>**FV — Any address can call any unsupported Safe function to initiate `fallback`, which can only make the Safe execute to Fallback Handler address if set to nonzero address:**<br>• SE141-14 `fallbackOnlyCallsItsHandler` ✅ passes: with a handler set, `fallback` only makes a plain call, with no ETH, to the handler. It never delegatecalls, so the handler's code runs as its own contract, not as the Safe, and cannot write the Safe's storage. Assumes the handler is not the Safe itself: v1.4.1's `setFallbackHandler` and `setup` refuse that (GS400), but a delegatecall run through `execTransaction` or a module can still write the handler slot directly. That case is covered by SE141-16.<br>• SE141-16 `selfHandlerFallbackChangesNothing` ✅ passes: with the Safe set as its own handler, `fallback` leaves the Safe's storage exactly as it was, and when it succeeds the Safe called nothing but itself, sent no ETH and made no delegatecall. The reason is the same as for SE-16 in G1.2: v1.4.1's functions that take no arguments are the same six views (`getThreshold`, `getOwners`, `getChainId`, `domainSeparator`, `nonce`, `VERSION`).<br>• SE141-13 `fallbackMakesNoCallWithoutAHandler` ✅ passes: with no handler set (the zero address), `fallback` makes no call or delegatecall at all.<br>• SE141-15 `fallbackHandlerCallsComeFromTheHandler` ✅ passes: once `fallback` calls its handler, every call the handler makes has the handler, not the Safe, as `msg.sender`. Checked with a real handler contract in the Safe's handler slot that makes a call onward, recording who it came from. The handler therefore cannot execute as the Safe to any address. Assumes the handler is not the Safe itself; that case is SE141-16.<br>• A handler can only be set by the Safe itself (SE141-7). Whether the DelayOwnerSafe has one is G2.5.<br><br>**FV — Any address can trigger `receive` by sending Eth without calldata and it does nothing but emits `SafeReceived`:**<br>• SE141-17 `receiveOnlyEmitsSafeReceived` ✅ passes: whenever `receive` runs, it does nothing beyond the event. It emits exactly one log, `SafeReceived`, naming the caller as sender. It makes no call of any kind (call, delegatecall, staticcall or callcode) and writes no storage.<br>• SE141-18 `receiveCanRun` ✅ passes: some call to the Safe succeeds and emits `SafeReceived`, so SE141-17 is not vacuous. |
| G2.5 | DelayOwnerSafe fallback handler is `address(0)`. | — |
| G2.6 | DelayOwnerSafe only has one enabled module, the Roles Modifier | — |
| G2.7 | Only Modules with assignedRoles or Owners can interact with Roles Modifier. | **FV — every entry point to the Roles Modifier is enumerated below:** RI-14 `rolesWriteFunctionsAreTheKnownTwentyFive` ✅ passes. The Roles Modifier has no `fallback` or `receive` and no write functions besides these twenty-five. Grouped by who can call each one:<br><br>*entry points gated to enabled modules with assigned roles:*<br>• `execTransactionFromModule` (the caller's default role)<br>• `execTransactionFromModuleReturnData` (the caller's default role)<br>• `execTransactionWithRole` (the role the call names)<br>• `execTransactionWithRoleReturnData` (the role the call names)<br><br>*owner gated entry points — the settings functions:*<br>• `setMultisend`<br>• `allowTarget`<br>• `revokeTarget`<br>• `scopeTarget`<br>• `scopeAllowFunction`<br>• `scopeRevokeFunction`<br>• `scopeFunction`<br>• `scopeFunctionExecutionOptions`<br>• `scopeParameter`<br>• `scopeParameterAsOneOf`<br>• `unscopeParameter`<br>• `assignRoles`<br>• `setDefaultRole`<br>• `setAvatar`<br>• `setTarget`<br>• `enableModule`<br>• `disableModule`<br>• `setGuard`<br>• `transferOwnership`<br>• `renounceOwnership`<br><br>*Non-interactions — this always reverts, so nothing it does stands:*<br>• `setUp`<br><br>**FV — execution functions succeed only if caller address is an enabled module AND has been assigned the permissioned role** `execTransactionFromModule`, `execTransactionFromModuleReturnData`, `execTransactionWithRole`, `execTransactionWithRoleReturnData`.<br>• RI-7 `onlyEnabledModulesCanExec` ✅ passes: only enabled modules can call exec functions<br>• RI-8 `moduleWithoutDefaultRoleCannotExecFromModule` ✅ passes: an enabled module that is not a member of its default role cannot execute through `execTransactionFromModule` or `execTransactionFromModuleReturnData`. <br>• RI-9 `moduleWithoutRoleCannotExecTransactionWithRole`, RI-10 `moduleWithoutRoleCannotExecTransactionWithRoleReturnData` ✅ pass: an enabled module that is not a member of the role the call names cannot execute through `execTransactionWithRole` or `execTransactionWithRoleReturnData`.  With RI-8, a module with no assigned role can execute nothing through any of the four.<br>• RI-11 `roleMemberModuleCanExecFromModule`, RI-12 `roleMemberModuleCanExecTransactionWithRole`, RI-13 `roleMemberModuleCanExecTransactionWithRoleReturnData` ✅ pass: an enabled module that is a member of the role the call runs under can successfully call each of the four, so the restriction is not achieved by nothing working.<br><br>**FV — owner-only settings:** RI-2 `rolesConfigOnlyChangesThroughOwner`, RI-3 `ownerOnlyChangesThroughOwnableTransfer`, RI-4 `ownerCanStillReconfigure`, RI-5 `onlyOwnerCanCallRolesSettings`, RI-6 `ownerCanCallEachRolesSetting` ✅ pass. Each of the twenty settings functions only succeeds for the owner (RI-5), and the owner can successfully call each one (RI-6); a `setDefaultRole` the owner makes takes effect (RI-4). Over every write function and every caller, if the guard, `multisend`, `avatar`, `target`, owner, module list, default roles, role membership or target clearance changed, the caller was the owner, from any starting state (RI-2). Ownership itself only moves through `transferOwnership` or `renounceOwnership`, and only for the current owner, so nobody else can first become the owner (RI-3).<br><br>**FV — setup is not a callable function after deploy:** RI-1 `setUpAlwaysRevertsAfterDeployment` ✅ passes. Once the module list is set up, `setUp` always reverts, so nobody can re-run it to replace the owner or the module list.<br><br> |
| G2.8 | The Governor  is the only enabled module of the Roles Modifier with an assignedRole. | — |
| G2.9 | The Governor  is assigned only role 1, its defaultRole. | — |
| G2.10 | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | **FV — role 1 alone restricts member module executions to vetos (Delay.setTxNonce(uint256)), except through MultiSend:** RC-1 `roleConfigLimitsExecTransactionWithRoleToDelaySetTxNonce`, RC-2 `roleConfigLimitsExecTransactionFromModuleToDelaySetTxNonce`, RC-3 `roleConfigLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, RC-4 `roleConfigLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` ✅ pass. With no guard, role 1's scope configuration admits only `setTxNonce(uint256)` on the Delay, with zero value and as a plain `Call`, on all four entry points, provided the destination is not the MultiSend address.<br>• RC-5 `nonMemberExecTransactionWithRoleAlwaysReverts` ✅ passes: a caller that is not a member of the role it names can execute nothing at all. Stated on `execTransactionWithRole`.<br>• RC-7 `withoutSetTxNonceGuardMultisendTargetEscapesRoleConfig` ✅ passes: without the guard, a transaction addressed to the MultiSend address completes although it is not the Delay. This is the gap the guard closes (RS-6).<br><br>**FV — setTxNonceGuard alone restricts all Roles Modifier executions to vetos `Delay.setTxNonce(uint256)`:** RS-1 `setTxNonceGuardLimitsExecTransactionWithRoleToDelaySetTxNonce`, RS-2 `setTxNonceGuardLimitsExecTransactionFromModuleToDelaySetTxNonce`, RS-3 `setTxNonceGuardLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, RS-4 `setTxNonceGuardLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` ✅ pass. With SetTxNonceGuard installed, every execution on all four entry points is `setTxNonce(uint256)` on the Delay, with zero value and as a plain `Call`, for any caller, any role and any Roles configuration.<br>• RS-5 `setTxNonceGuardLimitsToDelaySetTxNonceUnderMaximallyPermissiveRoles` ✅ passes: the same holds under the worst-case configuration, blanket `Clearance.Target` with `ExecutionOptions.Both`.<br>• RS-6 `setTxNonceGuardRejectsMultisendTarget` ✅ passes: a transaction addressed to the MultiSend address always reverts.<br>• RS-7 `withoutSetTxNonceGuardPermissiveRolesAllowNonDelayCall` ✅ passes: with no guard and the same permissive configuration, a call to something other than the Delay succeeds, so it is the guard that imposes the restriction.<br><br>**FV — With role 1 and SetTxNonceGuard applied together, the Governor can only veto:** RG-2 `governorExecTransactionWithRoleLimitedToDelaySetTxNonce`, RG-3 `governorExecTransactionFromModuleLimitedToDelaySetTxNonce`, RG-4 `governorExecTransactionWithRoleReturnDataLimitedToDelaySetTxNonce`, RG-5 `governorExecTransactionFromModuleReturnDataLimitedToDelaySetTxNonce` ✅ pass. Every call the Governor completes through the Roles Modifier is `setTxNonce(uint256)` on the Delay, with zero value and as a plain `Call`, on all four execution entry points: `execTransactionWithRole`, `execTransactionFromModule`, `execTransactionWithRoleReturnData` and `execTransactionFromModuleReturnData`. Assumes SetTxNonceGuard is installed and pointed at the Delay, and the Governor is an enabled module, a member of role 1 only, with default role 1 (G2.9).<br><br>**FV — Governor successfully vetoes:** RG-6 `governorCanStillCallDelaySetTxNonce` ✅ passes. Under the same setup, the Governor's `setTxNonce` call really does go through, so the restriction is not achieved by nothing working.<br><br>|
| G2.11 | TERM Token holders can create a Governor proposal to veto, and once it passes vote, successfully execute. | **FV — TERM holders can propose the veto:** GV-1 `holderAboveThresholdCanProposeVeto` ⏳ not yet run. Any address with at least 1,000 TERM of votes at `clock() − 1` can propose the veto, the one-action proposal calling the Roles Modifier with `execTransactionWithRole(Delay, 0, setTxNonce(n), Call, 1, true)`, for any `n` and any description `propose` accepts from it, unless that exact proposal already exists. The proposal records the caller as its proposer, and its vote opens at once and runs for 22 hours.<br><br>**FV — once it passes, the veto executes:** GV-2 `passedVetoExecutes` ⏳ not yet run. Once the veto's state is `Succeeded`, anyone's `execute` succeeds and the Delay's `txNonce` becomes `n`, for any `n` the Delay accepts (`txNonce < n ≤ queueNonce`). Assumes the deployed wiring: SetTxNonceGuard is the Roles Modifier's guard and points at the Delay, role 1 is scoped to `Delay.setTxNonce`, the Governor is an enabled module in role 1 (G2.8, G2.9), and the DelayOwnerSafe has the Roles Modifier as a module (G2.6) and owns the Delay (G2.3).<br><br>Both rules run on the deployed code: the Governor (`0x2B715634134220ffeEE9458b4e34E41A41418607`) and TERM's implementation (`0xeC222d8AfB8b4E78C418ebc1ab2cA181f19FbadC`) from their verified sources, the Roles Modifier, SetTxNonceGuard, and Safe v1.4.1 for the DelayOwnerSafe. The Delay is DelayTarget, the vendored Delay v1.0.1 that the Roles scenes use. |

### Generalization 3 — Governance settings cannot be changed other than by the ownerless safe, proposer safe, or DelayModOwner safe

Each contract has its own section: its settings functions, then its tables. Every table is titled `Contract · Table N`, so it is clear which contract it belongs to. Where a contract's flow splits into branches, each branch gets its own table, numbered 2a, 2b, …, and its rows carry on the step numbers from the split with the table's letter: 4a, 5a, … in Table 2a and 4b, 5b, … in Table 2b.

---

#### Ownerless Safe

Settings functions (GnosisSafe v1.3.0; only the Safe itself can call them):

- `enableModule(address)`
- `disableModule(address,address)`
- `addOwnerWithThreshold(address,uint256)`
- `removeOwner(address,address,uint256)`
- `swapOwner(address,address,address)`
- `changeThreshold(uint256)`
- `setGuard(address)`
- `setFallbackHandler(address)`
- `setup(address[],uint256,address,bytes,address,address,uint256,address)`, one-time initializer: always reverts once the Safe is set up

**Conclusion:** There are only 3 paths to changing the Ownerless Safe's settings. The Ownerless Safe's signers can execute settings changes as owners (Table 1). The DelayOwnerSafe's signers can modify the Delay Modifier, the Ownerless Safe's only enabled module, as the Delay Modifier's owner (Table 2a). The Proposer Safe's signers can propose settings changes through the Delay Modifier, as its enabled module (Table 2b).

##### Ownerless Safe · Table 1 - The Ownerless Safe's owners can modify the Ownerless Safe's settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.OwnerlessSafe.1 | Only Modules or Owners can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. The settings functions can only be called by the Safe itself, so only Modules or Owners can successfully execute them, by having the Safe call itself. | Same as G1.2. |
| G3.OwnerlessSafe.2 | Delay Module is the only enabled module on OwnerlessSafe. | Same as G1.4. |
| G3.OwnerlessSafe.3 | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5. |

After G3.OwnerlessSafe.3 the branch splits in two at the Ownerless Safe's only enabled module the Delay Modifier: the Delay Modifier's owner, and the Delay Modifier's modules. 


##### Ownerless Safe · Table 2a — Conclusion: The owner of the Delay Modifier, the DelayOwnerSafe, can modify the Delay Modifier's settings. It can act only through its signers. None of its enabled modules, are allowed to submit changes to the Ownerless Safe's settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.OwnerlessSafe.4a | DelayMod only has one owner, which is the DelayOwnerSafe. | Same as G2.3. |
| G3.OwnerlessSafe.5a | Only Modules or Owners can interact with DelayOwnerSafe, except fallback and receive, which anyone can call. | Same as G2.4. |
| G3.OwnerlessSafe.6a | DelayOwnerSafe fallback handler is `address(0)`. | Same as G2.5. |
| G3.OwnerlessSafe.7a | DelayOwnerSafe only has one enabled module, the Roles Modifier | Same as G2.6. |
| G3.OwnerlessSafe.8a | Only Modules with assignedRoles or Owners can interact with Roles Modifier. | Same as G2.7. |
| G3.OwnerlessSafe.9a | Roles Modifier only has one owner, which is the Ownerless Safe. | — |
| G3.OwnerlessSafe.10a | The Governor  is the only module of the Roles Modifier with an assignedRole. | Same as G2.8. |
| G3.OwnerlessSafe.11a | The Governor  is assigned only role 1, its defaultRole. | Same as G2.9. |
| G3.OwnerlessSafe.12a | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | Same as G2.10. |


##### Ownerless Safe · Table 2b — Conclusion: The only enabled module of the Delay Modifier, the Proposer Safe, can propose transactions. Each one waits out the cooldown and can be vetoed.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.OwnerlessSafe.4b | ProposerSafe is the only module on the Delay Mod | Same as G1.6. |
| G3.OwnerlessSafe.5b | Only Modules or Owners can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.7. |
| G3.OwnerlessSafe.6b | ProposerSafe fallback handler is address(0). | Same as G1.8. |
| G3.OwnerlessSafe.7b | ProposerSafe has no modules. | Same as G1.9. |
| G3.OwnerlessSafe.8b | The Proposer Safe, can propose a transaction that modifies the Ownerless Safe. It executes on the Ownerless Safe once the cooldown has passed, if it hasn't expired, the system isn't paused, and it hasn't been vetoed. | — |

---

#### Delay Modifier

Settings functions (zodiac-modifier-delay v1.0.1; `onlyOwner`):

- `setTxCooldown(uint256)`
- `setTxExpiration(uint256)`
- `setAvatar(address)`
- `setTarget(address)`
- `enableModule(address)`
- `disableModule(address,address)`
- `setGuard(address)`
- `transferOwnership(address)`
- `renounceOwnership()`
- `setUp(bytes)`, one-time initializer: always reverts after deployment

**Conclusion:** There are only 2 paths to changing the Delay Modifier's settings. The DelayOwnerSafe's signers can execute settings changes as owners (Table 1). The Ownerless Safe's signers (directly) and the Proposer Safe's signers (through the delay module) can modify the Roles Modifier, the DelayOwnerSafe's only enabled module (Table 2a).

##### Delay Modifier · Table 1 - Conclusion:  The owner of the Delay Modifier, the DelayOwnerSafe, can change the Delay Modifier's settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayModifier.1 | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. The settings functions are owner-only: only the Owner can successfully execute them. | Same as G1.5. |
| G3.DelayModifier.2 | DelayMod only has one owner, which is the DelayOwnerSafe. | Same as G2.3. |
| G3.DelayModifier.3 | Only Modules or Owners can interact with DelayOwnerSafe. | Same as G2.4. |
| G3.DelayModifier.4 | DelayOwnerSafe fallback handler is `address(0)`. | Same as G2.5. |
| G3.DelayModifier.5 | DelayOwnerSafe only has one module, the Roles Modifier | Same as G2.6. |
| G3.DelayModifier.6 | Only Modules with assignedRoles or Owners can interact with Roles Modifier. | Same as G2.7. |

After G3.DelayModifier.6 the branch splits in two at the DelayOwnerSafe's only enabled module the Roles Modifier: the Roles Modifier's owner, and the Roles Modifier's modules.


##### Delay Modifier · Table 2a —  Conclusion: The owner of the Roles Modifier, the Ownerless Safe, can modify the Roles Modifier's settings. The Ownerless Safe's signers can directly execute changes, while the Proposer Safe's signers can propose through the Ownerless Safe's only enabled module, thte Delay Modifier.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayModifier.7a | Roles Modifier only has one owner, which is the Ownerless Safe. | Same as G3.RolesModifier.2a. |
| G3.DelayModifier.8a | Only Modules or Owners can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.2. |
| G3.DelayModifier.9a | OwnerlessSafe fallback handler is `address(0)`. | Same as G1.3. |
| G3.DelayModifier.10a | Delay Module is the only enabled module on OwnerlessSafe. | Same as G1.4. |
| G3.DelayModifier.11a | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5. |
| G3.DelayModifier.12a | ProposerSafe is the only module on the Delay Mod | Same as G1.6. |
| G3.DelayModifier.13a | Only Modules or Owners can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.7. |
| G3.DelayModifier.14a | ProposerSafe fallback handler is set to zero address. | Same as G1.8. |
| G3.DelayModifier.15a | ProposerSafe has no enabled modules. | Same as G1.9. |


##### Delay Modifier · Table 2b — Conclusion: The only enabled module of the Roles Modifier, the Governor, can only veto, so it cannot change the Roles Modifier's settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayModifier.7b | The Governor  is the only module of the Roles Modifier with an assignedRole. | Same as G2.8. |
| G3.DelayModifier.8b | The Governor  is assigned only role 1, its defaultRole. | Same as G2.9. |
| G3.DelayModifier.9b | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | Same as G2.10. |

---

#### Proposer Safe

Settings functions (GnosisSafe v1.3.0; only the Safe itself can call them):

- `enableModule(address)`
- `disableModule(address,address)`
- `addOwnerWithThreshold(address,uint256)`
- `removeOwner(address,address,uint256)`
- `swapOwner(address,address,address)`
- `changeThreshold(uint256)`
- `setGuard(address)`
- `setFallbackHandler(address)`
- `setup(address[],uint256,address,bytes,address,address,uint256,address)`, one-time initializer: always reverts once the Safe is set up

**Conclusion:** There is only 1 path to changing the Proposer Safe's settings. The Proposer Safe's signers can execute settings changes as owners (Table 1).

##### Proposer Safe · Table 1 — Conclusion: Only the Proposer Safe's owners can change its settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.ProposerSafe.1 | Only Modules or Owners can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. The settings functions can only be called by the Safe itself, so only Modules or Owners can successfully execute them, by having the Safe call itself. | Same as G1.7. |
| G3.ProposerSafe.2 | ProposerSafe fallback handler is address(0). | Same as G1.8. |
| G3.ProposerSafe.3 | ProposerSafe has no modules. | Same as G1.9. |

---

#### DelayOwnerSafe

Settings functions (Safe v1.4.1; only the Safe itself can call them):

- `enableModule(address)`
- `disableModule(address,address)`
- `addOwnerWithThreshold(address,uint256)`
- `removeOwner(address,address,uint256)`
- `swapOwner(address,address,address)`
- `changeThreshold(uint256)`
- `setGuard(address)`
- `setFallbackHandler(address)`
- `setup(address[],uint256,address,bytes,address,address,uint256,address)`, one-time initializer: always reverts once the Safe is set up

**Conclusion:** There are only 2 paths to changing DelayOwnerSafe's settings. The DelayOwnerSafe's signers can execute settings changes as owners (Table 1). The Ownerless Safe's signers (directly) and the Proposer Safe's signers (through delay module), can modify the DelayOwnerSafe's only enabled module the Roles Modifier (Table 2a).

##### DelayOwnerSafe · Table 1 — Shared path, up to the Roles Modifier. Conclusion: The DelayOwnerSafe's settings can only be changed by its owners or through the Roles Modifier, by its owner (Table 2a) or its modules (Table 2b).

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayOwnerSafe.1 | Only Modules or Owners can interact with DelayOwnerSafe, except fallback and receive, which anyone can call. The settings functions can only be called by the Safe itself, so only Modules or Owners can successfully execute them, by having the Safe call itself. | Same as G2.4. |
| G3.DelayOwnerSafe.2 | DelayOwnerSafe only has one module, the Roles Modifier | Same as G2.6. |
| G3.DelayOwnerSafe.3 | Only Modules with assignedRoles or Owners can interact with Roles Modifier. | Same as G2.7. |

After G3.DelayOwnerSafe.3 the branch splits in two: the Roles Modifier's owner, and the Roles Modifier's modules.


##### DelayOwnerSafe · Table 2a — Ownerless Safe branch (the Roles Modifier's owner). Conclusion: The owner of the Roles Modifier, the Ownerless Safe, can modify the Roles Modifier's settings, so the Ownerless Safe's signers (directly) and the Proposer Safe's signers (through the delay module) can change the DelayOwnerSafe's settings through it.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayOwnerSafe.4a | Roles Modifier only has one owner, which is the Ownerless Safe. | Same as G3.RolesModifier.2a. |
| G3.DelayOwnerSafe.5a | Only Modules or Owners can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.2. |
| G3.DelayOwnerSafe.6a | OwnerlessSafe fallback handler is `address(0)`. | Same as G1.3. |
| G3.DelayOwnerSafe.7a | Delay Module is the only enabled module on OwnerlessSafe. | Same as G1.4. |
| G3.DelayOwnerSafe.8a | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5. |
| G3.DelayOwnerSafe.9a | DelayMod only has one owner, which is the DelayOwnerSafe. | Same as G2.3. |
| G3.DelayOwnerSafe.10a | ProposerSafe is the only module on the Delay Mod | Same as G1.6. |
| G3.DelayOwnerSafe.11a | Only Modules or Owners can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.7. |
| G3.DelayOwnerSafe.12a | ProposerSafe fallback handler is set to zero address. | Same as G1.8. |
| G3.DelayOwnerSafe.13a | ProposerSafe has no enabled modules. | Same as G1.9. |


##### DelayOwnerSafe · Table 2b — Governor branch (the Roles Modifier's modules). Conclusion: The only enabled module of the Roles Modifier, the Governor, can only veto, so it cannot change the DelayOwnerSafe's settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayOwnerSafe.4b | The Governor  is the only module of the Roles Modifier with an assignedRole. | Same as G2.8. |
| G3.DelayOwnerSafe.5b | The Governor  is assigned only role 1, its defaultRole. | Same as G2.9. |
| G3.DelayOwnerSafe.6b | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | Same as G2.10. |

---

#### Roles Modifier

Settings functions (Roles v1.0.0; `onlyOwner`):

- `setMultisend(address)`
- `allowTarget(uint16,address,ExecutionOptions)`
- `revokeTarget(uint16,address)`
- `scopeTarget(uint16,address)`
- `scopeAllowFunction(uint16,address,bytes4,ExecutionOptions)`
- `scopeRevokeFunction(uint16,address,bytes4)`
- `scopeFunction(uint16,address,bytes4,bool[],ParameterType[],Comparison[],bytes[],ExecutionOptions)`
- `scopeFunctionExecutionOptions(uint16,address,bytes4,ExecutionOptions)`
- `scopeParameter(uint16,address,bytes4,uint256,ParameterType,Comparison,bytes)`
- `scopeParameterAsOneOf(uint16,address,bytes4,uint256,ParameterType,bytes[])`
- `unscopeParameter(uint16,address,bytes4,uint8)`
- `assignRoles(address,uint16[],bool[])`
- `setDefaultRole(address,uint16)`
- `setAvatar(address)`
- `setTarget(address)`
- `enableModule(address)`
- `disableModule(address,address)`
- `setGuard(address)`
- `transferOwnership(address)`
- `renounceOwnership()`
- `setUp(bytes)`, one-time initializer: reverts once initialized

**Conclusion:** There are only 3 paths to changing the Roles Modifier's settings. The Ownerless Safe's signers can directly execute as owners. The Ownerless safe can also execute through its only enabled module, the Delay Modifier, who canonly receives proposals from the Proposer Safe. The DelayOwnerSafe's signers can also modify the Delay Modifier settings.

##### Roles Modifier · Table 1 — Conclusion: Only the Roles Modifier's owner or enabled modules may interact with the Roles Modifier.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.RolesModifier.1 | Only Modules with assignedRoles or Owners can interact with Roles Modifier. The settings functions are owner-only: only the Owner can successfully execute them. | Same as G2.7. |

After G3.RolesModifier.1 the branch splits in two: the Roles Modifier's owner, and the Roles Modifier's modules.


##### Roles Modifier · Table 2a — Conclusion: The owner of the Roles Modifier, the Ownerless Safe, can modify the Roles Modifier's settings. The Ownerless Safe can execute directly through its signers or through its only enabled module the Delay Modifier. They Delay Modifier, unless its settings are modified by the signers of the DelayOwnerSafe, can receive proposals only from the Proposer Safe.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.RolesModifier.2a | Roles Modifier only has one owner, which is the Ownerless Safe. | — |
| G3.RolesModifier.3a | Only Modules or Owners can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.2. |
| G3.RolesModifier.4a | OwnerlessSafe fallback handler is `address(0)`. | Same as G1.3. |
| G3.RolesModifier.5a | Delay Module is the only enabled module on OwnerlessSafe. | Same as G1.4. |
| G3.RolesModifier.6a | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5. |
| G3.RolesModifier.7a | DelayMod only has one owner, which is the DelayOwnerSafe. | Same as G2.3. |
| G3.RolesModifier.8a | ProposerSafe is the only module on the Delay Mod | Same as G1.6. |
| G3.RolesModifier.9a | Only Modules or Owners can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.7. |
| G3.RolesModifier.10a | ProposerSafe has no fallback handler. | Same as G1.8. |
| G3.RolesModifier.11a | ProposerSafe has no modules. | Same as G1.9. |


##### Roles Modifier · Table 2b - Conclusion: The only enabled module of the Roles Modifier, the Governor, can only veto.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.RolesModifier.2b | The Governor  is the only module of the Roles Modifier with an assignedRole. | Same as G2.8. |
| G3.RolesModifier.3b | The Governor  is assigned only role 1, its defaultRole. | Same as G2.9. |
| G3.RolesModifier.4b | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | Same as G2.10. |

---

#### Governor

Settings functions: none. TermFinanceGovernor (OpenZeppelin Governor v5.0.2, `GovernorVotes` + `GovernorCountingSimple`) is non-upgradeable. `votingDelay`, `votingPeriod`, `proposalThreshold` and the quorum fraction are constants compiled into its bytecode, and the token is immutable. `GovernorSettings`, `GovernorVotesQuorumFraction` and `GovernorTimelockControl` are not inherited, so there is no setter.

**Conclusion:** There are no paths to changing the Governor's settings (Table 1).

##### Governor · Table 1 — No settings functions. Conclusion: Nobody can change the Governor's settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.Governor.1 | Governor configuration changes are not possible. | — |
