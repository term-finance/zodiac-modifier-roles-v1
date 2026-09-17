/*
 * Property 2 — SetTxNonceGuard alone is sufficient.
 *
 * "The guard" in this file always means SetTxNonceGuard, installed on the
 * Roles module. PauseGuard, installed on the Delay, is not in this
 * scene and nothing here says anything about it.
 *
 * The role configuration is left completely unconstrained — no require
 * touches roles[] storage — so the Prover is free to pick the most permissive
 * configuration that exists, including one where every address holds
 * Clearance.Target with ExecutionOptions.Both and every caller is a member of
 * every role. The claim is that SetTxNonceGuard still admits nothing but
 * setTxNonce(uint256) on the Delay.
 *
 * This is the "we got the scoping wrong" story. It is the reason the guard is
 * worth deploying at all: Roles configuration is a large mutable surface
 * (scopeTarget, scopeAllowFunction, scopeParameter, assignRoles, and an owner
 * who can change any of them later), while the guard is an immutable address
 * check in code that no Roles-side mistake can widen.
 *
 * Note that the caller is NOT pinned to the Governor here. The rules quantify
 * over any msg.sender that clears the moduleOnly gate, so this bounds every
 * module on the modifier, present and future.
 *
 * Deliberately NOT claimed here:
 *   - That the guard survives its own removal. Roles.setGuard is onlyOwner;
 *     an owner that calls setGuard(0) is outside this model, and
 *     setTxNonceRoleConfigSufficient.spec is what covers that world.
 *   - That the guard constrains the 9/9 Safe's own signed transactions. It is
 *     installed on the Roles module, so it sees module transactions only.
 *
 * Modelling note. `target` is linked to DummyAvatar so the avatar never
 * reverts on its own account, leaving the guard as the only rejecter once
 * Permissions.check is satisfied. The IGuard hooks are resolved by
 * DISPATCHER, which lets withoutSetTxNonceGuardPermissiveRolesAllowNonDelayCall below flip guard() to 0 and
 * exhibit the same call succeeding.
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
 * THE property. No assumption whatsoever about the role configuration.
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
 * The fourth execution entry point: the default role AND execAndReturnData.
 * The guard sees the outer transaction on every one of the four, so the claim
 * does not weaken here — but the path is distinct code and is asserted
 * separately.
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
 * The same claim stated against a configuration that is explicitly the worst
 * case rather than merely unconstrained: the caller is an enabled module, a
 * member of the role it names, and that role holds blanket Target clearance
 * with both Send and DelegateCall permitted on whatever address it likes.
 *
 * Logically this is implied by setTxNonceGuardLimitsExecTransactionWithRoleToDelaySetTxNonce. It is written out
 * because it is the configuration a reader actually worries about, and
 * because if the general rule ever fails this one localises whether the cause
 * is the permissive branch or something else.
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
 * The multisend branch, which is the one place where the role layer alone
 * does not bound `to` at all: Permissions.check diverts to
 * checkMultisendTransaction whenever to == multisend, and that branch never
 * consults clearance for `to` itself (Permissions.sol:188-192). The guard
 * closes it, because the guard sees the OUTER transaction.
 *
 * setTxNonceRoleConfigSufficient.spec carries the counterpart showing this branch open
 * when the guard is absent.
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
 * The guard is what is doing the work, not some incidental property of the
 * scene. Same permissive configuration, same non-setTxNonce call, guard
 * removed: it succeeds.
 *
 * Without this witness every rule above is consistent with a scene in which
 * nothing at all can execute.
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
