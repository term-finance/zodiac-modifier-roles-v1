/*
 * NOTE ON THE FUNCTION-SCOPE PINS BELOW.
 *
 * They go through functionScopeConfigForSelector (uint32 selector), not
 * functionScopeConfigForData (bytes blob). Same slot either way -- the bytes
 * form does bytes4(data) on entry -- but calling the bytes form inside a CVL
 * `require` makes every surrounding require stop binding, and all four
 * roleConfigLimits rules then report counterexamples in which to, value,
 * operation AND the selector are simultaneously unconstrained.
 *
 * That is not possible for a sound require: adding one can only remove states.
 * Confirmed by bisecting setTxNonceGuardAndRoleConfig.spec, whose preconditions
 * are a strict superset of setTxNonceGuardSufficient.spec's yet which failed
 * the same four conclusions until the bytes-form call was removed.
 *
 * Unlike that spec, the pins here are load-bearing -- no guard is installed, so
 * the options pin is what forces value == 0 and Operation.Call -- so they
 * cannot be dropped, only restated. Do not switch them back to the bytes form.
 */
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
 *     the rules would fail — correctly. optionsSendLetsValueThrough and its
 *     two siblings at the end of this file exhibit exactly that.
 *   - That the entry LOOP visits every entry of a batch of three or more.
 *     What an entry may BE is settled for any batch length, loop-free, by
 *     checkTransactionAdmitsOnlyDelaySetTxNonce: checkMultisendTransaction
 *     decides nothing itself, it hands each entry to checkTransaction, and
 *     that function admits only setTxNonce on the Delay. What loop_iter still
 *     bounds is the parse — that the stride lands on each successive entry —
 *     which roleConfigLimitsSingleEntry/TwoEntryMultisendToDelaySetTxNonce
 *     check for one and two entries. Raising loop_iter extends the parse check
 *     to longer bounded batches, never to arbitrary ones.
 *   - Multisend blobs of at most 100 bytes. checkMultisendTransaction's loop
 *     starts at i = 100, so such a blob never enters it and check() returns
 *     having verified role membership only — no target, function or parameter
 *     scoping — while the outer transaction still fires at multisend(). Open
 *     in this scene; SetTxNonceGuard closes it. shortMultisendBlobSkipsEvery-
 *     EntryCheck exhibits it, so the hole is machine-checked rather than only
 *     described here.
 */

using DelayTarget as delayMod;

methods {
    function memberOf(uint16, address) external returns (bool) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForSelector(uint16, address, uint32) external returns (uint256) envfree;
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

    // Permissions.checkTransaction itself, reached without going through
    // either the direct path or the multisend loop; see the harness.
    function checkEntry(uint16, address, uint256, bytes, Enum.Operation) external;
}

definition ROLE() returns uint16 = 1;

// The scoped function's ExecutionOptions, as checkExecutionOptions will read
// them. Options.None is what scopeAllowFunction was called with, and it is
// what forces value == 0 and Operation.Call.
function setTxNonceScopedWithNoOptions(bytes data) {
    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length =
        unpackFunctionOptions(
            functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data))
        );
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
        => functionScopeConfigForSelector(role, delayMod, selectorOf(data)) == 0;
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
 * SCOPE, STATED RATHER THAN ASSUMED. The conf runs `optimistic_loop: true`,
 * so executions needing more iterations than `loop_iter` are ASSUMED away
 * rather than checked. Requiring the batch to hold exactly one entry makes
 * this rule's scope explicit instead of hiding behind that assumption — this
 * rule on its own says nothing about longer batches. Two entries are covered
 * by roleConfigLimitsTwoEntryMultisendToDelaySetTxNonce; three or more are
 * not, and raising loop_iter is what would extend the pattern further.
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

/*
 * The multisend branch, bounded — for a TWO-ENTRY batch.
 *
 * Same argument as the single-entry rule: checkMultisendTransaction hands
 * every entry it visits to the same checkTransaction the direct path uses
 * (Permissions.sol:236), so the per-entry conclusion does not depend on how
 * many entries there are. What IS bounded is how many the Prover unrolls.
 * This rule exists so that the single-entry result cannot be mistaken for an
 * artefact of the one-entry shape, and so that a second iteration of the loop
 * is actually exercised rather than assumed away.
 *
 * Requires `loop_iter: 2` in the conf. The batch shape is pinned explicitly,
 * as it is in the single-entry rule:
 *
 *     i1 = 100                     first entry (the loop's starting index)
 *     i2 = 185 + dataLength1       second entry (i += 85 + dataLength)
 *     data.length > i2             the loop reaches the second entry
 *     data.length <= i2 + 85 + dataLength2    and stops after it
 *
 * This still says nothing about batches of three or more, and nothing about
 * blobs of at most 100 bytes, which never enter the loop at all — see
 * shortMultisendBlobSkipsEveryEntryCheck below.
 */
rule roleConfigLimitsTwoEntryMultisendToDelaySetTxNonce(
    uint256 value, bytes data, Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    address governor;

    Enum.Operation op1; address to1; uint256 value1; uint256 dataLength1; bytes data1;
    op1, to1, value1, dataLength1, data1 = multisendEntryAt(data, 100);

    uint256 i2 = require_uint256(185 + to_mathint(dataLength1));

    Enum.Operation op2; address to2; uint256 value2; uint256 dataLength2; bytes data2;
    op2, to2, value2, dataLength2, data2 = multisendEntryAt(data, i2);

    // Exactly two entries.
    require to_mathint(data.length) > to_mathint(i2);
    require to_mathint(data.length) <= to_mathint(i2) + 85 + to_mathint(dataLength2);
    require data1.length >= 4;
    require data2.length >= 4;

    // Pinned pointwise on BOTH inner entries, because both are what
    // checkTransaction is handed in this branch — never the outer `to`,
    // which is multisend() and which this branch does not consult.
    setTxNonceRoleConfigWithoutGuard(e, governor, to1, role, data1);
    setTxNonceRoleConfigWithoutGuard(e, governor, to2, role, data2);
    require multisend() != delayMod;

    execTransactionWithRole@withrevert(
        e, multisend(), value, data, operation, role, shouldRevert
    );

    assert !lastReverted => (
        to1 == delayMod &&
        value1 == 0 &&
        op1 == Enum.Operation.Call &&
        selectorOf(data1) == sig:DelayTarget.setTxNonce(uint256).selector &&
        to2 == delayMod &&
        value2 == 0 &&
        op2 == Enum.Operation.Call &&
        selectorOf(data2) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "a two-entry multisend batch carried something other than setTxNonce on the Delay";
}

/*
 * The 100-byte hole, exhibited rather than left as a comment.
 *
 * checkMultisendTransaction's entry loop starts at i = 100
 * (Permissions.sol:216), so a blob of at most 100 bytes never enters the body.
 * check() then returns having verified role MEMBERSHIP ONLY: no clearance for
 * the outer `to`, no per-entry check, and — because check() is not even passed
 * the outer value or operation on this branch (Permissions.sol:186-191) —
 * no constraint on either of those.
 *
 * This rule pins that shape down: the outer destination is multisend(), which
 * the configuration leaves at Clearance.None, the operation is DelegateCall,
 * and the value is symbolic. If it completes, none of those was checked by
 * anything.
 *
 * It is a witness. It does not bound the hole, it proves the hole is real, so
 * that the file header's caveat is machine-checked rather than asserted. It is
 * strictly sharper than withoutSetTxNonceGuardMultisendTargetEscapesRoleConfig,
 * which leaves data.length free and can therefore be satisfied by a
 * well-formed single setTxNonce entry instead of by the empty-loop case.
 *
 * Nothing in this file closes this. SetTxNonceGuard does, by rejecting
 * to != delay before any of it is reached — see
 * setTxNonceGuardSufficient.spec's setTxNonceGuardRejectsMultisendTarget.
 */
rule shortMultisendBlobSkipsEveryEntryCheck(bytes data, uint256 value, uint16 role) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, multisend(), role, data);

    require multisend() != delayMod;
    require multisend() != 0;

    // Below the loop's starting index (i starts at 100), so the loop body is
    // unreachable and no entry is ever parsed, let alone checked.
    require data.length <= 100;

    // Pin the witness rather than leaving it to the Prover's choice: a NON-ZERO
    // value rides along on a DELEGATECALL to an address the configuration
    // leaves at Clearance.None. If any of those three were actually gated,
    // this rule would have no model.
    require value != 0;

    execTransactionWithRole@withrevert(
        e, multisend(), value, data, Enum.Operation.DelegateCall, role, true
    );

    // Stated over @withrevert rather than leaning on path pruning, so the
    // obligation is visible in the rule: there EXISTS a completing execution
    // of exactly this shape.
    satisfy !lastReverted,
        "a multisend blob of at most 100 bytes cannot complete, so the 100-byte caveat in this file's header overstates the gap";
}

/*
 * THE PER-ENTRY RESTRICTION, WITHOUT ANY LOOP.
 *
 * This is the rule that makes batch length stop mattering.
 *
 * checkMultisendTransaction does not decide anything itself. It parses the
 * blob and hands each entry to checkTransaction (Permissions.sol:236) — the
 * same function the direct, non-multisend path calls (Permissions.sol:190).
 * So "what may an entry be?" is a question about checkTransaction alone, and
 * checkTransaction contains no loop over entries.
 *
 * This rule asks exactly that question, with `to`, `value`, `data` and
 * `operation` universally quantified and nothing driving the batch loop: if
 * checkTransaction accepts, the arguments were setTxNonce on the Delay, value
 * 0, Operation.Call. `to` ranges over every address, multisend() included —
 * a case the OUTER dispatch never reaches but the loop body can hand over.
 *
 * Composed with roleConfigLimitsSingleEntry/TwoEntryMultisendToDelaySetTxNonce,
 * which confirm the parse feeds checkTransaction the entry's real fields, this
 * gives: every entry the loop visits is setTxNonce on the Delay, FOR ANY
 * NUMBER OF ENTRIES. loop_iter then bounds only how many entries the Prover
 * walks, not what is true of the ones it walks.
 *
 * ON isWildcarded. checkTransaction's one loop is checkParameters
 * (Permissions.sol:312), reached only when isWildcarded is false. The runbook
 * configures the scoped function wildcarded, and pinning that here is what
 * keeps this rule free of every loop. The conclusion does not depend on it:
 * parameter scoping can only narrow what is admitted, never widen it. The pin
 * buys loop-freedom, not strength.
 *
 * WHAT THIS STILL DOES NOT COVER. It says what an entry may be, not which
 * entries get checked. A blob of at most 100 bytes has no entry checked at all
 * (shortMultisendBlobSkipsEveryEntryCheck), and it says nothing about the
 * OUTER value or operation, which Permissions.check is not passed on this
 * branch (Permissions.sol:186-191) and which no configuration can restrict.
 */
rule checkTransactionAdmitsOnlyDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;

    // scopeTarget(1, delay), and nothing else scoped or allowed.
    require clearanceOf(ROLE(), delayMod) == RolesHarness.Clearance.Function;
    require to != delayMod => clearanceOf(ROLE(), to) == RolesHarness.Clearance.None;

    // scopeAllowFunction(1, delay, setTxNonce, None), and nothing else.
    require selectorOf(data) != sig:DelayTarget.setTxNonce(uint256).selector
        => functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data)) == 0;

    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length =
        unpackFunctionOptions(
            functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data))
        );
    require options == RolesHarness.ExecutionOptions.None;
    // Keeps checkParameters, the only loop reachable from here, off the path.
    require isWildcarded;

    checkEntry@withrevert(e, ROLE(), to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "checkTransaction admitted an entry other than setTxNonce on the Delay";
}

/*
 * Non-vacuity for the rule above: checkTransaction really does accept the
 * intended entry, so the restriction is not achieved by it rejecting
 * everything.
 */
rule checkTransactionStillAdmitsDelaySetTxNonce(bytes data) {
    env e;

    require clearanceOf(ROLE(), delayMod) == RolesHarness.Clearance.Function;
    require selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector;
    require data.length == 36;

    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length =
        unpackFunctionOptions(
            functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data))
        );
    require options == RolesHarness.ExecutionOptions.None;
    require isWildcarded;
    require functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data)) != 0;

    checkEntry(e, ROLE(), delayMod, 0, data, Enum.Operation.Call);

    satisfy true, "checkTransaction rejects even the intended setTxNonce entry";
}

/*
 * THE EXCEPTION THAT IS NOT EMPTY, AND THE REASON THE GUARD IS LOAD-BEARING.
 *
 * The 100-byte hole lets a caller past the permission check but carries no
 * payload: 32 bytes cannot hold an 85-byte entry header, and MultiSendCallOnly
 * executes nothing (Property 7). On its own that is a bypass to do nothing.
 *
 * The OUTER VALUE is a different matter, and it is not empty.
 *
 * Permissions.check is handed `value` but does not forward it on the multisend
 * branch (Permissions.sol:186-191): checkMultisendTransaction takes `data`
 * alone. So no configuration constrains the outer value. Roles then runs
 * exec(multisend(), value, data, operation) with it intact.
 *
 * With Operation.Call that value is real money. The avatar's Executor passes
 * it straight to the `call` (safe-contracts Executor.sol; delegatecall takes no
 * value argument, which is why the DelegateCall witness above does not move
 * any), and MultiSendCallOnly.multiSend is `payable` and has no withdrawal
 * function of any kind. ETH sent there is gone.
 *
 * So the role configuration alone does NOT confine the Governor to
 * setTxNonce: it cannot stop ETH leaving the contract at `target` -- the
 * DelayOwnerSafe in the deployment -- whose own balance is what Module.exec
 * spends, and which therefore bounds the loss. SetTxNonceGuard does,
 * because it inspects the outer transaction and requires both
 * `to == delay` and `value == 0` (SetTxNonceGuard.checkTransaction).
 *
 * This rule exhibits the permission half: Roles lets such a transaction out.
 * What the avatar then does with it is the source fact above -- the Roles
 * scenes link `target` to DummyAvatar, which returns true and moves nothing.
 */
rule roleConfigDoesNotStopValueLeavingOnMultisendBranch(
    bytes data, uint256 value, uint16 role
) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, multisend(), role, data);

    require multisend() != delayMod;
    require multisend() != 0;

    // A plain Call, so the avatar's Executor forwards the value, and a
    // non-zero one, so there is something to forward.
    require value != 0;

    execTransactionWithRole@withrevert(
        e, multisend(), value, data, Enum.Operation.Call, role, true
    );

    satisfy !lastReverted,
        "the role configuration does constrain the outer value on the multisend branch, so the guard is redundant after all";
}

/*
 * WHY THE OPTIONS PIN IS LOAD-BEARING: RAISING IT BREAKS THE RESTRICTION.
 *
 * Every bounding rule above pins the scoped function's ExecutionOptions to
 * None, and the header lists "ExecutionOptions other than None" as not
 * claimed. These witnesses turn that into a checked statement rather than an
 * asserted one: with the guard absent and the same runbook configuration
 * except for the options, a call outside the restriction completes on the
 * direct path, exactly as checkExecutionOptions (Permissions.sol:284-306)
 * says it should.
 *
 *   Send          -> a non-zero value reaches setTxNonce on the Delay
 *   DelegateCall  -> Operation.DelegateCall reaches setTxNonce on the Delay
 *   Both          -> both at once
 *
 * So the value == 0 and Operation.Call halves of the restriction rest on the
 * options staying None, and nothing else in the configuration supplies them.
 * With SetTxNonceGuard installed this does not arise: Property 2 leaves the
 * configuration, options included, entirely unconstrained.
 *
 * `to` is the Delay, never multisend(), so this is the direct path and not the
 * multisend branch, which ignores the outer value and operation regardless
 * (roleConfigDoesNotStopValueLeavingOnMultisendBranch). isWildcarded keeps
 * checkParameters, the only loop on the path, out of it.
 */
function setTxNonceRoleConfigWithOptions(
    env e, address governor, bytes data, RolesHarness.ExecutionOptions raised
) {
    require guard() == 0;
    require delayMod != currentContract;
    require target() != currentContract;
    require delayMod != multisend();

    // scopeTarget(1, delay) and scopeAllowFunction(1, delay, setTxNonce, raised).
    require clearanceOf(ROLE(), delayMod) == RolesHarness.Clearance.Function;
    require selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector;
    require data.length == 36;
    require functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data)) != 0;

    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length =
        unpackFunctionOptions(
            functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data))
        );
    require options == raised;
    require isWildcarded;

    // assignRoles(governor, [1], [true]).
    require moduleEntry(governor) != 0;
    require memberOf(ROLE(), governor);
    require governor != owner();

    require e.msg.sender == governor;
    require e.msg.value == 0;
}

rule optionsSendLetsValueThrough(bytes data, uint256 value) {
    env e;
    address governor;
    setTxNonceRoleConfigWithOptions(e, governor, data, RolesHarness.ExecutionOptions.Send);
    require value != 0;

    execTransactionWithRole@withrevert(
        e, delayMod, value, data, Enum.Operation.Call, ROLE(), true
    );

    satisfy !lastReverted,
        "with options Send a valued setTxNonce still cannot complete, so the value == 0 half does not rest on the options pin";
}

rule optionsDelegateCallLetsDelegateCallThrough(bytes data) {
    env e;
    address governor;
    setTxNonceRoleConfigWithOptions(e, governor, data, RolesHarness.ExecutionOptions.DelegateCall);

    execTransactionWithRole@withrevert(
        e, delayMod, 0, data, Enum.Operation.DelegateCall, ROLE(), true
    );

    satisfy !lastReverted,
        "with options DelegateCall a delegatecall setTxNonce still cannot complete, so the Operation.Call half does not rest on the options pin";
}

rule optionsBothLetsValueAndDelegateCallThrough(bytes data, uint256 value) {
    env e;
    address governor;
    setTxNonceRoleConfigWithOptions(e, governor, data, RolesHarness.ExecutionOptions.Both);
    require value != 0;

    execTransactionWithRole@withrevert(
        e, delayMod, value, data, Enum.Operation.DelegateCall, ROLE(), true
    );

    satisfy !lastReverted,
        "with options Both a valued delegatecall setTxNonce still cannot complete, so neither half rests on the options pin";
}
