/*
 * SetTxNonceGuard alone is sufficient: with the guard installed and pointed
 * at the Delay, and the role configuration left completely unconstrained,
 * every call that completes through the Roles Modifier is setTxNonce(uint256)
 * on the Delay, with zero value and as a plain Call. The caller is any
 * module, not just the Governor.
 *
 * The scene is the Roles Modifier under RolesHarness with `target` linked to
 * DummyAvatar, and DelayTarget as the Delay.
 */

using SetTxNonceGuard as setTxNonceGuardContract;
using DelayTarget as delayMod;

methods {
    function memberOf(uint16, address) external returns (bool) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function optionsOf(uint16, address) external returns (RolesHarness.ExecutionOptions) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;
    function multisend() external returns (address) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;

    function setTxNonceGuardContract.delay() external returns (address) envfree;

    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
}

// The guard is installed and pinned to the Delay. Nothing else is assumed:
// in particular, nothing about roles[] storage.
function setTxNonceGuardInstalled(env e) {
    require guard() == setTxNonceGuardContract;
    require setTxNonceGuardContract.delay() == delayMod;
    require delayMod != currentContract;
    require target() != currentContract;
    require e.msg.value == 0;
}

/*
 * Every call that completes through execTransactionWithRole is setTxNonce on
 * the Delay, with zero value and as a plain Call.
 */
rule setTxNonceGuardLimitsExecTransactionWithRoleToDelaySetTxNonce(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    setTxNonceGuardInstalled(e);

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "a call that was not setTxNonce on the Delay completed with SetTxNonceGuard installed";
}

/*
 * The same through execTransactionFromModule.
 */
rule setTxNonceGuardLimitsExecTransactionFromModuleToDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    setTxNonceGuardInstalled(e);

    execTransactionFromModule@withrevert(e, to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "a non-setTxNonce call completed through the default-role entry point with SetTxNonceGuard installed";
}

/*
 * The same through execTransactionWithRoleReturnData.
 */
rule setTxNonceGuardLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    setTxNonceGuardInstalled(e);

    execTransactionWithRoleReturnData@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "a non-setTxNonce call completed through the ReturnData path with SetTxNonceGuard installed";
}

/*
 * The same through execTransactionFromModuleReturnData.
 */
rule setTxNonceGuardLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    setTxNonceGuardInstalled(e);

    execTransactionFromModuleReturnData@withrevert(e, to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "a non-setTxNonce call completed through the default-role ReturnData path with SetTxNonceGuard installed";
}

/*
 * The same under the worst-case configuration: the caller is an enabled
 * module and a member of the role it names, and that role has Target
 * clearance on `to` with both Send and DelegateCall.
 */
rule setTxNonceGuardLimitsToDelaySetTxNonceUnderMaximallyPermissiveRoles(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    setTxNonceGuardInstalled(e);

    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);
    require clearanceOf(role, to) == RolesHarness.Clearance.Target;
    require optionsOf(role, to) == RolesHarness.ExecutionOptions.Both;

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "blanket Target clearance with Both options got a non-setTxNonce call past SetTxNonceGuard";
}

/*
 * A transaction addressed to the multisend address always reverts. The role
 * configuration does not bound `to` on the multisend branch; the guard does,
 * because it sees the outer transaction.
 */
rule setTxNonceGuardRejectsMultisendTarget(
    uint256 value, bytes data, Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    setTxNonceGuardInstalled(e);

    require multisend() != delayMod;

    execTransactionWithRole@withrevert(e, multisend(), value, data, operation, role, shouldRevert);

    assert lastReverted,
        "a multisend batch went through with SetTxNonceGuard installed";
}

/*
 * With no guard and the same permissive configuration, a call to something
 * other than the Delay succeeds, so it is the guard that imposes the
 * restriction.
 */
rule withoutSetTxNonceGuardPermissiveRolesAllowNonDelayCall(
    address to, bytes data, uint16 role
) {
    env e;
    require guard() == 0;
    require target() != currentContract;
    require e.msg.value == 0;

    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);
    require clearanceOf(role, to) == RolesHarness.Clearance.Target;
    require optionsOf(role, to) == RolesHarness.ExecutionOptions.Both;
    require to != multisend();
    require data.length >= 4;

    // The thing the guard exists to stop.
    require to != delayMod;

    execTransactionWithRole(e, to, 0, data, Enum.Operation.Call, role, true);

    satisfy true, "even without SetTxNonceGuard this call cannot execute, so the SetTxNonceGuard rules prove nothing";
}
