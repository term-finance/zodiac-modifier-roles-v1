/*
 * Recovery from the contained state, back to a single allowed function on a
 * single target.
 *
 * Starting state: target revoked, module disabled, role revoked.
 *
 * The three containment setters each write a narrow slice of storage:
 * revokeTarget assigns TargetAddress(Clearance.None, ExecutionOptions.None)
 * (Permissions.sol:417-427), the role revocation writes
 * roles[r].members[module] (Roles.sol:288-290), and disabling the module
 * writes the module linked list. None of them touch role.functions, so the
 * scopeAllowFunction entry written before containment is still in storage.
 * That is why no scopeAllowFunction call appears below: returning clearance
 * to Function is on its own enough to re-arm the surviving entry. The same
 * fact means any OTHER function ever scoped on y for this role is re-armed at
 * the same instant, since scopeRevokeFunction is the only setter that clears
 * one — which is what the scopeConfig == 0 branch of the assertion below is
 * quantifying over.
 *
 * Only the target half of the recovery is invoked as a real call, because
 * only it acts on the permission surface. The caller half (assignRoles, which
 * also re-enables the module, Roles.sol:290-292) is stated as a precondition
 * on the post-recovery state instead: CVL cannot construct the calldata
 * arrays assignRoles takes, and the moduleOnly and membership gates it
 * restores are covered in access.spec and are not reachable from clearance or
 * from role.functions.
 *
 * Why clearance is the whole story for the original widening: allowTarget
 * overwrites the TargetAddress struct with Clearance.Target
 * (Permissions.sol:403-411), and checkTransaction's Target branch
 * short-circuits to checkExecutionOptions and returns
 * (Permissions.sol:263-266) without reading role.functions at all. The
 * function entry is inert at Target clearance and live at Function clearance.
 *
 * Shape note: both halves of the claim are stated over ONE payload, whose
 * scope config is read once. Two payloads (one allowed, one not) is the
 * obvious phrasing and does not work — the prover cannot keep two
 * bytes-derived keys of role.functions apart, and any rule reading the
 * mapping through two different `bytes` values comes out vacuous even though
 * keyForFunctions makes the keys plainly distinct. Quantifying over a single
 * `data` is also strictly stronger: it covers every selector rather than one
 * allowed and one rejected instance.
 */

methods {
    function moduleEntry(address) external returns (address) envfree;
    function memberOf(uint16, address) external returns (bool) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForData(uint16, address, bytes) external returns (uint256) envfree;
    function unpackFunctionOptions(uint256) external returns (RolesHarness.ExecutionOptions, bool, uint256) envfree;
    function multisend() external returns (address) envfree;
}

// Both halves of the recovery, over an arbitrary payload:
//
//   safety   — a selector with no surviving entry is rejected;
//   liveness — a selector whose surviving entry is live goes through.
//
// scopeConfig is read in the contained state, before scopeTarget runs;
// scopeTarget writes role.targets only, so it still describes storage at the
// point of the call.
//
// The liveness half is conditioned on isWildcarded because that is what
// packLeft(0, opts, true, 0) writes (Permissions.sol:451-476), pinning it to
// an entry scopeAllowFunction actually produced. It also means checkParameters
// is skipped, so no parameter revert is reachable on that branch. The
// remaining case — a nonzero entry that is NOT wildcarded, i.e. one written by
// scopeFunction — is deliberately left unasserted: whether it reverts depends
// on the parameter comparison, which is params.spec's subject.
rule recoveredConfigConfinesToScopedFunction(
    uint16 role,
    address y,
    bytes data
) {
    env eOwner;
    env eModule;

    require y != multisend();

    // Contained starting state, target half.
    require clearanceOf(role, y) == RolesHarness.Clearance.None;

    // Whatever containment left behind for this selector.
    uint256 scopeConfig = functionScopeConfigForData(role, y, data);
    RolesHarness.ExecutionOptions entryOptions;
    bool isWildcarded;
    uint256 length;
    entryOptions, isWildcarded, length = unpackFunctionOptions(scopeConfig);

    // The fix.
    scopeTarget(eOwner, role, y);

    // Caller half of the recovery: module re-enabled, role re-assigned.
    require moduleEntry(eModule.msg.sender) != 0;
    require memberOf(role, eModule.msg.sender);
    require eModule.msg.value == 0;
    require data.length >= 4;

    callTargetFunctionWithRole@withrevert(eModule, y, data, role);

    assert scopeConfig == 0 => lastReverted,
        "a function with no scope config was permitted after recovery";

    assert (scopeConfig != 0 && isWildcarded) => !lastReverted,
        "a surviving wildcarded entry did not restore access after recovery";
}
