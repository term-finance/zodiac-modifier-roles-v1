/*
 * Delay Modifier queue provenance: executeNextTx and skipExpired, the two
 * functions anyone can call, only act on queue entries that an enabled module
 * or the owner queued.
 *
 * A hook on txHash records, for each queue entry, whether the call that wrote
 * it came from the owner or an enabled module. The scene is
 * moduleIntegrity.spec's: the real Delay under DelayHarness, ReenteringAvatar
 * as the target, and PauseGuard.
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

    // Guard calls resolve to PauseGuard, the only guard in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);
}

// SENTINEL_MODULES, an internal constant in Modifier.sol.
definition SENTINEL_MODULES() returns address = 0x1;

/// Whether the caller of the call being checked is the owner or an enabled module.
ghost bool callerAuthorized;

/// For each queue index, whether the call that last wrote it was from the owner or an enabled module.
ghost mapping(uint256 => bool) queuedByModuleOrOwner;

hook Sstore txHash[KEY uint256 n] bytes32 newHash {
    queuedByModuleOrOwner[n] = callerAuthorized;
}

/*
 * txNonce never passes queueNonce.
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
