/*
 * GnosisSafe v1.3.0 (solc 0.7.6): who can make the Safe act or change it.
 * No assumption about modules or a fallback handler.
 *
 * "Act" = an outgoing CALL or DELEGATECALL.
 *
 * Assumes the Safe is set up (threshold > 0). No rule depends on the
 * threshold or the number of owners, and no rule runs the signature loop.
 */

methods {
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function guardAddress() external returns (address) envfree;
    function fallbackHandlerSlotWord() external returns (uint256) envfree;
    function fallbackHandlerAddress() external returns (address) envfree;
    function approvedHashes(address, bytes32) external returns (uint256) envfree;

    function nonce() external returns (uint256) envfree;
    function signatureTypeAt(bytes, uint256) external returns (uint8) envfree;

    // Stand-in for the signature loop: it records that it ran, on which hash
    // and for how many signatures, and returns. checkSignatures itself runs
    // for real, so its "threshold > 0" check (GS001) is kept. execTransaction
    // reads the owners nowhere else (GnosisSafe.sol:111-194). The loop is
    // covered one pass at a time by eachSignatureAcceptsANewApprovingOwner.
    // The other rules here leave execTransaction out, or only check which
    // function was called.
    function checkNSignatures(bytes32 dataHash, bytes memory data, bytes memory signatures, uint256 requiredSignatures) internal
        => recordSignatureCheck(dataHash, requiredSignatures);
}

/// Head of the Safe's owner and module lists.
definition SENTINEL() returns address = 0x1;

definition isExecTransaction(method f) returns bool =
    f.selector == sig:execTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes
    ).selector;

definition isModuleExec(method f) returns bool =
    f.selector == sig:execTransactionFromModule(address, uint256, bytes, Enum.Operation).selector ||
    f.selector == sig:execTransactionFromModuleReturnData(address, uint256, bytes, Enum.Operation).selector;

/// The three ways the Safe can make an outgoing call.
definition isActPath(method f) returns bool =
    isExecTransaction(f) || isModuleExec(f) || f.isFallback;

definition isSelfOnlySetting(method f) returns bool =
    f.selector == sig:enableModule(address).selector ||
    f.selector == sig:disableModule(address, address).selector ||
    f.selector == sig:addOwnerWithThreshold(address, uint256).selector ||
    f.selector == sig:removeOwner(address, address, uint256).selector ||
    f.selector == sig:swapOwner(address, address, address).selector ||
    f.selector == sig:changeThreshold(uint256).selector ||
    f.selector == sig:setGuard(address).selector ||
    f.selector == sig:setFallbackHandler(address).selector;

definition isAlwaysClosed(method f) returns bool =
    f.selector == sig:setup(address[], uint256, address, bytes, address, address, uint256, address).selector ||
    f.selector == sig:requiredTxGas(address, uint256, bytes, Enum.Operation).selector ||
    f.selector == sig:simulateAndRevert(address, bytes).selector;

definition isApproveHash(method f) returns bool =
    f.selector == sig:approveHash(bytes32).selector;

ghost bool safeActed;

/*
 * These three record what already happened in this call. They are persistent
 * so a DELEGATECALL to unknown code does not havoc them: that code runs after
 * the check and cannot undo it. The Safe's storage is still havoced.
 */

/// Set if the Safe made an outgoing call before the signature check ran.
persistent ghost bool actedBeforeSignatureCheck;

persistent ghost bool signatureCheckRan;
persistent ghost bytes32 signatureCheckHash;
persistent ghost uint256 signatureCheckRequired;

/*
 * What the Safe's outgoing calls looked like, for the two fallback rules.
 * `expectedCallee` is set by the rule; the hooks flag any call that differs.
 */
persistent ghost mathint expectedCallee;
persistent ghost bool calledSomeoneElse;
persistent ghost bool calledWithValue;
persistent ghost bool madeDelegateCall;

function recordSignatureCheck(bytes32 dataHash, uint256 requiredSignatures) {
    signatureCheckRan = true;
    signatureCheckHash = dataHash;
    signatureCheckRequired = requiredSignatures;
}

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    safeActed = true;
    if (!signatureCheckRan) {
        actedBeforeSignatureCheck = true;
    }
    // The hook sees CALL's raw 256-bit address word; the EVM calls only its
    // low 160 bits. fallback() passes its whole slot word, which may carry
    // upper bits, so compare the address actually called.
    if (to_mathint(addr) % 2^160 != expectedCallee) {
        calledSomeoneElse = true;
    }
    if (value != 0) {
        calledWithValue = true;
    }
}

hook DELEGATECALL(uint g, address addr, uint argsOffset, uint argsLength,
                  uint retOffset, uint retLength) uint rc {
    safeActed = true;
    if (!signatureCheckRan) {
        actedBeforeSignatureCheck = true;
    }
    madeDelegateCall = true;
}

/*
 * Every write function is one of the sixteen above (fallback covers every
 * other selector). @withrevert keeps the always-reverting ones reachable.
 */
rule safeEntryPointsAreAllAccountedFor(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;

    f@withrevert(e, args);

    assert isActPath(f) || isSelfOnlySetting(f) || isApproveHash(f) || isAlwaysClosed(f),
        "the Safe has a write function that no rule covers";
}

/*
 * Apart from execTransaction, the Safe only acts through an enabled module or
 * a set fallback handler. The handler is checked as the raw slot word, as
 * fallback() does (`if iszero(handler)`).
 */
rule safeActsOnlyThroughItsThreeEntryPaths(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isExecTransaction(f) }
{
    env e;
    require thresholdValue() > 0;
    bool senderWasModule = e.msg.sender != SENTINEL() && moduleEntry(e.msg.sender) != 0;
    bool handlerWasSet = fallbackHandlerSlotWord() != 0;
    require !safeActed;

    f@withrevert(e, args);

    assert (!lastReverted && safeActed) =>
        ((isModuleExec(f) && senderWasModule) || (f.isFallback && handlerWasSet)),
        "the Safe acted through something other than execTransaction, an enabled module, or a set fallback handler";
}

/*
 * With a handler set, fallback() only ever makes a plain call, with no ETH,
 * to the handler stored in its slot. It never delegatecalls, so the handler
 * runs as its own contract, not as the Safe, and cannot write the Safe's
 * storage. Anything the handler then calls has the handler as msg.sender.
 *
 * Assumes the handler is not the Safe itself. v1.3.0 does not forbid that
 * (v1.4.0 added GS400 for it), and then fallback() calls back into the Safe
 * as the Safe, with the caller's address appended to the calldata, which can
 * select a different function. Only the Safe can set its handler (SE-7).
 */
rule fallbackOnlyCallsItsHandler(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    uint256 handlerWord = fallbackHandlerSlotWord();
    require handlerWord != 0;
    require fallbackHandlerAddress() != currentContract;
    require expectedCallee == to_mathint(handlerWord) % 2^160;
    require !calledSomeoneElse;
    require !calledWithValue;
    require !madeDelegateCall;

    f@withrevert(e, args);

    assert !calledSomeoneElse,
        "fallback called an address other than its handler";
    assert !calledWithValue,
        "fallback sent ETH to its handler";
    assert !madeDelegateCall,
        "fallback delegatecalled, running code inside the Safe";
}

/*
 * With no handler set (the zero address), fallback() makes no outgoing call
 * or delegatecall at all. The slot is checked as the raw word, as fallback()
 * does (`if iszero(handler)`). -1 matches no address, so any call is flagged.
 */
rule fallbackMakesNoCallWithoutAHandler(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require fallbackHandlerSlotWord() == 0;
    require expectedCallee == -1;
    require !calledSomeoneElse;
    require !madeDelegateCall;

    f@withrevert(e, args);

    assert !calledSomeoneElse && !madeDelegateCall,
        "fallback made an outgoing call with no handler set";
}

/*
 * Only an enabled module can call execTransactionFromModule or
 * execTransactionFromModuleReturnData: any call to either that succeeds came
 * from an address in the module list other than the list head 0x1. Checked
 * once per function.
 */
rule onlyEnabledModulesCanCallModuleExec(method f, calldataarg args)
    filtered { f -> isModuleExec(f) }
{
    env e;
    bool senderWasModule = e.msg.sender != SENTINEL() && moduleEntry(e.msg.sender) != 0;

    f@withrevert(e, args);

    assert !lastReverted => senderWasModule,
        "an address that is not an enabled module successfully called a module entry point";
}

/*
 * An enabled module can make the Safe act through each of the two module
 * entry points, execTransactionFromModule and
 * execTransactionFromModuleReturnData. Checked once per function.
 */
rule enabledModuleCanMakeTheSafeAct(method f, calldataarg args)
    filtered { f -> isModuleExec(f) }
{
    env e;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;
    require !safeActed;

    f@withrevert(e, args);

    satisfy !lastReverted && safeActed,
        "an enabled module cannot make the Safe act";
}

/*
 * execTransaction only succeeds after the signature check has run on its own
 * transaction hash at the current nonce, asking for as many signatures as the
 * threshold, and at least one. The Safe makes no outgoing call before that
 * check. execTransaction calls checkSignatures directly, with no try/catch,
 * so on chain a failing check reverts the whole transaction. The threshold is
 * not assumed: a zero threshold is shown to fail. No loop runs, so this holds
 * for any threshold.
 */
rule execTransactionRunsOnlyAfterTheSignatureCheck(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, uint256 gasPrice,
    address gasToken, address refundReceiver, bytes signatures
) {
    env e;
    require !signatureCheckRan;
    require !actedBeforeSignatureCheck;
    uint256 threshold = thresholdValue();

    bytes32 txHash = getTransactionHash(e,
        to, value, data, operation, safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, nonce());

    execTransaction@withrevert(e,
        to, value, data, operation, safeTxGas, baseGas, gasPrice, gasToken, refundReceiver, signatures);

    assert !lastReverted => (signatureCheckRan && signatureCheckHash == txHash),
        "execTransaction succeeded without the signature check running on its own transaction hash";
    assert !lastReverted => (signatureCheckRequired == threshold && threshold > 0),
        "execTransaction succeeded without needing at least one owner signature, or fewer than the threshold";
    assert !lastReverted => !actedBeforeSignatureCheck,
        "execTransaction made the Safe act before the signature check ran";
}

/*
 * Once the threshold is passed — the signature check succeeds — owners can
 * make the Safe act through execTransaction, whatever the threshold and
 * however many owners there are. No guard and gasPrice 0, so the transaction
 * is the only outgoing call.
 */
rule ownersCanMakeTheSafeAct(
    address to, uint256 value, bytes data, Enum.Operation operation,
    uint256 safeTxGas, uint256 baseGas, address gasToken,
    address refundReceiver, bytes signatures
) {
    env e;
    require thresholdValue() > 0;
    require guardAddress() == 0;
    require !safeActed;

    execTransaction@withrevert(e,
        to, value, data, operation, safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted && safeActed,
        "with the signature check passed, execTransaction still could not make the Safe act";
}

/*
 * Owners, threshold, modules, guard and fallback handler only change when the
 * caller is the Safe itself. The three act paths are left out: a change they
 * cause comes from their call back into the Safe, which this rule covers.
 */
rule settingsOnlyChangeWhenTheSafeCallsItself(method f, calldataarg args, address a)
    filtered { f -> !f.isView && !f.isPure && !isActPath(f) }
{
    env e;
    require thresholdValue() > 0;

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    address guardBefore = guardAddress();
    uint256 handlerBefore = fallbackHandlerSlotWord();

    f@withrevert(e, args);

    bool changed = !lastReverted && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != guardBefore ||
        fallbackHandlerSlotWord() != handlerBefore);

    assert changed => e.msg.sender == currentContract,
        "the Safe's settings changed in a call that did not come from the Safe itself";
}

/*
 * An approval for `a` is only recorded by `a` itself, while `a` is in the
 * owner list. (The list head 0x1 also passes, but cannot send transactions and
 * is rejected as a signer.)
 */
rule onlyOwnersCanApproveHashes(method f, calldataarg args, address a, bytes32 h)
    filtered { f -> !f.isView && !f.isPure && !isActPath(f) }
{
    env e;
    require thresholdValue() > 0;
    uint256 approvedBefore = approvedHashes(a, h);
    bool senderWasListed = ownerEntry(e.msg.sender) != 0;

    f@withrevert(e, args);

    assert (!lastReverted && approvedHashes(a, h) != approvedBefore) =>
        (e.msg.sender == a && senderWasListed),
        "an approval was recorded for an address other than the caller, or by an address not in the owner list";
}

rule setupAlwaysRevertsAfterSetup(
    address[] owners_, uint256 threshold_, address to, bytes data,
    address fallbackHandler, address paymentToken, uint256 payment, address paymentReceiver
) {
    env e;
    require thresholdValue() > 0;

    setup@withrevert(e, owners_, threshold_, to, data, fallbackHandler, paymentToken, payment, paymentReceiver);

    assert lastReverted, "setup ran on a Safe that was already set up";
}

rule requiredTxGasAlwaysReverts(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;

    requiredTxGas@withrevert(e, to, value, data, operation);

    assert lastReverted, "requiredTxGas returned instead of reverting";
}

rule simulateAndRevertAlwaysReverts(address targetContract, bytes payload) {
    env e;

    simulateAndRevert@withrevert(e, targetContract, payload);

    assert lastReverted, "simulateAndRevert returned instead of reverting";
}

/*
 * Each pass of the signature check accepts exactly one new, approving owner.
 * Stated on one pass of the loop body (checkNSignaturesLoopBody, a verbatim
 * copy of GnosisSafe.sol:256-301) for any pass `i` and any previous signer, so
 * no loop runs and it covers every pass, for any threshold: `t` passes accept
 * `t` distinct approving owners.
 *
 * The signer it accepts is above the previous one (so no repeats), is in the
 * owner list and is not the list head 0x1. For v == 1 it approved by being the
 * sender or with approveHash; otherwise it is the address ecrecover returns
 * for the signature (v > 1) or a contract that returned the EIP-1271 magic
 * value (v == 0), by the body's own code.
 */
rule eachSignatureAcceptsANewApprovingOwner(
    bytes32 dataHash, bytes data, bytes signatures,
    uint256 requiredSignatures, uint256 i, address lastOwner
) {
    env e;
    uint8 v = signatureTypeAt(signatures, i);

    // Called without @withrevert, so only passes that accept a signer are
    // checked. A rejected pass returns no signer to check.
    address signer = checkNSignaturesLoopBody(e,
        dataHash, data, signatures, requiredSignatures, i, lastOwner);

    assert to_mathint(signer) > to_mathint(lastOwner),
        "a pass accepted a signer that is not above the previous one";
    assert ownerEntry(signer) != 0 && signer != SENTINEL(),
        "a pass accepted a signer that is not an owner";
    assert v == 1 => (e.msg.sender == signer || approvedHashes(signer, dataHash) != 0),
        "a pass accepted an approved-hash signature that the owner did not approve";
}
