/*
 * DelayOwnerSafe owners veto directly: an owner's approveHash approval of a
 * setTxNonce(n) transaction, used as the signature, lets execTransaction set
 * the Delay's txNonce to n.
 *
 * The scene is the real Safe v1.4.1 (SafeV141Harness) and the real Delay
 * (certora/helpers/Delay.sol), with the Safe as the Delay's owner. The Safe's
 * threshold is 1 and no guard is installed on it; ownersCanMakeTheSafeAct
 * (SE141-6) covers any threshold.
 */

using Delay as delayContract;
using CalldataReader as reader;

methods {
    function guardAddress() external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function nonce() external returns (uint256) envfree;
    function approvedHashes(address, bytes32) external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function delayContract.owner() external returns (address) envfree;
    function delayContract.txNonce() external returns (uint256) envfree;
    function delayContract.queueNonce() external returns (uint256) envfree;

    function reader.wordAfterSelector(bytes) external returns (uint256) envfree;
    function reader.isApprovedHashSig(bytes, address) external returns (bool) envfree;

    // The Safe's call to `to`, run as a call to Delay.setTxNonce.
    unresolved external in SafeV141Harness._ => DISPATCH [
        Delay.setTxNonce(uint256)
    ] default NONDET;
}

/// Head of the Safe's owner list.
definition SENTINEL() returns address = 0x1;

/*
 * With the Safe owning the Delay, an owner's approval of the exact
 * setTxNonce(n) transaction, used as that owner's signature, lets
 * execTransaction succeed and set the Delay's txNonce to n, for an n the
 * Delay accepts (txNonce < n <= queueNonce).
 */
rule approvedOwnersVetoThroughExecTransaction(
    env e, address owner, uint256 n, bytes data, bytes signatures
) {
    // The Safe owns the Delay and has no guard.
    require guardAddress() == 0;
    require delayContract != currentContract;
    require delayContract.owner() == currentContract;

    // One owner is the whole threshold.
    require thresholdValue() == 1;
    require owner != 0 && owner != SENTINEL();
    require ownerEntry(owner) != 0;

    // The veto: setTxNonce(n), for an n the Delay accepts.
    require data.length == 36;
    require selectorOf(data) == sig:Delay.setTxNonce(uint256).selector;
    require reader.wordAfterSelector(data) == n;
    require delayContract.txNonce() < n;
    require n <= delayContract.queueNonce();

    // The owner approved exactly this transaction and signs with that approval.
    bytes32 txHash = getTransactionHash(e,
        delayContract, 0, data, Enum.Operation.Call, 0, 0, 0, 0, 0, nonce());
    require approvedHashes(owner, txHash) == 1;
    require reader.isApprovedHashSig(signatures, owner);

    execTransaction@withrevert(e,
        delayContract, 0, data, Enum.Operation.Call, 0, 0, 0, 0, 0, signatures);

    satisfy !lastReverted && delayContract.txNonce() == n,
        "an owner-approved veto could not land through execTransaction";
}
