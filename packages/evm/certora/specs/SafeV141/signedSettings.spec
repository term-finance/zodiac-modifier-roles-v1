/*
 * Owners' approval changes Safe v1.4.1 settings: an owner approves with
 * approveHash the hash of the Safe's call to one of its own settings
 * functions, anyone submits it through execTransaction with that approval as
 * the signature, and the setting changes. The signature check is the real
 * one.
 *
 * The threshold is 1 and no guard is installed; ownersCanMakeTheSafeAct
 * (SE141-6) covers any threshold. The Safe's call to itself is routed to the
 * matching settings function, with `to` pinned to the Safe.
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
 * For each of the eight settings functions, an owner approves the hash of the
 * Safe's call to it, anyone submits the transaction with that approval as the
 * signature, and a setting changes. `f` picks the selector the call carries.
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
