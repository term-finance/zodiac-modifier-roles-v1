/*
 * DEVOPS_ROLE methods end to end: the Term multisig holders on the
 * ProposerSafe, through the Delay Modifier, and the Term multisig holders on
 * the OwnerlessSafe, directly, can make the OwnerlessSafe run a DEVOPS_ROLE
 * method, provided the call is not vetoed.
 *
 * The scene is the real GnosisSafe v1.3.0 twice (ProposerSafeHarness, and
 * OwnerlessSafeHarness as the main contract), the real Delay
 * (certora/helpers/Delay.sol) with the OwnerlessSafe as its target and
 * PauseGuard as its guard, and DevopsRoleTarget, a DEVOPS_ROLE method behind
 * OpenZeppelin's onlyRole(DEVOPS_ROLE). Each Safe's threshold is 1;
 * ownersCanMakeTheSafeAct (SE-6) covers any threshold. No guard is installed
 * on either Safe.
 */

using ProposerSafeHarness as proposerSafe;
using Delay as delayContract;
using PauseGuard as pauseGuard;
using DevopsRoleTarget as protocol;
using CalldataReader as reader;

methods {
    // The OwnerlessSafe, the scene's main contract.
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function guardAddress() external returns (address) envfree;
    function nonce() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function proposerSafe.ownerEntry(address) external returns (address) envfree;
    function proposerSafe.thresholdValue() external returns (uint256) envfree;
    function proposerSafe.guardAddress() external returns (address) envfree;
    function proposerSafe.nonce() external returns (uint256) envfree;

    function delayContract.guard() external returns (address) envfree;
    function delayContract.target() external returns (address) envfree;
    function delayContract.isModuleEnabled(address) external returns (bool) envfree;
    function delayContract.txNonce() external returns (uint256) envfree;
    function delayContract.queueNonce() external returns (uint256) envfree;
    function delayContract.txCooldown() external returns (uint256) envfree;
    function delayContract.txExpiration() external returns (uint256) envfree;
    function delayContract.txCreatedAt(uint256) external returns (uint256) envfree;

    function pauseGuard.paused() external returns (bool) envfree;

    function protocol.DEVOPS_ROLE() external returns (bytes32) envfree;
    function protocol.hasRole(bytes32, address) external returns (bool) envfree;
    function protocol.lastValue() external returns (uint256) envfree;
    function protocol.lastCaller() external returns (address) envfree;

    function reader.wordAfterSelector(bytes) external returns (uint256) envfree;
    function reader.wordAtByte(bytes, uint256) external returns (uint256) envfree;
    function reader.addressAtByte(bytes, uint256) external returns (address) envfree;
    function reader.isApprovedHashSig(bytes, address) external returns (bool) envfree;

    // The ProposerSafe's call to `to`, run as the call to the Delay it makes
    // on chain.
    unresolved external in ProposerSafeHarness._ => DISPATCH [
        Delay.execTransactionFromModule(address, uint256, bytes, Enum.Operation)
    ] default NONDET;

    // The OwnerlessSafe's call to `to`, run as the call to the protocol
    // contract's DEVOPS_ROLE method.
    unresolved external in OwnerlessSafeHarness._ => DISPATCH [
        DevopsRoleTarget.devopsMethod(uint256)
    ] default NONDET;
}

/// Head of the Safes' owner and module lists.
definition SENTINEL() returns address = 0x1;

/// The length of the call to the DEVOPS_ROLE method: the selector and one
/// 32-byte word.
definition DEVOPS_CALL_LENGTH() returns uint256 = 36;

/// The length of the ProposerSafe's call to the Delay that carries it (see
/// isQueueCall).
definition QUEUE_CALL_LENGTH() returns uint256 = 228;

/// P1.1: the OwnerlessSafe holds DEVOPS_ROLE on the protocol contract, and
/// the scene's other callers do not.
function onlyTheOwnerlessSafeHoldsDevopsRole(address owner) {
    bytes32 devopsRole = protocol.DEVOPS_ROLE();
    require protocol.hasRole(devopsRole, currentContract);
    require !protocol.hasRole(devopsRole, proposerSafe);
    require !protocol.hasRole(devopsRole, delayContract);
    require !protocol.hasRole(devopsRole, owner);
}

/// `data` is the call to the DEVOPS_ROLE method with argument `v`, and the
/// method has not already recorded `v`.
function devopsCall(bytes data, uint256 v) {
    require data.length == DEVOPS_CALL_LENGTH();
    require selectorOf(data) == sig:DevopsRoleTarget.devopsMethod(uint256).selector;
    require reader.wordAfterSelector(data) == v;
    require protocol.lastValue() != v;
}

/*
 * `q` is the ABI encoding of the Delay's execTransactionFromModule(to, 0,
 * inner, Call), with `inner` 36 bytes long:
 *   bytes 0-3          the selector
 *   bytes 4-35         to
 *   bytes 36-67        value, 0
 *   bytes 68-99        the offset of `data`, 128
 *   bytes 100-131      operation, 0 (Call)
 *   bytes 132-163      the length of `data`, 36
 *   bytes 164-199      `data`, then zero padding to byte 227
 *
 * The 36 bytes of `data` are compared by two overlapping 32-byte windows, at
 * its start and at its end.
 */
function isQueueCall(bytes q, address to, bytes inner) returns bool {
    return
        selectorOf(q) == sig:Delay.execTransactionFromModule(address, uint256, bytes, Enum.Operation).selector &&
        reader.addressAtByte(q, 4) == to &&
        reader.wordAtByte(q, 36) == 0 &&
        reader.wordAtByte(q, 68) == 128 &&
        reader.wordAtByte(q, 100) == 0 &&
        reader.wordAtByte(q, 132) == DEVOPS_CALL_LENGTH() &&
        reader.wordAtByte(q, 164) == reader.wordAtByte(inner, 0) &&
        reader.wordAtByte(q, 168) == reader.wordAtByte(inner, 4);
}

/*
 * DE-1. A Term multisig holder on the ProposerSafe approves the ProposerSafe
 * transaction that proposes a DEVOPS_ROLE method call to the Delay, and
 * anyone submits it: the Delay queues the proposal. Nobody vetoes it, and
 * once the cooldown has passed, before it expires and while the PauseGuard
 * is not paused, anyone's executeNextTx runs it: the OwnerlessSafe calls the
 * protocol contract and the DEVOPS_ROLE method runs, called by the
 * OwnerlessSafe.
 */
rule proposerOwnersExecuteDevopsMethodThroughTheDelay(
    address owner, uint256 v, bytes inner, bytes queueData, bytes signatures
) {
    env eApprove;
    env eQueue;
    env eExec;

    // The deployed wiring: the ProposerSafe is a module of the Delay, the
    // Delay is a module of the OwnerlessSafe and its target, the PauseGuard
    // is the Delay's guard and is not paused, and neither Safe has a guard.
    require delayContract.isModuleEnabled(proposerSafe);
    require delayContract != SENTINEL();
    require moduleEntry(delayContract) != 0;
    require delayContract.target() == currentContract;
    require delayContract.guard() == pauseGuard;
    require !pauseGuard.paused();
    require guardAddress() == 0;
    require proposerSafe.guardAddress() == 0;
    onlyTheOwnerlessSafeHoldsDevopsRole(owner);

    // One owner of the ProposerSafe is the whole threshold, and signs with
    // its approval.
    require proposerSafe.thresholdValue() == 1;
    require owner != 0 && owner != SENTINEL();
    require proposerSafe.ownerEntry(owner) != 0;
    require reader.isApprovedHashSig(signatures, owner);
    require eApprove.msg.sender == owner;

    // The proposal: the OwnerlessSafe's call to the DEVOPS_ROLE method,
    // carried in the ProposerSafe's call to the Delay.
    devopsCall(inner, v);
    require queueData.length == QUEUE_CALL_LENGTH();
    require isQueueCall(queueData, protocol, inner);

    // The Delay's queue starts empty.
    require delayContract.txNonce() == delayContract.queueNonce();
    require delayContract.queueNonce() < max_uint256;
    uint256 slot = delayContract.queueNonce();

    // 1. The owner approves the ProposerSafe transaction and anyone submits
    // it; the ProposerSafe calls the Delay, which queues the proposal.
    bytes32 txHash = proposerSafe.getTransactionHash(eQueue,
        delayContract, 0, queueData, Enum.Operation.Call, 0, 0, 0, 0, 0, proposerSafe.nonce());
    proposerSafe.approveHash(eApprove, txHash);
    proposerSafe.execTransaction(eQueue,
        delayContract, 0, queueData, Enum.Operation.Call, 0, 0, 0, 0, 0, signatures);

    // Nobody vetoes it: no setTxNonce runs before step 2, so the proposal is
    // still at txNonce.

    // 2. After the cooldown, and before the proposal expires, anyone executes
    // it.
    uint256 createdAt = delayContract.txCreatedAt(slot);
    require eExec.msg.value == 0;
    require eExec.block.timestamp >= createdAt;
    require eExec.block.timestamp - createdAt >= delayContract.txCooldown();
    require createdAt + delayContract.txCooldown() + delayContract.txExpiration() <= max_uint256;
    require delayContract.txExpiration() == 0 ||
        createdAt + delayContract.txCooldown() + delayContract.txExpiration() >= to_mathint(eExec.block.timestamp);

    delayContract.executeNextTx@withrevert(eExec, protocol, 0, inner, Enum.Operation.Call);
    bool executed = !lastReverted;

    satisfy executed &&
        to_mathint(delayContract.txNonce()) == slot + 1 &&
        protocol.lastValue() == v &&
        protocol.lastCaller() == currentContract,
        "a ProposerSafe owner's proposal could not get through the Delay to make the OwnerlessSafe run a DEVOPS_ROLE method";
}

/*
 * DE-2. A Term multisig holder on the OwnerlessSafe approves the
 * OwnerlessSafe transaction that calls the DEVOPS_ROLE method, and anyone
 * submits it with that approval as the signature: execTransaction succeeds
 * and the DEVOPS_ROLE method runs, called by the OwnerlessSafe.
 */
rule ownerlessOwnersExecuteDevopsMethodThroughExecTransaction(
    address owner, uint256 v, bytes data, bytes signatures
) {
    env eApprove;
    env eExec;

    // The OwnerlessSafe has no guard and holds DEVOPS_ROLE.
    require guardAddress() == 0;
    onlyTheOwnerlessSafeHoldsDevopsRole(owner);

    // One owner of the OwnerlessSafe is the whole threshold, and signs with
    // its approval.
    require thresholdValue() == 1;
    require owner != 0 && owner != SENTINEL();
    require ownerEntry(owner) != 0;
    require reader.isApprovedHashSig(signatures, owner);
    require eApprove.msg.sender == owner;

    // The transaction: the OwnerlessSafe's call to the DEVOPS_ROLE method.
    devopsCall(data, v);

    // The owner approves it and anyone submits it.
    bytes32 txHash = getTransactionHash(eExec,
        protocol, 0, data, Enum.Operation.Call, 0, 0, 0, 0, 0, nonce());
    approveHash(eApprove, txHash);
    execTransaction@withrevert(eExec,
        protocol, 0, data, Enum.Operation.Call, 0, 0, 0, 0, 0, signatures);

    satisfy !lastReverted &&
        protocol.lastValue() == v &&
        protocol.lastCaller() == currentContract,
        "an OwnerlessSafe owner's approved transaction could not make the OwnerlessSafe run a DEVOPS_ROLE method";
}
