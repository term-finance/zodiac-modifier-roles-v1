/*
 * The Delay's half of the ConfigLockGuard lock on the DelayOwnerSafe, plus
 * witnesses that the guarded Safe can still run the Delay.
 *
 * ConfigLockGuard rejects seven calls to its lockedModifier
 * (transferOwnership, renounceOwnership, enableModule, disableModule,
 * setGuard, setAvatar and setTarget; CL141-23) and every delegate call (CL141-16).
 * This file shows that no other Delay call, from any caller, changes the
 * Delay's owner, modules, guard, avatar or target.
 *
 * The scene is the real Delay (certora/helpers/Delay.sol), the real
 * ConfigLockGuard with its lockedModifier linked to the Delay, and, for the
 * witnesses, the real Safe v1.4.1 (SafeV141Harness). In the witnesses the
 * signature check is stubbed to pass (SE141-5 and SE141-12 cover it), and the
 * Safe's call to `to` is routed to the Delay function each witness names,
 * with `to` pinned to the Delay.
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

    // Guard calls resolve to ConfigLockGuard, the only guard in the scene.
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
 * Over every Delay write function except the seven the guard rejects and
 * setUp, and for any caller, the owner, guard, avatar and target are
 * unchanged. The Safe's plain calls that pass the guard are among these
 * calls. setUp always reverts after deployment (DM-1).
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
 * Over every Delay write function except setUp, the avatar only changes
 * through setAvatar and the target only through setTarget, and only for the
 * owner.
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
