/*
 * Property: executeNextTx and skipExpired, the two entry points anyone can
 * call, only ever act on queue entries that an enabled module or the owner
 * put there.
 *
 * queueOnlyGrowsThroughEnabledModules (moduleIntegrity.spec) shows each write
 * to the queue comes from an enabled module, and
 * executeNextTxConsumesOnlyTheEntryAtTxNonce (pauseGuardSufficient.spec) shows
 * executeNextTx runs the entry at txNonce. This file states the two together,
 * end to end, by recording who wrote each queue entry:
 *
 *   - `callerAuthorized` is fixed by the invariant's preserved block to
 *     whether the caller of the current call is the owner or an enabled module
 *     (the raw ring entry moduleOnly reads, as in moduleIntegrity.spec).
 *   - The hook on txHash records it against the entry being written.
 *   - everyQueuedEntryWasQueuedByModuleOrOwner: every entry below queueNonce
 *     was written by such a caller. It holds from deployment (the queue is
 *     empty) and is preserved by every write function.
 *
 * The two rules then show executeNextTx runs only such an entry, and
 * skipExpired only steps txNonce over such entries.
 *
 * The scene is moduleIntegrity.spec's: the real Delay through DelayHarness,
 * ReenteringAvatar as the target, and PauseGuard. The avatar calls back into
 * the Delay on every execution. A queue write made from inside such a
 * callback would be recorded against the outer caller, which can only make
 * the invariant fail, never pass wrongly.
 *
 * Modelling notes.
 *   - loop_iter 1 with optimistic_loop bounds skipExpired's loop to one
 *     iteration per call, as in moduleIntegrity.spec. skipExpiredSkipsOnly...
 *     is stated for every skipped index, so it does not depend on the count.
 *   - optimistic_hashing with hashing_length_bound 1024: the rules cover
 *     transactions whose `data` is at most 971 bytes, as in
 *     moduleIntegrity.spec.
 */

using ReenteringAvatar as hostileAvatar;

methods {
    function owner() external returns (address) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;
    function txNonce() external returns (uint256) envfree;
    function queueNonce() external returns (uint256) envfree;
    function txHash(uint256) external returns (bytes32) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function getTransactionHash(address, uint256, bytes, Enum.Operation) external returns (bytes32) envfree;

    function hostileAvatar.delay() external returns (address) envfree;

    // Module.exec's guard hooks, and Guardable.setGuard's ERC-165 probe of a
    // new guard. PauseGuard is the only implementor in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);
}

/// Modifier.sol:13 — `address internal constant`, so there is no getter.
definition SENTINEL_MODULES() returns address = 0x1;

/// Whether the caller of the call being checked is the owner or an enabled module.
ghost bool callerAuthorized;

/// For each queue index, whether the call that last wrote it was from the owner or an enabled module.
ghost mapping(uint256 => bool) queuedByModuleOrOwner;

hook Sstore txHash[KEY uint256 n] bytes32 newHash {
    queuedByModuleOrOwner[n] = callerAuthorized;
}

/*
 * txNonce never passes queueNonce: executeNextTx and skipExpired only move it
 * while it is below queueNonce, and setTxNonce caps it there.
 */
invariant txNonceNeverPassesQueueNonce()
    txNonce() <= queueNonce();

/*
 * Every entry in the queue, that is every index below queueNonce, was written
 * by the owner or an enabled module.
 */
invariant everyQueuedEntryWasQueuedByModuleOrOwner(uint256 n)
    n < queueNonce() => queuedByModuleOrOwner[n]
    {
        preserved with (env e) {
            require callerAuthorized ==
                (e.msg.sender == owner() || moduleEntry(e.msg.sender) != 0);
        }
    }

/*
 * executeNextTx runs only a transaction queued by an enabled module or the
 * owner: the transaction it runs is the queue entry at txNonce, that entry is
 * in the queue, and it was written by the owner or an enabled module.
 */
rule executeNextTxRunsOnlyEntriesQueuedByModuleOrOwner(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    uint256 n = txNonce();
    uint256 queueNonceBefore = queueNonce();
    bytes32 entryBefore = txHash(n);
    requireInvariant everyQueuedEntryWasQueuedByModuleOrOwner(n);

    executeNextTx(e, to, value, data, operation);

    assert n < queueNonceBefore,
        "executeNextTx ran with no transaction in the queue";
    assert entryBefore == getTransactionHash(to, value, data, operation),
        "executeNextTx ran a transaction other than the queue entry at txNonce";
    assert queuedByModuleOrOwner[n],
        "executeNextTx ran a queue entry not written by the owner or an enabled module";
}

/*
 * skipExpired steps txNonce only over entries queued by an enabled module or
 * the owner: every index it skips is in the queue and was written by one.
 */
rule skipExpiredSkipsOnlyEntriesQueuedByModuleOrOwner(uint256 k) {
    env e;
    uint256 nonceBefore = txNonce();
    requireInvariant txNonceNeverPassesQueueNonce();
    requireInvariant everyQueuedEntryWasQueuedByModuleOrOwner(k);

    skipExpired(e);

    assert (nonceBefore <= k && k < txNonce()) => k < queueNonce(),
        "skipExpired skipped an index that is not in the queue";
    assert (nonceBefore <= k && k < txNonce()) => queuedByModuleOrOwner[k],
        "skipExpired skipped a queue entry not written by the owner or an enabled module";
}

/*
 * The two rules above are not vacuous: executeNextTx can run a queue entry,
 * and skipExpired can skip one.
 */
rule executeNextTxCanRunAQueuedEntry(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require target() == hostileAvatar;
    require hostileAvatar.delay() == currentContract;
    require guard() == 0;
    uint256 n = txNonce();
    requireInvariant everyQueuedEntryWasQueuedByModuleOrOwner(n);

    executeNextTx@withrevert(e, to, value, data, operation);

    satisfy !lastReverted && to_mathint(txNonce()) == n + 1,
        "executeNextTx cannot run any queue entry";
}

rule skipExpiredCanSkipAQueuedEntry() {
    env e;
    require e.msg.value == 0;
    uint256 nonceBefore = txNonce();
    requireInvariant txNonceNeverPassesQueueNonce();
    requireInvariant everyQueuedEntryWasQueuedByModuleOrOwner(nonceBefore);

    skipExpired@withrevert(e);

    satisfy !lastReverted && txNonce() > nonceBefore,
        "skipExpired cannot skip any queue entry";
}
