/*
 * Property: PauseGuard can be installed on the Delay with Guardable.setGuard,
 * its two roles are enforced, and while it is paused no queue entry reaches
 * the Delay's target — while it is not paused, entries execute as before.
 *
 * "The guard" in this file always means PauseGuard, installed on the Delay
 * modifier with Guardable.setGuard. SetTxNonceGuard, installed on the Roles
 * module, is not in this scene and nothing here says anything about it.
 *
 * The scene is the real Delay, not a model: certora/helpers/Delay.sol is the
 * verified mastercopy source.
 *
 * Who may do what:
 *     pauser      pause — one account, checked directly against msg.sender
 *     ADMIN_ROLE  unpause, setPauser — a role, so it can have several members
 * DEFAULT_ADMIN_ROLE is never granted and administers ADMIN_ROLE, so the
 * inherited grantRole and revokeRole revert for every caller and renounceRole
 * is disabled: ADMIN_ROLE is fixed at deployment.
 *
 * Unlike the guard it replaced, PauseGuard reads only its own `paused` slot,
 * so checkTransaction never calls back into the Delay and the blocking
 * property can be stated end to end:
 *
 *     Delay.executeNextTx -> Module.exec -> guard.checkTransaction
 *                                              -> reverts while paused
 *
 * Rules, by property:
 *
 *   setGuard accepts the guard
 *     setGuardInstallsPauseGuard          the owner can install it, and the
 *                                         Delay's `guard` slot then holds it
 *     pauseGuardAnswersIGuardInterfaceId  supportsInterface(0xe6d7a83a) is
 *                                         true, which is the only thing
 *                                         Guardable.setGuard checks
 *
 *   who may pause
 *     pauseRevertsForAnyoneButThePauser   only the pauser can pause
 *     pauseSucceedsForThePauser           the pauser always can
 *     adminAloneCannotPause               ADMIN_ROLE does not carry the right
 *                                         to pause
 *
 *   roles on unpause
 *     unpauseRevertsWithoutAdminRole      no ADMIN_ROLE, no unpause
 *     unpauseSucceedsForAdminRole         ADMIN_ROLE is enough
 *     pauserAloneCannotUnpause            being the pauser does not let the
 *                                         caller lift a pause
 *     pausedOnlyChangesThroughPauseOrUnpause
 *                                         over every entry point of both
 *                                         contracts, nothing else moves the
 *                                         flag
 *
 *   roles on setPauser, and membership integrity
 *     setPauserRevertsWithoutAdminRole    no ADMIN_ROLE, no new pauser
 *     setPauserSetsThePauser              ADMIN_ROLE replaces the pauser
 *     inheritedGrantAndRevokeAlwaysRevert the inherited AccessControl entry
 *                                         points are dead, for every role
 *     renounceRoleAlwaysReverts           no holder can drop a role
 *     pauserOnlyChangesThroughSetPauser
 *     adminRoleNeverChanges               ADMIN_ROLE is fixed at deployment,
 *                                         given the constructor's role-admin
 *                                         wiring
 *     defaultAdminRoleNeverGranted        the unheld role stays unheld, which
 *                                         is what freezes ADMIN_ROLE
 *     roleAdminWiringNeverChanges         _setRoleAdmin is never called
 *
 *   pause blocks executeNextTx
 *     pausedBlocksExecuteNextTx           end to end: executeNextTx reverts
 *                                         and nothing reaches the target
 *     checkTransactionRevertsWhilePaused  guard half, called directly
 *
 *   unpause unblocks executeNextTx
 *     unpauseReopensExecuteNextTx         end to end: after the admin
 *                                         unpauses, an entry can execute
 *     checkTransactionAcceptsWhileNotPaused
 *                                         guard half: not paused, the guard
 *                                         accepts any arguments
 *
 *   a pause does not disarm the owner
 *     ownerCanSetTxNonceWhilePaused       setTxNonce is onlyOwner and never
 *                                         reaches Module.exec, so the guard
 *                                         never sees it
 *     pausedBlocksExecuteNextTxWhileOwnerCanStillSetTxNonce
 *                                         both halves in one state: the queue
 *                                         is held AND the owner can cancel
 *     executeNextTxStillBlockedAfterSetTxNonceDuringPause
 *                                         and the other order: after the
 *                                         cancellation the pause still stands
 *     executeNextTxAfterSetTxNonceReopensOnUnpause
 *                                         attribution witness for it
 *   a skipped entry stays skipped
 *     txNonceNeverDecreases               over every entry point of both
 *                                         contracts, txNonce only moves up
 *     executeNextTxConsumesOnlyTheEntryAtTxNonce
 *                                         a successful executeNextTx ran the
 *                                         entry stored at the current txNonce
 *                                         and advanced txNonce by exactly one
 *
 *   end to end: a queued entry executes, on time and only on time
 *     queuedTransactionExecutesAfterCooldown
 *                                         a module queues a transaction; once
 *                                         the cooldown has passed, before it
 *                                         expires and while not paused,
 *                                         anyone's executeNextTx runs it and
 *                                         it reaches the target
 *     executeNextTxRevertsDuringCooldown  before the cooldown has passed the
 *                                         head entry cannot run
 *     executeNextTxRevertsAfterExpiration after it has expired it cannot run
 *
 * Non-vacuity witness: withoutPauseGuardExecuteNextTxForwardsUnchecked (with
 * no guard installed executeNextTx forwards without any check, so the guard is
 * what does the work in the rules above).
 *
 * Two links are read off Module.exec (@gnosis.pm/zodiac 1.0.1
 * core/Module.sol:43-77) rather than checked by the Prover:
 *   - the call is IGuard(guard).checkTransaction(...), i.e. it goes to the
 *     address in the Delay's `guard` slot — the installed guard;
 *   - it is a plain external call with no try/catch, so a revert inside
 *     checkTransaction reverts executeNextTx.
 *
 * Deliberately NOT claimed here:
 *   - Anything about who holds the roles. Membership is left unconstrained
 *     apart from the holder under test, so these rules hold for any admin and
 *     pauser, including Safes.
 *   - That the guard survives its own removal. Delay.setGuard is onlyOwner, so
 *     the Delay's owner can always detach the guard.
 *   - That the DelayOwnerSafe's signed transactions are unguarded in general.
 *     Section 7 depends on PauseGuard being installed on the DELAY only; were
 *     it also the Safe's own transaction guard, a pause would block that route
 *     too. See the note there.
 *   - Anything about queueing. execTransactionFromModule and
 *     execTransactionFromModuleReturnData never reach Module.exec.
 *
 * Modelling notes.
 *   - `target` is linked to DummyAvatar, whose execTransactionFromModule is
 *     summarised to record that the Delay forwarded a transaction.
 *   - checkTransaction, checkAfterExecution and supportsInterface are
 *     DISPATCHER(true), so inside executeNextTx and setGuard the real
 *     PauseGuard code runs: it is the only contract in the scene that
 *     implements them.
 *   - loop_iter 1 with optimistic_loop only bounds skipExpired's while loop,
 *     which never calls exec.
 *   - executeNextTx and the queueing entry points hash the whole transaction
 *     (keccak256(abi.encodePacked(to, value, data, operation)), 53 bytes plus
 *     `data`). Without a bound the Prover reports that hash as a violation of
 *     whichever rule is running. The conf sets optimistic_hashing with
 *     hashing_length_bound 1024, so the rules cover transactions whose `data`
 *     is at most 971 bytes. Nothing in these rules depends on `data` beyond
 *     that hash equality check, but longer payloads are outside what is proved.
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

    // Module.exec's guard hooks, and Guardable.setGuard's ERC-165 probe of the
    // new guard. PauseGuard is the only implementation in the scene.
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
 * Set when the Delay hands a transaction to its target, i.e. when a queue
 * entry actually executes. Persistent, so nothing on the path can havoc what
 * was recorded.
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
 * The Delay's owner can install the guard: setGuard does not revert on the
 * ERC-165 probe, and the `guard` slot ends up holding PauseGuard.
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
 * What setGuard's probe asks for: type(IGuard).interfaceId, 0xe6d7a83a.
 * ERC-165's own id is answered too.
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
 * ADMIN_ROLE is not a superset: it opens unpause and setPauser, not pause.
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
 * The pauser always can: from unpaused, it pauses and the flag is set. Also the
 * non-vacuity witness for the two rules above.
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
 * The asymmetry the design depends on: pausing is cheap, unpausing is not.
 * The pauser, without ADMIN_ROLE, cannot lift a pause.
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
 * ADMIN_ROLE is sufficient: from paused, the holder unpauses and the flag is
 * cleared. Also the non-vacuity witness for the two rules above.
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
 * No other way to move the flag. Over every state-changing entry point of the
 * Delay and of the guard: if `paused` changed, the entry point was pause or
 * unpause.
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
 * ADMIN_ROLE replaces the pauser, and only the named account can pause
 * afterwards. Also the non-vacuity witness for the rule above.
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
 * AccessControl lets a holder drop its own role; this guard does not, so the
 * pauser field cannot be left pointing at a non-holder and the last admin
 * cannot strand the guard.
 */
rule renounceRoleAlwaysReverts(bytes32 role, address account) {
    env e;

    pauseGuardContract.renounceRole@withrevert(e, role, account);

    assert lastReverted,
        "renounceRole is meant to be disabled";
}

/*
 * Both roles are administered by DEFAULT_ADMIN_ROLE, which nobody holds, so
 * AccessControl's own entry points are dead for every role and every caller —
 * including admins. setPauser is the only way in.
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
 * The pauser only ever changes through setPauser.
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
 * ADMIN_ROLE membership is fixed at deployment: its admin is DEFAULT_ADMIN_ROLE
 * which nobody holds, so grantRole and revokeRole revert, and renounceRole is
 * disabled.
 */
rule adminRoleNeverChanges(method f, calldataarg args, address account)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    // grantRole and revokeRole are gated on getRoleAdmin(role), not on
    // DEFAULT_ADMIN_ROLE, so the wiring has to be pinned as well: the
    // constructor leaves ADMIN_ROLE's admin at DEFAULT_ADMIN_ROLE and
    // roleAdminWiringNeverChanges shows nothing can re-point it.
    require pauseGuardContract.getRoleAdmin(pauseGuardContract.ADMIN_ROLE()) ==
        pauseGuardContract.DEFAULT_ADMIN_ROLE();
    // The constructor grants DEFAULT_ADMIN_ROLE to nobody, and
    // defaultAdminRoleNeverGranted below shows nothing can grant it later, so
    // no caller holds it.
    require !pauseGuardContract.hasRole(
        pauseGuardContract.DEFAULT_ADMIN_ROLE(), e.msg.sender
    );
    bool adminBefore = pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), account);

    f(e, args);

    assert pauseGuardContract.hasRole(pauseGuardContract.ADMIN_ROLE(), account) == adminBefore,
        "an entry point changed ADMIN_ROLE membership, which is fixed at deployment";
}

/*
 * What freezes ADMIN_ROLE: an unheld DEFAULT_ADMIN_ROLE stays unheld, because
 * it administers itself and no code path grants it.
 *
 * This is the induction step only. The base case is the constructor, which
 * grants DEFAULT_ADMIN_ROLE to nobody; the Prover starts parametric rules from
 * arbitrary storage, so the pre-state is assumed here rather than proved.
 */
rule defaultAdminRoleNeverGranted(method f, calldataarg args, address account)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    // DEFAULT_ADMIN_ROLE administers itself, the value AccessControl starts
    // from and that nothing here changes.
    require pauseGuardContract.getRoleAdmin(pauseGuardContract.DEFAULT_ADMIN_ROLE()) ==
        pauseGuardContract.DEFAULT_ADMIN_ROLE();
    // Nobody holds it in the pre-state: not the caller, who would otherwise
    // pass grantRole's check, and not the account under test, which would
    // otherwise still hold it afterwards for reasons having nothing to do
    // with f.
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
 * Nothing calls _setRoleAdmin, so the wiring the rules above rely on —
 * ADMIN_ROLE administered by the unheld DEFAULT_ADMIN_ROLE — cannot be
 * re-pointed.
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
 * THE blocking property, end to end. With the guard installed and paused,
 * executeNextTx reverts and nothing reaches the target, whatever the
 * transaction arguments and whatever the queue looks like.
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
 * Guard half: called directly, with nothing running on the Delay, a paused
 * guard rejects every transaction and every caller.
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
 * The other half of the blocking property: once the admin unpauses, a queue
 * entry can execute again through the installed guard.
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
 * Guard half: not paused, the guard accepts any transaction from any caller,
 * so it contributes no revert of its own to executeNextTx.
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
 * The point of pausing is to hold the queue while the owner cancels what is in
 * it. That is only worth anything if the pause does not also freeze the
 * cancellation, so the two halves have to hold in the SAME state:
 *
 *     paused  =>  executeNextTx blocked  AND  owner's setTxNonce still lands
 *
 * Why setTxNonce is untouched by the guard: it is a plain onlyOwner function
 * on the Delay (Delay.sol:136-143) that writes txNonce and returns. It never
 * calls Module.exec, so IGuard.checkTransaction is never reached and the
 * `paused` flag is never read on its path. executeNextTx, by contrast, ends in
 * exec(to, value, data, operation) (Delay.sol:224), which is where the guard
 * sits.
 *
 * ON THE TWO ROUTES IN THE SCENARIO. The Delay cannot tell them apart, and
 * neither rule below needs to:
 *
 *   signer/owner execution   the 9/9 DelayOwnerSafe signs a transaction whose
 *                            destination is the Delay
 *   via execTransactionFromModule
 *                            Governor -> Roles -> Module.exec ->
 *                            IAvatar(target).execTransactionFromModule, where
 *                            target IS the DelayOwnerSafe, which then calls
 *                            the Delay
 *
 * Both arrive at Delay.setTxNonce as an ordinary external call whose
 * msg.sender is the DelayOwnerSafe, i.e. owner(). `e.msg.sender == owner()`
 * is exactly that, and covers both. What happens UPSTREAM of the Safe on the
 * second route is a different scene and is not claimed here: that the Roles
 * module admits nothing but setTxNonce is Property 1, and that PauseGuard
 * being paused cannot interfere with it is immediate — PauseGuard is
 * installed on the Delay, SetTxNonceGuard on the Roles module, and neither
 * reads the other's storage.
 *
 * Deliberately NOT claimed here:
 *   - That the DelayOwnerSafe's own signed transactions are unguarded in
 *     general. This holds because PauseGuard is installed on the DELAY, with
 *     the Zodiac Modifier's Guardable.setGuard. If the same PauseGuard were
 *     also installed as the SAFE's transaction guard (Safe's own setGuard),
 *     the Safe's signed transactions WOULD go through checkTransaction and a
 *     pause would block this route too. That is a deployment constraint these
 *     rules depend on, not something they prove.
 *   - That the skipped entry can never execute afterwards. These rules show
 *     txNonce moves; they say nothing about the hash check that a later
 *     executeNextTx would run against the new txNonce.
 */

/*
 * Half one, on its own: while the guard is installed AND paused, the owner's
 * setTxNonce succeeds and the new nonce lands.
 *
 * The two requires on `nonce` are setTxNonce's own preconditions
 * (Delay.sol:137-141), not concessions to the pause — without them the call
 * reverts for reasons that have nothing to do with the guard. Note they also
 * force txNonce() < queueNonce(), i.e. a non-empty queue: there is something
 * to cancel.
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
 * The scenario itself, both halves in one state. A transaction is pending, the
 * guard is paused: executeNextTx reverts and nothing reaches the target, and
 * in that same state the owner can still bump txNonce past the pending entry.
 *
 * executeNextTx is called first and reverts, so storage rolls back and the
 * setTxNonce half runs against the same pre-state. forwardedToTarget is
 * persistent and therefore NOT rolled back, which is what makes the second
 * assert say something: had the Delay reached its target before reverting,
 * the ghost would still be set.
 *
 * The caller of executeNextTx is left unconstrained — it is a public function,
 * so this covers anyone trying to push the queue through during the pause.
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

    // Something is actually queued, so executeNextTx is not reverting merely
    // because the queue is empty (Delay.sol:206) and there is an entry for the
    // owner to skip.
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
 * The other order, and the one that matters for the veto: the owner cancels
 * FIRST, and the pause is still standing afterwards. Bumping txNonce must not
 * be a way to slip the next entry past a paused guard.
 *
 * `nonce < queueNonce()` is strict, where setTxNonce itself only requires
 * `<=` (Delay.sol:141). That is deliberate: it leaves the queue NON-EMPTY
 * after the bump, so the executeNextTx revert below cannot be blamed on the
 * empty-queue check at Delay.sol:206. Something is still queued and the guard
 * is what stops it.
 *
 * executeNextTxAfterSetTxNonceReopensOnUnpause is the other half of the
 * attribution: it exhibits the same post-bump state executing once the pause
 * is lifted, so the revert here really is the pause and not some leftover of
 * what setTxNonce did.
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
 * Attribution witness for the rule above. Same sequence — paused, owner bumps
 * txNonce, queue still non-empty — and then the admin unpauses: now an entry
 * CAN execute.
 *
 * Without this, executeNextTxStillBlockedAfterSetTxNonceDuringPause is
 * consistent with a post-bump state that is stuck for some reason of its own,
 * which would make "still blocked BY THE PAUSE" an overstatement.
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
 * The guard is what does the work: with no guard installed, executeNextTx
 * forwards an entry without any check at all.
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

/*
 * A SKIPPED ENTRY STAYS SKIPPED.
 *
 * 4.18-4.19 show the owner's setTxNonce lands during a pause. That moves
 * txNonce past the pending entry; these two rules are what make the skip
 * permanent. Together: once txNonce > k, txNonce never returns to k
 * (txNonceNeverDecreases), and executeNextTx only ever runs the entry stored
 * at txNonce (executeNextTxConsumesOnlyTheEntryAtTxNonce). So the entry at
 * index k can never be the one executed.
 *
 * What this does not say: that the same TRANSACTION can never run. The hash
 * check compares against txHash[txNonce], so an identical transaction queued
 * again at a later index is a new entry and can execute. That is a fresh
 * proposal through the queue, cooldown and pause, not the skipped entry
 * coming back.
 *
 * Every write to txNonce in Delay.sol is setTxNonce (:142, which requires the
 * new value to be strictly greater), executeNextTx (:223) or skipExpired
 * (:234), both increments under checked arithmetic. No guard or pause state is
 * assumed: both rules hold whatever is installed.
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
 * The functional half of the design, stated end to end on the real Delay with
 * the real PauseGuard installed: an enabled module (the Proposer Safe) queues
 * a transaction, time passes, and once the cooldown is over — before the
 * entry expires, and while the guard is not paused — anyone's executeNextTx
 * runs it and it reaches the Delay's target (the Ownerless Safe).
 *
 * This is an assert, not a satisfy: it holds for every such transaction, not
 * just one the Prover picks. The queue starts empty so the new entry is the
 * one at the head; an entry behind others runs once those ahead of it have
 * run or been skipped, which 4.22 covers.
 *
 * Assumptions:
 *   - The target accepts the call. `target` is DummyAvatar, summarized to
 *     succeed. On chain the target is the Ownerless Safe, which returns the
 *     inner call's success, so a transaction that itself reverts on the
 *     Ownerless Safe makes executeNextTx revert. This rule is about the
 *     governance path, not about whether the proposal's own call succeeds.
 *   - Creation time + cooldown + expiration fits in a uint256. Delay adds
 *     them under checked arithmetic, so an overflow reverts; real
 *     timestamps and settings are nowhere near that bound.
 *   - `data` is at most 971 bytes (hashing_length_bound, see the header).
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
 * The two timing conditions are real: outside them the head entry cannot run.
 * The pause condition is 4.15.
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
