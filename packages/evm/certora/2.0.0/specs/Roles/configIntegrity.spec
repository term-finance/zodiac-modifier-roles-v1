/*
 * Roles Modifier configuration integrity: the configuration changes only
 * through the owner, only the owner can call the settings functions, only an
 * enabled module holding the role a call runs under can execute, and with no
 * owner the settings are frozen.
 *
 * The scene is the Roles Modifier under RolesHarness, with `target` linked to
 * DummyAvatar.
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

    // Guard calls resolve to SetTxNonceGuard, the only guard in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);
}

// SENTINEL_MODULES, an internal constant in Modifier.sol.
definition SENTINEL_MODULES() returns address = 0x1;

/* ------------------------------------------------------------------------
 * 1. setUp is spent
 * --------------------------------------------------------------------- */

/*
 * Once the module list is set up, setUp always reverts, so nobody can re-run
 * it to replace the owner or the module list. The parametric rules below,
 * except those in section 6, exclude setUp; this rule covers it.
 */
rule setUpAlwaysRevertsAfterDeployment(bytes initParams) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) != 0;

    setUp@withrevert(e, initParams);

    assert lastReverted,
        "setUp ran a second time, which would reset the module ring and the owner";
}

/* ------------------------------------------------------------------------
 * 2. Configuration is owner-only
 * --------------------------------------------------------------------- */

/*
 * Over every write function except setUp, and every caller, the guard,
 * multisend, avatar, target, owner, module list, default roles, role
 * membership and target clearances change only when the caller is the owner.
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
 * Over every write function except setUp, the owner changes only through
 * transferOwnership or renounceOwnership, and only when the caller is the
 * current owner.
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
 * The owner's setDefaultRole succeeds and records the new default role, so
 * the rules above are not vacuous.
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

/// The twenty settings functions. Every one carries `onlyOwner`.
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
 * Each of the twenty settings functions succeeds only when the caller is the
 * owner. This also covers the function and parameter scoping, which
 * rolesConfigOnlyChangesThroughOwner does not track.
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
 * For each of the twenty settings functions, some call from the owner
 * succeeds, so the rule above is not vacuous.
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
 * Each settings function succeeds only when the caller is the owner, and from
 * the same state no two different callers can both succeed.
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
 * module list.
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
 * An enabled module that is not a member of its default role cannot execute
 * through execTransactionFromModule or execTransactionFromModuleReturnData.
 * With the two rules below, a module with no assigned role can execute
 * nothing through any of the four execution functions.
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
 * An enabled module that is not a member of the role the call names cannot
 * execute through execTransactionWithRole.
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
 * An enabled module that is a member of the role the call runs under can
 * successfully call each of the four execution functions, so the rules above
 * are not vacuous.
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
 * Roles has no fallback, and its write functions are exactly the twenty
 * settings functions, the four execution functions and setUp.
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

/*
 * Apart from setUp, a call to any write function succeeds only if the caller
 * is the owner or an enabled module.
 */
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
 * With the owner at address(0), each of the twenty settings functions reverts
 * for every caller except address(0), which never sends a transaction.
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
 * With the owner at address(0), no write function other than setUp can give
 * the Roles Modifier an owner again. setUp always reverts after deployment
 * (setUpAlwaysRevertsAfterDeployment).
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
 * An owner's renounceOwnership succeeds and leaves the Roles Modifier with no
 * owner, so the two rules above are not vacuous.
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
 * The Roles Modifier's AssignRoles and SetDefaultRole history records every
 * membership and default-role change only if none happens without its event.
 * These rules keep setUp in `f`. Neither event has an indexed parameter, so
 * each is a LOG1 whose only topic is its signature.
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
 * SetDefaultRole.
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
 * The owner's assignRoles can flip a module's membership of a role, so
 * membershipOnlyChangesThroughAssignRoles is not vacuous.
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
 * The owner's call to any of the four execution functions reverts unless the
 * owner is itself an enabled module and a member of the role the call runs
 * under: its default role for the two FromModule functions, the role it names
 * for the two WithRole functions.
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
