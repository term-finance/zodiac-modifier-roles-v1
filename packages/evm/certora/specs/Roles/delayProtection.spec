/*
 * A target scoped to functions must reject an explicitly cleared selector
 * through every implemented Roles forwarding entrypoint. This is a policy
 * transition theorem for any role, target, payload, value and operation, not a deployment or
 * Safe/Delay correctness theorem. The special multisend target is excluded
 * because it parses and authorizes inner transactions instead; deployment
 * checks bind multisend separately.
 */
methods {
    unresolved external in _._ => DISPATCH [] default ASSERT_FALSE;
    function owner() external returns (address) envfree;
    function multisend() external returns (address) envfree;
    function selectorForData(bytes) external returns (bytes4) envfree;
    function delayVetoSelector() external returns (bytes4) envfree;
    function clearanceOf(uint16,address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForData(uint16,address,bytes) external returns (uint256) envfree;
}

rule revokedSelectorCannotBeForwarded(address to, bytes data, uint16 role, uint256 value, Enum.Operation operation, bool shouldRevert) {
    env admin;
    // Plain configuration calls restrict this transition to successful setup,
    // including the contract's owner and nonpayable checks.
    require to != multisend(), "Multisend parses inner transactions; deployment checks bind it to zero and Delay is nonzero";
    bytes4 deniedSelector = selectorForData(data);
    bytes4 vetoSelector = delayVetoSelector();
    require deniedSelector != vetoSelector, "The veto selector is intentionally permitted";

    scopeTarget(admin, role, to);
    scopeRevokeFunction(admin, role, to, deniedSelector);
    scopeAllowFunction(admin, role, to, vetoSelector, RolesHarness.ExecutionOptions.None);
    assert clearanceOf(role, to) == RolesHarness.Clearance.Function;
    assert functionScopeConfigForData(role, to, data) == 0;

    storage configured = lastStorage;
    env caller;
    callTargetFunctionWithRole@withrevert(caller, to, data, role);
    assert lastReverted, "cleared selector passed direct forwarding";

    execTransactionWithRole@withrevert(caller, to, value, data, operation, role, shouldRevert) at configured;
    assert lastReverted, "cleared selector passed Safe forwarding";

    execTransactionWithRoleReturnData@withrevert(caller, to, value, data, operation, role, shouldRevert) at configured;
    assert lastReverted, "cleared selector passed return-data forwarding";
}
