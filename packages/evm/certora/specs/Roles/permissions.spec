/*
 * Permission-enforcement (clearance / function-allowlist) properties of
 * callTargetFunctionWithRole, plus the authorization-equivalence rule
 * anchoring it to the audited execTransactionWithRole path.
 *
 * All rules here restrict to `to != multisend()` via a precondition, which
 * collapses the unbounded multisend-unwrapping loop for free (see
 * multisend.spec for the multisend branch itself). checkExecutionOptions is
 * proven dead code on this path because value is hardcoded 0 and operation
 * is hardcoded Call — see the comment above the headline rule below for why
 * that needs no dedicated rule of its own.
 */

methods {
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForData(uint16, address, bytes) external returns (uint256) envfree;
    function multisend() external returns (address) envfree;
    function guard() external returns (address) envfree;
}

rule successImpliesTargetCleared(address to, bytes data, uint16 role) {
    env e;
    require to != multisend();

    callTargetFunctionWithRole(e, to, data, role);

    assert clearanceOf(role, to) != RolesHarness.Clearance.None,
        "callTargetFunctionWithRole succeeded against a target with no clearance";
}

rule successImpliesFunctionAllowed(address to, bytes data, uint16 role) {
    env e;
    require to != multisend();
    require clearanceOf(role, to) == RolesHarness.Clearance.Function;
    require data.length >= 4;

    uint256 scopeConfigBefore = functionScopeConfigForData(role, to, data);

    callTargetFunctionWithRole(e, to, data, role);

    assert scopeConfigBefore != 0,
        "callTargetFunctionWithRole succeeded on a Function-cleared target with no matching function allowlisted";
}

rule shortCalldataReverts(address to, bytes data, uint16 role) {
    env e;
    require data.length > 0 && data.length < 4;

    callTargetFunctionWithRole@withrevert(e, to, data, role);

    assert lastReverted,
        "callTargetFunctionWithRole did not revert on calldata shorter than a selector";
}

// checkExecutionOptions gates on `value > 0` (Send) or `operation ==
// DelegateCall`. callTargetFunctionWithRole hardcodes value 0 and
// Enum.Operation.Call, so both revert branches of checkExecutionOptions are
// unreachable here regardless of the configured ExecutionOptions.
//
// This does not need its own comparison rule: `clearedTargetNeverReverts`
// and `wildcardedFunctionNeverReverts` (access.spec, group E) already assert
// "no revert" while leaving `optionsOf(role, to)` completely unconstrained.
// Since the prover quantifies over every storage state satisfying a rule's
// requires, an unconstrained variable that a passing assertion never
// depends on is, by construction, proven irrelevant to the outcome — a
// second rule fixing two option values and diffing the results would prove
// nothing those two do not already establish. The one case neither of those
// rules covers — Function clearance, not wildcarded, i.e. checkParameters
// actually runs — needs no proof either: `options` is local to
// checkExecutionOptions and is never passed into checkParameters
// (Permissions.sol:277-284), so it cannot influence that branch's
// revert-ness by construction.

// The headline rule: with value pinned to 0 and operation pinned to Call,
// callTargetFunctionWithRole must revert on the permission check exactly
// when execTransactionWithRole's identical Permissions.check call would.
// This anchors the fast path's authorization strength to the audited one.
//
// Two revert sources on the exec side are unrelated to permissions and must
// be scoped out, or they surface as fake divergences:
//
//  1. `target` is linked to DummyAvatar in the conf. Module.exec makes a
//     high-level `IAvatar(target).execTransactionFromModule(...)` call
//     returning bool, so solc emits an `extcodesize(target) > 0` guard
//     before dispatch. With `target` left as an arbitrary codeless address
//     that guard reverts — while callTargetFunctionWithRole's raw assembly
//     `call` has no such check and succeeds against a codeless address.
//     That is a pure artifact of high-level-call codegen, not a difference
//     in authorization. Note a NONDET summary does NOT fix this: the
//     extcodesize guard lives in the caller's own bytecode, ahead of the
//     dispatch the summary would replace.
//  2. `guard == 0` is required, skipping Module.exec's IGuard hooks. Those
//     carry the identical extcodesize problem, and the fact that the raw
//     path never invokes a configured guard at all is a separate property
//     (characterized in execution.spec), not part of this rule's claim.
//
// What remains after both: moduleOnly and Permissions.check are the only
// revert sources on either side, which is exactly the comparison intended.
rule permissionCheckMatchesExecTransactionWithRole(address to, bytes data, uint16 role) {
    env e;
    require e.msg.value == 0;
    require guard() == 0;

    storage initState = lastStorage;

    callTargetFunctionWithRole@withrevert(e, to, data, role);
    bool directReverted = lastReverted;

    execTransactionWithRole@withrevert(e, to, 0, data, Enum.Operation.Call, role, false) at initState;
    bool viaExecReverted = lastReverted;

    assert directReverted == viaExecReverted,
        "callTargetFunctionWithRole and execTransactionWithRole diverge on an identical permission check";
}
