/*
 * Property: the Delay's half of the ConfigLockGuard lock on the DelayOwnerSafe,
 * plus witnesses that the guarded Safe can still run the Delay.
 *
 * ConfigLockGuard, built with lockedModifier = the Delay and installed on the
 * Safe that owns it, rejects seven calls to the Delay: transferOwnership,
 * renounceOwnership, enableModule, disableModule, setGuard, setAvatar and
 * setTarget. OG-23 (specs/SafeV141/delayOwnerGuard.spec) shows an
 * execTransaction carrying any of them reverts before the Safe makes its
 * call, and OG-16 that the Safe cannot delegate call. So every call the
 * Safe's owners get through to the Delay is a plain call carrying some other
 * selector. This file shows that no such call, from any caller, changes the
 * Delay's owner, modules, guard, avatar or target. Together they give the
 * lock end to end.
 *
 * The proof is split at the Safe's call into the Delay, as GV-2 and GV-3 are
 * in PROOFS.md P2.13. With the Safe routing arbitrary calldata into the
 * Delay's functions, the Prover (certora-cli 7.31.0) stops with an internal
 * error. It does not when the calldata is pinned to one call of fixed length,
 * which is how the witnesses in section 2 are stated.
 *
 * "The guard" in this file always means ConfigLockGuard. The Delay's own
 * guard (PauseGuard on chain) is just a slot here.
 *
 * The scene is the real Delay mastercopy source, certora/helpers/Delay.sol
 * (solc 0.8.6), the real ConfigLockGuard (solc 0.8.6) with its
 * `lockedModifier` linked to the Delay, and the real Safe v1.4.1 through SafeV141Harness (solc 0.7.6)
 * for the witnesses.
 *
 * Rules, by property:
 *
 *   the Delay's half of the lock, over every Delay write function
 *     unlockedDelayCallsNeverChangeOwnerGuardAvatarOrTarget
 *                                                any caller, any function but
 *                                                the seven locked ones and setUp:
 *                                                owner, guard, avatar and
 *                                                target are unchanged
 *     unlockedDelayCallsNeverChangeModules       ... and no module is added
 *                                                or removed
 *     delayAvatarAndTargetOnlyChangeThroughOwnerSetters
 *                                                avatar and target only move
 *                                                through the owner's setAvatar
 *                                                and setTarget
 *
 *   once installed, the Safe still runs the Delay
 *     guardedSafeCanStillVeto                    setTxNonce(n) succeeds and
 *                                                txNonce becomes n
 *     guardedSafeCanStillSetTxCooldown
 *     guardedSafeCanStillSetTxExpiration
 *
 * Modelling notes.
 *   - setUp is left out of the parametric rules. It always reverts after
 *     deployment (DM-1).
 *   - A Delay function that no selector matches does not exist: the Delay has
 *     no fallback (DM-13), so a call with any other selector, or with less
 *     than four bytes of calldata, reverts.
 *   - The Delay's call to its target in executeNextTx is NONDET. A target
 *     that called back into the Delay would do so as itself, which the
 *     parametric rules already cover for any caller.
 *   - checkTransaction, checkAfterExecution and supportsInterface are
 *     DISPATCHER(true), so the real ConfigLockGuard code runs wherever a guard
 *     hook is called: it is the only contract in the scene that implements
 *     them.
 *   - In the witnesses, checkSignatures is NONDET (the signature check
 *     passes; SE141-5 and SE141-12 cover it), and the Safe's call to `to` is
 *     DISPATCHed to the three Delay functions the witnesses use. DISPATCH
 *     ignores `to`, so each witness pins `to` to the Delay.
 */

using Delay as delayContract;
using ConfigLockGuard as configLockGuard;
using CalldataReader as reader;

methods {
    function guardAddress() external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function configLockGuard.lockedModifier() external returns (address) envfree;

    function delayContract.owner() external returns (address) envfree;
    function delayContract.guard() external returns (address) envfree;
    function delayContract.avatar() external returns (address) envfree;
    function delayContract.target() external returns (address) envfree;
    function delayContract.isModuleEnabled(address) external returns (bool) envfree;
    function delayContract.txNonce() external returns (uint256) envfree;
    function delayContract.queueNonce() external returns (uint256) envfree;
    function delayContract.txCooldown() external returns (uint256) envfree;
    function delayContract.txExpiration() external returns (uint256) envfree;

    function reader.wordAfterSelector(bytes) external returns (uint256) envfree;

    // The signature check passes.
    function checkSignatures(bytes32, bytes memory, bytes memory) internal => NONDET;

    // Guard hooks and the ERC-165 probe. ConfigLockGuard is the only
    // implementation in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);

    // The Delay's call to its target in executeNextTx.
    function _.execTransactionFromModule(address, uint256, bytes, Enum.Operation) external => NONDET;

    // The Safe's call to `to` in the witnesses, run as a call to the Delay
    // function the witness names.
    unresolved external in SafeV141Harness._ => DISPATCH [
        Delay.setTxNonce(uint256),
        Delay.setTxCooldown(uint256),
        Delay.setTxExpiration(uint256)
    ] default NONDET;
}

/// The seven Delay functions ConfigLockGuard rejects for its Safe, and setUp.
definition isLockedOrSetUp(method f) returns bool =
    f.selector == sig:Delay.transferOwnership(address).selector ||
    f.selector == sig:Delay.renounceOwnership().selector ||
    f.selector == sig:Delay.enableModule(address).selector ||
    f.selector == sig:Delay.disableModule(address, address).selector ||
    f.selector == sig:Delay.setGuard(address).selector ||
    f.selector == sig:Delay.setAvatar(address).selector ||
    f.selector == sig:Delay.setTarget(address).selector ||
    f.selector == sig:Delay.setUp(bytes).selector;

/// The guard is installed on the Safe and points at the Delay, the Delay is
/// not the Safe, and the Safe owns the Delay.
definition guardedOwner() returns bool =
    guardAddress() == configLockGuard &&
    configLockGuard.lockedModifier() == delayContract &&
    delayContract != currentContract &&
    delayContract.owner() == currentContract;

/* ------------------------------------------------------------------------
 * 1. The Delay's half of the lock
 * --------------------------------------------------------------------- */

/*
 * Over every write function of the Delay except the seven the guard rejects and
 * setUp, and for any caller, the owner, guard, avatar and target read the
 * same afterwards. The Safe's plain calls that pass the guard are among
 * these calls.
 */
rule unlockedDelayCallsNeverChangeOwnerGuardAvatarOrTarget(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure &&
                    f.contract == delayContract && !isLockedOrSetUp(f) }
{
    env e;
    address ownerBefore = delayContract.owner();
    address guardBefore = delayContract.guard();
    address avatarBefore = delayContract.avatar();
    address targetBefore = delayContract.target();

    f(e, args);

    assert delayContract.owner() == ownerBefore,
        "a Delay function the guard lets through changed the Delay's owner";
    assert delayContract.guard() == guardBefore,
        "a Delay function the guard lets through changed the Delay's guard";
    assert delayContract.avatar() == avatarBefore,
        "a Delay function the guard lets through changed the Delay's avatar";
    assert delayContract.target() == targetBefore,
        "a Delay function the guard lets through changed the Delay's target";
}

/*
 * Over the same functions and any caller, every address is a module of the
 * Delay afterwards exactly when it was before: no module is added or removed.
 */
rule unlockedDelayCallsNeverChangeModules(method f, calldataarg args, address m)
    filtered { f -> !f.isView && !f.isPure &&
                    f.contract == delayContract && !isLockedOrSetUp(f) }
{
    env e;
    bool enabledBefore = delayContract.isModuleEnabled(m);

    f(e, args);

    assert delayContract.isModuleEnabled(m) == enabledBefore,
        "a Delay function the guard lets through enabled or disabled a module";
}

/*
 * Over every write function of the Delay except setUp (DM-1), the avatar only
 * changes through setAvatar and the target only through setTarget, and only
 * for the owner. This closes the gap proofsContext.md records under
 * Premise 12, independent of ConfigLockGuard.
 */
rule delayAvatarAndTargetOnlyChangeThroughOwnerSetters(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure &&
                    f.contract == delayContract &&
                    f.selector != sig:Delay.setUp(bytes).selector }
{
    env e;
    address ownerBefore = delayContract.owner();
    address avatarBefore = delayContract.avatar();
    address targetBefore = delayContract.target();

    f(e, args);

    assert delayContract.avatar() != avatarBefore =>
        (f.selector == sig:Delay.setAvatar(address).selector && e.msg.sender == ownerBefore),
        "the Delay's avatar changed other than through the owner's setAvatar";
    assert delayContract.target() != targetBefore =>
        (f.selector == sig:Delay.setTarget(address).selector && e.msg.sender == ownerBefore),
        "the Delay's target changed other than through the owner's setTarget";
}

/* ------------------------------------------------------------------------
 * 2. Once installed, the Safe still runs the Delay
 *
 * Each witness pins the calldata to one call of fixed length.
 * --------------------------------------------------------------------- */

/*
 * The veto still works on the signed path: with the guard installed and the
 * Safe owning the Delay, an execTransaction of setTxNonce(n) to the Delay
 * succeeds and txNonce becomes n, for an n the Delay accepts.
 */
rule guardedSafeCanStillVeto(
    uint256 n, bytes data, uint256 safeTxGas, uint256 baseGas,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require thresholdValue() > 0;
    require guardedOwner();

    require data.length == 36;
    require selectorOf(data) == sig:Delay.setTxNonce(uint256).selector;
    require reader.wordAfterSelector(data) == n;
    require delayContract.txNonce() < n;
    require n <= delayContract.queueNonce();

    execTransaction@withrevert(e,
        delayContract, 0, data, Enum.Operation.Call,
        safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted && delayContract.txNonce() == n,
        "with ConfigLockGuard installed, the Safe could not veto with setTxNonce";
}

/*
 * The cooldown can still be set: an execTransaction of setTxCooldown(c) to
 * the Delay succeeds and txCooldown becomes c.
 */
rule guardedSafeCanStillSetTxCooldown(
    uint256 c, bytes data, uint256 safeTxGas, uint256 baseGas,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require thresholdValue() > 0;
    require guardedOwner();

    require data.length == 36;
    require selectorOf(data) == sig:Delay.setTxCooldown(uint256).selector;
    require reader.wordAfterSelector(data) == c;
    require delayContract.txCooldown() != c;

    execTransaction@withrevert(e,
        delayContract, 0, data, Enum.Operation.Call,
        safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted && delayContract.txCooldown() == c,
        "with ConfigLockGuard installed, the Safe could not set the Delay's cooldown";
}

/*
 * The expiration can still be set: an execTransaction of setTxExpiration(x)
 * to the Delay succeeds and txExpiration becomes x.
 */
rule guardedSafeCanStillSetTxExpiration(
    uint256 x, bytes data, uint256 safeTxGas, uint256 baseGas,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require thresholdValue() > 0;
    require guardedOwner();

    require data.length == 36;
    require selectorOf(data) == sig:Delay.setTxExpiration(uint256).selector;
    require reader.wordAfterSelector(data) == x;
    require delayContract.txExpiration() != x;

    execTransaction@withrevert(e,
        delayContract, 0, data, Enum.Operation.Call,
        safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted && delayContract.txExpiration() == x,
        "with ConfigLockGuard installed, the Safe could not set the Delay's expiration";
}
