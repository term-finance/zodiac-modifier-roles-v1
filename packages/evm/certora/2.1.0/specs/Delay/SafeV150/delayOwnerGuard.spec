/*
 * The Delay's half of the ConfigLockGuard lock on the DelayOwnerSafe, plus
 * witnesses that the guarded Safe can still run the Delay.
 *
 * ConfigLockGuard rejects nine calls to its lockedDelay
 * (transferOwnership, renounceOwnership, enableModule, disableModule,
 * setGuard, setAvatar, setTarget, setTxCooldown and setTxExpiration;
 * CL150-23) and every delegate call (CL150-16). This file shows that no
 * other Delay call, from any caller, changes the Delay's owner, modules,
 * guard, avatar, target, txCooldown or txExpiration.
 *
 * The scene is the real Delay (certora/helpers/Delay.sol), the real
 * ConfigLockGuard with its lockedDelay linked to the Delay, and, for the
 * witnesses, the real Safe v1.5.0 (SafeV150Harness). In the witnesses the
 * signature check is stubbed to pass (SE150-5 and SE150-12 cover it), and the
 * Safe's call to `to` is routed to the Delay function each witness names,
 * with `to` pinned to the Delay.
 *
 * zodiac's import of the v1.4.1 Enum is remapped to v1.5.0's Enum in the
 * conf, so the scene has a single Enum.Operation type.
 */

using Delay as delayContract;
using ConfigLockGuard as configLockGuard;
using CalldataReader as reader;

methods {
    function guardAddress() external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function configLockGuard.lockedDelay() external returns (address) envfree;

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
    function checkSignatures(address, bytes32, bytes memory) internal => NONDET;

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
    unresolved external in SafeV150Harness._ => DISPATCH [
        Delay.setTxNonce(uint256)
    ] default NONDET;
}

/// The nine Delay functions ConfigLockGuard rejects for its Safe, and setUp.
definition isLockedOrSetUp(method f) returns bool =
    f.selector == sig:Delay.transferOwnership(address).selector ||
    f.selector == sig:Delay.renounceOwnership().selector ||
    f.selector == sig:Delay.enableModule(address).selector ||
    f.selector == sig:Delay.disableModule(address, address).selector ||
    f.selector == sig:Delay.setGuard(address).selector ||
    f.selector == sig:Delay.setAvatar(address).selector ||
    f.selector == sig:Delay.setTarget(address).selector ||
    f.selector == sig:Delay.setTxCooldown(uint256).selector ||
    f.selector == sig:Delay.setTxExpiration(uint256).selector ||
    f.selector == sig:Delay.setUp(bytes).selector;

/// The guard is installed on the Safe and points at the Delay, the Delay is
/// not the Safe, and the Safe owns the Delay.
definition guardedOwner() returns bool =
    guardAddress() == configLockGuard &&
    configLockGuard.lockedDelay() == delayContract &&
    delayContract != currentContract &&
    delayContract.owner() == currentContract;

/* ------------------------------------------------------------------------
 * 1. The Delay's half of the lock
 * --------------------------------------------------------------------- */

/*
 * Over every Delay write function except the nine the guard rejects and
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

    assert true; // Check pessimistic assertions alongside the existential witness.
    satisfy !lastReverted && delayContract.txNonce() == n,
        "with ConfigLockGuard installed, the Safe could not veto with setTxNonce";
}

/* ------------------------------------------------------------------------
 * 3. The Delay's half of the timing lock
 * --------------------------------------------------------------------- */

/*
 * Over every Delay write function except the nine the guard rejects and
 * setUp, and for any caller, txCooldown and txExpiration are unchanged. The
 * Safe's plain calls that pass the guard are among these calls. It belongs
 * with the rules in section 1; it is placed here so their numbers stay the
 * same.
 */
rule unlockedDelayCallsNeverChangeTxCooldownOrTxExpiration(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure &&
                    f.contract == delayContract && !isLockedOrSetUp(f) }
{
    env e;
    uint256 cooldownBefore = delayContract.txCooldown();
    uint256 expirationBefore = delayContract.txExpiration();

    f(e, args);

    assert delayContract.txCooldown() == cooldownBefore,
        "a Delay function the guard lets through changed the Delay's txCooldown";
    assert delayContract.txExpiration() == expirationBefore,
        "a Delay function the guard lets through changed the Delay's txExpiration";
}
