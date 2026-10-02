/*
 * Property: the Term multisig holders on the DelayOwnerSafe can change the
 * Delay Modifier's owner, target, modules, guard, txCooldown and txExpiration
 * through the signed path, end to end, with the real signature check.
 *
 * It covers P4.DelayModifier.13. The Delay Modifier's owner is the
 * DelayOwnerSafe (P2.3 in PROOFS.md), so a Safe transaction addressed to the
 * Delay is how the Term multisig holders reach these settings. The flow is the
 * one the owners use:
 *   1. an owner calls approveHash on the hash of a Safe transaction that calls
 *      one of the Delay's settings functions;
 *   2. anyone calls execTransaction with that approval as the signature;
 *   3. the Safe's signature check runs for real, the Safe calls the Delay, the
 *      Delay's onlyOwner check sees the Safe, and the setting changes.
 * The signature check is the real one: the owner's approval is what lets the
 * call through. Every setting the statement names is covered, and the veto,
 * setTxNonce, is specs/Delay/vetoSignedPath.spec.
 *
 * The scene is the real Safe v1.4.1 code through SafeV141Harness (solc 0.7.6)
 * and the real Delay mastercopy source, certora/helpers/Delay.sol (solc 0.8.6).
 * No guard is installed on the Safe.
 *
 * Why witnesses (satisfy) and not asserts. execTransaction reads gasleft()
 * (GS010), which the Prover treats as an unconstrained value, so "does not
 * revert" cannot be asserted for every execution. Each rule shows an
 * execution exists in which the owner's approval alone makes the Delay change
 * the setting. That is what "can be changed by the Term multisig holders"
 * needs.
 *
 * Rules, by setting:
 *   owner                 ownersApprovalTransfersOwnership
 *   target                ownersApprovalSetsTarget
 *   modules               ownersApprovalEnablesModule, ownersApprovalDisablesModule
 *   guard                 ownersApprovalSetsGuard
 *   txCooldown            ownersApprovalSetsTxCooldown
 *   txExpiration          ownersApprovalSetsTxExpiration
 * The veto, setTxNonce, is vetoSignedPath.spec.
 *
 * Modelling notes.
 *   - The threshold is 1 and the owner's approval is the one signature. The
 *     Prover unrolls the signature loop once (loop_iter 1); the deployed
 *     threshold is larger. The loop is covered one pass at a time by
 *     eachSignatureAcceptsANewApprovingOwner (SE141-12), and a threshold-t
 *     check only repeats that pass t times.
 *   - The Safe's call to the Delay is a low-level `call` with a symbolic
 *     target, which the Prover cannot resolve. The DISPATCH declaration routes
 *     it to the Delay function the call names, where it lands on chain.
 *     DISPATCH ignores `to`, so each rule pins `to` to the Delay. As in
 *     delayOwnerGuard.spec, each rule pins the calldata to one call of fixed
 *     length: with arbitrary calldata routed into the Delay's functions the
 *     Prover (certora-cli 7.31.0) stops with an internal error.
 *   - setGuard probes the new guard with ERC-165's supportsInterface. No guard
 *     contract is in the scene, so the probe is NONDET: the witness is a guard
 *     that answers yes, as PauseGuard does (DP-2 in PAUSEGUARD_PROOFS.md).
 */

using Delay as delayContract;
using CalldataReader as reader;

methods {
    function thresholdValue() external returns (uint256) envfree;
    function guardAddress() external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function nonce() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function delayContract.owner() external returns (address) envfree;
    function delayContract.target() external returns (address) envfree;
    function delayContract.guard() external returns (address) envfree;
    function delayContract.txCooldown() external returns (uint256) envfree;
    function delayContract.txExpiration() external returns (uint256) envfree;
    function delayContract.isModuleEnabled(address) external returns (bool) envfree;

    function reader.wordAtByte(bytes, uint256) external returns (uint256) envfree;
    function reader.addressAtByte(bytes, uint256) external returns (address) envfree;
    function reader.isApprovedHashSig(bytes, address) external returns (bool) envfree;

    // setGuard's ERC-165 probe of the new guard.
    function _.supportsInterface(bytes4) external => NONDET;

    // The Safe's call to `to`, run as a call to the Delay function it names.
    unresolved external in SafeV141Harness._ => DISPATCH [
        Delay.setTxCooldown(uint256),
        Delay.setTxExpiration(uint256),
        Delay.setTarget(address),
        Delay.enableModule(address),
        Delay.disableModule(address, address),
        Delay.setGuard(address),
        Delay.transferOwnership(address)
    ] default NONDET;
}

/// Head of the Safe's owner list.
definition SENTINEL() returns address = 0x1;

/// The Safe owns the Delay, has one owner who is the signer, and has no guard.
definition ownedByTheSafe(address owner) returns bool =
    thresholdValue() == 1 &&
    guardAddress() == 0 &&
    owner != SENTINEL() &&
    ownerEntry(owner) != 0 &&
    delayContract != currentContract &&
    delayContract.owner() == currentContract;

/*
 * The owner approves the hash of the Safe's call to the Delay, and anyone
 * submits the transaction with that approval as the signature. True if the
 * transaction did not revert.
 */
function ownersApprovedCallLands(address owner, bytes data, bytes signatures) returns bool {
    env eApprove;
    env eExec;
    require eApprove.msg.sender == owner;

    bytes32 txHash = getTransactionHash(eExec,
        delayContract, 0, data, Enum.Operation.Call, 0, 0, 0, 0, 0, nonce());
    approveHash(eApprove, txHash);

    execTransaction@withrevert(eExec,
        delayContract, 0, data, Enum.Operation.Call, 0, 0, 0, 0, 0, signatures);
    return !lastReverted;
}

/* ------------------------------------------------------------------------
 * txCooldown and txExpiration
 * --------------------------------------------------------------------- */

/// setTxCooldown(c) through the owners' approval sets the Delay's txCooldown to c.
rule ownersApprovalSetsTxCooldown(address owner, uint256 c, bytes data, bytes signatures) {
    require ownedByTheSafe(owner);
    require data.length == 36;
    require selectorOf(data) == sig:Delay.setTxCooldown(uint256).selector;
    require reader.wordAtByte(data, 4) == c;
    require reader.isApprovedHashSig(signatures, owner);
    require delayContract.txCooldown() != c;

    bool landed = ownersApprovedCallLands(owner, data, signatures);

    satisfy landed && delayContract.txCooldown() == c,
        "the owners' approved hash could not set the Delay's txCooldown";
}

/// setTxExpiration(x) through the owners' approval sets the Delay's txExpiration to x.
rule ownersApprovalSetsTxExpiration(address owner, uint256 x, bytes data, bytes signatures) {
    require ownedByTheSafe(owner);
    require data.length == 36;
    require selectorOf(data) == sig:Delay.setTxExpiration(uint256).selector;
    require reader.wordAtByte(data, 4) == x;
    require reader.isApprovedHashSig(signatures, owner);
    require delayContract.txExpiration() != x;

    bool landed = ownersApprovedCallLands(owner, data, signatures);

    satisfy landed && delayContract.txExpiration() == x,
        "the owners' approved hash could not set the Delay's txExpiration";
}

/* ------------------------------------------------------------------------
 * target, guard and owner
 * --------------------------------------------------------------------- */

/// setTarget(t) through the owners' approval sets the Delay's target to t.
rule ownersApprovalSetsTarget(address owner, address t, bytes data, bytes signatures) {
    require ownedByTheSafe(owner);
    require data.length == 36;
    require selectorOf(data) == sig:Delay.setTarget(address).selector;
    require reader.addressAtByte(data, 4) == t;
    require reader.isApprovedHashSig(signatures, owner);
    require delayContract.target() != t;

    bool landed = ownersApprovedCallLands(owner, data, signatures);

    satisfy landed && delayContract.target() == t,
        "the owners' approved hash could not set the Delay's target";
}

/// setGuard(g) through the owners' approval sets the Delay's guard to g.
rule ownersApprovalSetsGuard(address owner, address g, bytes data, bytes signatures) {
    require ownedByTheSafe(owner);
    require data.length == 36;
    require selectorOf(data) == sig:Delay.setGuard(address).selector;
    require reader.addressAtByte(data, 4) == g;
    require reader.isApprovedHashSig(signatures, owner);
    require delayContract.guard() != g;

    bool landed = ownersApprovedCallLands(owner, data, signatures);

    satisfy landed && delayContract.guard() == g,
        "the owners' approved hash could not set the Delay's guard";
}

/// transferOwnership(o) through the owners' approval moves the Delay's owner to o.
rule ownersApprovalTransfersOwnership(address owner, address o, bytes data, bytes signatures) {
    require ownedByTheSafe(owner);
    require data.length == 36;
    require selectorOf(data) == sig:Delay.transferOwnership(address).selector;
    require reader.addressAtByte(data, 4) == o;
    require reader.isApprovedHashSig(signatures, owner);
    require o != currentContract;

    bool landed = ownersApprovedCallLands(owner, data, signatures);

    satisfy landed && delayContract.owner() == o,
        "the owners' approved hash could not transfer the Delay's ownership";
}

/* ------------------------------------------------------------------------
 * modules
 * --------------------------------------------------------------------- */

/// enableModule(m) through the owners' approval enables m on the Delay.
rule ownersApprovalEnablesModule(address owner, address m, bytes data, bytes signatures) {
    require ownedByTheSafe(owner);
    require data.length == 36;
    require selectorOf(data) == sig:Delay.enableModule(address).selector;
    require reader.addressAtByte(data, 4) == m;
    require reader.isApprovedHashSig(signatures, owner);
    require !delayContract.isModuleEnabled(m);

    bool landed = ownersApprovedCallLands(owner, data, signatures);

    satisfy landed && delayContract.isModuleEnabled(m),
        "the owners' approved hash could not enable a module on the Delay";
}

/// disableModule(prev, m) through the owners' approval disables m on the Delay.
rule ownersApprovalDisablesModule(
    address owner, address prev, address m, bytes data, bytes signatures
) {
    require ownedByTheSafe(owner);
    require data.length == 68;
    require selectorOf(data) == sig:Delay.disableModule(address, address).selector;
    require reader.addressAtByte(data, 4) == prev;
    require reader.addressAtByte(data, 36) == m;
    require reader.isApprovedHashSig(signatures, owner);
    require delayContract.isModuleEnabled(m);

    bool landed = ownersApprovedCallLands(owner, data, signatures);

    satisfy landed && !delayContract.isModuleEnabled(m),
        "the owners' approved hash could not disable a module on the Delay";
}
