/*
 * Property 3 — the setTxNonce role configuration alone is sufficient:
 * SetTxNonceGuard is absent, and the scoping still admits nothing but
 * setTxNonce on the Delay.
 *
 * "The guard" in this file always means SetTxNonceGuard, installed on the
 * Roles module. PauseGuard, installed on the Delay, is not in this
 * scene and nothing here says anything about it.
 *
 * `guard() == 0` throughout, so Module.exec skips the IGuard hooks entirely
 * and Permissions.check is the only gate left. The configuration is the one
 * from the deployment runbook:
 *
 *     scopeTarget(1, delay)                                  -> Clearance.Function
 *     scopeAllowFunction(1, delay, 0x46ba2307, Options.None) -> setTxNonce only
 *     assignRoles(governor, [1], [true])                     -> member of role 1
 *
 * stated pointwise on each rule's own universally quantified `to`, `role` and
 * `data`, which is a faithful encoding of "nothing else was ever scoped,
 * allowed, or assigned".
 *
 * WHY THIS SPEC IS NARROWER THAN setTxNonceGuardSufficient.spec — the multisend branch.
 * Permissions.check dispatches on `to == multisend` BEFORE it looks at
 * clearance (Permissions.sol:188-192), and the batch branch never consults
 * clearance for `to` itself; it only checks the entries inside the blob. So
 * the role layer does not bound the OUTER destination or the OUTER operation
 * at all, and a caller can address the configured multisend and have the
 * module delegatecall into it. Every bounding rule below therefore has to
 * carry `to != multisend()` as a precondition, and
 * withoutSetTxNonceGuardMultisendTargetEscapesRoleConfig exhibits the gap. The guard has no such
 * precondition — it inspects the outer transaction — which is the concrete
 * sense in which the two mechanisms are not interchangeable.
 *
 * Deliberately NOT claimed here:
 *   - That the configuration stays this way. Every require below describes
 *     mutable storage that Roles' owner can change with a single call; that
 *     is the asymmetry with the immutable guard, not an oversight.
 *   - Anything about ExecutionOptions other than None on the scoped function.
 *     A future scopeFunctionExecutionOptions raising it to Send or Both would
 *     break the value == 0 and Operation.Call halves of the conclusion, and
 *     the rules would fail — correctly.
 *   - Multisend batches of two or more entries. roleConfigLimitsSingleEntry-
 *     MultisendToDelaySetTxNonce covers one entry and says so; the conf's
 *     loop_iter 1 with optimistic_loop is what bounds it.
 *   - Multisend blobs of at most 100 bytes. checkMultisendTransaction's loop
 *     starts at i = 100, so such a blob never enters it and check() returns
 *     having verified role membership only — no target, function or parameter
 *     scoping — while the outer transaction still fires at multisend(). Open
 *     in this scene; SetTxNonceGuard closes it.
 */

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
    function owner() external returns (address) envfree;
    function defaultRoles(address) external returns (uint16) envfree;

    // Mirrors checkMultisendTransaction's own per-entry parsing
    // (Permissions.sol:220-235) byte for byte; see the harness.
    function multisendEntryAt(bytes, uint256) external
        returns (Enum.Operation, address, uint256, uint256, bytes) envfree;
}

definition ROLE() returns uint16 = 1;

// The scoped function's ExecutionOptions, as checkExecutionOptions will read
// them. Options.None is what scopeAllowFunction was called with, and it is
// what forces value == 0 and Operation.Call.
function setTxNonceScopedWithNoOptions(bytes data) {
    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length =
        unpackFunctionOptions(functionScopeConfigForData(ROLE(), delayMod, data));
    require options == RolesHarness.ExecutionOptions.None;
}

function setTxNonceRoleConfigWithoutGuard(env e, address governor, address to, uint16 role, bytes data) {
    // The guard is gone. This is the whole point of the file.
    require guard() == 0;

    require delayMod != currentContract;
    require target() != currentContract;
    require delayMod != multisend();

    // scopeTarget(1, delay), and nothing else scoped or allowed.
    require clearanceOf(ROLE(), delayMod) == RolesHarness.Clearance.Function;
    require to != delayMod => clearanceOf(role, to) == RolesHarness.Clearance.None;

    // scopeAllowFunction(1, delay, setTxNonce, None), and nothing else.
    require selectorOf(data) != sig:DelayTarget.setTxNonce(uint256).selector
        => functionScopeConfigForData(role, delayMod, data) == 0;
    setTxNonceScopedWithNoOptions(data);

    // assignRoles(governor, [1], [true]).
    require moduleEntry(governor) != 0;
    require memberOf(ROLE(), governor);
    require role != ROLE() => !memberOf(role, governor);
    require defaultRoles(governor) == ROLE();
    require governor != owner();

    require e.msg.sender == governor;
    require e.msg.value == 0;
}

/*
 * THE property, outside the multisend branch.
 */
rule roleConfigLimitsExecTransactionWithRoleToDelaySetTxNonce(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, to, role, data);
    require to != multisend();

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the role configuration alone let a non-setTxNonce call through";
}

rule roleConfigLimitsExecTransactionFromModuleToDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, to, ROLE(), data);
    require to != multisend();

    execTransactionFromModule@withrevert(e, to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the role configuration alone let a non-setTxNonce call through the default-role entry point";
}

rule roleConfigLimitsExecTransactionWithRoleReturnDataToDelaySetTxNonce(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, to, role, data);
    require to != multisend();

    execTransactionWithRoleReturnData@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the role configuration alone let a non-setTxNonce call through the ReturnData path";
}

/*
 * The fourth execution entry point: the default role AND execAndReturnData.
 * Carries the same to != multisend() precondition as the three above, for the
 * same reason — Permissions.check dispatches on the batch branch before it
 * looks at clearance, on every entry point alike.
 */
rule roleConfigLimitsExecTransactionFromModuleReturnDataToDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, to, ROLE(), data);
    require to != multisend();

    execTransactionFromModuleReturnData@withrevert(e, to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the role configuration alone let a non-setTxNonce call through the default-role ReturnData path";
}

/*
 * A caller that is not a member of the role gets nothing, whatever it sends.
 * This is the half of the configuration that assignRoles carries, isolated
 * from the scoping half.
 */
rule nonMemberExecTransactionWithRoleAlwaysReverts(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    require guard() == 0;
    require target() != currentContract;
    require e.msg.value == 0;
    require !memberOf(role, e.msg.sender);

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert lastReverted,
        "a non-member executed through a role it does not belong to";
}

/*
 * The multisend branch, bounded — for a SINGLE-ENTRY batch.
 *
 * The four rules above exclude `to == multisend()` outright. This one goes
 * into that branch and shows the role layer still bounds what is in it: if a
 * one-entry batch completes, that entry is setTxNonce on the Delay, value 0,
 * Operation.Call. checkMultisendTransaction forwards every entry to the same
 * checkTransaction the non-multisend path uses (Permissions.sol:236), so the
 * scoping that pins the direct call pins the entry too.
 *
 * SCOPE, STATED RATHER THAN ASSUMED. The conf runs `loop_iter: 1` with
 * `optimistic_loop: true`: the entry loop is unrolled once and executions
 * needing more iterations are ASSUMED away rather than checked. Requiring the
 * batch to hold exactly one entry makes that scope explicit instead of hiding
 * behind the optimistic assumption — this rule says nothing whatsoever about
 * two-or-more-entry batches, and raising loop_iter is what would extend it.
 *
 *     data.length > 100         the loop is entered at all (i starts at 100)
 *     data.length <= 185 + len  it exits after one entry (i += 85 + dataLength)
 *
 * The first of those is not a formality. A blob of at most 100 bytes never
 * enters the loop body, so check() returns having verified role MEMBERSHIP
 * ONLY — no target, function or parameter scoping at all — and the outer
 * transaction still fires at multisend(). That is a real hole in this
 * guard-less scene, it is not closed by this rule, and it is listed with the
 * other non-claims in the file header. SetTxNonceGuard closes it, along with
 * the whole branch: see setTxNonceGuardRejectsMultisendTarget.
 */
rule roleConfigLimitsSingleEntryMultisendToDelaySetTxNonce(
    uint256 value, bytes data, Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    address governor;

    Enum.Operation innerOp;
    address innerTo;
    uint256 innerValue;
    uint256 innerDataLength;
    bytes innerData;
    innerOp, innerTo, innerValue, innerDataLength, innerData =
        multisendEntryAt(data, 100);

    // Exactly one entry.
    require to_mathint(data.length) > 100;
    require to_mathint(data.length) <= 185 + to_mathint(innerDataLength);
    require innerData.length >= 4;

    // The configuration is pinned pointwise on the INNER entry, because that
    // is what checkTransaction is handed in this branch — not on the outer
    // `to`, which is multisend() and which this branch never consults.
    setTxNonceRoleConfigWithoutGuard(e, governor, innerTo, role, innerData);
    require multisend() != delayMod;

    execTransactionWithRole@withrevert(
        e, multisend(), value, data, operation, role, shouldRevert
    );

    assert !lastReverted => (
        innerTo == delayMod &&
        innerValue == 0 &&
        innerOp == Enum.Operation.Call &&
        selectorOf(innerData) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "a single-entry multisend batch carried something other than setTxNonce on the Delay";
}

/*
 * The gap named in the file header, exhibited rather than asserted away: with
 * the guard absent, a transaction addressed to the configured multisend can
 * complete even though `to` is not the Delay. Permissions.check took the
 * batch branch and never asked what clearance `to` itself holds.
 *
 * Read this together with setTxNonceGuardSufficient.spec's setTxNonceGuardRejectsMultisendTarget:
 * the same call reverts once the guard is installed. That pair is the
 * argument for keeping the guard even though the role configuration is
 * correct.
 */
rule withoutSetTxNonceGuardMultisendTargetEscapesRoleConfig(bytes data, uint16 role) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, multisend(), role, data);

    require multisend() != delayMod;
    require multisend() != 0;

    execTransactionWithRole(e, multisend(), 0, data, Enum.Operation.DelegateCall, role, true);

    satisfy true, "the multisend branch is unreachable, so the caveat in this file's header overstates the gap";
}
