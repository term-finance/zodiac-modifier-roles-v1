/*
 * MultiSendCallOnly: a batch too short to hold a single entry executes
 * nothing, and multiSend is its only entry point.
 */

methods {
    function multiSend(bytes) external;
}

/*
 * A multisend blob of at most ROLES_LOOP_START bytes is ABI_HEADER bytes of
 * selector, offset word and length word, plus at most MULTISEND_HOLE_MAX
 * bytes of `transactions`: less than one 85-byte entry header.
 */
definition ABI_HEADER() returns mathint = 4 + 32 + 32;      // 68
definition ROLES_LOOP_START() returns mathint = 100;        // Permissions.sol:219
definition MULTISEND_HOLE_MAX() returns mathint =
    ROLES_LOOP_START() - ABI_HEADER();                      // 32

/*
 * Set by the CALL hook. MultiSendCallOnly makes each entry's call with a raw
 * `call`.
 */
ghost bool sawCall;

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    sawCall = true;
}

/*
 * With at most MULTISEND_HOLE_MAX bytes of `transactions`, multiSend makes no
 * call, whether it completes or reverts.
 */
rule shortBatchExecutesNothing(bytes transactions) {
    env e;

    require !sawCall;
    require to_mathint(transactions.length) <= MULTISEND_HOLE_MAX();

    multiSend@withrevert(e, transactions);

    assert !sawCall,
        "a batch too short to hold a single entry still made a call";
}

/*
 * A batch that short can complete as a no-op rather than revert.
 */
rule shortBatchCompletesAsNoOp(bytes transactions) {
    env e;

    require to_mathint(transactions.length) <= MULTISEND_HOLE_MAX();
    require e.msg.value == 0;

    multiSend@withrevert(e, transactions);

    satisfy !lastReverted,
        "every batch of at most 32 bytes reverts, so the no-op reading is wrong";
}

/*
 * A longer batch can make a call, so the CALL hook fires and
 * shortBatchExecutesNothing is not vacuous.
 */
rule longerBatchCanExecute(bytes transactions) {
    env e;

    require !sawCall;
    require to_mathint(transactions.length) > MULTISEND_HOLE_MAX();

    multiSend@withrevert(e, transactions);

    satisfy !lastReverted && sawCall,
        "no batch of any length makes a call, so the CALL hook is not firing and shortBatchExecutesNothing is vacuous";
}

/*
 * One byte past the threshold, an entry can execute, so MULTISEND_HOLE_MAX is
 * the exact cutoff.
 */
rule oneByteAboveTheHoleExecutes(bytes transactions) {
    env e;

    require !sawCall;
    require to_mathint(transactions.length) == MULTISEND_HOLE_MAX() + 1;

    multiSend@withrevert(e, transactions);

    satisfy !lastReverted && sawCall,
        "one byte past the threshold still executes nothing, so the cutoff is not where the arithmetic puts it";
}

/*
 * MultiSendCallOnly's only entry point is multiSend, and it has no fallback.
 */
rule multiSendIsTheOnlyEntryPoint(method f, calldataarg args) {
    env e;

    f(e, args);

    assert !f.isFallback,
        "MultiSendCallOnly has a fallback, so unmatched calldata need not revert: prove that fallback executes no call on a short input before relying on shortBatchExecutesNothing";
    assert f.selector == sig:multiSend(bytes).selector,
        "MultiSendCallOnly has an entry point other than multiSend: prove that entry point executes no call on a short input before relying on shortBatchExecutesNothing";
}
