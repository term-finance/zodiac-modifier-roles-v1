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
 *   who can call each entry point
 *     onlyOwnerCanCallRolesSettings       each of the twenty settings
 *                                         functions succeeds only for the owner
 *     ownerCanCallEachRolesSetting        and the owner can call each (witness)
 *     onlyEnabledModulesCanExec           each of the four execution functions
 *                                         succeeds only for an address in the
 *                                         module list
 *     moduleWithoutDefaultRoleCannotExecFromModule
 *                                         an enabled module that is not a
 *                                         member of its default role cannot
 *                                         call the two FromModule ones
 *     moduleWithoutRoleCannotExecTransactionWithRole
 *     moduleWithoutRoleCannotExecTransactionWithRoleReturnData
 *                                         nor the two WithRole ones without
 *                                         membership of the role the call
 *                                         names; a module with no assigned
 *                                         role can call none of the four
 *     roleMemberModuleCanExecFromModule
 *     roleMemberModuleCanExecTransactionWithRole
 *     roleMemberModuleCanExecTransactionWithRoleReturnData
 *                                         an enabled module holding the role
 *                                         the call runs under can call each
 *                                         (witnesses)
 *
 *   every entry point is accounted for
 *     rolesWriteFunctionsAreTheKnownTwentyFive
 *                                         no fallback, and the write functions
 *                                         are exactly the twenty-five above
 *     onlyModulesOrOwnerCanCallRoles      over every write function but setUp,
 *                                         by behaviour rather than by name: a
 *                                         call that succeeds came from the
 *                                         owner or an address in the module
 *                                         list
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

/* ------------------------------------------------------------------------
 * 3. Who can call each entry point
 * --------------------------------------------------------------------- */

/*
 * The twenty settings functions: Roles' own thirteen (Roles.sol:73-313),
 * setAvatar and setTarget (zodiac core/Module.sol:23, :31), disableModule and
 * enableModule (core/Modifier.sol:68, :85), setGuard (guard/Guardable.sol:17),
 * renounceOwnership and transferOwnership (OwnableUpgradeable.sol:59, :67).
 * Every one carries `onlyOwner`.
 */
definition isOnlyOwner(method f) returns bool =
    f.selector == sig:setMultisend(address).selector ||
    f.selector == sig:allowTarget(uint16, address, RolesHarness.ExecutionOptions).selector ||
    f.selector == sig:revokeTarget(uint16, address).selector ||
    f.selector == sig:scopeTarget(uint16, address).selector ||
    f.selector == sig:scopeAllowFunction(uint16, address, bytes4, RolesHarness.ExecutionOptions).selector ||
    f.selector == sig:scopeRevokeFunction(uint16, address, bytes4).selector ||
    f.selector == sig:scopeFunction(
        uint16, address, bytes4, bool[], RolesHarness.ParameterType[],
        RolesHarness.Comparison[], bytes[], RolesHarness.ExecutionOptions
    ).selector ||
    f.selector == sig:scopeFunctionExecutionOptions(uint16, address, bytes4, RolesHarness.ExecutionOptions).selector ||
    f.selector == sig:scopeParameter(
        uint16, address, bytes4, uint256, RolesHarness.ParameterType, RolesHarness.Comparison, bytes
    ).selector ||
    f.selector == sig:scopeParameterAsOneOf(
        uint16, address, bytes4, uint256, RolesHarness.ParameterType, bytes[]
    ).selector ||
    f.selector == sig:unscopeParameter(uint16, address, bytes4, uint8).selector ||
    f.selector == sig:assignRoles(address, uint16[], bool[]).selector ||
    f.selector == sig:setDefaultRole(address, uint16).selector ||
    f.selector == sig:setAvatar(address).selector ||
    f.selector == sig:setTarget(address).selector ||
    f.selector == sig:enableModule(address).selector ||
    f.selector == sig:disableModule(address, address).selector ||
    f.selector == sig:setGuard(address).selector ||
    f.selector == sig:transferOwnership(address).selector ||
    f.selector == sig:renounceOwnership().selector;

/// The two execution functions that run under the caller's default role
/// (Roles.sol:321, :344).
definition isExecFromModule(method f) returns bool =
    f.selector == sig:execTransactionFromModule(address, uint256, bytes, Enum.Operation).selector ||
    f.selector == sig:execTransactionFromModuleReturnData(address, uint256, bytes, Enum.Operation).selector;

/// The two execution functions that run under a role the caller names
/// (Roles.sol:369, :392).
definition isExecWithRole(method f) returns bool =
    f.selector == sig:execTransactionWithRole(address, uint256, bytes, Enum.Operation, uint16, bool).selector ||
    f.selector == sig:execTransactionWithRoleReturnData(address, uint256, bytes, Enum.Operation, uint16, bool).selector;

definition isExec(method f) returns bool =
    isExecFromModule(f) || isExecWithRole(f);

definition isSetUp(method f) returns bool =
    f.selector == sig:setUp(bytes).selector;

/*
 * Only the owner gets through any of the twenty settings functions. Unlike
 * rolesConfigOnlyChangesThroughOwner, this is about the call succeeding, not
 * about which storage moved, so it also covers the function and parameter
 * scoping that rule does not track. Checked once per function.
 */
rule onlyOwnerCanCallRolesSettings(method f, calldataarg args)
    filtered { f -> isOnlyOwner(f) }
{
    env e;
    address ownerBefore = owner();

    f@withrevert(e, args);

    assert !lastReverted => e.msg.sender == ownerBefore,
        "a settings function succeeded for a caller other than the owner";
}

/*
 * The bound above is not achieved by nothing working: for each of the twenty
 * settings functions, some call from the owner succeeds.
 */
rule ownerCanCallEachRolesSetting(method f, calldataarg args)
    filtered { f -> isOnlyOwner(f) }
{
    env e;
    require e.msg.sender == owner();

    f@withrevert(e, args);

    satisfy !lastReverted,
        "the owner cannot successfully call this settings function";
}

/*
 * Each of the four execution functions only succeeds for an address in the
 * module list: moduleOnly (Modifier.sol:59-62) checks `modules[msg.sender]`
 * before anything else. The list head 0x1 also has an entry, but 0x1 is the
 * ecrecover precompile and never sends a transaction. Checked once per
 * function.
 */
rule onlyEnabledModulesCanExec(method f, calldataarg args)
    filtered { f -> isExec(f) }
{
    env e;
    bool senderWasModule = moduleEntry(e.msg.sender) != 0;

    f@withrevert(e, args);

    assert !lastReverted => senderWasModule,
        "an address not in the module list successfully called an execution function";
}

/*
 * A module without an assigned role cannot execute. Stated per call: an
 * enabled module that is not a member of the role a call runs under always
 * reverts, whatever it sends, because Permissions.check first reverts unless
 * the caller is a member of that role (Permissions.sol:184-186). A module
 * with no assigned role at all is a member of no role, so all four execution
 * functions revert for it.
 *
 * execTransactionFromModule and execTransactionFromModuleReturnData run under
 * the caller's default role. Checked once per function.
 */
rule moduleWithoutDefaultRoleCannotExecFromModule(method f, calldataarg args)
    filtered { f -> isExecFromModule(f) }
{
    env e;
    require moduleEntry(e.msg.sender) != 0;
    require !memberOf(defaultRoles(e.msg.sender), e.msg.sender);

    f@withrevert(e, args);

    assert lastReverted,
        "an enabled module that is not a member of its default role executed through a FromModule function";
}

/*
 * execTransactionWithRole runs under the role the call names. Unlike
 * nonMemberExecTransactionWithRoleAlwaysReverts in
 * setTxNonceRoleConfigSufficient.spec, nothing is assumed about the guard,
 * the target or the value sent.
 */
rule moduleWithoutRoleCannotExecTransactionWithRole(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint16 role, bool shouldRevert
) {
    env e;
    require moduleEntry(e.msg.sender) != 0;
    require !memberOf(role, e.msg.sender);

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert lastReverted,
        "an enabled module that is not a member of the role it named executed through execTransactionWithRole";
}

/* The same for execTransactionWithRoleReturnData. */
rule moduleWithoutRoleCannotExecTransactionWithRoleReturnData(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint16 role, bool shouldRevert
) {
    env e;
    require moduleEntry(e.msg.sender) != 0;
    require !memberOf(role, e.msg.sender);

    execTransactionWithRoleReturnData@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert lastReverted,
        "an enabled module that is not a member of the role it named executed through execTransactionWithRoleReturnData";
}

/*
 * The bounds above are not achieved by nothing working: an enabled module
 * that is a member of the role the call runs under can successfully call each
 * of the four execution functions. The two FromModule ones run under the
 * caller's default role, checked once per function here; the two WithRole
 * ones under the role the call names, one rule each below.
 */
rule roleMemberModuleCanExecFromModule(method f, calldataarg args)
    filtered { f -> isExecFromModule(f) }
{
    env e;
    require e.msg.sender != SENTINEL_MODULES();
    require moduleEntry(e.msg.sender) != 0;
    require memberOf(defaultRoles(e.msg.sender), e.msg.sender);

    f@withrevert(e, args);

    satisfy !lastReverted,
        "an enabled module holding its default role cannot successfully call this execution function";
}

rule roleMemberModuleCanExecTransactionWithRole(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint16 role, bool shouldRevert
) {
    env e;
    require e.msg.sender != SENTINEL_MODULES();
    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    satisfy !lastReverted,
        "an enabled module holding the role it names cannot successfully call execTransactionWithRole";
}

rule roleMemberModuleCanExecTransactionWithRoleReturnData(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint16 role, bool shouldRevert
) {
    env e;
    require e.msg.sender != SENTINEL_MODULES();
    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);

    execTransactionWithRoleReturnData@withrevert(e, to, value, data, operation, role, shouldRevert);

    satisfy !lastReverted,
        "an enabled module holding the role it names cannot successfully call execTransactionWithRoleReturnData";
}

/* ------------------------------------------------------------------------
 * 4. Every entry point is accounted for
 * --------------------------------------------------------------------- */

/*
 * The rules in section 3 each cover a list of functions. These two show the
 * lists are complete, as delayWriteFunctionsAreTheKnownFifteen and
 * onlyModulesOrOwnerCanCallDelay do for the Delay.
 *
 * The first is a claim about shape: Roles has no fallback, and its write
 * functions are exactly the twenty settings functions, the four execution
 * functions and setUp. If a function is ever added, this rule fails, and the
 * new function needs its own access rule. @withrevert keeps functions that
 * revert in the chosen state reachable.
 *
 * The second covers every write function but setUp at once, by behaviour
 * rather than by name: any call that succeeds came from the owner or an
 * address in the module list. It holds for a function added later too. setUp
 * is setUpAlwaysRevertsAfterDeployment's.
 */
rule rolesWriteFunctionsAreTheKnownTwentyFive(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;

    f@withrevert(e, args);

    assert !f.isFallback,
        "Roles has a fallback, which no access rule covers";
    assert isOnlyOwner(f) || isExec(f) || isSetUp(f),
        "Roles has a write function that no access rule covers";
}

rule onlyModulesOrOwnerCanCallRoles(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isSetUp(f) }
{
    env e;
    address ownerBefore = owner();
    bool senderWasModule = moduleEntry(e.msg.sender) != 0;

    f@withrevert(e, args);

    assert !lastReverted => (e.msg.sender == ownerBefore || senderWasModule),
        "a caller that is neither the owner nor in the module list successfully called Roles";
}
