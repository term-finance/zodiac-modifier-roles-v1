/*
 * Property: the Term multisig holders on the DelayOwnerSafe can veto directly
 * from the DelayOwnerSafe, through execTransaction, with the real signature
 * check.
 *
 * The veto is Delay.setTxNonce(n) from the Delay's owner, the DelayOwnerSafe
 * (P2.3 in PROOFS.md). An owner approves the exact veto transaction's hash
 * (approveHash) and signs with that approval, and then execTransaction
 * succeeds and the Delay's txNonce becomes n. The threshold is 1, the most one
 * signature loop pass the Prover unrolls (loop_iter 1); the loop is covered
 * one pass at a time by eachSignatureAcceptsANewApprovingOwner (SE141-12).
 *
 * The scene is the real Safe v1.4.1 through SafeV141Harness (solc 0.7.6) and
 * the real Delay mastercopy source, certora/helpers/Delay.sol (solc 0.8.6).
 * No guard is installed on the Safe.
 *
 * Modelling note. The Safe's call to the Delay is DISPATCHed to
 * Delay.setTxNonce, where it lands on chain, as in
 * specs/Delay/delayOwnerSettings.spec. The rule pins `to` to the Delay.
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

/// Head of the Safe's owner list. The zero address is no owner either, but
/// the Prover does not assume the owner list is well formed, so a rule that
/// needs a real owner has to say so (checkNSignatures requires
/// currentOwner > 0, GS026).
definition SENTINEL() returns address = 0x1;

/*
 * With the Safe owning the Delay, an owner's approval of the exact
 * setTxNonce(n) transaction, used as that owner's
 * signature, lets execTransaction succeed and set the Delay's txNonce to n,
 * for an n the Delay accepts (txNonce < n <= queueNonce).
 *
 * A satisfy, like every other rule here that needs execTransaction to
 * succeed: the Prover leaves gasleft() unconstrained, so it can always pick a
 * run that fails Safe's gas checks (GS010, GS013), which an assert could not
 * rule out. The signature check is the real one: the owner's approval is what
 * lets the call through.
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
