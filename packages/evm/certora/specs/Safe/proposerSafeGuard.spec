/*
 * Property: once the Proposer Safe (GnosisSafe v1.3.0) installs
 * ConfigLockGuard with its own setGuard, the Safe cannot remove or replace
 * the guard, cannot enable or disable a module, cannot change its fallback
 * handler, and cannot delegate call. Everything else still goes through:
 * plain calls to other contracts (queueing into the Delay among them) and the
 * Safe's owner and threshold management.
 *
 * "The guard" in this file always means ConfigLockGuard, installed as the
 * Safe's transaction guard. PauseGuard and SetTxNonceGuard are not in this
 * scene. The Proposer Safe owns no modifier, so its ConfigLockGuard is built
 * with lockedModifier = address(0). The rules that the guard rejects a call
 * hold for any lockedModifier, since the Safe branch is checked first;
 * checkTransactionAcceptsEverythingElse assumes address(0). The guard then
 * also rejects the seven modifier selectors sent to address(0), which has no
 * code, so it locks nothing real outside the Safe.
 *
 * The scene is the real v1.3.0 code through GnosisSafeHarness (solc 0.7.6)
 * and the real ConfigLockGuard (solc 0.8.6).
 *
 * Why these locks are enough. Safe v1.3.0 consults its guard in
 * execTransaction (sections 3 and 4) but not in execTransactionFromModule or
 * execTransactionFromModuleReturnData (section 5), so:
 *   - a module would bypass the guard, hence enableModule is blocked;
 *   - a delegate call could write the guard, module or handler slots
 *     directly, hence delegate calls are blocked;
 *   - setGuard is the only function that moves the guard slot, and
 *     setFallbackHandler the only one that moves the handler slot, hence both
 *     are blocked.
 * disableModule is blocked too, so the module list does not change at all.
 * The Safe's settings only change when the Safe calls itself (SE-7), and it
 * calls itself only through execTransaction, a module, or fallback's call to
 * its handler, which comes from the handler, not the Safe (SE-15). So with no
 * modules enabled and the handler locked, execTransaction's calls to itself
 * are the only way in, and those are what the rules below cover.
 *
 * Rules, by property:
 *
 *   the guard, called directly
 *     checkTransactionRejectsDelegateCall            any delegate call reverts
 *     checkTransactionRejectsSelfSetGuard            the Safe's own setGuard
 *     checkTransactionRejectsSelfEnableModule        the Safe's own enableModule
 *     checkTransactionRejectsSelfDisableModule       the Safe's own disableModule
 *     checkTransactionRejectsSelfSetFallbackHandler  the Safe's own
 *                                                    setFallbackHandler
 *     checkTransactionAcceptsEverythingElse          every other plain call
 *                                                    passes
 *
 *   installing it
 *     ownersCanInstallConfigLockGuard                the owners' execTransaction
 *                                                    of setGuard(guard) on the
 *                                                    Safe succeeds and the slot
 *                                                    holds it
 *
 *   once installed, end to end through execTransaction
 *     guardedSafeCannotCallSetGuard
 *     guardedSafeCannotCallEnableModule
 *     guardedSafeCannotCallDisableModule
 *     guardedSafeCannotCallSetFallbackHandler
 *     guardedSafeCannotDelegateCall
 *     guardedSelfCallNeverChangesGuard               for any calldata, a call to
 *                                                    itself leaves the guard slot
 *     guardedSelfCallNeverChangesModules             ... leaves the module list
 *     guardedSelfCallNeverChangesFallbackHandler     ... leaves the handler slot
 *
 *   once installed, the Safe still works
 *     guardedOwnersCanStillCallOut                   a plain call to another
 *                                                    contract succeeds
 *     guardedOwnersCanStillChangeOtherSettings       each of the four unblocked
 *                                                    settings functions works
 *
 *   the module path does not consult the guard
 *     moduleCanDelegateCallPastTheGuard              with the guard installed, an
 *                                                    enabled module's delegate
 *                                                    call still succeeds
 *     moduleCanDelegateCallPastTheGuardWithReturnData
 *                                                    the same through the other
 *                                                    module entry point
 *     moduleCanRemoveTheGuard                        an enabled module can call
 *                                                    the Safe's own setGuard and
 *                                                    move the guard out; this is
 *                                                    why enableModule has to be
 *                                                    blocked
 *
 * Modelling notes.
 *   - checkSignatures is NONDET: the signature check passes. That only adds
 *     executions, so the revert and "never changes" rules are unaffected; the
 *     signature check itself is SE-5 and SE-12.
 *   - checkTransaction and checkAfterExecution are DISPATCHER(true), so inside
 *     execTransaction the real ConfigLockGuard code runs: it is the only
 *     contract in the scene that implements them.
 *   - The Safe's low-level call to `to` has a symbolic target. As in
 *     selfCalls.spec, it is DISPATCHed to the Safe's eight settings functions,
 *     from execTransaction and from execTransactionFromModule.
 *     DISPATCH runs the function on the Safe whatever `to` is, so the rules
 *     that rely on it pin `to` to the Safe itself. A call to any other address
 *     can only change the Safe's settings by calling back into the Safe, where
 *     msg.sender is not the Safe (SE-7).
 *   - A call whose selector is none of the eight is HAVOC_ECF: it leaves the
 *     Safe's storage alone. That includes the Safe calling its own
 *     execTransaction again; the nested call goes through the same guard.
 */

using ConfigLockGuard as configLockGuard;

methods {
    function guardAddress() external returns (address) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function fallbackHandlerSlotWord() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function configLockGuard.lockedModifier() external returns (address) envfree;

    // The signature check passes.
    function checkSignatures(bytes32, bytes memory, bytes memory) internal => NONDET;

    // execTransaction's guard hooks. ConfigLockGuard is the only
    // implementation in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);

    // The Safe's call to `to`, run as a call to its own settings functions.
    unresolved external in GnosisSafeHarness.execTransaction(
        address, uint256, bytes, Enum.Operation, uint256, uint256, uint256, address, address, bytes
    ) => DISPATCH [
        GnosisSafeHarness.enableModule(address),
        GnosisSafeHarness.disableModule(address, address),
        GnosisSafeHarness.addOwnerWithThreshold(address, uint256),
        GnosisSafeHarness.removeOwner(address, address, uint256),
        GnosisSafeHarness.swapOwner(address, address, address),
        GnosisSafeHarness.changeThreshold(uint256),
        GnosisSafeHarness.setGuard(address),
        GnosisSafeHarness.setFallbackHandler(address)
    ] default HAVOC_ECF;

    unresolved external in GnosisSafeHarness.execTransactionFromModule(address, uint256, bytes, Enum.Operation) => DISPATCH [
        GnosisSafeHarness.enableModule(address),
        GnosisSafeHarness.disableModule(address, address),
        GnosisSafeHarness.addOwnerWithThreshold(address, uint256),
        GnosisSafeHarness.removeOwner(address, address, uint256),
        GnosisSafeHarness.swapOwner(address, address, address),
        GnosisSafeHarness.changeThreshold(uint256),
        GnosisSafeHarness.setGuard(address),
        GnosisSafeHarness.setFallbackHandler(address)
    ] default HAVOC_ECF;
}

/// Head of the Safe's owner and module lists.
definition SENTINEL() returns address = 0x1;

definition SET_GUARD() returns uint32 = sig:setGuard(address).selector;
definition ENABLE_MODULE() returns uint32 = sig:enableModule(address).selector;
definition DISABLE_MODULE() returns uint32 = sig:disableModule(address, address).selector;
definition SET_FALLBACK_HANDLER() returns uint32 = sig:setFallbackHandler(address).selector;

definition isLockedSelfSelector(uint32 sel) returns bool =
    sel == SET_GUARD() || sel == ENABLE_MODULE() ||
    sel == DISABLE_MODULE() || sel == SET_FALLBACK_HANDLER();

// What the guard rejects on calls to lockedModifier. setGuard(address),
// enableModule(address) and disableModule(address,address) share the Safe's
// selectors; the other four are Ownable's and Module's.
definition TRANSFER_OWNERSHIP() returns uint32 = 0xf2fde38b;
definition RENOUNCE_OWNERSHIP() returns uint32 = 0x715018a6;
definition SET_AVATAR() returns uint32 = 0x086cfca8;
definition SET_TARGET() returns uint32 = 0x776d1a01;

definition isLockedModifierSelector(uint32 sel) returns bool =
    sel == TRANSFER_OWNERSHIP() || sel == RENOUNCE_OWNERSHIP() ||
    sel == ENABLE_MODULE() || sel == DISABLE_MODULE() || sel == SET_GUARD() ||
    sel == SET_AVATAR() || sel == SET_TARGET();

/// The settings functions the guard leaves open.
definition isUnblockedSetting(method f) returns bool =
    f.selector == sig:addOwnerWithThreshold(address, uint256).selector ||
    f.selector == sig:removeOwner(address, address, uint256).selector ||
    f.selector == sig:swapOwner(address, address, address).selector ||
    f.selector == sig:changeThreshold(uint256).selector;

/* ------------------------------------------------------------------------
 * 1. The guard, called directly
 *
 * Safe v1.3.0 calls the guard itself, so inside checkTransaction msg.sender
 * is the Safe. Here e.msg.sender stands for it.
 * --------------------------------------------------------------------- */

/*
 * Every delegate call is rejected, whatever the destination and calldata.
 */
rule checkTransactionRejectsDelegateCall(
    address to, uint256 value, bytes data,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;

    configLockGuard.checkTransaction@withrevert(
        e, to, value, data, Enum.Operation.DelegateCall,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "ConfigLockGuard accepted a delegate call";
}

/*
 * The Safe calling its own setGuard is rejected, whatever the new guard,
 * the value and the rest of the calldata.
 */
rule checkTransactionRejectsSelfSetGuard(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require selectorOf(data) == SET_GUARD();

    configLockGuard.checkTransaction@withrevert(
        e, e.msg.sender, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "ConfigLockGuard let the Safe call its own setGuard";
}

/*
 * The Safe calling its own enableModule is rejected, whatever the module.
 */
rule checkTransactionRejectsSelfEnableModule(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require selectorOf(data) == ENABLE_MODULE();

    configLockGuard.checkTransaction@withrevert(
        e, e.msg.sender, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "ConfigLockGuard let the Safe call its own enableModule";
}

/*
 * The Safe calling its own disableModule is rejected, whatever the module.
 */
rule checkTransactionRejectsSelfDisableModule(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require selectorOf(data) == DISABLE_MODULE();

    configLockGuard.checkTransaction@withrevert(
        e, e.msg.sender, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "ConfigLockGuard let the Safe call its own disableModule";
}

/*
 * The Safe calling its own setFallbackHandler is rejected, whatever the
 * handler.
 */
rule checkTransactionRejectsSelfSetFallbackHandler(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require selectorOf(data) == SET_FALLBACK_HANDLER();

    configLockGuard.checkTransaction@withrevert(
        e, e.msg.sender, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "ConfigLockGuard let the Safe call its own setFallbackHandler";
}

/*
 * Nothing else is rejected: with lockedModifier = address(0), a plain call
 * that is not the Safe calling one of its four locked settings functions
 * always passes, apart from the seven modifier selectors sent to address(0).
 * address(0) has no code, so those calls could never do anything. So the
 * five rules above are all the guard blocks that matters.
 */
rule checkTransactionAcceptsEverythingElse(
    address to, uint256 value, bytes data,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require e.msg.value == 0;
    require configLockGuard.lockedModifier() == 0;
    uint32 sel = selectorOf(data);
    require !(to == e.msg.sender && isLockedSelfSelector(sel));
    require !(to != e.msg.sender && to == 0 && isLockedModifierSelector(sel));

    configLockGuard.checkTransaction@withrevert(
        e, to, value, data, Enum.Operation.Call,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert !lastReverted,
        "ConfigLockGuard rejected a plain call that is not a locked settings call on the Safe";
}

/* ------------------------------------------------------------------------
 * 2. Installing it
 * --------------------------------------------------------------------- */

/*
 * With no guard yet, the owners' execTransaction of setGuard(ConfigLockGuard)
 * on the Safe succeeds and the guard slot then holds it. v1.3.0's setGuard
 * makes no ERC-165 check, so nothing about the guard can refuse it.
 */
rule ownersCanInstallConfigLockGuard(
    bytes data, uint256 safeTxGas, uint256 baseGas,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require thresholdValue() > 0;
    require guardAddress() == 0;
    require selectorOf(data) == SET_GUARD();

    execTransaction@withrevert(e,
        currentContract, 0, data, Enum.Operation.Call,
        safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted && guardAddress() == configLockGuard,
        "the owners could not install ConfigLockGuard with setGuard";
}

/* ------------------------------------------------------------------------
 * 3. Once installed, end to end through execTransaction
 * --------------------------------------------------------------------- */

/*
 * The Safe cannot remove or replace the guard: an execTransaction calling the
 * Safe's own setGuard reverts, whatever the new guard, value or operation.
 */
rule guardedSafeCannotCallSetGuard(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require guardAddress() == configLockGuard;
    require selectorOf(data) == SET_GUARD();

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with ConfigLockGuard installed, the Safe called its own setGuard";
}

/*
 * The Safe cannot enable a module: an execTransaction calling the Safe's own
 * enableModule reverts, whatever the module.
 */
rule guardedSafeCannotCallEnableModule(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require guardAddress() == configLockGuard;
    require selectorOf(data) == ENABLE_MODULE();

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with ConfigLockGuard installed, the Safe called its own enableModule";
}

/*
 * The Safe cannot disable a module: an execTransaction calling the Safe's own
 * disableModule reverts, whatever the module.
 */
rule guardedSafeCannotCallDisableModule(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require guardAddress() == configLockGuard;
    require selectorOf(data) == DISABLE_MODULE();

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with ConfigLockGuard installed, the Safe called its own disableModule";
}

/*
 * The Safe cannot change its fallback handler: an execTransaction calling the
 * Safe's own setFallbackHandler reverts, whatever the handler.
 */
rule guardedSafeCannotCallSetFallbackHandler(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require guardAddress() == configLockGuard;
    require selectorOf(data) == SET_FALLBACK_HANDLER();

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with ConfigLockGuard installed, the Safe called its own setFallbackHandler";
}

/*
 * The Safe cannot delegate call, to any address, so no code can run as the
 * Safe and write its guard, module or handler slots directly.
 */
rule guardedSafeCannotDelegateCall(
    address to, uint256 value, bytes data,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require guardAddress() == configLockGuard;

    execTransaction@withrevert(e,
        to, value, data, Enum.Operation.DelegateCall,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with ConfigLockGuard installed, the Safe made a delegate call";
}

/*
 * For any calldata and operation, an execTransaction addressed to the Safe
 * itself leaves the guard slot as it was. The Safe's call to itself runs the
 * real settings functions (DISPATCH above), so this covers every settings
 * function, not just setGuard.
 */
rule guardedSelfCallNeverChangesGuard(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require guardAddress() == configLockGuard;

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert guardAddress() == configLockGuard,
        "an execTransaction to the Safe itself moved ConfigLockGuard out of the guard slot";
}

/*
 * For any calldata and operation, an execTransaction addressed to the Safe
 * itself leaves every entry of the module list as it was: no module is
 * added or removed.
 */
rule guardedSelfCallNeverChangesModules(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address a
) {
    env e;
    require guardAddress() == configLockGuard;
    address entryBefore = moduleEntry(a);

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert moduleEntry(a) == entryBefore,
        "an execTransaction to the Safe itself changed the module list";
}

/*
 * For any calldata and operation, an execTransaction addressed to the Safe
 * itself leaves the fallback handler slot as it was, all 256 bits of it.
 */
rule guardedSelfCallNeverChangesFallbackHandler(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require guardAddress() == configLockGuard;
    uint256 handlerBefore = fallbackHandlerSlotWord();

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert fallbackHandlerSlotWord() == handlerBefore,
        "an execTransaction to the Safe itself changed the fallback handler";
}

/* ------------------------------------------------------------------------
 * 4. Once installed, the Safe still works
 * --------------------------------------------------------------------- */

/*
 * A plain call to another contract, the shape of the Proposer Safe's queue
 * call into the Delay, still succeeds with the guard installed. Also the
 * non-vacuity witness for section 3: the guard does not block everything.
 */
rule guardedOwnersCanStillCallOut(
    address to, uint256 value, bytes data,
    uint256 safeTxGas, uint256 baseGas,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require thresholdValue() > 0;
    require guardAddress() == configLockGuard;
    require to != currentContract;

    execTransaction@withrevert(e,
        to, value, data, Enum.Operation.Call,
        safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted,
        "with ConfigLockGuard installed, the Safe could not make a plain call to another contract";
}

/*
 * Each settings function the guard leaves open still works: an execTransaction
 * addressed to the Safe with a call to it succeeds and a setting changes.
 * `f` only picks which selector the call carries.
 */
rule guardedOwnersCanStillChangeOtherSettings(
    method f, bytes data, address a, uint256 safeTxGas, uint256 baseGas,
    address gasToken, address refundReceiver, bytes signatures
)
    filtered { f -> isUnblockedSetting(f) }
{
    env e;
    require thresholdValue() > 0;
    require guardAddress() == configLockGuard;
    require selectorOf(data) == f.selector;

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);

    execTransaction@withrevert(e,
        currentContract, 0, data, Enum.Operation.Call,
        safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore),
        "with ConfigLockGuard installed, the owners could not use this settings function";
}

/* ------------------------------------------------------------------------
 * 5. The module path does not consult the guard
 *
 * These are why enableModule is locked: with the guard installed, an enabled
 * module still does exactly what the guard forbids. The module is assumed
 * here; the Proposer Safe has none, and section 3 shows it cannot get one.
 * --------------------------------------------------------------------- */

/*
 * With the guard installed, an enabled module's delegate call through
 * execTransactionFromModule succeeds. The guard rejects every delegate call
 * (checkTransactionRejectsDelegateCall), so it was not consulted.
 */
rule moduleCanDelegateCallPastTheGuard(address to, uint256 value, bytes data) {
    env e;
    require guardAddress() == configLockGuard;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;

    execTransactionFromModule@withrevert(e, to, value, data, Enum.Operation.DelegateCall);

    satisfy !lastReverted,
        "an enabled module could not delegate call with ConfigLockGuard installed";
}

/* The same through execTransactionFromModuleReturnData. */
rule moduleCanDelegateCallPastTheGuardWithReturnData(address to, uint256 value, bytes data) {
    env e;
    require guardAddress() == configLockGuard;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;

    execTransactionFromModuleReturnData@withrevert(e, to, value, data, Enum.Operation.DelegateCall);

    satisfy !lastReverted,
        "an enabled module could not delegate call through execTransactionFromModuleReturnData with ConfigLockGuard installed";
}

/*
 * With the guard installed, an enabled module can have the Safe call its own
 * setGuard and move the guard out of the slot, which execTransaction can never
 * do (guardedSelfCallNeverChangesGuard).
 */
rule moduleCanRemoveTheGuard(bytes data) {
    env e;
    require guardAddress() == configLockGuard;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;
    require selectorOf(data) == SET_GUARD();

    execTransactionFromModule@withrevert(e, currentContract, 0, data, Enum.Operation.Call);

    satisfy !lastReverted && guardAddress() != configLockGuard,
        "an enabled module could not move ConfigLockGuard out of the guard slot";
}
