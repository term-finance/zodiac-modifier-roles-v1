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
 *     atMostOneCallerPassesOnlyOwner      from the same state, each settings
 *                                         function admits at most one
 *                                         caller, and it is owner()
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
 *   with no owner, the settings functions are unreachable
 *     noOwnerSettingsAlwaysRevert         with the owner at address(0), each of
 *                                         the twenty settings functions reverts
 *                                         for every caller but address(0),
 *                                         which never sends a transaction
 *     noOwnerStaysNoOwner                 and no entry point but setUp can give
 *                                         the module an owner back
 *     renounceOwnershipLeavesNoOwner      an owner's renounceOwnership reaches
 *                                         that state (witness)
 *
 *   role membership and default roles have one setter each
 *     membershipOnlyChangesThroughAssignRoles
 *                                         over every write function, setUp
 *                                         included: a membership changes only
 *                                         through assignRoles, and always
 *                                         with an AssignRoles event
 *     defaultRoleOnlyChangesThroughSetDefaultRole
 *                                         likewise a default role, through
 *                                         setDefaultRole and SetDefaultRole
 *     ownerCanChangeMembershipThroughAssignRoles
 *                                         the owner's assignRoles really does
 *                                         change a membership (witness)
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
 * One owner at a time. From the same state and with the same arguments, each
 * of the twenty settings functions admits at most one caller, and that caller
 * is owner(). Mirrors the Delay's atMostOneCallerPassesOnlyOwner.
 *
 * Both calls run from the same snapshot, with the same arguments, so the only
 * thing that differs between them is msg.sender. The first assertion is the
 * substance; the second is its consequence, stated so the claim reads as
 * written. ownerCanCallEachRolesSetting is the witness that the admitted
 * caller really does get through, so "at most one" is not "none".
 */
rule atMostOneCallerPassesOnlyOwner(method f, calldataarg args)
    filtered { f -> isOnlyOwner(f) }
{
    env ea;
    env eb;
    require ea.msg.sender != eb.msg.sender;

    address ownerBefore = owner();
    storage init = lastStorage;

    f@withrevert(ea, args);
    bool aPassed = !lastReverted;

    f@withrevert(eb, args) at init;
    bool bPassed = !lastReverted;

    assert aPassed => ea.msg.sender == ownerBefore,
        "a settings function admitted a caller other than owner()";
    assert !(aPassed && bPassed),
        "two distinct callers both passed the same settings function from the same state";
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

/* ------------------------------------------------------------------------
 * 5. With no owner, the settings functions are unreachable
 * --------------------------------------------------------------------- */

/*
 * renounceOwnership sets the owner to address(0) (OwnableUpgradeable.sol:59).
 * onlyOwner then admits only msg.sender == address(0), and no transaction
 * comes from address(0): nobody holds its key and no contract lives there.
 * onlyOwnerCanCallRolesSettings leaves that caller open, because the Prover
 * does not rule out msg.sender == 0 by itself, so these rules exclude it
 * explicitly.
 *
 * With the owner at address(0), none of the twenty settings functions
 * succeeds, for any caller and any arguments. Checked once per function.
 */
rule noOwnerSettingsAlwaysRevert(method f, calldataarg args)
    filtered { f -> isOnlyOwner(f) }
{
    env e;
    require owner() == 0;
    require e.msg.sender != 0;

    f@withrevert(e, args);

    assert lastReverted,
        "a settings function succeeded while the Roles module has no owner";
}

/*
 * And the owner stays address(0): no entry point but setUp can give the
 * module an owner back. setUp is setUpAlwaysRevertsAfterDeployment's.
 * @withrevert keeps every instance reachable, including the settings
 * functions, which always revert in this pre-state; a revert leaves the owner
 * where it was.
 */
rule noOwnerStaysNoOwner(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isSetUp(f) }
{
    env e;
    require owner() == 0;
    require e.msg.sender != 0;

    f@withrevert(e, args);

    assert owner() == 0,
        "the Roles module got an owner back";
}

/*
 * The two rules above are not about an unreachable state: an owner's
 * renounceOwnership succeeds and leaves the module with no owner. Witness.
 */
rule renounceOwnershipLeavesNoOwner() {
    env e;
    require owner() != 0;
    require e.msg.sender == owner();

    renounceOwnership@withrevert(e);

    satisfy !lastReverted && owner() == 0,
        "the owner cannot renounce ownership";
}

/* ------------------------------------------------------------------------
 * 6. Role membership and default roles have one setter each
 * --------------------------------------------------------------------- */

/*
 * The deployment evidence for "the Governor has only ever been given role 1"
 * reads the Roles Modifier's event history: one AssignRoles and one
 * SetDefaultRole. That reading is sound only if no membership or default role
 * can change without the matching event. These rules prove it.
 *
 * Neither event has an indexed parameter, so each is a LOG1 whose only topic
 * is the event signature. The hook records only logs the Roles Modifier
 * itself emits.
 *
 * Unlike the parametric rules above, these keep setUp in `f`: setUp writes
 * neither membership nor default roles, so it satisfies both rules in any
 * pre-state, including the one it runs in at creation.
 */

/// keccak256("AssignRoles(address,uint16[],bool[])")
definition ASSIGN_ROLES_TOPIC() returns bytes32 =
    to_bytes32(0x4dcd99505817a4d3e4d3f751a4a49739ec38cb0f83319ff1224a3b289597e86c);

/// keccak256("SetDefaultRole(address,uint16)")
definition SET_DEFAULT_ROLE_TOPIC() returns bytes32 =
    to_bytes32(0x197e61bb67ba4b0f657afcb5d2dbed385d50b697c51090f466cdbcc4c30a21ce);

persistent ghost bool emittedAssignRoles;
persistent ghost bool emittedSetDefaultRole;

hook LOG1(uint offset, uint length, bytes32 t1) {
    if (executingContract == currentContract && t1 == ASSIGN_ROLES_TOPIC()) {
        emittedAssignRoles = true;
    }
    if (executingContract == currentContract && t1 == SET_DEFAULT_ROLE_TOPIC()) {
        emittedSetDefaultRole = true;
    }
}

/*
 * Over every write function, setUp included, and every caller: if any
 * module's membership of any role changed, the function was assignRoles
 * (Roles.sol:290) and the Roles Modifier emitted AssignRoles.
 */
rule membershipOnlyChangesThroughAssignRoles(
    method f, calldataarg args, uint16 roleId, address acct
) filtered { f -> !f.isView && !f.isPure }
{
    env e;
    require !emittedAssignRoles;
    bool memberBefore = memberOf(roleId, acct);

    f(e, args);

    bool changed = memberOf(roleId, acct) != memberBefore;
    assert changed =>
        f.selector == sig:RolesHarness.assignRoles(address, uint16[], bool[]).selector,
        "a function other than assignRoles changed a role membership";
    assert changed => emittedAssignRoles,
        "a role membership changed without an AssignRoles event";
}

/*
 * The same for default roles: if any module's default role changed, the
 * function was setDefaultRole (Roles.sol:310) and the Roles Modifier emitted
 * SetDefaultRole. ownerCanStillReconfigure is the witness that a default
 * role really can change.
 */
rule defaultRoleOnlyChangesThroughSetDefaultRole(
    method f, calldataarg args, address acct
) filtered { f -> !f.isView && !f.isPure }
{
    env e;
    require !emittedSetDefaultRole;
    uint16 defaultRoleBefore = defaultRoles(acct);

    f(e, args);

    bool changed = defaultRoles(acct) != defaultRoleBefore;
    assert changed =>
        f.selector == sig:RolesHarness.setDefaultRole(address, uint16).selector,
        "a function other than setDefaultRole changed a default role";
    assert changed => emittedSetDefaultRole,
        "a default role changed without a SetDefaultRole event";
}

/*
 * membershipOnlyChangesThroughAssignRoles is not achieved by nothing working:
 * the owner's assignRoles can flip a module's membership of a role. Witness.
 */
rule ownerCanChangeMembershipThroughAssignRoles(
    address module, uint16 roleId, uint16[] rolesArg, bool[] memberOfArg
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require e.msg.sender == owner();

    bool memberBefore = memberOf(roleId, module);
    require rolesArg.length == 1 && memberOfArg.length == 1;
    require rolesArg[0] == roleId && memberOfArg[0] == !memberBefore;

    assignRoles@withrevert(e, module, rolesArg, memberOfArg);

    satisfy !lastReverted && memberOf(roleId, module) != memberBefore,
        "the owner cannot change a role membership through assignRoles";
}

/*
 * Being the owner gives no way to execute. The owner's call to any of the
 * four execution functions reverts unless the owner is itself an enabled
 * module and a member of the role the call runs under: its default role for
 * the two FromModule functions, the role it names for the two WithRole
 * functions. Same notion of "enabled module" as onlyEnabledModulesCanExec.
 */
rule ownerWithoutModuleRoleCannotExecFromModule(method f, calldataarg args)
    filtered { f -> isExecFromModule(f) }
{
    env e;
    require e.msg.sender == owner();
    require !(moduleEntry(e.msg.sender) != 0 &&
              memberOf(defaultRoles(e.msg.sender), e.msg.sender));

    f@withrevert(e, args);

    assert lastReverted,
        "the owner executed through a FromModule function without being an enabled module in its default role";
}

rule ownerWithoutModuleRoleCannotExecTransactionWithRole(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint16 role, bool shouldRevert
) {
    env e;
    require e.msg.sender == owner();
    require !(moduleEntry(e.msg.sender) != 0 && memberOf(role, e.msg.sender));

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert lastReverted,
        "the owner executed through execTransactionWithRole without being an enabled module in the role it named";
}

rule ownerWithoutModuleRoleCannotExecTransactionWithRoleReturnData(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint16 role, bool shouldRevert
) {
    env e;
    require e.msg.sender == owner();
    require !(moduleEntry(e.msg.sender) != 0 && memberOf(role, e.msg.sender));

    execTransactionWithRoleReturnData@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert lastReverted,
        "the owner executed through execTransactionWithRoleReturnData without being an enabled module in the role it named";
}
