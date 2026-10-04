/*
 * PauseGuard on the Delay Modifier: it can be installed with
 * Guardable.setGuard, only the pauser can pause, only an ADMIN_ROLE holder
 * can unpause or replace the pauser, and while it is paused no queue entry
 * reaches the Delay's target.
 *
 * The scene is the real Delay (certora/helpers/Delay.sol) with the real
 * PauseGuard. `target` is linked to DummyAvatar, whose
 * execTransactionFromModule is summarized to record that the Delay forwarded
 * a transaction. Role membership is left unconstrained apart from the caller
 * under test, so the rules hold for any admin and pauser.
 */

using PauseGuard as pauseGuardContract;
using DummyAvatar as delayTargetContract;

methods {
    function txNonce() external returns (uint256) envfree;
    function queueNonce() external returns (uint256) envfree;
    function txHash(uint256) external returns (bytes32) envfree;
    function getTransactionHash(address, uint256, bytes, Enum.Operation) external returns (bytes32) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;
    function owner() external returns (address) envfree;
    function isModuleEnabled(address) external returns (bool) envfree;
    function txCooldown() external returns (uint256) envfree;
    function txExpiration() external returns (uint256) envfree;
    function txCreatedAt(uint256) external returns (uint256) envfree;

    function pauseGuardContract.paused() external returns (bool) envfree;
    function pauseGuardContract.pauser() external returns (address) envfree;
    function pauseGuardContract.hasRole(bytes32, address) external returns (bool) envfree;
    function pauseGuardContract.ADMIN_ROLE() external returns (bytes32) envfree;
    function pauseGuardContract.DEFAULT_ADMIN_ROLE() external returns (bytes32) envfree;
    function pauseGuardContract.getRoleAdmin(bytes32) external returns (bytes32) envfree;
    function pauseGuardContract.supportsInterface(bytes4) external returns (bool) envfree;

    // Guard calls resolve to PauseGuard, the only guard in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);

    // Module.exec forwards the queue entry to the Delay's target.
    function DummyAvatar.execTransactionFromModule(
        address, uint256, bytes, Enum.Operation
    ) external returns (bool) => recordForwardToTarget();
}

/*
 * Set when the Delay hands a transaction to its target. Persistent, so a
 * revert does not clear it.
 */
persistent ghost bool forwardedToTarget {
    init_state axiom !forwardedToTarget;
}

function recordForwardToTarget() returns bool {
    forwardedToTarget = true;
    return true;
}

/* ------------------------------------------------------------------------
 * 1. setGuard accepts PauseGuard
 * --------------------------------------------------------------------- */

/*
 * The owner's setGuard(PauseGuard) succeeds and the Delay's `guard` slot then
 * holds PauseGuard.
 */
rule setGuardInstallsPauseGuard() {
    env e;
    require e.msg.sender == owner();
    require e.msg.value == 0;

    setGuard@withrevert(e, pauseGuardContract);

    assert !lastReverted,
        "the Delay's owner could not install PauseGuard with setGuard";
    assert guard() == pauseGuardContract,
        "setGuard returned without storing PauseGuard in the guard slot";
}

/*
 * PauseGuard reports IGuard (0xe6d7a83a), the only check Guardable.setGuard
 * makes, and ERC-165 (0x01ffc9a7).
 */
rule pauseGuardAnswersIGuardInterfaceId() {
    assert pauseGuardContract.supportsInterface(to_bytes4(0xe6d7a83a)),
        "PauseGuard does not report IGuard, so Guardable.setGuard would reject it";
    assert pauseGuardContract.supportsInterface(to_bytes4(0x01ffc9a7)),
        "PauseGuard does not report ERC-165";
}

/* ------------------------------------------------------------------------
 * 2. Roles on pause
 * --------------------------------------------------------------------- */

/*
 * Anyone who is not the pauser is rejected.
 */
rule pauseRevertsForAnyoneButThePauser() {
    env e;
    require e.msg.sender != pauseGuardContract.pauser();

    pauseGuardContract.pause@withrevert(e);

    assert lastReverted,
        "PauseGuard let an account other than the pauser pause";
}

/*
 * Holding ADMIN_ROLE does not let a caller pause.
 */
rule adminAloneCannotPause() {
    env e;
    require pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), e.msg.sender);
    require e.msg.sender != pauseGuardContract.pauser();

    pauseGuardContract.pause@withrevert(e);

    assert lastReverted,
        "an ADMIN_ROLE holder paused without being the pauser";
}

/*
 * From an unpaused state, the pauser's pause() succeeds and `paused` is then
 * true.
 */
rule pauseSucceedsForThePauser() {
    env e;
    require e.msg.value == 0;
    require e.msg.sender == pauseGuardContract.pauser();
    require !pauseGuardContract.paused();

    pauseGuardContract.pause@withrevert(e);

    assert !lastReverted,
        "the pauser could not pause an unpaused guard";
    assert pauseGuardContract.paused(),
        "pause returned without setting the paused flag";
}

/* ------------------------------------------------------------------------
 * 3. Roles on unpause
 * --------------------------------------------------------------------- */

/*
 * Without ADMIN_ROLE the call reverts, whoever the caller is.
 */
rule unpauseRevertsWithoutAdminRole() {
    env e;
    require !pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), e.msg.sender);

    pauseGuardContract.unpause@withrevert(e);

    assert lastReverted,
        "PauseGuard let an account without ADMIN_ROLE unpause";
}

/*
 * Being the pauser, without ADMIN_ROLE, does not let a caller lift a pause.
 */
rule pauserAloneCannotUnpause() {
    env e;
    require e.msg.sender == pauseGuardContract.pauser();
    require !pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), e.msg.sender);
    require pauseGuardContract.paused();

    pauseGuardContract.unpause@withrevert(e);

    assert lastReverted,
        "the pauser lifted a pause without ADMIN_ROLE";
}

/*
 * From a paused state, an ADMIN_ROLE holder's unpause() succeeds and `paused`
 * is then false.
 */
rule unpauseSucceedsForAdminRole() {
    env e;
    require e.msg.value == 0;
    require pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), e.msg.sender);
    require pauseGuardContract.paused();

    pauseGuardContract.unpause@withrevert(e);

    assert !lastReverted,
        "an ADMIN_ROLE holder could not unpause a paused guard";
    assert !pauseGuardContract.paused(),
        "unpause returned without clearing the paused flag";
}

/*
 * Over every write function of both the Delay and PauseGuard, `paused`
 * changes only through pause or unpause.
 */
rule pausedOnlyChangesThroughPauseOrUnpause(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    bool pausedBefore = pauseGuardContract.paused();

    f(e, args);

    bool pausedAfter = pauseGuardContract.paused();

    assert pausedBefore != pausedAfter =>
        (f.selector == sig:PauseGuard.pause().selector ||
         f.selector == sig:PauseGuard.unpause().selector),
        "an entry point other than pause or unpause changed the paused flag";
}

/* ------------------------------------------------------------------------
 * 4. Roles on setPauser
 * --------------------------------------------------------------------- */

/*
 * Without ADMIN_ROLE the call reverts, so nobody else can hand out or take
 * away the right to pause.
 */
rule setPauserRevertsWithoutAdminRole(address account) {
    env e;
    require !pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), e.msg.sender);

    pauseGuardContract.setPauser@withrevert(e, account);

    assert lastReverted,
        "PauseGuard let an account without ADMIN_ROLE replace the pauser";
}

/*
 * For any nonzero account, an ADMIN_ROLE holder's setPauser(account)
 * succeeds, pauser() then returns account, and the previous pauser no longer
 * holds the slot.
 */
rule setPauserSetsThePauser(address account) {
    env e;
    require e.msg.value == 0;
    require account != 0;
    require pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), e.msg.sender);

    address previousPauser = pauseGuardContract.pauser();

    pauseGuardContract.setPauser@withrevert(e, account);

    assert !lastReverted,
        "an ADMIN_ROLE holder could not replace the pauser";
    assert pauseGuardContract.pauser() == account,
        "setPauser returned without recording the new pauser";
    assert previousPauser != account => pauseGuardContract.pauser() != previousPauser,
        "setPauser left the outgoing pauser in place, so two accounts could pause";
}

/*
 * No holder can drop a role, so the last admin cannot strand the guard with
 * nobody able to unpause.
 */
rule renounceRoleAlwaysReverts(bytes32 role, address account) {
    env e;

    pauseGuardContract.renounceRole@withrevert(e, role, account);

    assert lastReverted,
        "renounceRole is meant to be disabled";
}

/*
 * The inherited grantRole and revokeRole revert for every role and every
 * caller, admins included, because both roles are administered by
 * DEFAULT_ADMIN_ROLE, which nobody holds.
 */
rule inheritedGrantAndRevokeAlwaysRevert(bytes32 role, address account) {
    env e;
    require pauseGuardContract.getRoleAdmin(role) ==
        pauseGuardContract.DEFAULT_ADMIN_ROLE();
    require !pauseGuardContract.hasRole(
        pauseGuardContract.DEFAULT_ADMIN_ROLE(), e.msg.sender
    );

    pauseGuardContract.grantRole@withrevert(e, role, account);
    assert lastReverted,
        "grantRole handed out a role although nobody holds DEFAULT_ADMIN_ROLE";

    pauseGuardContract.revokeRole@withrevert(e, role, account);
    assert lastReverted,
        "revokeRole took away a role although nobody holds DEFAULT_ADMIN_ROLE";
}

/*
 * Over every write function of both contracts, the pauser only changes
 * through setPauser.
 */
rule pauserOnlyChangesThroughSetPauser(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    address pauserBefore = pauseGuardContract.pauser();

    f(e, args);

    assert pauseGuardContract.pauser() != pauserBefore =>
        f.selector == sig:PauseGuard.setPauser(address).selector,
        "an entry point other than setPauser changed the pauser";
}

/*
 * Over every write function of both contracts, ADMIN_ROLE membership never
 * changes for any account.
 */
rule adminRoleNeverChanges(method f, calldataarg args, address account)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    // ADMIN_ROLE is administered by DEFAULT_ADMIN_ROLE
    // (roleAdminWiringIsFixed).
    require pauseGuardContract.getRoleAdmin(pauseGuardContract.ADMIN_ROLE()) ==
        pauseGuardContract.DEFAULT_ADMIN_ROLE();
    // Nobody holds DEFAULT_ADMIN_ROLE (defaultAdminRoleNeverHeld).
    require !pauseGuardContract.hasRole(
        pauseGuardContract.DEFAULT_ADMIN_ROLE(), e.msg.sender
    );
    bool adminBefore = pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), account);

    f(e, args);

    assert pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), account) == adminBefore,
        "an entry point changed ADMIN_ROLE membership, which is fixed at deployment";
}

/*
 * An unheld DEFAULT_ADMIN_ROLE stays unheld. The base case, that nobody holds
 * it from the constructor on, is defaultAdminRoleNeverHeld.
 */
rule defaultAdminRoleNeverGranted(method f, calldataarg args, address account)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    // DEFAULT_ADMIN_ROLE administers itself (roleAdminWiringIsFixed).
    require pauseGuardContract.getRoleAdmin(pauseGuardContract.DEFAULT_ADMIN_ROLE()) ==
        pauseGuardContract.DEFAULT_ADMIN_ROLE();
    require !pauseGuardContract.hasRole(
        pauseGuardContract.DEFAULT_ADMIN_ROLE(), e.msg.sender
    );
    require !pauseGuardContract.hasRole(
        pauseGuardContract.DEFAULT_ADMIN_ROLE(), account
    );

    f(e, args);

    assert !pauseGuardContract.hasRole(pauseGuardContract.DEFAULT_ADMIN_ROLE(), account),
        "an account gained DEFAULT_ADMIN_ROLE, which is never meant to be held";
}

/*
 * Nothing re-points the admin of ADMIN_ROLE or DEFAULT_ADMIN_ROLE.
 */
rule roleAdminWiringNeverChanges(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    bytes32 defaultAdminAdminBefore =
        pauseGuardContract.getRoleAdmin(pauseGuardContract.DEFAULT_ADMIN_ROLE());
    bytes32 adminAdminBefore =
        pauseGuardContract.getRoleAdmin(pauseGuardContract.ADMIN_ROLE());

    f(e, args);

    assert pauseGuardContract.getRoleAdmin(pauseGuardContract.ADMIN_ROLE()) == adminAdminBefore,
        "an entry point re-pointed the admin of ADMIN_ROLE";
    assert pauseGuardContract.getRoleAdmin(pauseGuardContract.DEFAULT_ADMIN_ROLE()) ==
        defaultAdminAdminBefore,
        "an entry point re-pointed the admin of DEFAULT_ADMIN_ROLE";
}

/* ------------------------------------------------------------------------
 * 5. Pause blocks executeNextTx
 * --------------------------------------------------------------------- */

/*
 * With PauseGuard installed and paused, executeNextTx reverts and nothing
 * reaches the Delay's target, for any transaction arguments and any queue
 * state.
 */
rule pausedBlocksExecuteNextTx(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require guard() == pauseGuardContract;
    require target() == delayTargetContract;
    require pauseGuardContract.paused();
    require !forwardedToTarget;

    executeNextTx@withrevert(e, to, value, data, operation);

    assert lastReverted,
        "executeNextTx succeeded while PauseGuard was paused";
    assert !forwardedToTarget,
        "a queue entry reached the target while PauseGuard was paused";
}

/*
 * Called directly, a paused PauseGuard rejects every transaction from every
 * caller.
 */
rule checkTransactionRevertsWhilePaused(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require pauseGuardContract.paused();

    pauseGuardContract.checkTransaction@withrevert(
        e, to, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert lastReverted,
        "PauseGuard accepted a transaction while paused";
}

/* ------------------------------------------------------------------------
 * 6. Unpause unblocks executeNextTx
 * --------------------------------------------------------------------- */

/*
 * With PauseGuard installed and paused, after an ADMIN_ROLE holder unpauses,
 * a following executeNextTx can succeed and reach the Delay's target.
 */
rule unpauseReopensExecuteNextTx(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env eUnpause;
    env eExec;
    require guard() == pauseGuardContract;
    require target() == delayTargetContract;
    require !forwardedToTarget;
    require eUnpause.msg.value == 0;
    require pauseGuardContract.hasRole(
        pauseGuardContract.ADMIN_ROLE(), eUnpause.msg.sender
    );
    require pauseGuardContract.paused();

    pauseGuardContract.unpause(eUnpause);

    executeNextTx(eExec, to, value, data, operation);

    satisfy forwardedToTarget,
        "no queue entry can execute after the admin unpaused, so the pause is not reversible";
}

/*
 * While not paused, PauseGuard accepts any transaction from any caller, so it
 * adds no revert of its own to executeNextTx.
 */
rule checkTransactionAcceptsWhileNotPaused(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures, address msgSender
) {
    env e;
    require e.msg.value == 0;
    require !pauseGuardContract.paused();

    pauseGuardContract.checkTransaction@withrevert(
        e, to, value, data, operation,
        safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures, msgSender
    );

    assert !lastReverted,
        "PauseGuard rejected a transaction while not paused";
}

/* ------------------------------------------------------------------------
 * 7. A pause does not disarm the owner: setTxNonce still works
 * --------------------------------------------------------------------- */

/*
 * While PauseGuard is installed and paused, the owner's setTxNonce succeeds
 * and the new nonce lands.
 */
rule ownerCanSetTxNonceWhilePaused(uint256 nonce) {
    env e;
    require guard() == pauseGuardContract;
    require pauseGuardContract.paused();
    require e.msg.sender == owner();
    require e.msg.value == 0;

    require nonce > txNonce();
    require nonce <= queueNonce();

    setTxNonce@withrevert(e, nonce);

    assert !lastReverted,
        "the Delay owner could not set txNonce while PauseGuard was paused";
    assert txNonce() == nonce,
        "setTxNonce returned without recording the new nonce";
}

/*
 * In one state, with an entry queued and PauseGuard paused: executeNextTx
 * reverts and nothing reaches the target, and the owner's setTxNonce still
 * succeeds.
 */
rule pausedBlocksExecuteNextTxWhileOwnerCanStillSetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation, uint256 nonce
) {
    env eExec;
    env eNonce;
    require guard() == pauseGuardContract;
    require target() == delayTargetContract;
    require pauseGuardContract.paused();
    require !forwardedToTarget;

    require txNonce() < queueNonce();

    executeNextTx@withrevert(eExec, to, value, data, operation);

    assert lastReverted,
        "executeNextTx succeeded while PauseGuard was paused";
    assert !forwardedToTarget,
        "a queue entry reached the target while PauseGuard was paused";

    require eNonce.msg.sender == owner();
    require eNonce.msg.value == 0;
    require nonce > txNonce();
    require nonce <= queueNonce();

    setTxNonce@withrevert(eNonce, nonce);

    assert !lastReverted,
        "the pause also froze the owner's setTxNonce, so a paused queue cannot be cancelled";
    assert txNonce() == nonce,
        "setTxNonce returned without recording the new nonce";
}

/*
 * While paused, after the owner's setTxNonce leaves an entry still queued,
 * executeNextTx still reverts and nothing reaches the target.
 */
rule executeNextTxStillBlockedAfterSetTxNonceDuringPause(
    address to, uint256 value, bytes data, Enum.Operation operation, uint256 nonce
) {
    env eNonce;
    env eExec;
    require guard() == pauseGuardContract;
    require target() == delayTargetContract;
    require pauseGuardContract.paused();
    require !forwardedToTarget;

    require eNonce.msg.sender == owner();
    require eNonce.msg.value == 0;
    require nonce > txNonce();
    require nonce < queueNonce();

    setTxNonce(eNonce, nonce);

    assert txNonce() == nonce,
        "setTxNonce returned without recording the new nonce";
    assert pauseGuardContract.paused(),
        "setTxNonce cleared the pause";

    executeNextTx@withrevert(eExec, to, value, data, operation);

    assert lastReverted,
        "executeNextTx succeeded after the owner bumped txNonce during the pause";
    assert !forwardedToTarget,
        "a queue entry reached the target after the owner bumped txNonce during the pause";
}

/*
 * The same sequence, then the admin unpauses: an entry can now execute. So
 * the block in the rule above comes from the pause.
 */
rule executeNextTxAfterSetTxNonceReopensOnUnpause(
    address to, uint256 value, bytes data, Enum.Operation operation, uint256 nonce
) {
    env eNonce;
    env eUnpause;
    env eExec;
    require guard() == pauseGuardContract;
    require target() == delayTargetContract;
    require pauseGuardContract.paused();
    require !forwardedToTarget;

    require eNonce.msg.sender == owner();
    require eNonce.msg.value == 0;
    require nonce > txNonce();
    require nonce < queueNonce();

    setTxNonce(eNonce, nonce);

    require eUnpause.msg.value == 0;
    require pauseGuardContract.hasRole(
        pauseGuardContract.ADMIN_ROLE(), eUnpause.msg.sender
    );
    pauseGuardContract.unpause(eUnpause);

    executeNextTx(eExec, to, value, data, operation);

    satisfy forwardedToTarget,
        "nothing can execute after a bump-then-unpause, so the block in the previous rule is not the pause";
}

/* ------------------------------------------------------------------------
 * Non-vacuity
 * --------------------------------------------------------------------- */

/*
 * With no guard installed, executeNextTx forwards without any check, so the
 * pause rules are not achieved by nothing working.
 */
rule withoutPauseGuardExecuteNextTxForwardsUnchecked(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require guard() == 0;
    require target() == delayTargetContract;
    require !forwardedToTarget;

    executeNextTx(e, to, value, data, operation);

    satisfy forwardedToTarget,
        "executeNextTx cannot forward without a guard, so the guard rules prove nothing about the guard";
}

/* ------------------------------------------------------------------------
 * A skipped entry stays skipped
 * --------------------------------------------------------------------- */

/*
 * Over every write function of both contracts, txNonce never decreases.
 */
rule txNonceNeverDecreases(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    uint256 before = txNonce();

    f(e, args);

    assert txNonce() >= before,
        "txNonce moved backwards, so a skipped queue entry could become executable again";
}

/*
 * A successful executeNextTx ran exactly the transaction queued at txNonce,
 * and advanced txNonce by one.
 */
rule executeNextTxConsumesOnlyTheEntryAtTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    uint256 nonceBefore = txNonce();
    bytes32 storedHash = txHash(nonceBefore);

    executeNextTx(e, to, value, data, operation);

    assert getTransactionHash(to, value, data, operation) == storedHash,
        "executeNextTx ran a transaction other than the entry stored at txNonce";
    assert to_mathint(txNonce()) == nonceBefore + 1,
        "executeNextTx did not advance txNonce by exactly one";
}

/* ------------------------------------------------------------------------
 * 8. End to end: a queued entry executes, on time and only on time
 * --------------------------------------------------------------------- */

/*
 * Once a module has queued a transaction, the cooldown has passed, it has not
 * expired and PauseGuard is not paused, anyone's executeNextTx runs it and it
 * reaches the Delay's target. Assumes the target accepts the call.
 */
rule queuedTransactionExecutesAfterCooldown(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env eQueue;
    env eExec;
    require guard() == pauseGuardContract;
    require target() == delayTargetContract;
    require !pauseGuardContract.paused();
    require !forwardedToTarget;
    require isModuleEnabled(eQueue.msg.sender);
    require eQueue.msg.value == 0;
    require eExec.msg.value == 0;

    require txNonce() == queueNonce();
    require queueNonce() < max_uint256;

    execTransactionFromModule(eQueue, to, value, data, operation);

    uint256 createdAt = txCreatedAt(txNonce());
    require eExec.block.timestamp >= createdAt;
    require eExec.block.timestamp - createdAt >= txCooldown();
    require createdAt + txCooldown() + txExpiration() <= max_uint256;
    require txExpiration() == 0 ||
        createdAt + txCooldown() + txExpiration() >= to_mathint(eExec.block.timestamp);

    uint256 nonceBefore = txNonce();

    executeNextTx@withrevert(eExec, to, value, data, operation);

    assert !lastReverted,
        "a queued transaction past its cooldown, not expired and not paused could not be executed";
    assert forwardedToTarget,
        "executeNextTx returned without handing the transaction to the target";
    assert to_mathint(txNonce()) == nonceBefore + 1,
        "executeNextTx did not advance the queue past the executed entry";
}

/*
 * The head entry cannot run before its cooldown has passed or after it has
 * expired.
 */
rule executeNextTxRevertsDuringCooldown(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require txNonce() < queueNonce();
    require to_mathint(e.block.timestamp) < txCreatedAt(txNonce()) + txCooldown();

    executeNextTx@withrevert(e, to, value, data, operation);

    assert lastReverted,
        "the head entry executed before its cooldown had passed";
}

rule executeNextTxRevertsAfterExpiration(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require txNonce() < queueNonce();
    require txExpiration() != 0;
    require to_mathint(e.block.timestamp) >
        txCreatedAt(txNonce()) + txCooldown() + txExpiration();

    executeNextTx@withrevert(e, to, value, data, operation);

    assert lastReverted,
        "the head entry executed after it had expired";
}

/* ------------------------------------------------------------------------
 * 9. A vetoed entry cannot execute
 * --------------------------------------------------------------------- */

/*
 * A module queues a transaction, the owner's setTxNonce moves txNonce past
 * it, and executeNextTx with that transaction then reverts.
 */
rule vetoedTransactionCannotExecute(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env eQueue;
    env eVeto;
    env eExec;
    require isModuleEnabled(eQueue.msg.sender);
    require eQueue.msg.value == 0;
    require eVeto.msg.sender == owner();
    require eVeto.msg.value == 0;

    require txNonce() == queueNonce();
    require queueNonce() < max_uint256;

    execTransactionFromModule(eQueue, to, value, data, operation);

    setTxNonce(eVeto, queueNonce());

    executeNextTx@withrevert(eExec, to, value, data, operation);

    assert lastReverted,
        "a transaction executed after the owner had moved txNonce past it";
}

/*
 * From any state: once txNonce is past entry k, executeNextTx with entry k's
 * transaction reverts, unless the same transaction was queued again and now
 * sits at txNonce.
 */
rule entryPassedByTxNonceNeverExecutes(
    uint256 k, address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require txNonce() > k;
    require txHash(k) == getTransactionHash(to, value, data, operation);
    require txHash(txNonce()) != txHash(k);

    executeNextTx@withrevert(e, to, value, data, operation);

    assert lastReverted,
        "txNonce had already passed this entry, yet its transaction executed without being queued again";
}

/* ------------------------------------------------------------------------
 * 10. executeNextTx is the only way out
 * --------------------------------------------------------------------- */

/*
 * Over every write function of both the Delay and PauseGuard, if a
 * transaction reached the Delay's target, the function was executeNextTx.
 * With pausedBlocksExecuteNextTx, a pause stops every transaction the Delay
 * can send.
 */
rule onlyExecuteNextTxReachesTheTarget(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    require target() == delayTargetContract;
    require !forwardedToTarget;

    f(e, args);

    assert forwardedToTarget =>
        f.selector == sig:executeNextTx(address, uint256, bytes, Enum.Operation).selector,
        "an entry point other than executeNextTx handed a transaction to the Delay's target";
}
