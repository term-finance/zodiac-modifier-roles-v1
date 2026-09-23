/*
 * MultiSendCallOnly — a batch too short to hold an entry writes no storage.
 *
 * SPLIT OUT FROM shortBatchExecutesNothing.spec DELIBERATELY. The ALL_SSTORE
 * hook below requires storage splitting to be disabled, which is a global
 * Prover setting. Rather than change it for the whole ruleset and invalidate
 * the green run of 7.1-7.5 under the settings they verified with, this rule
 * lives in its own conf: confs/MultiSend-noStorageWrite.conf.
 *
 * See shortBatchExecutesNothing.spec for the full context, the arithmetic
 * behind the threshold, and what is deliberately not claimed.
 */

methods {
    function multiSend(bytes) external;
}

/*
 * The threshold, with its provenance rather than as a bare 32. Kept in step
 * with the identical block in shortBatchExecutesNothing.spec: a blob of at
 * most 100 bytes is 68 bytes of ABI header plus at most 32 of payload.
 */
definition ABI_HEADER() returns mathint = 4 + 32 + 32;      // 68
definition ROLES_LOOP_START() returns mathint = 100;        // Permissions.sol:219
definition MULTISEND_HOLE_MAX() returns mathint =
    ROLES_LOOP_START() - ABI_HEADER();                      // 32

/*
 * Set by the SSTORE opcode hook. Under delegatecall this contract runs in the
 * avatar's storage context, so any write reached here is a write to the Safe.
 */
ghost bool sawStore;

hook ALL_SSTORE(uint loc, uint v) {
    sawStore = true;
}

/*
 * NO ENTRY POINT OF THIS CONTRACT EVER WRITES STORAGE.
 *
 * WHY THIS IS PARAMETRIC, AND WHY IT IS NOT LENGTH-BOUNDED.
 *
 * The claim that matters under DELEGATECALL is about the avatar's storage,
 * not this contract's: the avatar delegatecalls MultiSendCallOnly, so this
 * code runs in the SAFE'S storage context. A single SSTORE reached here would
 * land on the Safe's own slots -- owners, threshold, modules, nonce. "Executes
 * no calls" would be cold comfort if the body could still write.
 *
 * multiSend performs only `call`s; it has no storage access at any input
 * length. So unlike the no-call claim -- which genuinely depends on the
 * 100-byte threshold, since a longer batch does call -- this one needs no
 * bound on the input at all. That makes it strictly stronger stated over every
 * entry point and every argument.
 *
 * It is parametric for a second reason. multiSendIsTheOnlyEntryPoint
 * establishes that the external surface is exactly multiSend and that none of
 * it is a fallback, which is what makes the no-call case analysis exhaustive.
 * But that is a claim about the contract's SHAPE, not its behaviour: it says a
 * fallback does not exist, not that a fallback would be harmless. If one were
 * ever added, that rule would fail and the obligation would be to prove the
 * new entry point also cannot violate the restriction.
 *
 * Stating this one parametrically discharges half of that obligation in
 * advance: any entry point added later, fallback included, is already covered
 * here and would have to write no storage to pass. What would still need
 * proving is the no-call half, which is length-bounded and cannot be
 * generalised the same way.
 */
rule noEntryPointWritesStorage(method f, calldataarg args) {
    env e;

    require !sawStore;

    f@withrevert(e, args);

    assert !sawStore,
        "an entry point of MultiSendCallOnly wrote storage, which under delegatecall is the avatar's";
}
