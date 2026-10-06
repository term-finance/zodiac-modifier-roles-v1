/*
 * The setTxNonce role configuration alone, with no SetTxNonceGuard: outside
 * the multisend branch, every call that completes through the Roles Modifier
 * is setTxNonce(uint256) on the Delay, with zero value and as a plain Call.
 * On the multisend branch the configuration bounds each entry of a batch, but
 * not the outer destination, value or operation.
 *
 * The configuration is role 1's: Function clearance on the Delay, setTxNonce
 * allowed with ExecutionOptions None, and the Governor a member of role 1,
 * stated pointwise on each rule's `to`, `role` and `data`. The scene is the
 * Roles Modifier under RolesHarness with `target` linked to DummyAvatar, and
 * DelayTarget as the Delay.
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

    // Parses one multisend entry the way checkMultisendTransaction does.
    function multisendEntryAt(bytes, uint256) external
        returns (Enum.Operation, address, uint256, uint256, bytes) envfree;

    // Permissions.checkTransaction, called directly.
    function checkEntry(uint16, address, uint256, bytes, Enum.Operation) external;
}

definition ROLE() returns uint16 = 1;

// The scoped function's ExecutionOptions are None, which forces value == 0
// and Operation.Call.
function setTxNonceScopedWithNoOptions(bytes data) {
    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length =
        unpackFunctionOptions(
            functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data))
        );
    require options == RolesHarness.ExecutionOptions.None;
}

function setTxNonceRoleConfigWithoutGuard(env e, address governor, address to, uint16 role, bytes data) {
    // No SetTxNonceGuard.
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
 * Outside the multisend branch, every call that completes through
 * execTransactionWithRole is setTxNonce on the Delay, with zero value and as
 * a plain Call.
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

/*
 * The same through execTransactionFromModule.
 */
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

/*
 * The same through execTransactionWithRoleReturnData.
 */
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
 * The same through execTransactionFromModuleReturnData.
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
 * A caller that is not a member of the role it names can execute nothing
 * through execTransactionWithRole.
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
 * On the multisend branch, for a single-entry batch: if the batch completes,
 * its entry is setTxNonce on the Delay, with zero value and as a plain Call.
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

    // The configuration is pinned on the inner entry, which is what
    // checkTransaction is handed on this branch.
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
 * Without the guard, a transaction addressed to the multisend address can
 * complete although it is not the Delay.
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
 * The same for a two-entry batch: if it completes, both entries are
 * setTxNonce on the Delay, with zero value and as a plain Call.
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

    // The configuration is pinned on both inner entries.
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
 * A multisend blob of at most 100 bytes never enters
 * checkMultisendTransaction's entry loop, so a DelegateCall with non-zero
 * value to the multisend address, which has no clearance, can complete.
 */
rule shortMultisendBlobSkipsEveryEntryCheck(bytes data, uint256 value, uint16 role) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, multisend(), role, data);

    require multisend() != delayMod;
    require multisend() != 0;

    // Below the entry loop's starting index of 100.
    require data.length <= 100;

    require value != 0;

    execTransactionWithRole@withrevert(
        e, multisend(), value, data, Enum.Operation.DelegateCall, role, true
    );

    satisfy !lastReverted,
        "a multisend blob of at most 100 bytes cannot complete, so the 100-byte caveat in this file's header overstates the gap";
}

/*
 * If checkTransaction accepts an entry, the entry is setTxNonce on the Delay,
 * with zero value and as a plain Call, for any `to`, multisend included.
 * checkMultisendTransaction hands each entry of a batch to checkTransaction,
 * so this holds for every entry of a batch of any length.
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
 * checkTransaction accepts the intended setTxNonce entry, so the rule above
 * is not vacuous.
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
 * On the multisend branch the role configuration does not constrain the outer
 * value: a Call with non-zero value to the multisend address can complete.
 */
rule roleConfigDoesNotStopValueLeavingOnMultisendBranch(
    bytes data, uint256 value, uint16 role
) {
    env e;
    address governor;
    setTxNonceRoleConfigWithoutGuard(e, governor, multisend(), role, data);

    require multisend() != delayMod;
    require multisend() != 0;

    require value != 0;

    execTransactionWithRole@withrevert(
        e, multisend(), value, data, Enum.Operation.Call, role, true
    );

    satisfy !lastReverted,
        "the role configuration does constrain the outer value on the multisend branch, so the guard is redundant after all";
}

/*
 * With no guard, and role 1's configuration except that the scoped function's
 * ExecutionOptions are raised, a call outside the restriction completes:
 *   Send          a non-zero value reaches setTxNonce on the Delay
 *   DelegateCall  Operation.DelegateCall reaches setTxNonce on the Delay
 *   Both          both at once
 * So the value == 0 and Operation.Call halves rest on the options being None.
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
