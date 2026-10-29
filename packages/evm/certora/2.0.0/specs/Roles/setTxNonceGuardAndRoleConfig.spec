/*
 * Governor limited to Delay.setTxNonce: with SetTxNonceGuard installed and
 * pointed at the Delay, and role 1 configured, every call the Governor
 * completes through the Roles Modifier is setTxNonce(uint256) on the Delay,
 * with zero value and as a plain Call, on all four execution entry points.
 *
 * The Governor is an enabled module, a member of role 1 only, with default
 * role 1. The scene is the Roles Modifier under RolesHarness with `target`
 * linked to DummyAvatar, and DelayTarget as the Delay.
 */

using SetTxNonceGuard as setTxNonceGuardContract;
using DelayTarget as delayMod;

methods {
    function memberOf(uint16, address) external returns (bool) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForData(uint16, address, bytes) external returns (uint256) envfree;
    function unpackFunctionOptions(uint256) external returns (RolesHarness.ExecutionOptions, bool, uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;
    function multisend() external returns (address) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;
    function avatar() external returns (address) envfree;
    function owner() external returns (address) envfree;
    function defaultRoles(address) external returns (uint16) envfree;

    function setTxNonceGuardContract.delay() external returns (address) envfree;

    // Guard calls resolve to SetTxNonceGuard, the only guard in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
}

definition ROLE() returns uint16 = 1;
definition SENTINEL_MODULES() returns address = 0x1;

/*
 * The wiring: the guard is installed and pointed at the Delay, and the
 * Governor is an enabled module, a member of role 1 with default role 1, and
 * not the owner.
 */
function governorWiredWithSetTxNonceGuard(env e, address governor) {
    require guard() == setTxNonceGuardContract;              // Roles.setGuard
    require setTxNonceGuardContract.delay() == delayMod;     // guard pinned to this Delay
    require delayMod != currentContract;
    require target() != currentContract;

    require target() != delayMod;

    require avatar() == owner();
    require target() != owner();

    // The module has been set up.
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();

    require moduleEntry(governor) != 0;            // assignRoles enabled it
    require memberOf(ROLE(), governor);
    require defaultRoles(governor) == ROLE();

    // The Governor does not own the Roles Modifier.
    require governor != owner();

    require e.msg.sender == governor;
    require e.msg.value == 0;
}

/*
 * The configuration: role 1 has Function clearance on the Delay, no other
 * target has clearance under the role the call runs under, and the Governor
 * is a member of no role but role 1. `to`, `role` and `data` are the
 * arguments the rule executes with.
 */
function setTxNonceRoleConfigPinned(address governor, address to, uint16 role, bytes data) {
    require clearanceOf(ROLE(), delayMod) == RolesHarness.Clearance.Function;
    require to != delayMod => clearanceOf(role, to) == RolesHarness.Clearance.None;
    require role != ROLE() => !memberOf(role, governor);
}

/*
 * The Governor can successfully call no Roles write function other than the
 * four execution functions.
 */
rule governorSucceedsOnlyThroughRolesExecEntryPoints(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);

    f@withrevert(e, args);

    assert !lastReverted => (
        f.selector == sig:execTransactionFromModule(address,uint256,bytes,Enum.Operation).selector ||
        f.selector == sig:execTransactionFromModuleReturnData(address,uint256,bytes,Enum.Operation).selector ||
        f.selector == sig:execTransactionWithRole(address,uint256,bytes,Enum.Operation,uint16,bool).selector ||
        f.selector == sig:execTransactionWithRoleReturnData(address,uint256,bytes,Enum.Operation,uint16,bool).selector
    ), "the Governor got through a Roles entry point other than the four execution ones";
}

/*
 * Every call the Governor completes through execTransactionWithRole is
 * setTxNonce on the Delay, with zero value and as a plain Call.
 */
rule governorExecTransactionWithRoleLimitedToDelaySetTxNonce(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, to, role, data);

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the Governor completed a call that was not setTxNonce on the Delay";
}

/*
 * The same through execTransactionFromModule, which runs under the Governor's
 * default role.
 */
rule governorExecTransactionFromModuleLimitedToDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, to, ROLE(), data);

    execTransactionFromModule@withrevert(e, to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the Governor completed a non-setTxNonce call through its default role";
}

/*
 * The same through execTransactionWithRoleReturnData.
 */
rule governorExecTransactionWithRoleReturnDataLimitedToDelaySetTxNonce(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, to, role, data);

    execTransactionWithRoleReturnData@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the Governor completed a non-setTxNonce call through the ReturnData path";
}

/*
 * The same through execTransactionFromModuleReturnData.
 */
rule governorExecTransactionFromModuleReturnDataLimitedToDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, to, ROLE(), data);

    execTransactionFromModuleReturnData@withrevert(e, to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the Governor completed a non-setTxNonce call through the default-role ReturnData path";
}

/*
 * The Governor's setTxNonce call on the Delay goes through, so the rules
 * above are not vacuous.
 */
rule governorCanStillCallDelaySetTxNonce(bytes data, uint256 scopeConfig) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, delayMod, ROLE(), data);

    require selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector;
    require data.length == 36;

    // The function really is allowed: wildcarded, no Send, no DelegateCall.
    require functionScopeConfigForData(ROLE(), delayMod, data) == scopeConfig;
    require scopeConfig != 0;
    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length = unpackFunctionOptions(scopeConfig);
    require isWildcarded;
    require options == RolesHarness.ExecutionOptions.None;
    require delayMod != multisend();

    execTransactionWithRole(e, delayMod, 0, data, Enum.Operation.Call, ROLE(), true);

    satisfy true, "the configured setTxNonce call is not reachable at all, so the bounding rules are vacuous";
}
