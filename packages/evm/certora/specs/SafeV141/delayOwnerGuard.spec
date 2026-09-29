/*
 * Property: once the DelayOwnerSafe (Safe v1.4.1) installs DelayOwnerGuard
 * with its own setGuard, the Safe cannot remove or replace the guard, cannot
 * enable a module, cannot change its fallback handler, and cannot delegate
 * call. The guard, called directly, rejects exactly those calls and the six
 * locked calls to the Delay, and lets everything else through. The module
 * path never reaches the guard.
 *
 * "The guard" in this file always means DelayOwnerGuard, installed as the
 * Safe's transaction guard. PauseGuard and SetTxNonceGuard are not in this
 * scene. What the guard does to calls into the Delay, end to end, is
 * specs/Delay/delayOwnerGuard.spec.
 *
 * The scene is the real v1.4.1 code through SafeV141Harness (solc 0.7.6) and
 * the real DelayOwnerGuard (solc 0.8.6). The guard's `delay` is left
 * unconstrained, so the rules hold for whatever Delay it was built with.
 *
 * Why these locks are enough on the Safe. Safe v1.4.1 calls checkTransaction
 * from execTransaction only (Safe.sol:177), never from
 * execTransactionFromModule, so:
 *   - a module would bypass the guard (moduleCallBypassesTheGuard), hence
 *     enableModule is blocked;
 *   - a delegate call could write the guard or module slots directly, hence
 *     delegate calls are blocked;
 *   - setGuard is the only function that moves the guard slot, and
 *     setFallbackHandler the only one that moves the handler slot, hence both
 *     are blocked.
 * The Safe's settings only change when the Safe calls itself (SE141-7), and it
 * calls itself only through execTransaction, a module, or fallback's call to
 * its handler, which comes from the handler, not the Safe (SE141-15). So once
 * the handler is locked at zero and no module can be added, the owners'
 * execTransaction calls to the Safe itself are what the rules below cover.
 * The Roles Modifier, already a module, is bounded by G2.10 in PROOFS.md.
 *
 * Rules, by property:
 *
 *   the guard, called directly
 *     checkTransactionRejectsDelegateCall            any delegate call reverts
 *     checkTransactionRejectsSelfSetGuard            the Safe's own setGuard
 *     checkTransactionRejectsSelfEnableModule        the Safe's own enableModule
 *     checkTransactionRejectsSelfSetFallbackHandler  the Safe's own
 *                                                    setFallbackHandler
 *     checkTransactionRejectsDelayOwnershipChange    transferOwnership and
 *                                                    renounceOwnership on the
 *                                                    Delay
 *     checkTransactionRejectsDelayEnableModule       enableModule on the Delay
 *     checkTransactionRejectsDelaySetGuard           setGuard on the Delay
 *     checkTransactionRejectsDelaySetAvatarOrTarget  setAvatar and setTarget on
 *                                                    the Delay
 *     checkTransactionAcceptsEverythingElse          every other plain call
 *                                                    passes
 *
 *   installing it
 *     ownersCanInstallDelayOwnerGuard                the owners' execTransaction
 *                                                    of setGuard(guard) on the
 *                                                    Safe succeeds, ERC-165 probe
 *                                                    included, and the slot
 *                                                    holds it
 *
 *   once installed, end to end through execTransaction
 *     guardedSafeCannotCallSetGuard
 *     guardedSafeCannotCallEnableModule
 *     guardedSafeCannotCallSetFallbackHandler
 *     guardedSafeCannotDelegateCall
 *     guardedSelfCallNeverChangesGuard               for any calldata, a call to
 *                                                    itself leaves the guard slot
 *     guardedSelfCallNeverEnablesAModule             ... enables no module
 *     guardedSelfCallNeverChangesFallbackHandler     ... leaves the handler slot
 *
 *   once installed, the Safe still works
 *     guardedOwnersCanStillCallOut                   a plain call to an address
 *                                                    other than the Safe and the
 *                                                    Delay succeeds
 *     guardedOwnersCanStillChangeOtherSettings       each of the five unblocked
 *                                                    settings functions works
 *
 *   the module path
 *     moduleCallBypassesTheGuard                     with the guard installed,
 *                                                    an enabled module can still
 *                                                    move the guard slot, so the
 *                                                    guard never sees it
 *
 *   once installed, the Safe's half of the Delay lock
 *     guardedSafeCannotCallLockedDelayFunctions      an execTransaction to the
 *                                                    Delay carrying any of the
 *                                                    six locked selectors
 *                                                    reverts, before the Safe
 *                                                    makes any call. The Delay's
 *                                                    half, that every other call
 *                                                    leaves the locked settings
 *                                                    alone, is
 *                                                    specs/Delay/delayOwnerGuard.spec
 *
 * Modelling notes.
 *   - checkSignatures is NONDET: the signature check passes. That only adds
 *     executions, so the revert and "never changes" rules are unaffected; the
 *     signature check itself is SE141-5 and SE141-12.
 *   - checkTransaction, checkAfterExecution and supportsInterface are
 *     DISPATCHER(true), so inside execTransaction and setGuard the real
 *     DelayOwnerGuard code runs: it is the only contract in the scene that
 *     implements them.
 *   - The Safe's low-level call to `to` has a symbolic target. As in
 *     selfCalls.spec, it is DISPATCHed to the Safe's eight settings functions.
 *     DISPATCH runs the function on the Safe whatever `to` is, so the rules
 *     that rely on it pin `to` to the Safe itself. A call to any other address
 *     can only change the Safe's settings by calling back into the Safe, where
 *     msg.sender is not the Safe (SE141-7).
 *   - A call whose selector is none of the eight is HAVOC_ECF: it leaves the
 *     Safe's storage alone. That includes the Safe calling its own
 *     execTransaction again; the nested call goes through the same guard.
 */

using DelayOwnerGuard as delayOwnerGuard;

methods {
    function guardAddress() external returns (address) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function fallbackHandlerSlotWord() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function delayOwnerGuard.delay() external returns (address) envfree;

    // The signature check passes.
    function checkSignatures(bytes32, bytes memory, bytes memory) internal => NONDET;

    // execTransaction's guard hooks, and setGuard's ERC-165 probe of the new
    // guard. DelayOwnerGuard is the only implementation in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);

    // The Safe's call to `to`, from execTransaction or the module path, run as
    // a call to its own settings functions.
    unresolved external in SafeV141Harness._ => DISPATCH [
        SafeV141Harness.enableModule(address),
        SafeV141Harness.disableModule(address, address),
        SafeV141Harness.addOwnerWithThreshold(address, uint256),
        SafeV141Harness.removeOwner(address, address, uint256),
        SafeV141Harness.swapOwner(address, address, address),
        SafeV141Harness.changeThreshold(uint256),
        SafeV141Harness.setGuard(address),
        SafeV141Harness.setFallbackHandler(address)
    ] default HAVOC_ECF;
}

/// Head of the Safe's owner and module lists.
definition SENTINEL() returns address = 0x1;

// Locked on the Safe itself.
definition SET_GUARD() returns uint32 = sig:setGuard(address).selector;
definition ENABLE_MODULE() returns uint32 = sig:enableModule(address).selector;
definition SET_FALLBACK_HANDLER() returns uint32 = sig:setFallbackHandler(address).selector;

// Locked on the Delay. setGuard(address) and enableModule(address) share the
// Safe's selectors; the other four are Ownable's and Module's.
definition TRANSFER_OWNERSHIP() returns uint32 = 0xf2fde38b;
definition RENOUNCE_OWNERSHIP() returns uint32 = 0x715018a6;
definition SET_AVATAR() returns uint32 = 0x086cfca8;
definition SET_TARGET() returns uint32 = 0x776d1a01;

definition isLockedSelfSelector(uint32 sel) returns bool =
    sel == SET_GUARD() || sel == ENABLE_MODULE() || sel == SET_FALLBACK_HANDLER();

definition isLockedDelaySelector(uint32 sel) returns bool =
    sel == TRANSFER_OWNERSHIP() || sel == RENOUNCE_OWNERSHIP() ||
    sel == ENABLE_MODULE() || sel == SET_GUARD() ||
    sel == SET_AVATAR() || sel == SET_TARGET();

/// What the guard is meant to reject from `safe`, for a plain call. The Safe
/// branch is tested first, as in checkTransaction.
definition isLockedCall(address to, address safe, address d, uint32 sel) returns bool =
    (to == safe && isLockedSelfSelector(sel)) ||
    (to != safe && to == d && isLockedDelaySelector(sel));

/// The settings functions the guard leaves open on the Safe.
definition isUnblockedSetting(method f) returns bool =
    f.selector == sig:disableModule(address, address).selector ||
    f.selector == sig:addOwnerWithThreshold(address, uint256).selector ||
    f.selector == sig:removeOwner(address, address, uint256).selector ||
    f.selector == sig:swapOwner(address, address, address).selector ||
    f.selector == sig:changeThreshold(uint256).selector;

/* ------------------------------------------------------------------------
 * 1. The guard, called directly
 *
 * Safe v1.4.1 calls the guard itself, so inside checkTransaction msg.sender
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

    delayOwnerGuard.checkTransaction@withrevert(
        e, to, value, data, Enum.Operation.DelegateCall,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "DelayOwnerGuard accepted a delegate call";
}

/*
 * The Safe calling its own setGuard is rejected, whatever the new guard, the
 * value, the operation and the rest of the calldata.
 */
rule checkTransactionRejectsSelfSetGuard(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require selectorOf(data) == SET_GUARD();

    delayOwnerGuard.checkTransaction@withrevert(
        e, e.msg.sender, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "DelayOwnerGuard let the Safe call its own setGuard";
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

    delayOwnerGuard.checkTransaction@withrevert(
        e, e.msg.sender, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "DelayOwnerGuard let the Safe call its own enableModule";
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

    delayOwnerGuard.checkTransaction@withrevert(
        e, e.msg.sender, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "DelayOwnerGuard let the Safe call its own setFallbackHandler";
}

/*
 * transferOwnership and renounceOwnership on the Delay are rejected, whatever
 * the new owner.
 */
rule checkTransactionRejectsDelayOwnershipChange(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    address d = delayOwnerGuard.delay();
    require d != e.msg.sender;
    uint32 sel = selectorOf(data);
    require sel == TRANSFER_OWNERSHIP() || sel == RENOUNCE_OWNERSHIP();

    delayOwnerGuard.checkTransaction@withrevert(
        e, d, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "DelayOwnerGuard let the Safe transfer or renounce the Delay";
}

/*
 * enableModule on the Delay is rejected, whatever the module.
 */
rule checkTransactionRejectsDelayEnableModule(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    address d = delayOwnerGuard.delay();
    require d != e.msg.sender;
    require selectorOf(data) == ENABLE_MODULE();

    delayOwnerGuard.checkTransaction@withrevert(
        e, d, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "DelayOwnerGuard let the Safe enable a module on the Delay";
}

/*
 * setGuard on the Delay is rejected, whatever the new guard, so PauseGuard
 * cannot be taken off.
 */
rule checkTransactionRejectsDelaySetGuard(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    address d = delayOwnerGuard.delay();
    require d != e.msg.sender;
    require selectorOf(data) == SET_GUARD();

    delayOwnerGuard.checkTransaction@withrevert(
        e, d, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "DelayOwnerGuard let the Safe change the Delay's guard";
}

/*
 * setAvatar and setTarget on the Delay are rejected, whatever the address.
 */
rule checkTransactionRejectsDelaySetAvatarOrTarget(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    address d = delayOwnerGuard.delay();
    require d != e.msg.sender;
    uint32 sel = selectorOf(data);
    require sel == SET_AVATAR() || sel == SET_TARGET();

    delayOwnerGuard.checkTransaction@withrevert(
        e, d, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "DelayOwnerGuard let the Safe change the Delay's avatar or target";
}

/*
 * Nothing else is rejected: a plain call that is not one of the locked calls
 * above always passes, whatever the destination, value and calldata. So the
 * eight rules above are exactly what the guard blocks. This covers
 * Delay.setTxNonce, every other Delay and Safe function, and any call with
 * less than four bytes of calldata.
 */
rule checkTransactionAcceptsEverythingElse(
    address to, uint256 value, bytes data,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require e.msg.value == 0;
    require !isLockedCall(to, e.msg.sender, delayOwnerGuard.delay(), selectorOf(data));

    delayOwnerGuard.checkTransaction@withrevert(
        e, to, value, data, Enum.Operation.Call,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert !lastReverted,
        "DelayOwnerGuard rejected a plain call that is not one of the locked calls";
}

/* ------------------------------------------------------------------------
 * 2. Installing it
 * --------------------------------------------------------------------- */

/*
 * With no guard yet, the owners' execTransaction of setGuard(DelayOwnerGuard)
 * on the Safe succeeds and the guard slot then holds it. v1.4.1's setGuard
 * probes the new guard with supportsInterface (GuardManager.sol:55), which
 * runs the real DelayOwnerGuard here, so this also shows the probe passes.
 */
rule ownersCanInstallDelayOwnerGuard(
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

    satisfy !lastReverted && guardAddress() == delayOwnerGuard,
        "the owners could not install DelayOwnerGuard with setGuard";
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
    require guardAddress() == delayOwnerGuard;
    require selectorOf(data) == SET_GUARD();

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with DelayOwnerGuard installed, the Safe called its own setGuard";
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
    require guardAddress() == delayOwnerGuard;
    require selectorOf(data) == ENABLE_MODULE();

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with DelayOwnerGuard installed, the Safe called its own enableModule";
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
    require guardAddress() == delayOwnerGuard;
    require selectorOf(data) == SET_FALLBACK_HANDLER();

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with DelayOwnerGuard installed, the Safe called its own setFallbackHandler";
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
    require guardAddress() == delayOwnerGuard;

    execTransaction@withrevert(e,
        to, value, data, Enum.Operation.DelegateCall,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with DelayOwnerGuard installed, the Safe made a delegate call";
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
    require guardAddress() == delayOwnerGuard;

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert guardAddress() == delayOwnerGuard,
        "an execTransaction to the Safe itself moved DelayOwnerGuard out of the guard slot";
}

/*
 * For any calldata and operation, an execTransaction addressed to the Safe
 * itself enables no module: an address that was not in the module list is
 * still not in it. disableModule stays open, and can only remove.
 */
rule guardedSelfCallNeverEnablesAModule(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address a
) {
    env e;
    require guardAddress() == delayOwnerGuard;
    require moduleEntry(a) == 0;

    execTransaction@withrevert(e,
        currentContract, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert moduleEntry(a) == 0,
        "an execTransaction to the Safe itself added a module";
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
    require guardAddress() == delayOwnerGuard;
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
 * A plain call to an address other than the Safe and the Delay still succeeds
 * with the guard installed. Also the non-vacuity witness for section 3: the
 * guard does not block everything.
 */
rule guardedOwnersCanStillCallOut(
    address to, uint256 value, bytes data,
    uint256 safeTxGas, uint256 baseGas,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require thresholdValue() > 0;
    require guardAddress() == delayOwnerGuard;
    require to != currentContract;
    require to != delayOwnerGuard.delay();

    execTransaction@withrevert(e,
        to, value, data, Enum.Operation.Call,
        safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted,
        "with DelayOwnerGuard installed, the Safe could not make a plain call to another contract";
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
    require guardAddress() == delayOwnerGuard;
    require selectorOf(data) == f.selector;

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);

    execTransaction@withrevert(e,
        currentContract, 0, data, Enum.Operation.Call,
        safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore),
        "with DelayOwnerGuard installed, the owners could not use this settings function";
}

/* ------------------------------------------------------------------------
 * 5. The module path
 * --------------------------------------------------------------------- */

/*
 * The guard does not see module transactions. With DelayOwnerGuard installed,
 * an enabled module's execTransactionFromModule addressed to the Safe with a
 * setGuard call succeeds and moves the guard slot, which section 3 shows the
 * owners cannot do. So the module path is bounded by what the module itself
 * may send, not by this guard.
 */
rule moduleCallBypassesTheGuard(bytes data) {
    env e;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;
    require guardAddress() == delayOwnerGuard;
    require selectorOf(data) == SET_GUARD();

    bool success = execTransactionFromModule@withrevert(
        e, currentContract, 0, data, Enum.Operation.Call);

    satisfy !lastReverted && success && guardAddress() != delayOwnerGuard,
        "an enabled module could not move the guard slot, so the module path might be guarded";
}

/* ------------------------------------------------------------------------
 * 6. Once installed, the Safe's half of the Delay lock
 * --------------------------------------------------------------------- */

/*
 * An execTransaction addressed to the Delay whose calldata starts with any of
 * the six locked selectors reverts, whatever the arguments, value and
 * operation. The guard runs before the Safe makes its call, so the Delay is
 * never reached and does not need to be in this scene. With OG-14 (no
 * delegate calls), every execTransaction to the Delay that succeeds is a
 * plain call carrying some other selector; specs/Delay/delayOwnerGuard.spec
 * shows no such call changes the Delay's owner, modules, guard, avatar or
 * target.
 */
rule guardedSafeCannotCallLockedDelayFunctions(
    uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require guardAddress() == delayOwnerGuard;
    address d = delayOwnerGuard.delay();
    require d != currentContract;
    require isLockedDelaySelector(selectorOf(data));

    execTransaction@withrevert(e,
        d, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert lastReverted,
        "with DelayOwnerGuard installed, the Safe called a locked function on the Delay";
}
