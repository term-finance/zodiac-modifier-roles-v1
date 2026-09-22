/*
 * Property: every piece of Roles state that bounds the Governor is
 * owner-only, so the Governor can never widen its own scope.
 *
 * Properties 1-3 all bound what the Governor can execute GIVEN a
 * configuration: SetTxNonceGuard installed and pinned to the Delay, role 1
 * scoped to Clearance.Function on the Delay with setTxNonce allowed. Each of
 * those is mutable storage. If the Governor could reach any of it — the
 * guard, the scoping, its own role membership, the module ring, `target` —
 * the bounds those properties prove would hold right up until the Governor
 * chose to remove them.
 *
 * This file closes that loop. `governorSucceedsOnlyThroughRolesExecEntryPoints`
 * (Property 1.2) already says it for the Governor specifically; these rules
 * say it for every caller and every piece of configuration at once, which is
 * the form that survives someone later adding an entry point.
 *
 * Rules:
 *
 *   setUp is spent
 *     setUpAlwaysRevertsAfterDeployment   the public, unmodified setUp cannot
 *                                         be re-entered to reset the module
 *                                         ring and the owner. PROOFS.md
 *                                         currently carries this as an
 *                                         assumption read off Roles.sol:56-59
 *                                         for Properties 1.1-1.3; this proves
 *                                         it instead
 *
 *   configuration is owner-only
 *     rolesConfigOnlyChangesThroughOwner  over every entry point and every
 *                                         caller: if any of guard, multisend,
 *                                         avatar, target, owner, the module
 *                                         ring, defaultRoles, role membership
 *                                         or target clearance moved, the
 *                                         caller was the owner
 *     ownerOnlyChangesThroughOwnableTransfer
 *                                         and ownership itself moves only
 *                                         through OwnableUpgradeable's own
 *                                         two entry points
 *     ownerCanStillReconfigure            the owner still can (witness)
 *
 * Deliberately NOT claimed here:
 *   - That the configuration is correct. What the owner has configured is
 *     Property 3's subject; this file says only that nobody else can move it.
 *   - That the owner will not widen the Governor's scope itself. The Roles
 *     owner is the Ownerless Safe, reachable only by queueing through the
 *     Delay — a 5-of-11 signature plus a 1-day cooldown, in the open. That
 *     asymmetry is the design, and it is a deployment fact rather than
 *     something these rules establish.
 *   - Anything about the avatar's return path. `target` is linked to
 *     DummyAvatar here, which calls nothing, so the equivalent of the Delay
 *     spec's claim 4 is not in scene. On this side the avatar is the
 *     DelayOwnerSafe, and what the Governor can make it emit is Property 1.
 *
 * Modelling notes.
 *   - The parametric rules exclude setUp from `f` and assume nothing about
 *     the pre-state; setUpAlwaysRevertsAfterDeployment carries that entry
 *     point on its own. See the note above the rules for why pinning the
 *     pre-state instead would make the setUp instance vacuous.
 *   - SetTxNonceGuard is in the scene only so Guardable.setGuard's ERC-165
 *     probe and Module.exec's hooks resolve against a real implementation
 *     rather than an unresolved call that could havoc storage. No rule here
 *     says anything about what the guard checks.
 */

using SetTxNonceGuard as setTxNonceGuardContract;

methods {
    function memberOf(uint16, address) external returns (bool) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function multisend() external returns (address) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;
    function avatar() external returns (address) envfree;
    function owner() external returns (address) envfree;
    function defaultRoles(address) external returns (uint16) envfree;

    // Module.exec / execAndReturnData call these on `guard` when it is set,
    // and setGuard probes supportsInterface on a new guard. SetTxNonceGuard
    // is the only implementor in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);
}

/// Modifier.sol:13 — `address internal constant`, so there is no getter.
definition SENTINEL_MODULES() returns address = 0x1;

/*
 * On setUp, and why the parametric rules exclude it.
 *
 * setUp is the one entry point that can legitimately rewrite the module ring
 * and the owner, so a parametric rule that left it in would report it as a
 * counterexample to every claim in this file. The obvious fix — requiring the
 * ring already set up (moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES(),
 * Roles.sol:56-59) — is worse than useless: in that pre-state setUp ALWAYS
 * reverts, and a parametric `f(e, args)` without @withrevert prunes reverting
 * paths, so the setUp instance passes with an unreachable body. Vacuous, not
 * proved.
 *
 * So the parametric rules below filter setUp out of `f` and assume nothing at
 * all about the pre-state, which makes them strictly stronger — they hold from
 * any storage the Prover can pick. setUpAlwaysRevertsAfterDeployment states
 * the setUp case directly instead, as a revert claim where a revert is the
 * thing being asserted rather than something silently assumed away.
 *
 * The two together cover every entry point of the deployed contract. The
 * non-parametric rules further down still require the ring set up, because
 * they are about behaviour in the deployed configuration rather than about
 * every reachable storage state.
 */

/* ------------------------------------------------------------------------
 * 1. setUp is spent
 * --------------------------------------------------------------------- */

/*
 * setUp is `public` with no access modifier of its own (Roles.sol:44). It is
 * safe only because of two things inside it: __Ownable_init() carries OZ's
 * `initializer`, and setupModules() asserts the sentinel slot is still empty
 * (Roles.sol:56-59). A second setUp would run transferOwnership(attacker) and
 * reset the module ring, which is every bound in this file at once.
 *
 * Stated against the module ring alone, so it holds whichever of the two
 * guards the Prover's chosen pre-state trips.
 */
rule setUpAlwaysRevertsAfterDeployment(bytes initParams) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();

    setUp@withrevert(e, initParams);

    assert lastReverted,
        "setUp ran a second time, which would reset the module ring and the owner";
}

/* ------------------------------------------------------------------------
 * 2. Configuration is owner-only
 * --------------------------------------------------------------------- */

/*
 * Over every state-changing entry point and every caller: if any piece of the
 * configuration that Properties 1-3 depend on moved, the caller was the
 * owner. The Governor is an enabled module, never the owner, so this is the
 * rule that says its bounds cannot be lifted from inside.
 */
rule rolesConfigOnlyChangesThroughOwner(
    method f, calldataarg args, uint16 roleId, address acct, address targetAddress
) filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:RolesHarness.setUp(bytes).selector
    }
{
    env e;
    address ownerBefore = owner();

    address guardBefore = guard();
    address multisendBefore = multisend();
    address avatarBefore = avatar();
    address targetBefore = target();
    address moduleEntryBefore = moduleEntry(acct);
    uint16 defaultRoleBefore = defaultRoles(acct);
    bool memberBefore = memberOf(roleId, acct);
    RolesHarness.Clearance clearanceBefore = clearanceOf(roleId, targetAddress);

    f(e, args);

    bool changed =
        guard() != guardBefore ||
        multisend() != multisendBefore ||
        avatar() != avatarBefore ||
        target() != targetBefore ||
        owner() != ownerBefore ||
        moduleEntry(acct) != moduleEntryBefore ||
        defaultRoles(acct) != defaultRoleBefore ||
        memberOf(roleId, acct) != memberBefore ||
        clearanceOf(roleId, targetAddress) != clearanceBefore;

    assert changed => e.msg.sender == ownerBefore,
        "a caller other than the owner changed the Roles configuration";
}

/*
 * Ownership itself moves only through OwnableUpgradeable's own two entry
 * points, and only for the current owner — so the rule above cannot be
 * sidestepped by first becoming the owner.
 */
rule ownerOnlyChangesThroughOwnableTransfer(method f, calldataarg args)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:RolesHarness.setUp(bytes).selector
    }
{
    env e;
    address ownerBefore = owner();

    f(e, args);

    assert owner() != ownerBefore =>
        (f.selector == sig:RolesHarness.transferOwnership(address).selector ||
         f.selector == sig:RolesHarness.renounceOwnership().selector),
        "an entry point other than transferOwnership or renounceOwnership changed the owner";
    assert owner() != ownerBefore => e.msg.sender == ownerBefore,
        "a caller other than the owner changed the owner";
}

/*
 * The bound above is not achieved by nothing working: the owner can still
 * reconfigure. Non-vacuity witness for the rules above, on the one piece of
 * configuration whose whole purpose is to be changed after deployment.
 */
rule ownerCanStillReconfigure(address module, uint16 roleId) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require e.msg.sender == owner();
    require defaultRoles(module) != roleId;

    setDefaultRole@withrevert(e, module, roleId);

    assert !lastReverted,
        "the Roles owner could not set a default role";
    assert defaultRoles(module) == roleId,
        "setDefaultRole returned without recording the new default role";
}
