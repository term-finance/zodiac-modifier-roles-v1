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
| G1.1 | Only the Ownerless Safe holds the DEVOPS_ROLE required for protocol changes. | **On-chain — the Ownerless Safe holds DEVOPS_ROLE on each core contract:** ✅ at block 26080131, `DEVOPS_ROLE` (`keccak256("DEVOPS_ROLE")` = `0x793a6c9b7e0a9549c74edc2f9ae0dc50903dfaa9a56fb0116b27a8c71de3e2c6`) is held by the Ownerless Safe (`0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03`) on:<br>• TermController (`0xd902EBb8AEb832643af38f43d466a6155cD8Bd5A`), read by `hasRole`<br>• TermEventEmitter (`0xf021B31282a60528B2F47D07Ce353da870be78b3`), read by `hasRole`<br>• TermPriceConsumerV3 (`0x13Ca4ddB295d621761057D682a1c7b5f5D7Bba4c`), read by `hasRole`<br>• TermRepoDeployerFactory (`0x44058C32B154A516F3b9DE2413e6cb938F93c3B4`), read by `hasRole`<br>• TermInitializer (`0x3B668F408293e9a5700D6Eeae78E1f945CF501eF`), read by `hasRole`<br>• TermDiamond (`0xb4B1de03F229220eDbBB31A224b2a004b3c3e47f`), read by storage slot `0x5fdec70149aea3337a70dda36f71a4911e25e15ef0e98916a983b6ff4c6aa5a4` = 1<br><br>**On-chain — it has only ever been granted to the Ownerless Safe:** ✅ Blockscout's full log history for each contract holds exactly one event naming `DEVOPS_ROLE`: a `RoleGranted` to the Ownerless Safe, emitted in the contract's own creation transaction. There is no `RoleRevoked`, no `RoleAdminChanged`, and no grant to any other address.<br>• TermController: block 25188635, tx `0xdeea44228ef14d20a66a02e0a3d84907bcd854aa0f352a5ad8233b48b23f7f15`<br>• TermEventEmitter: block 25188643, tx `0x15c3af7845f086fca8a069ea755f92f4613ae716978aa100089788d98a68d29e`<br>• TermPriceConsumerV3: block 25188652, tx `0x7b960b5c31408ac8cf6eb77766c2c8f747bf74b9f2ec1fd98f1d66999a3d6063`<br>• TermRepoDeployerFactory: block 25188657, tx `0x22c72baf2cf6a6ad808e874ca9d75190592059fa9e0591451ea738147394f8f5`<br>• TermInitializer: block 25555701, tx `0xec1c9e2935569e769123e7a05f6d1f5fc2c1ba7aa2a7b4013d799dfee76885d7`<br>• TermDiamond: block 25188499, tx `0xe70a739ab7ff78a6b8ae8beefd002c7ee4a87d8c41b6ec594ae45eba87412788`<br><br>**On-chain — nobody can grant it with `grantRole`:** ✅ on the five AccessControl contracts, `getRoleAdmin(DEVOPS_ROLE)` is `DEFAULT_ADMIN_ROLE` (`0x00`). No production contract grants `DEFAULT_ADMIN_ROLE` or calls `_setRoleAdmin`, and no `RoleGranted` for `DEFAULT_ADMIN_ROLE` appears in any of the six histories, so no address can call `grantRole(DEVOPS_ROLE, …)`. On the TermDiamond, `grantRole` is not registered at all: its roles are set once by `initDiamond`, or by a new facet added through `diamondCut`, which is itself `DEVOPS_ROLE`-only. |
| G1.2 | Only Modules or Owners can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. | **FV — every entry point to the Safe is enumerated below:** SE-1 `safeEntryPointsAreAllAccountedFor` ✅ passes. Safe v1.3.0 has no write functions besides these seventeen entry points (the Prover checks `fallback` and `receive` as one entry), and any other call lands in `fallback`. Grouped by who can call each one:<br><br>*module gated entry points:*<br>• `execTransactionFromModule`<br>• `execTransactionFromModuleReturnData`<br><br>*owner gated entry points:*<br>• `execTransaction`<br>• `approveHash`<br><br>*Self calls — only modules and owners can reach these:*<br>• `enableModule`<br>• `disableModule`<br>• `addOwnerWithThreshold`<br>• `removeOwner`<br>• `swapOwner`<br>• `changeThreshold`<br>• `setGuard`<br>• `setFallbackHandler`<br><br>*Non-interactions — these always revert, so nothing they do stands:*<br>• `setup`<br>• `requiredTxGas`<br>• `simulateAndRevert`<br><br>*Open to anyone:*<br>• `fallback`<br>• `receive`<br><br>**FV — module-only entry points can make the Safe execute to any destination:** `execTransactionFromModule`, `execTransactionFromModuleReturnData`.<br>• SE-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can successfully call `execTransactionFromModule` or `execTransactionFromModuleReturnData`.<br>• SE-4 `enabledModuleCanMakeTheSafeAct` ✅ passes: an enabled module can call `execTransactionFromModule` and `execTransactionFromModuleReturnData` directly, with no owner signatures, and the Safe makes an outgoing call or delegatecall.<br><br>**FV — owner-only entry points can make the Safe execute to any destination:** `execTransaction`, `approveHash`.<br>• SE-5 `execTransactionRunsOnlyAfterTheSignatureCheck` ✅ passes: `execTransaction` only runs once the signature threshold check has passed for that exact transaction.<br>• SE-12 `eachSignatureAcceptsANewApprovingOwner` ✅ passes: every signature the check accepts is a different owner who approved it. With SE-5, the Safe acts through `execTransaction` only when as many different owners as the threshold have approved.<br>• SE-8 `onlyOwnersCanApproveHashes` ✅ passes: `approveHash` only records an owner's own approval, which then counts as that owner's signature in `execTransaction`.<br>• SE-6 `ownersCanMakeTheSafeAct` ✅ passes: once the threshold is passed, `execTransaction` succeeds and the Safe acts, for any threshold and any number of owners.<br><br>**FV — settings functions are only reached through the module-only or owner-only points:**<br><br>• SE-7 `settingsOnlyChangeWhenTheSafeCallsItself` ✅ passes: these only change a setting when the caller is the Safe itself.<br>• SC-4 `settingsOnlyChangeThroughAModuleOrOwners` ✅ passes: over every write function, `fallback` included, a setting only changes through an enabled module's `execTransactionFromModule` or `execTransactionFromModuleReturnData`, or through `execTransaction`. A fallback handler is checked as if it were the Safe itself, so it cannot reach these functions even then.<br>• SC-1 `moduleCanChangeSettings`, SC-2 `moduleCanChangeSettingsWithReturnData` ✅ pass: for each function above, a module's `execTransactionFromModule`, and likewise its `execTransactionFromModuleReturnData`, addressed to the Safe with a call to that function, succeeds and changes a setting.<br>• SC-3 `ownersCanChangeSettings` ✅ passes: the same through `execTransaction`, once the threshold is passed.<br><br>**FV — setup is not a callable function after deploy:** SE-9 `setupAlwaysRevertsAfterSetup` ✅ passes. Once the Safe is set up, `setup` always reverts, so nobody can re-run it to replace the owners, threshold, modules or handler.<br><br>**FV — `requiredTxGas` and `simulateAndRevert` always revert:** SE-10 `requiredTxGasAlwaysReverts`, SE-11 `simulateAndRevertAlwaysReverts` ✅ pass. Anyone can call them, and they do execute a call (`requiredTxGas`) or delegatecall (`simulateAndRevert`), but they always revert afterwards, so nothing they do stands.<br><br>**FV — Any address can call any unsupported Safe function to initiate `fallback`, which can only make the Safe execute to Fallback Handler address if set to nonzero address:** <br>• SE-14 `fallbackOnlyCallsItsHandler` ✅ passes: with a handler set, `fallback` only makes a plain call, with no ETH, to the handler. It never delegatecalls, so the handler's code runs as its own contract, not as the Safe, and cannot write the Safe's storage. Assumes the handler is not the Safe itself: v1.3.0 allows that (v1.4.0 forbids it, GS400), and then `fallback` calls back into the Safe as the Safe. That case is covered by SE-16. <br>• SE-15 `fallbackHandlerCallsComeFromTheHandler` ✅ passes: once `fallback` calls its handler, every call has `msg.sender=handler`.  Assumes the handler is not the Safe itself; that case is SE-16. <br>• SE-16 `selfHandlerFallbackChangesNothing` ✅ passes: with the Safe set as its own handler, `fallback` leaves the Safe's storage exactly as it was, and when it succeeds the Safe called nothing but itself, sent no ETH and made no delegatecall.  <br>• SE-13 `fallbackMakesNoCallWithoutAHandler` ✅ passes: with no handler set (the zero address), `fallback` makes no call or delegatecall at all.<br><br>**FV — Any address can trigger `receive` by sending Eth without calldata and it does nothing but  emits `SafeReceived`:**<br>• SE-17 `receiveOnlyEmitsSafeReceived` ✅ passes: whenever `receive` runs, it does nothing beyond the event. It emits exactly one log, `SafeReceived`, naming the caller as sender. It makes no call of any kind (call, delegatecall, staticcall or callcode) and writes no storage.<br>• SE-18 `receiveCanRun` ✅ passes: some call to the Safe succeeds and emits `SafeReceived`, so SE-17 is not vacuous. |
| G1.3 | OwnerlessSafe fallback handler is `address(0)`. | — |
| G1.4 | Delay Module is the only enabled module on OwnerlessSafe. | — |
| G1.5 | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | **FV — every entry point to the Delay Modifier is enumerated below:** DM-13 `delayWriteFunctionsAreTheKnownFifteen` ✅ passes. The Delay has no fallback and exactly fifteen write functions, each covered below:<br>• `setTxCooldown` — owner only (DM-8)<br>• `setTxExpiration` — owner only (DM-8)<br>• `setTxNonce` — owner only (DM-8)<br>• `setAvatar` — owner only (DM-8)<br>• `setTarget` — owner only (DM-8)<br>• `enableModule` — owner only (DM-8)<br>• `disableModule` — owner only (DM-8)<br>• `setGuard` — owner only (DM-8)<br>• `transferOwnership` — owner only (DM-8)<br>• `renounceOwnership` — owner only (DM-8)<br>• `execTransactionFromModule` — modules only (DM-4)<br>• `execTransactionFromModuleReturnData` — modules only (DM-4)<br>• `executeNextTx` — anyone (DM-11)<br>• `skipExpired` — anyone (DM-12)<br>• `setUp` — nobody after deployment (DM-1)<br><br>**FV — owner-only settings:** DM-8 `atMostOneCallerPassesOnlyOwner` ✅ passes. Only the owner can call the Delay's ten settings functions. There can only be one owner at a time.<br><br>**FV — module-only queueing:** DM-4 `queueOnlyGrowsThroughEnabledModules` ✅ passes. Only an enabled module can add a transaction to the queue.<br><br>**FV — setup is closed:** DM-1 `setUpAlwaysRevertsAfterDeployment` ✅ passes. Nobody can re-run the Delay's setup after deployment.<br><br>**FV — the two exceptions are open:** DM-11 `anyoneCanExecuteNextTx`, DM-12 `anyoneCanSkipExpired` ✅ pass. An address that is neither the owner nor a module can execute a queued transaction and skip an expired one.<br><br>**FV — every other function, checked all at once:** DM-14 `onlyModulesOrOwnerCanCallDelay` ✅ passes. For every write function except `executeNextTx`, `skipExpired` and `setUp`, a call that succeeds came from the owner or an enabled module. It does not rely on a list of names, so it also covers any function added later. |
| G1.6 | ProposerSafe is the only enabled module on the Delay Mod | **On-chain — the Delay's module list contains only the Proposer Safe:** ✅ asked for all of its modules, the Delay (`0x0C19d8A404079d71E5CA3e32fE3f758Ab543ACdf`) returns just one, the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`), and reports that the list ends there (`getModulesPaginated`, block 26080101).<br><br>**On-chain — the Delay's storage holds only the Proposer Safe as a module:** ✅ read directly from storage rather than through the Delay's own functions, the module list starts at the Proposer Safe and the Proposer Safe points back to the start, so it is the only entry (`modules`, storage slot 104, block 26080101). |
| G1.7 | Only Modules or Owners can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.2: the Proposer Safe runs the same GnosisSafe v1.3.0 code as the Ownerless Safe. |
| G1.8 | ProposerSafe fallback handler is address(0). | **On-chain:** ✅ the fallback handler slot (`0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5`, `FallbackManager.sol:12`) on the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`) is zero at block 26056133. |
| G1.9 | ProposerSafe has no enabled modules. | **On-chain:** ✅ `getModulesPaginated` on the Proposer Safe (`0xd5E12854A3Dba99deF295A7635D3Ba16427d2A28`) returns an empty list at block 26050570. |
| G1.10 | ProposerSafe can propose a transaction to Delay Modifier that is executed on the Ownerless Safe once the cooldown has passed, if it hasn't expired, the system isn't paused, and it hasn't been vetoed. | **FV — the Proposer Safe can propose to the Delay Modifier as a module:** DM-5 `enabledModuleCanQueue` ✅ passes. Any enabled module can queue a transaction on the Delay Modifier: its call to `execTransactionFromModule`, with any destination, value, calldata and operation, succeeds and adds the transaction to the queue. The Proposer Safe is the Delay Modifier's only enabled module (G1.6).<br><br>**FV — transaction proposed by module executes after cooldown and gefore expiration:** DP-29 `queuedTransactionExecutesAfterCooldown` ✅ passes. Once a module has queued a transaction, and the cooldown has passed, it hasn't expired and the system isn't paused, anyone can execute it and it reaches the Ownerless Safe. Holds for every transaction, assuming the Ownerless Safe accepts the call.<br><br>**FV — transaction cannot execute too early or too late:** DP-30 `executeNextTxRevertsDuringCooldown`, DP-31 `executeNextTxRevertsAfterExpiration` ✅ pass. It cannot run before the cooldown has passed or after it has expired.<br><br>**FV — transaction cannot be executed while paused:** DP-18 `pausedBlocksExecuteNextTx` ✅ passes. It cannot run while PauseGuard is paused.<br><br>**FV — Only the transaction at the current txNonce executes:** DP-28 `executeNextTxConsumesOnlyTheEntryAtTxNonce` ✅ passes. What executes is exactly the transaction that was queued.<br><br>**FV — transaction cannot be executed once vetoed:** DP-32 `vetoedTransactionCannotExecute`, DP-33 `entryPassedByTxNonceNeverExecutes` ✅ pass. Once `txNonce` has moved past a proposal's nonce, it can never be executed. A proposal is vetoed by moving `txNonce` past it with `setTxNonce`. |

### Generalization 2 — Only TERM token holders and Term multisig holders may veto Delay modifier transactions, holding the governance settings constant

| # | Statement | Evidence |
| --- | --- | --- |
| G2.1 | Veto power (`Delay.setTxNonce(uint256)`) is held exclusively by the owner of the DelayMod. | **FV — `setTxNonce` is owner-only:** DM-8 `atMostOneCallerPassesOnlyOwner` ✅ passes. `setTxNonce` is one of the Delay's ten `onlyOwner` functions: only the address recorded as the owner can call it successfully, and no two different callers can both get through from the same state. |
| G2.2 | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5 |
| G2.3 | DelayMod only has one owner, which is the DelayOwnerSafe. | **FV — one owner:** DM-8 `atMostOneCallerPassesOnlyOwner` ✅ passes. The Delay has only one owner: at any moment, only one address can change the Delay's settings, and it is the address recorded as the owner. No second address can ever do it alongside it.<br><br>**On-chain — owner is DelayOwnerSafe:** ⏳ pending migration. `owner()` on the Delay must return `0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3`. At block 26049693 it returns `0x405b47354CF06A25DE1DDb35EC65F03939E2e8D2` (old Roles). |
| G2.4 | Only Modules or Owners can interact with DelayOwnerSafe, except fallback and receive, which anyone can call. | The same rules as G1.2, run against Safe v1.4.1 through the `Safe-v141-*` confs.  <br><br>**FV — every entry point to the Safe is enumerated below:** SE141-1 `safeEntryPointsAreAllAccountedFor` ✅ passes. Safe v1.4.1 has no write functions besides these sixteen entry points (the Prover checks `fallback` and `receive` as one entry), and any other call lands in `fallback`. These are G1.2's seventeen minus `requiredTxGas`, which Safe removed in v1.4.0. Grouped by who can call each one:<br><br>*module gated entry points:*<br>• `execTransactionFromModule`<br>• `execTransactionFromModuleReturnData`<br><br>*owner gated entry points:*<br>• `execTransaction`<br>• `approveHash`<br><br>*Self calls — only modules and owners can reach these:*<br>• `enableModule`<br>• `disableModule`<br>• `addOwnerWithThreshold`<br>• `removeOwner`<br>• `swapOwner`<br>• `changeThreshold`<br>• `setGuard`<br>• `setFallbackHandler`<br><br>*Non-interactions — these always revert, so nothing they do stands:*<br>• `setup`<br>• `simulateAndRevert`<br><br>*Open to anyone:*<br>• `fallback`<br>• `receive`<br><br>**FV — module-only entry points can make the Safe execute to any destination:** `execTransactionFromModule`, `execTransactionFromModuleReturnData`.<br>• SE141-3 `onlyEnabledModulesCanCallModuleExec` ✅ passes: only an enabled module can successfully call `execTransactionFromModule` or `execTransactionFromModuleReturnData`.<br>• SE141-4 `enabledModuleCanMakeTheSafeAct` ✅ passes: an enabled module can call `execTransactionFromModule` and `execTransactionFromModuleReturnData` directly, with no owner signatures, and the Safe makes an outgoing call or delegatecall.<br><br>**FV — owner-only entry points can make the Safe execute to any destination:** `execTransaction`, `approveHash`.<br>• SE141-5 `execTransactionRunsOnlyAfterTheSignatureCheck` ✅ passes: `execTransaction` only runs once the signature threshold check has passed for that exact transaction.<br>• SE141-12 `eachSignatureAcceptsANewApprovingOwner` ✅ passes: every signature the check accepts is a different owner who approved it. With SE141-5, the Safe acts through `execTransaction` only when as many different owners as the threshold have approved.<br>• SE141-8 `onlyOwnersCanApproveHashes` ✅ passes: `approveHash` only records an owner's own approval, which then counts as that owner's signature in `execTransaction`.<br>• SE141-6 `ownersCanMakeTheSafeAct` ✅ passes: once the threshold is passed, `execTransaction` succeeds and the Safe acts, for any threshold and any number of owners.<br><br>**FV — settings functions are only reached through the module-only or owner-only points:**<br><br>• SE141-7 `settingsOnlyChangeWhenTheSafeCallsItself` ✅ passes: these only change a setting when the caller is the Safe itself.<br>• SC141-4 `settingsOnlyChangeThroughAModuleOrOwners` ✅ passes: over every write function, `fallback` included, a setting only changes through an enabled module's `execTransactionFromModule` or `execTransactionFromModuleReturnData`, or through `execTransaction`. A fallback handler is checked as if it were the Safe itself, so it cannot reach these functions even then.<br>• SC141-1 `moduleCanChangeSettings`, SC141-2 `moduleCanChangeSettingsWithReturnData` ✅ pass: for each function above, a module's `execTransactionFromModule`, and likewise its `execTransactionFromModuleReturnData`, addressed to the Safe with a call to that function, succeeds and changes a setting.<br>• SC141-3 `ownersCanChangeSettings` ✅ passes: the same through `execTransaction`, once the threshold is passed.<br><br>**FV — setup is not a callable function after deploy:** SE141-9 `setupAlwaysRevertsAfterSetup` ✅ passes. Once the Safe is set up, `setup` always reverts, so nobody can re-run it to replace the owners, threshold, modules or handler.<br><br>**FV — `simulateAndRevert` always reverts:** SE141-11 `simulateAndRevertAlwaysReverts` ✅ passes. Anyone can call it, and it does make a delegatecall, but it always reverts afterwards, so nothing it does stands.<br><br>**FV — Any address can call any unsupported Safe function to initiate `fallback`, which can only make the Safe execute to Fallback Handler address if set to nonzero address:**<br>• SE141-14 `fallbackOnlyCallsItsHandler` ✅ passes: with a handler set, `fallback` only makes a plain call, with no ETH, to the handler. It never delegatecalls, so the handler's code runs as its own contract, not as the Safe, and cannot write the Safe's storage. Assumes the handler is not the Safe itself: v1.4.1's `setFallbackHandler` and `setup` refuse that (GS400), but a delegatecall run through `execTransaction` or a module can still write the handler slot directly. That case is covered by SE141-16. <br>• SE141-15 `fallbackHandlerCallsComeFromTheHandler` ✅ passes: once `fallback` calls its handler, every call the handler makes uses `msg.sender = handler`. Assumes the handler is not the Safe itself; that case is SE141-16. <br>• SE141-16 `selfHandlerFallbackChangesNothing` ✅ passes: with the Safe set as its own handler, `fallback` leaves the Safe's storage exactly as it was, and when it succeeds the Safe called nothing but itself, sent no ETH and made no delegatecall. <br>• SE141-13 `fallbackMakesNoCallWithoutAHandler` ✅ passes: with no handler set (the zero address), `fallback` makes no call or delegatecall at all.<br><br>**FV — Any address can trigger `receive` by sending Eth without calldata and it does nothing but emits `SafeReceived`:**<br>• SE141-17 `receiveOnlyEmitsSafeReceived` ✅ passes: whenever `receive` runs, it does nothing beyond the event. It emits exactly one log, `SafeReceived`, naming the caller as sender. It makes no call of any kind (call, delegatecall, staticcall or callcode) and writes no storage.<br>• SE141-18 `receiveCanRun` ✅ passes: some call to the Safe succeeds and emits `SafeReceived`, so SE141-17 is not vacuous. |
| G2.5 | DelayOwnerSafe fallback handler is `address(0)`. | **On-chain:** ✅ the fallback handler slot (`0x6c9a6c4a39284e37ed1cf53d337577d14212a4870fb976a4366c693b939918d5`, `FallbackManager.sol:14` in Safe v1.4.1) on the DelayOwnerSafe (`0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3`) is address(0) at block 26080124. |
| G2.6 | DelayOwnerSafe only has one enabled module, the Roles Modifier | **On-chain — the DelayOwnerSafe's module list contains only the Roles Modifier:** ✅ asked for all of its modules, the DelayOwnerSafe (`0x2a875746D0c88EBD2bbBfc8F8a773c58c3373ad3`) returns just one, the Roles Modifier (`0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3`), and reports that the list ends there (`getModulesPaginated`, block 26080124).<br><br>**On-chain — the DelayOwnerSafe's storage holds only the Roles Modifier as a module:** ✅ read directly from storage rather than through the Safe's own functions, the module list starts at the Roles Modifier and the Roles Modifier points back to the start, so it is the only entry (`modules`, storage slot 1, block 26080124). |
| G2.7 | Only Modules with assignedRoles or Owners can interact with Roles Modifier. | **FV — every entry point to the Roles Modifier is enumerated below:** RI-14 `rolesWriteFunctionsAreTheKnownTwentyFive` ✅ passes. The Roles Modifier has no `fallback` or `receive` and no write functions besides these twenty-five. Grouped by who can call each one:<br><br>*entry points gated to enabled modules with assigned roles:*<br>• `execTransactionFromModule` (the caller's default role)<br>• `execTransactionFromModuleReturnData` (the caller's default role)<br>• `execTransactionWithRole` (the role the call names)<br>• `execTransactionWithRoleReturnData` (the role the call names)<br><br>*owner gated entry points — the settings functions:*<br>• `setMultisend`<br>• `allowTarget`<br>• `revokeTarget`<br>• `scopeTarget`<br>• `scopeAllowFunction`<br>• `scopeRevokeFunction`<br>• `scopeFunction`<br>• `scopeFunctionExecutionOptions`<br>• `scopeParameter`<br>• `scopeParameterAsOneOf`<br>• `unscopeParameter`<br>• `assignRoles`<br>• `setDefaultRole`<br>• `setAvatar`<br>• `setTarget`<br>• `enableModule`<br>• `disableModule`<br>• `setGuard`<br>• `transferOwnership`<br>• `renounceOwnership`<br><br>*Non-interactions — this always reverts, so nothing it does stands:*<br>• `setUp`<br><br>**FV — execution functions succeed only if caller address is an enabled module AND has been assigned the permissioned role** `execTransactionFromModule`, `execTransactionFromModuleReturnData`, `execTransactionWithRole`, `execTransactionWithRoleReturnData`.<br>• RI-7 `onlyEnabledModulesCanExec` ✅ passes: only enabled modules can call exec functions<br>• RI-8 `moduleWithoutDefaultRoleCannotExecFromModule` ✅ passes: an enabled module that is not a member of its default role cannot execute through `execTransactionFromModule` or `execTransactionFromModuleReturnData`. <br>• RI-9 `moduleWithoutRoleCannotExecTransactionWithRole`, RI-10 `moduleWithoutRoleCannotExecTransactionWithRoleReturnData` ✅ pass: an enabled module that is not a member of the role the call names cannot execute through `execTransactionWithRole` or `execTransactionWithRoleReturnData`.  With RI-8, a module with no assigned role can execute nothing through any of the four.<br>• RI-11 `roleMemberModuleCanExecFromModule`, RI-12 `roleMemberModuleCanExecTransactionWithRole`, RI-13 `roleMemberModuleCanExecTransactionWithRoleReturnData` ✅ pass: an enabled module that is a member of the role the call runs under can successfully call each of the four, so the restriction is not achieved by nothing working.<br><br>**FV — owner-only settings:** RI-2 `rolesConfigOnlyChangesThroughOwner`, RI-3 `ownerOnlyChangesThroughOwnableTransfer`, RI-4 `ownerCanStillReconfigure`, RI-5 `onlyOwnerCanCallRolesSettings`, RI-6 `ownerCanCallEachRolesSetting` ✅ pass. Each of the twenty settings functions only succeeds for the owner (RI-5), and the owner can successfully call each one (RI-6);<br><br>**FV — setup is not a callable function after deploy:** RI-1 `setUpAlwaysRevertsAfterDeployment` ✅ passes. Once the module list is set up, `setUp` always reverts, so nobody can re-run it to replace the owner or the module list.<br><br> |
| G2.8 | The Governor  is the only enabled module of the Roles Modifier with an assignedRole. | **On-chain — the Roles Modifier's module list contains only the Governor:** ✅ asked for all of its modules, the Roles Modifier (`0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3`) returns just one, the Governor (`0x2B715634134220ffeEE9458b4e34E41A41418607`), and reports that the list ends there (`getModulesPaginated`, block 26080168).<br><br>**On-chain — the Roles Modifier's storage holds only the Governor as a module:** ✅ read directly from storage rather than through the Roles Modifier's own functions, the module list starts at the Governor and the Governor points back to the start, so it is the only entry (`modules`, storage slot 104, block 26080168).<br><br>**On-chain — the Governor holds a role:** ✅ the Governor is recorded as a member of role 1 (`roles[1].members`, storage slot 107, block 26080168).<br><br>**On-chain — no other module has ever been added or given a role:** ✅ the Roles Modifier's complete event history, from its creation at block 26042039 to block 26080168, has one `EnabledModule`, for the Governor, and no `DisabledModule`. It has one `AssignRoles`, also for the Governor. |
| G2.9 | The Governor  is assigned only role 1, its defaultRole. | **On-chain — the Governor's default role is 1:** ✅ `defaultRoles` on the Roles Modifier (`0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3`) returns `1` for the Governor (`0x2B715634134220ffeEE9458b4e34E41A41418607`) at block 26080168.<br><br>**On-chain — the Governor is a member of role 1:** ✅ the Governor is recorded as a member of role 1 (`roles[1].members`, storage slot 107, block 26080168).<br><br>**On-chain — the Governor has only ever been given role 1:** ✅ a module's roles can only change through `assignRoles` (`Roles.sol:290`), which always emits `AssignRoles`. The Roles Modifier's complete event history, from its creation at block 26042039 to block 26080168, has exactly one `AssignRoles`: the Governor, role 1, member (tx `0x1d4ec5029b9c66cff2c92bc8be16196bba4d4484caaa74488bdcc61616fb186a`). It also has exactly one `SetDefaultRole`: the Governor, role 1 (tx `0xf01e95980c86dc59667c78094ba1f7a65c744b5214029ef70e721ec8c340a928`). |
| G2.10 | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | **FV — role 1 alone restricts member module executions to vetos (Delay.setTxNonce(uint256)), except through MultiSend:** RC-1 `roleConfigLimitsExecTransactionWithRoleToDelaySetTxNonce`, RC-2 `roleConfigLimitsExecTransactionFromModuleToDelaySetTxNonce`, RC-3 `roleConfigLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, RC-4 `roleConfigLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` ✅ pass. With no setTxNonceGuard, role 1's scope configuration admits only `setTxNonce(uint256)` on the Delay, with zero value and as a plain `Call`, on all four entry points, provided the destination is not the MultiSend address.<br>• RC-5 `nonMemberExecTransactionWithRoleAlwaysReverts` ✅ passes: a caller that is not a member of the role it names can execute nothing at all. Stated on `execTransactionWithRole`.<br>• RC-7 `withoutSetTxNonceGuardMultisendTargetEscapesRoleConfig` ✅ passes: without the guard, a transaction addressed to the MultiSend address completes although it is not the Delay. This is the gap the guard closes (RS-6).<br><br>**FV — setTxNonceGuard alone restricts all Roles Modifier executions to vetos `Delay.setTxNonce(uint256)`:** RS-1 `setTxNonceGuardLimitsExecTransactionWithRoleToDelaySetTxNonce`, RS-2 `setTxNonceGuardLimitsExecTransactionFromModuleToDelaySetTxNonce`, RS-3 `setTxNonceGuardLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce`, RS-4 `setTxNonceGuardLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce` ✅ pass. With SetTxNonceGuard installed, every execution on all four entry points is `setTxNonce(uint256)` on the Delay, with zero value and as a plain `Call`, for any caller, any role and any Roles configuration.<br>• RS-5 `setTxNonceGuardLimitsToDelaySetTxNonceUnderMaximallyPermissiveRoles` ✅ passes: the same holds under the worst-case configuration, blanket `Clearance.Target` with `ExecutionOptions.Both`.<br>• RS-6 `setTxNonceGuardRejectsMultisendTarget` ✅ passes: a transaction addressed to the MultiSend address always reverts.<br>• RS-7 `withoutSetTxNonceGuardPermissiveRolesAllowNonDelayCall` ✅ passes: with no guard and the same permissive configuration, a call to something other than the Delay succeeds, so it is the guard that imposes the restriction.<br><br>**FV — With role 1 and SetTxNonceGuard applied together, the Governor can only veto:** RG-2 `governorExecTransactionWithRoleLimitedToDelaySetTxNonce`, RG-3 `governorExecTransactionFromModuleLimitedToDelaySetTxNonce`, RG-4 `governorExecTransactionWithRoleReturnDataLimitedToDelaySetTxNonce`, RG-5 `governorExecTransactionFromModuleReturnDataLimitedToDelaySetTxNonce` ✅ pass. Every call the Governor completes through the Roles Modifier is `setTxNonce(uint256)` on the Delay, with zero value and as a plain `Call`, on all four execution entry points: `execTransactionWithRole`, `execTransactionFromModule`, `execTransactionWithRoleReturnData` and `execTransactionFromModuleReturnData`. Assumes SetTxNonceGuard is installed and pointed at the Delay, and the Governor is an enabled module, a member of role 1 only, with default role 1 (G2.9).<br><br>**FV — Governor successfully vetoes:** RG-6 `governorCanStillCallDelaySetTxNonce` ✅ passes. Under the same setup, the Governor's `setTxNonce` call really does go through, so the restriction is not achieved by nothing working.<br><br>|
| G2.11 | TERM Token holders can create a Governor proposal to veto, and once it passes vote, successfully execute. | **FV — TERM holders can propose the veto:** GV-1 `holderAboveThresholdCanProposeVeto` ✅ passes: any address with at least 1,000 TERM of votes at `clock() − 1` can propose the veto, the one-action proposal calling the Roles Modifier with `execTransactionWithRole(Delay, 0, setTxNonce(n), Call, 1, true)`, for any `n` and any description of up to 1,024 bytes that `propose` accepts from it, unless that exact proposal already exists. The proposal records the caller as its proposer, and its vote opens at once and runs for 22 hours.<br><br>**FV — once it passes, the veto executes and lands on the Delay:** Once the veto's state is `Succeeded`, anyone's `execute` succeeds and the Delay's `txNonce` becomes `n`, for any `n` the Delay accepts (`txNonce < n ≤ queueNonce`). This follows from two rules that meet at the Roles Modifier's module call on the DelayOwnerSafe:<br>• GV-2 `passedVetoReachesTheDelayOwnerSafe` ✅ passes: once the veto's state is `Succeeded`, anyone's `execute` succeeds, and the Roles Modifier forwards the veto to the DelayOwnerSafe as exactly one module call, `execTransactionFromModule(Delay, 0, setTxNonce(n), Call)`, for any `n`, provided that call returns true. Assumes the deployed wiring: SetTxNonceGuard is the Roles Modifier's guard and points at the Delay, role 1 is scoped to `Delay.setTxNonce`, and the Governor is an enabled module in role 1 (G2.8, G2.9). A recording stand-in takes the DelayOwnerSafe's place.<br>• GV-3 `delayOwnerSafeLandsTheVeto` ✅ passes: on Safe v1.4.1, an enabled module's `execTransactionFromModule(Delay, 0, setTxNonce(n), Call)` returns true and sets the Delay's `txNonce` to `n`, for any `n` the Delay accepts, when the Safe owns the Delay (G2.3). On chain that module is the Roles Modifier (G2.6). |

### Generalization 3 — Governance settings cannot be changed other than by the ownerless safe, proposer safe, or DelayModOwner safe

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

**Conclusion:** Settings functions of the Ownerless Safe can only be executed by its signers or its only enabled module, the Delay Modifier. The Delay Modifier only executes proposals queued by the signers of the Proposer Safe, and this setting can only be modified by the signers of the DelayOwnerSafe.

##### Ownerless Safe · Table 1 - Only Ownerless Safe's owners and the Delay Modifier, the only enabled module, can modify the Ownerless Safe's settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.OwnerlessSafe.1 | Only Modules or Owners (Signers) can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. The settings functions of the OwnerlessSafe can only be executed by Owners or enabled modules. | Same as G1.2. |
| G3.OwnerlessSafe.2 | OwnerlessSafe fallback handler is `address(0)`. | Same as G1.3. |
| G3.OwnerlessSafe.3 | Delay Module is the only enabled module on OwnerlessSafe. | Same as G1.4. |
| G3.OwnerlessSafe.4 | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5. |

After G3.OwnerlessSafe.4 the branch splits in two at the Ownerless Safe's only enabled module the Delay Modifier: the Delay Modifier's modules, and the Delay Modifier's owner. 


##### Ownerless Safe · Table 2a — Conclusion: The only enabled module of the Delay Modifier, the Proposer Safe, can propose transactions. Each one waits out the cooldown and can be vetoed.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.OwnerlessSafe.5a | ProposerSafe is the only enabled module on the Delay Mod | Same as G1.6. |
| G3.OwnerlessSafe.6a | Only Modules or Owners (Signers) can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.7. |
| G3.OwnerlessSafe.7a | ProposerSafe fallback handler is address(0). | Same as G1.8. |
| G3.OwnerlessSafe.8a | ProposerSafe has no enabled modules. | Same as G1.9. |
| G3.OwnerlessSafe.9a | ProposerSafe can propose a transaction to Delay Modifier that is executed on the Ownerless Safe once the cooldown has passed, if it hasn't expired, the system isn't paused, and it hasn't been vetoed. | Same as G1.10. |


##### Ownerless Safe · Table 2b — Conclusion: The owner of the Delay Modifier, the DelayOwnerSafe, can modify the Delay Modifier's settings. It can act only through its signers. None of its enabled modules are allowed to change its settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.OwnerlessSafe.5b | DelayMod only has one owner, which is the DelayOwnerSafe. | Same as G2.3. |
| G3.OwnerlessSafe.6b | Only Modules or Owners (Signers) can interact with DelayOwnerSafe, except fallback and receive, which anyone can call. | Same as G2.4. |
| G3.OwnerlessSafe.7b | DelayOwnerSafe fallback handler is `address(0)`. | Same as G2.5. |
| G3.OwnerlessSafe.8b | DelayOwnerSafe only has one enabled module, the Roles Modifier | Same as G2.6. |
| G3.OwnerlessSafe.9b | Only Modules with assignedRoles or Owners can interact with Roles Modifier. | Same as G2.7. |
| G3.OwnerlessSafe.10b | Roles Modifier only has one owner, which is the Ownerless Safe. | Same as G3.RolesModifier.2b. |
| G3.OwnerlessSafe.11b | The Governor  is the only module of the Roles Modifier with an assignedRole. | Same as G2.8. |
| G3.OwnerlessSafe.12b | The Governor  is assigned only role 1, its defaultRole. | Same as G2.9. |
| G3.OwnerlessSafe.13b | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | Same as G2.10. |


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

**Conclusion:** The settings functions of the Delay Modifier can only be executed by its owner, the DelayOwnerSafe. Only the signers on the DelayOwnerSafe may execute Delay settings functions, and this setting can only be changed by DelayOwnerSafe signers, Ownerless Safe signers, or Proposal Safe signers. 

##### Delay Modifier · Table 1 - Conclusion:  Only the owner of the Delay Modifier, the DelayOwnerSafe, can call the Delay Modifier's settings functions. The DelayOwnerSafe, can only receive interactions from its signers/owners, or its only enabled module the Roles Modifier.  

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayModifier.1 | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. The settings functions are owner-only: only the Owner can successfully execute them. | Same as G1.5. |
| G3.DelayModifier.2 | DelayMod only has one owner, which is the DelayOwnerSafe. | Same as G2.3. |
| G3.DelayModifier.3 | Only Modules or Owners can interact with DelayOwnerSafe. | Same as G2.4. |
| G3.DelayModifier.4 | DelayOwnerSafe fallback handler is `address(0)`. | Same as G2.5. |
| G3.DelayModifier.5 | DelayOwnerSafe only has one module, the Roles Modifier | Same as G2.6. |
| G3.DelayModifier.6 | Only Modules with assignedRoles or Owners can interact with Roles Modifier. | Same as G2.7. |

After G3.DelayModifier.6 the branch splits in two at the DelayOwnerSafe's only enabled module the Roles Modifier: the Roles Modifier's modules, and the Roles Modifier's owner.


##### Delay Modifier · Table 2a — The Roles Modifier, the only enabled module of the DelayOwnerSafe, can only execute veto transactions `Delay.setTxNonce(uint256)` from the Governor contract. 
| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayModifier.7a | The Governor  is the only enabled module of the Roles Modifier with an assignedRole. | Same as G2.8. |
| G3.DelayModifier.8a | The Governor  is assigned only role 1, its defaultRole. | Same as G2.9. |
| G3.DelayModifier.9a | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | Same as G2.10. |



##### Delay Modifier · Table 2b — The Roles Modifier, the only enabled module of the DelayOwnerSafe, is owned by the Ownerless Safe. The Roles Modifier's settings can only be changed by the signers of the OwnerlessSafe or from proposals from the signers of the ProposerSafe.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayModifier.7b | Roles Modifier only has one owner, which is the Ownerless Safe. | Same as G3.RolesModifier.2b. |
| G3.DelayModifier.8b | Only Modules or Owners (Signers) can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.2. |
| G3.DelayModifier.9b | OwnerlessSafe fallback handler is `address(0)`. | Same as G1.3. |
| G3.DelayModifier.10b | Delay Module is the only enabled module on OwnerlessSafe. | Same as G1.4. |
| G3.DelayModifier.11b | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5. |
| G3.DelayModifier.12b | ProposerSafe is the only module on the Delay Mod | Same as G1.6. |
| G3.DelayModifier.13b | Only Modules or Owners (Signers) can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.7. |
| G3.DelayModifier.14b | ProposerSafe fallback handler is set to address(0). | Same as G1.8. |
| G3.DelayModifier.15b | ProposerSafe has no enabled modules. | Same as G1.9. |


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

**Conclusion:** The settings functions of the Proposer Safe can only be executed by its signers since it has no enabled modules.

##### Proposer Safe · Table 1 — Conclusion: The settings functions of the Proposer Safe can only be executed by its signers since it has no enabled modules.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.ProposerSafe.1 | Only Modules or Owners (Signers) can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. The settings functions of the ProposerSafe can only be executed by Owners or enabled modules. | Same as G1.7. |
| G3.ProposerSafe.2 | ProposerSafe fallback handler is address(0). | Same as G1.8. |
| G3.ProposerSafe.3 | ProposerSafe has no enabled modules. | Same as G1.9. |

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

**Conclusion:** The settings functions of the DelayOwnerSafe can only be executed by its signers, and this setting can only be changed by DelayOwnerSafe signers, Ownerless Safe signers, or Proposal Safe signers. 

##### DelayOwnerSafe · Table 1 —  The DelayOwnerSafe's settings can only be changed by its owners or through the its only enabled module, the Roles Modifier.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayOwnerSafe.1 | Only Modules or Owners (Signers) can interact with DelayOwnerSafe, except fallback and receive, which anyone can call. The settings functions of the DelayOwnerSafe can only be executed by Owners or enabled modules. | Same as G2.4. |
| G3.DelayOwnerSafe.2 | DelayOwnerSafe fallback handler is `address(0)`. | Same as G2.5. |
| G3.DelayOwnerSafe.3 | DelayOwnerSafe only has one enabled module, the Roles Modifier | Same as G2.6. |
| G3.DelayOwnerSafe.4 | Only Modules with assignedRoles or Owners can interact with Roles Modifier. | Same as G2.7. |

After G3.DelayOwnerSafe.4 the branch splits in two at the DelayOwnerSafe's only module, the Roles Modifier: the Roles Modifier's modules, and the Roles Modifier's owner.


##### DelayOwnerSafe · Table 2a — The Roles Modifier, the only enabled module of the DelayOwnerSafe, can only execute veto transactions `Delay.setTxNonce(uint256)` from the Governor contract.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayOwnerSafe.5a | The Governor  is the only enabled module of the Roles Modifier with an assignedRole. | Same as G2.8. |
| G3.DelayOwnerSafe.6a | The Governor  is assigned only role 1, its defaultRole. | Same as G2.9. |
| G3.DelayOwnerSafe.7a | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | Same as G2.10. |



##### DelayOwnerSafe · Table 2b — The Roles Modifier, the only enabled module of the DelayOwnerSafe, is owned by the Ownerless Safe. The Roles Modifier's settings can only be changed by the signers of the OwnerlessSafe or from proposals from the signers of the ProposerSafe. 

| # | Statement | Evidence |
| --- | --- | --- |
| G3.DelayOwnerSafe.5b | Roles Modifier only has one owner, which is the Ownerless Safe. | Same as G3.RolesModifier.2b. |
| G3.DelayOwnerSafe.6b | Only Modules or Owners (Signers) can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.2. |
| G3.DelayOwnerSafe.7b | OwnerlessSafe fallback handler is `address(0)`. | Same as G1.3. |
| G3.DelayOwnerSafe.8b | Delay Module is the only enabled module on OwnerlessSafe. | Same as G1.4. |
| G3.DelayOwnerSafe.9b | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5. |
| G3.DelayOwnerSafe.10b | DelayMod only has one owner, which is the DelayOwnerSafe. | Same as G2.3. |
| G3.DelayOwnerSafe.11b | ProposerSafe is the only enabled module on the Delay Mod | Same as G1.6. |
| G3.DelayOwnerSafe.12b | Only Modules or Owners (Signers) can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.7. |
| G3.DelayOwnerSafe.13b | ProposerSafe fallback handler is set to zero address. | Same as G1.8. |
| G3.DelayOwnerSafe.14b | ProposerSafe has no enabled modules. | Same as G1.9. |


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

**Conclusion:** The settings functions on the Roles Modifier can only be executed by signers of the Ownerless Safe or through proposal from the signers of the Proposer Safe. This setting can only be changed by the signers of the DelayOwnerSafe.

##### Roles Modifier · Table 1 — Only the Roles Modifier's owner or enabled modules may interact with the Roles Modifier.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.RolesModifier.1 | Only Modules with assignedRoles or Owners can interact with Roles Modifier. The settings functions are owner-only: only the Owner can successfully execute them. | Same as G2.7. |

After G3.RolesModifier.1 the branch splits in two: the Roles Modifier's modules, and the Roles Modifier's owner.


##### Roles Modifier · Table 2a — The Roles Modifier's only enabled module, the Governor Contract, can only execute veto transactions `Delay.setTxNonce(uint256)`.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.RolesModifier.2a | The Governor  is the only module of the Roles Modifier with an assignedRole. | Same as G2.8. |
| G3.RolesModifier.3a | The Governor  is assigned only role 1, its defaultRole. | Same as G2.9. |
| G3.RolesModifier.4a | Role 1 and the SetTxNonceGuard together restrict the Governor to only vetos. | Same as G2.10. |



##### Roles Modifier · Table 2b — The Roles Modifier is owned by the Ownerless Safe. The Roles Modifier's settings can only be changed by the signers of the OwnerlessSafe or from proposals from the signers of the ProposerSafe.This restriction can only be changed by the signers of the DelayOwnerSafe enabling another module on the Delay Modifier. 

| # | Statement | Evidence |
| --- | --- | --- |
| G3.RolesModifier.2b | Roles Modifier only has one owner, which is the Ownerless Safe. | **FV — one owner:** RI-3 `ownerOnlyChangesThroughOwnableTransfer` ✅ passes. The Roles Modifier's owner is one address, and it only changes through `transferOwnership` or `renounceOwnership`, called by the current owner. RI-5 `onlyOwnerCanCallRolesSettings` ✅ passes: only that address can call the twenty settings functions (G2.7).<br><br>**On-chain — owner is the Ownerless Safe:** ✅ at block 26083996, `owner()` on the Roles Modifier (`0xaBAC51B6AEb05a2CE65310F79e64DF203D6c8Ab3`) returns the Ownerless Safe (`0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03`). Read directly from storage, `_owner` (slot 51, `OwnableUpgradeable`) holds the same address.<br><br>**On-chain — ownership has only ever moved to the Ownerless Safe:** ✅ the Roles Modifier's complete `OwnershipTransferred` history, from its creation at block 26042039 to block 26083996, is three events:<br>• block 26042039, tx `0xcd565c28bc3c771d4b5af1f0ba9bd55bf3245aadc8148b24e4041f3dd71b8a7e`: `0x0` → Zodiac `ModuleProxyFactory` (`0x000000000000aDdB49795b0f9bA5BC298cDda236`), then → deployer (`0xdace6985e42ec10f492d0919493964922b833b5b`), both inside the proxy's creation and `setUp`<br>• block 26042084, tx `0xda81af7fb8ba6d91e9148c349324a7c06146bf5a21703ebea8f561ab7fec4c7a`: deployer → Ownerless Safe, the deployer's `transferOwnership(0xb8A1dF43c1c88b13937C0c5CEBbAd15830cAeC03)`<br>There is no later transfer and no renounce. |
| G3.RolesModifier.3b | Only Modules or Owners (Signers) can interact with OwnerlessSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.2. |
| G3.RolesModifier.4b | OwnerlessSafe fallback handler is `address(0)`. | Same as G1.3. |
| G3.RolesModifier.5b | Delay Module is the only enabled module on OwnerlessSafe. | Same as G1.4. |
| G3.RolesModifier.6b | Only Modules or Owner can interact with Delay Modifier, except `executeNextTx` and `skipExpired`, which anyone can call. | Same as G1.5. |
| G3.RolesModifier.7b | DelayMod only has one owner, which is the DelayOwnerSafe. | Same as G2.3. |
| G3.RolesModifier.8b | ProposerSafe is the only module on the Delay Mod | Same as G1.6. |
| G3.RolesModifier.9b | Only Modules or Owners can interact with ProposerSafe, except `fallback` and `receive`, which anyone can call. | Same as G1.7. |
| G3.RolesModifier.10b | ProposerSafe has no fallback handler. | Same as G1.8. |
| G3.RolesModifier.11b | ProposerSafe has no modules. | Same as G1.9. |


---

#### Governor

Settings functions: none. 
**Conclusion:** There are no settings functions on the Governor contract.

##### Governor · Table 1 — No settings functions. Conclusion: Nobody can change the Governor's settings.

| # | Statement | Evidence |
| --- | --- | --- |
| G3.Governor.1 | Governor does not have settings functions. | **FV — every write function of the Governor is enumerated below, and none is a setter:** GS-1 `governorWriteFunctionsAreTheKnownFourteen` ✅ passes. TermFinanceGovernor builds on OpenZeppelin's Governor, GovernorVotes and GovernorCountingSimple only, not GovernorSettings, GovernorVotesQuorumFraction or GovernorTimelockControl, the extensions that add setters. It has no write functions besides these fourteen:<br><br>*proposal lifecycle:*<br>• `propose`<br>• `execute`<br>• `cancel`<br><br>*voting:*<br>• `castVote`<br>• `castVoteWithReason`<br>• `castVoteWithReasonAndParams`<br>• `castVoteBySig`<br>• `castVoteWithReasonAndParamsBySig`<br><br>*governance only — callable only by the Governor itself, as an action of an executed proposal:*<br>• `relay`, which makes one call out and writes nothing<br><br>*token and ETH receipt — each writes nothing:*<br>• `onERC721Received`<br>• `onERC1155Received`<br>• `onERC1155BatchReceived`<br>• `receive`<br><br>*Non-interactions — this always reverts, so nothing it does stands:*<br>• `queue`<br><br>**FV — `queue` always reverts:** GS-4 `queueAlwaysReverts` ✅ passes. The Governor has no timelock, so it never overrides OpenZeppelin's `_queueOperations`, which returns 0, and `queue` then reverts with `GovernorQueueNotImplemented`. A proposal that passes goes straight to `execute`.<br><br>**FV — no function changes a setting:** GS-2 `governorSettingsNeverChange` ✅ passes. For every write function except `queue` (GS-4), including `relay` called by the Governor as a proposal action, any caller and any arguments, every setting reads the same afterwards: `name`, `version`, `COUNTING_MODE`, the executor, `token`, `votingDelay`, `votingPeriod`, `proposalThreshold`, `quorumNumerator`, `quorumDenominator` and `proposalNeedsQueuing`. This holds for a function added later too.<br><br>**FV — the settings are compiled in:** GS-3 `governorSettingsAreTheDeployedValues` ✅ passes. In every state of the Governor's storage, `votingDelay` is 0, `votingPeriod` is 22 hours, `proposalThreshold` is 1,000 TERM, the quorum at any past timepoint is 1/100 of TERM's total supply at that timepoint, the executor is the Governor itself (no timelock), and no proposal needs queuing. None of these reads storage, so nothing the Governor stores can change them. The voting token is an immutable, and `name` is the only setting in storage, written only by the constructor.<br><br>All four run on the deployed Governor (`0x2B715634134220ffeEE9458b4e34E41A41418607`) from its verified source, through `confs/Governor-settings.conf`. |
