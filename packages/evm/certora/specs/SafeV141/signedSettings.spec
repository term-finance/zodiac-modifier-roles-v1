/*
 * Property: the Term multisig holders on the DelayOwnerSafe (Safe v1.4.1) can
 * change the Safe's owners, threshold, modules, guard and fallback handler
 * through the signed path, end to end, with the real signature check.
 *
 * It covers P4.DelayOwnerSafe.10. The DelayOwnerSafe runs Safe v1.4.1, a
 * different mastercopy from the Proposer and Ownerless Safes' v1.3.0 (P2.4 in
 * PROOFS.md), so specs/Safe/signedSettings.spec does not stand for it: the
 * same rule is stated here on SafeV141Harness, the real v1.4.1 code.
 *
 * The flow is the one the owners use:
 *   1. an owner calls approveHash on the hash of the settings transaction,
 *      a call of the Safe to one of its own settings functions;
 *   2. anyone calls execTransaction with that approval as the signature;
 *   3. the Safe's signature check runs for real, the Safe calls itself, and
 *      the setting changes.
 * specs/SafeV141/selfCalls.spec (ownersCanChangeSettings) shows the Safe can
 * make each settings call, with the signature check stubbed out. Here the
 * check is the real one, so the rule only passes if the owner's approval is
 * what lets the transaction through.
 *
 * Why a witness (satisfy) and not an assert. execTransaction reads gasleft()
 * (GS010), which the Prover treats as an unconstrained value, so "does not
 * revert" cannot be asserted for every execution. The rule shows an execution
 * exists in which the owner's approval alone makes the Safe change each
 * setting. That is what "can be changed by the Term multisig holders" needs.
 *
 * Modelling notes.
 *   - The threshold is 1 and the owner's approval is the one signature. The
 *     Prover unrolls the signature loop once (loop_iter 1); the deployed
 *     threshold is larger. The loop is covered one pass at a time by
 *     eachSignatureAcceptsANewApprovingOwner (SE141-12), and a threshold-t
 *     check only repeats that pass t times.
 *   - No guard is installed, and gasPrice is 0, so the settings call is the
 *     transaction's only outgoing call.
 *   - The Safe's call to itself is a low-level `call` with a symbolic target,
 *     which the Prover cannot resolve. The DISPATCH declaration routes it to
 *     the matching settings function on the Safe, which is what happens on
 *     chain when `to` is the Safe itself. DISPATCH ignores `to`, so the rule
 *     pins `to` to the Safe. Any other call the Safe makes is routed the same
 *     way (the new guard's ERC-165 probe in setGuard is havoced).
 *   - `data` is pinned to the length of its call, so the Prover does not
 *     reason about a symbolic-length payload through the hash.
 */

using CalldataReader as reader;

methods {
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function guardAddress() external returns (address) envfree;
    function fallbackHandlerSlotWord() external returns (uint256) envfree;
    function nonce() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function reader.isApprovedHashSig(bytes, address) external returns (bool) envfree;

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

definition isSelfOnlySetting(method f) returns bool =
    f.selector == sig:enableModule(address).selector ||
    f.selector == sig:disableModule(address, address).selector ||
    f.selector == sig:addOwnerWithThreshold(address, uint256).selector ||
    f.selector == sig:removeOwner(address, address, uint256).selector ||
    f.selector == sig:swapOwner(address, address, address).selector ||
    f.selector == sig:changeThreshold(uint256).selector ||
    f.selector == sig:setGuard(address).selector ||
    f.selector == sig:setFallbackHandler(address).selector;

/// The length of the call to each settings function: the selector, then one
/// 32-byte word per argument.
definition settingCallLength(method f) returns uint256 =
    (f.selector == sig:disableModule(address, address).selector ||
     f.selector == sig:addOwnerWithThreshold(address, uint256).selector) ? 68 :
    (f.selector == sig:removeOwner(address, address, uint256).selector ||
     f.selector == sig:swapOwner(address, address, address).selector) ? 100 :
    36;

/*
 * An owner's approval is enough for the Safe to change each setting: for each
 * of the eight settings functions, an owner approves the hash of the Safe's
 * call to it, anyone submits the transaction with that approval as the
 * signature, and a setting changes. `f` only picks which function's selector
 * the call carries.
 */
rule ownersApprovalChangesSettings(
    method f, address owner, address a, bytes data, bytes signatures
)
    filtered { f -> isSelfOnlySetting(f) }
{
    env eApprove;
    env eExec;
    require eApprove.msg.sender == owner;

    // The threshold is one and the owner is the signer; no guard installed.
    require thresholdValue() == 1;
    require guardAddress() == 0;
    require owner != SENTINEL();
    require ownerEntry(owner) != 0;

    // The Safe's call to one of its own settings functions, signed with the
    // owner's approved hash.
    require data.length == settingCallLength(f);
    require selectorOf(data) == f.selector;
    require reader.isApprovedHashSig(signatures, owner);

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    uint256 handlerBefore = fallbackHandlerSlotWord();

    // The owner approves this exact transaction.
    bytes32 txHash = getTransactionHash(eExec,
        currentContract, 0, data, Enum.Operation.Call, 0, 0, 0, 0, 0, nonce());
    approveHash(eApprove, txHash);

    // Anyone submits it.
    execTransaction@withrevert(eExec,
        currentContract, 0, data, Enum.Operation.Call, 0, 0, 0, 0, 0, signatures);

    satisfy !lastReverted && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != 0 ||
        fallbackHandlerSlotWord() != handlerBefore),
        "an owner's approved hash could not make the Safe change a setting through this settings function";
}
