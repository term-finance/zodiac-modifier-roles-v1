/*
 * MultiSendCallOnly — a batch too short to hold an entry executes nothing.
 *
 * WHY THIS SPEC EXISTS. Permissions.check dispatches on `to == multisend`
 * before it consults clearance, and checkMultisendTransaction's entry loop
 * starts at i = 100, so a blob of at most 100 bytes never enters it:
 * membership and the offset word are the only things checked. That much is
 * proved on the Roles side by shortMultisendBlobSkipsEveryEntryCheck in
 * specs/Roles/setTxNonceRoleConfigSufficient.spec.
 *
 * What that rule cannot say is whether anything then HAPPENS, because the
 * Roles scenes link `target` to DummyAvatar, which returns true and calls
 * nothing. This spec covers the other end: given the blob reaches the real
 * MultiSendCallOnly, nothing executes.
 *
 * THE ARITHMETIC. A blob is 4 selector + 32 offset word + 32 length word = 68
 * bytes of ABI header, then packed entries of 85 bytes each (1 operation + 20
 * to + 32 value + 32 dataLength) plus their data. At most 100 blob bytes
 * leaves at most 32 for `transactions`, and 32 < 85, so not even one entry
 * header fits.
 *
 * MultiSendCallOnly's own loop starts at i := 0x20 and runs while i < length,
 * where `length` is the content length -- the same pointer-frame/content-length
 * convention Roles uses. So a declared length of 32 or less means the loop
 * condition is false ON ENTRY: zero iterations. loop_iter is not doing any work
 * in the rule below; there is nothing to unroll.
 *
 * NO LOOP IS INVOLVED, which is the point. The claim does not inherit
 * loop_iter as a bound the way the batch-length rules on the Roles side do.
 *
 * DELIBERATELY NOT CLAIMED HERE:
 *
 *   - That a blob of at most 100 bytes yields a declared `transactions` length
 *     of at most 32. That is the ABI decoder's calldata bounds check, which is
 *     compiler-generated; this spec receives `transactions` already decoded and
 *     states the threshold on its length directly. The implication is a source
 *     fact, checked by test rather than here.
 *
 *   - That a blob whose selector is not multiSend(bytes) reverts.
 *     MultiSendCallOnly declares no fallback and no receive, so it does, but
 *     that is a property of the Solidity dispatcher, which the Prover
 *     abstracts: CVL's `method f` ranges only over declared functions, so an
 *     undeclared selector cannot be invoked from a rule at all.
 *
 *   - Anything about what a LONGER batch does. longerBatchCanExecute only
 *     witnesses that such a batch can make a call -- it is the non-vacuity
 *     guard for the rule above, not a claim about batch contents. On the
 *     deployed path those contents are constrained by the Roles side; see
 *     checkTransactionAdmitsOnlyDelaySetTxNonce.
 *
 * Both of the first two are covered against the real contracts by
 * test/MultisendShortBlob.spec.ts.
 */

methods {
    function multiSend(bytes) external;
}

/*
 * The threshold, with its provenance rather than as a bare 32.
 *
 * The hole on the Roles side is a BLOB of at most 100 bytes. The blob's ABI
 * header is 4 (selector) + 32 (offset word) + 32 (length word) = 68 bytes, so
 * at most 100 - 68 = 32 bytes of `transactions` payload can follow, and the
 * ABI decoder caps the declared length at what the calldata actually holds.
 * MULTISEND_HOLE_MAX is therefore the exact image of "blob of at most 100
 * bytes" under decoding -- not a number chosen for convenience.
 */
definition ABI_HEADER() returns mathint = 4 + 32 + 32;      // 68
definition ROLES_LOOP_START() returns mathint = 100;        // Permissions.sol:219
definition MULTISEND_HOLE_MAX() returns mathint =
    ROLES_LOOP_START() - ABI_HEADER();                      // 32

/*
 * Set by the CALL opcode hook below. MultiSendCallOnly performs each entry
 * with a raw `call(...)` in assembly, so this is the observable that says
 * "an entry executed".
 */
ghost bool sawCall;

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    sawCall = true;
}

/*
 * THE RULE. At most 32 bytes of `transactions` -- less than one 85-byte entry
 * header -- and no entry is executed. Stated over @withrevert so it covers the
 * reverting paths too: on neither a completing nor a reverting execution does
 * a call go out.
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
 * The no-op is clean: it returns rather than reverting. Without this, the rule
 * above would also be satisfied by multiSend reverting on every short input,
 * which is a different (and less useful) fact about the same threshold.
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
 * NON-VACUITY, and the one that matters most here.
 *
 * shortBatchExecutesNothing asserts that a ghost stays false. It would pass
 * just as green if the CALL hook never fired at all -- a wrong hook signature,
 * or the Prover not modelling the opcode -- in which case it would prove
 * nothing whatsoever. This rule exhibits a batch that DOES set the ghost, so
 * the observable is live and the rule above is meaningful.
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
 * THE BOUNDARY IS EXACTLY WHERE THE ARITHMETIC SAYS.
 *
 * One byte past the threshold -- a declared length of 33, i.e. a blob of 101
 * bytes -- and an entry DOES execute. Without this, shortBatchExecutesNothing
 * would be equally true of a threshold picked far too high, and there would be
 * nothing tying MULTISEND_HOLE_MAX to the real cutoff.
 *
 * 33 is also exactly where the Roles side starts checking: its loop condition
 * is `i < data.length` with i starting at 100, so a 101-byte blob is the first
 * one that enters the loop body. The two contracts use the same
 * pointer-frame/content-length convention and therefore share this cutoff --
 * which is why the hole below it is empty on both sides rather than on only
 * one.
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
 * THE ENTIRE EXTERNAL SURFACE IS multiSend(bytes).
 *
 * The 100-byte hole lets a caller put ARBITRARY bytes in front of
 * MultiSendCallOnly, not just a well-formed batch: Roles never checks the
 * selector, only the offset word (Permissions.sol:209-213). So "what can 100
 * arbitrary bytes reach here?" has two halves. If the selector matches
 * multiSend, shortBatchExecutesNothing covers it. This rule covers the other
 * half by showing there is nothing else to reach: every external entry point
 * of this contract is multiSend, and none of them is a fallback.
 *
 * A contract with no fallback and no receive reverts on unmatched calldata,
 * so the two halves together are exhaustive.
 *
 * WHAT THIS RULE DOES NOT SAY. It establishes that a fallback does not EXIST.
 * It does not establish that a fallback would be harmless -- that is a claim
 * about behaviour, and this is a claim about shape. The exhaustiveness of the
 * two-case analysis above is what rests on it.
 *
 * So if anyone ever adds a function or a fallback to the vendored copy, this
 * rule fails, and the obligation that follows is to prove the new entry point
 * ALSO cannot violate the restriction: that it executes no call on at most
 * MULTISEND_HOLE_MAX bytes, the way shortBatchExecutesNothing does for
 * multiSend. The storage half of that obligation is already discharged in
 * advance -- noEntryPointWritesStorage in shortBatchWritesNoStorage.spec is
 * parametric and would cover the new entry point automatically.
 */
rule multiSendIsTheOnlyEntryPoint(method f, calldataarg args) {
    env e;

    f(e, args);

    assert !f.isFallback,
        "MultiSendCallOnly has a fallback, so unmatched calldata need not revert: prove that fallback executes no call on a short input before relying on shortBatchExecutesNothing";
    assert f.selector == sig:multiSend(bytes).selector,
        "MultiSendCallOnly has an entry point other than multiSend: prove that entry point executes no call on a short input before relying on shortBatchExecutesNothing";
}
