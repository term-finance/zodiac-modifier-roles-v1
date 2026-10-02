/*
 * Property: the Term multisig holders on the ProposerSafe and the Term
 * multisig holders on the OwnerlessSafe may execute DEVOPS_ROLE methods,
 * provided the DEVOPS_ROLE method call is not vetoed (P1.13 in PROOFS.md).
 * One end-to-end rule for each group of holders.
 *
 * Only the OwnerlessSafe holds DEVOPS_ROLE on the protocol contracts (P1.1),
 * so a DEVOPS_ROLE method runs when the OwnerlessSafe calls it. Its own owners
 * make it call directly, through execTransaction. The ProposerSafe's owners
 * make it call through the Delay Modifier: the ProposerSafe is the Delay's one
 * module (P1.8) and the Delay is the OwnerlessSafe's one module (P1.5).
 *
 *   proposerOwnersExecuteDevopsMethodThroughTheDelay (DE-1)
 *     ProposerSafe owner --approveHash, execTransaction--> ProposerSafe
 *       --execTransactionFromModule--> Delay, which queues the proposal
 *     the cooldown passes, nobody vetoes, the PauseGuard is not paused
 *     anyone --executeNextTx--> Delay (+ PauseGuard)
 *       --execTransactionFromModule--> OwnerlessSafe
 *       --call--> protocol contract, onlyRole(DEVOPS_ROLE)
 *
 *   ownerlessOwnersExecuteDevopsMethodThroughExecTransaction (DE-2)
 *     OwnerlessSafe owner --approveHash, execTransaction--> OwnerlessSafe
 *       --call--> protocol contract, onlyRole(DEVOPS_ROLE)
 *
 * DE-1 runs in one execution what DM-5 (a module queues), DP-29 (a queued
 * transaction executes after the cooldown) and SE-6 (the OwnerlessSafe makes
 * the call) cover in pieces. DE-2 does the same for SE-5, SE-8, SE-12 and
 * SE-6. Each rule ends at the protocol contract's role check, and only passes
 * if the method behind it runs, called by the OwnerlessSafe.
 *
 * The scene:
 *   - the real GnosisSafe v1.3.0 code twice, as ProposerSafeHarness and
 *     OwnerlessSafeHarness (solc 0.7.6), as in
 *     proposerToOwnerlessSettings.spec;
 *   - the real Delay mastercopy source, certora/helpers/Delay.sol (solc
 *     0.8.6), whose target is linked to the OwnerlessSafe and whose guard is
 *     linked to PauseGuard;
 *   - the PauseGuard source, contracts/helpers/PauseGuard.sol;
 *   - DevopsRoleTarget, a protocol contract's DEVOPS_ROLE method behind
 *     OpenZeppelin's onlyRole(DEVOPS_ROLE), on the same OpenZeppelin v5
 *     AccessControl code the protocol runs (see its header).
 * No guard is installed on either Safe.
 *
 * Not vetoed. A veto moves the Delay's txNonce past the proposal's nonce
 * with setTxNonce (P2.13). In DE-1 nobody calls setTxNonce between the
 * queueing and the execution, so the proposal is still at txNonce when
 * executeNextTx runs. DP-32 and DP-33 show that a vetoed proposal cannot
 * execute.
 *
 * Why a witness (satisfy) and not an assert. As in DV-1
 * (vetoSignedPath.spec) and PO-5 (proposerToOwnerlessSettings.spec),
 * execTransaction reads gasleft() (GS010), which the Prover leaves
 * unconstrained, so "does not revert" cannot be asserted for every
 * execution. Each rule shows an execution exists in which the owner's
 * approval is what gets the DEVOPS_ROLE method run. The signature checks are
 * the real ones.
 *
 * Modelling notes.
 *   - Each Safe's threshold is 1 and the owner's approval is the one
 *     signature. The Prover unrolls the signature loop once (loop_iter 1);
 *     the deployed thresholds are 5 (ProposerSafe) and 9 (OwnerlessSafe).
 *     The loop is covered one pass at a time by
 *     eachSignatureAcceptsANewApprovingOwner (SE-12), and a threshold-t
 *     check only repeats that pass t times.
 *   - Each Safe's call is a low-level `call` with a symbolic target, which
 *     the Prover cannot resolve. The ProposerSafe's is routed to
 *     Delay.execTransactionFromModule and the OwnerlessSafe's to
 *     DevopsRoleTarget.devopsMethod, which is what each calls on chain.
 *     DISPATCH ignores `to`, so the rules pin `to`. The routed call keeps
 *     its caller, so the role check sees the OwnerlessSafe.
 *   - The roles are P1.1's: the OwnerlessSafe holds DEVOPS_ROLE, and the
 *     scene's other callers (the ProposerSafe, the Delay and the signing
 *     owner) do not.
 *   - The ProposerSafe's call to the Delay carries the DEVOPS_ROLE call as a
 *     `bytes` argument inside `bytes`. DE-1 pins that calldata word by word,
 *     as proposerToOwnerlessSettings.spec does, so the entry the Delay
 *     queues is the entry executeNextTx runs.
 *   - The conf remaps two OpenZeppelin interface files, IAccessControl and
 *     IERC165, to the vendored v5 tree (certora/vendor/TermToken/lib), so
 *     DevopsRoleTarget compiles against OpenZeppelin v5 while PauseGuard
 *     keeps the repository's OpenZeppelin v4.9.6.
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

/// The length of the ProposerSafe's call to the Delay that carries it: the
/// selector (4 bytes), four head words (to, value, the offset of `data`,
/// operation) and the length of `data` (32 bytes each), which is 164 bytes,
/// then the 36 bytes of `data` padded to 64.
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
 * `q` is the ABI encoding of the Delay's
 * execTransactionFromModule(to, 0, inner, Call), with `inner` 36 bytes long:
 *   bytes 0-3          the selector
 *   bytes 4-35         to
 *   bytes 36-67        value, 0
 *   bytes 68-99        the offset of `data`, 128
 *   bytes 100-131      operation, 0 (Call)
 *   bytes 132-163      the length of `data`, 36
 *   bytes 164-199      `data`, then zero padding to byte 227
 * The 36 bytes of `data` are compared by two overlapping 32-byte windows, at
 * its start and at its end. The caller pins both lengths first: a read past
 * the end of an array reverts, and a revert inside a `require` leaves no
 * execution at all.
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
    // it. The timing is the Delay's own, as in DP-29.
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
