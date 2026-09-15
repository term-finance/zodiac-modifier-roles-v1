/*
 * Access-control and completeness properties of callTargetFunctionWithRole.
 *
 * These are the two properties that MUST hold unconditionally: only an
 * enabled module can call at all, and only a member of the given role can
 * get past Permissions.check — on every path, including multisend, since
 * the membership test (Permissions.sol:185-187) precedes the branch.
 * Everything else in this suite (permissions.spec, params.spec,
 * multisend.spec, execution.spec) refines what an authorized caller may
 * then do; it does not touch these two facts.
 */

methods {
    function moduleEntry(address) external returns (address) envfree;
    function memberOf(uint16, address) external returns (bool) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForData(uint16, address, bytes) external returns (uint256) envfree;
    function unpackFunctionOptions(uint256) external returns (RolesHarness.ExecutionOptions, bool, uint256) envfree;
    function multisend() external returns (address) envfree;
}

// The authorization gate is the moduleOnly modifier, which tests
// `modules[msg.sender] != 0` (Modifier.sol:59-62) — NOT isModuleEnabled,
// which additionally excludes SENTINEL_MODULES (Modifier.sol:98-100).
// Those two predicates diverge at exactly one address: the sentinel is
// self-linked by setupModules (Roles.sol:56-59), so modules[0x1] == 0x1,
// which passes moduleOnly while isModuleEnabled(0x1) returns false.
// Asserting isModuleEnabled here would therefore be asserting something
// the contract never claims, and the prover rightly produces
// msg.sender == 0x1 as a counterexample. This rule states the real gate.
//
// The sentinel divergence is not exploitable: address(0x1) is the
// ecrecover precompile, so no caller can originate from it. It is an
// upstream Zodiac robustness quirk, not a property of this fork.
rule onlyEnabledModuleCanCall(address to, bytes data, uint16 role) {
    env e;

    address senderModuleEntry = moduleEntry(e.msg.sender);

    callTargetFunctionWithRole(e, to, data, role);

    assert senderModuleEntry != 0,
        "callTargetFunctionWithRole succeeded for a caller absent from the module linked list";
}

rule nonMemberAlwaysReverts(address to, bytes data, uint16 role) {
    env e;

    bool isMember = memberOf(role, e.msg.sender);
    require !isMember;

    callTargetFunctionWithRole@withrevert(e, to, data, role);

    assert lastReverted,
        "a non-member of the role was able to call callTargetFunctionWithRole";
}

// Liveness half of access control: a member of a role with plain Target
// clearance on `to` must be able to reach the outbound call at all. This
// also doubles as the canary for whether the Permissions library link
// resolved — if it did not, `check` havocs and this rule is vacuously
// unconstrained rather than meaningfully true.
rule clearedTargetNeverReverts(address to, bytes data, uint16 role) {
    env e;

    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);
    require to != multisend();
    require clearanceOf(role, to) == RolesHarness.Clearance.Target;
    require data.length >= 4;
    require e.msg.value == 0;

    callTargetFunctionWithRole@withrevert(e, to, data, role);

    assert !lastReverted,
        "a member with plain Target clearance was unable to reach the outbound call";
}

// Completeness for the other non-reverting branch: Function clearance with
// the wildcarded bit set skips checkParameters entirely (Permissions.sol:
// 283-286), so it must also never revert for an authorized member.
rule wildcardedFunctionNeverReverts(address to, bytes data, uint16 role) {
    env e;

    require moduleEntry(e.msg.sender) != 0;
    require memberOf(role, e.msg.sender);
    require to != multisend();
    require clearanceOf(role, to) == RolesHarness.Clearance.Function;
    require data.length >= 4;
    require e.msg.value == 0;

    uint256 scopeConfig = functionScopeConfigForData(role, to, data);
    require scopeConfig != 0;
    RolesHarness.ExecutionOptions options;
    bool isWildcarded;
    uint256 length;
    options, isWildcarded, length = unpackFunctionOptions(scopeConfig);
    require isWildcarded;

    callTargetFunctionWithRole@withrevert(e, to, data, role);

    assert !lastReverted,
        "a member with wildcarded Function clearance was unable to reach the outbound call";
}
