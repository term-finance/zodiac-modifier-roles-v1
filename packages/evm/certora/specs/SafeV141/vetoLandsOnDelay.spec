/*
 * The veto lands on the DelayOwnerSafe: on the real Safe v1.4.1
 * (SafeV141Harness), an enabled module's execTransactionFromModule(Delay, 0,
 * setTxNonce(n), Call) succeeds and sets the Delay's txNonce to n. This is
 * the other side of the module call that veto.spec's
 * passedVetoReachesTheDelayOwnerSafe (GV-2) records.
 *
 * The Delay is DelayTarget, and the Safe's call to it is routed to
 * DelayTarget.setTxNonce.
 */

using DelayTarget as delay;
using CalldataReader as reader;

methods {
    function moduleEntry(address) external returns (address) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function delay.owner() external returns (address) envfree;
    function delay.txNonce() external returns (uint256) envfree;
    function delay.queueNonce() external returns (uint256) envfree;

    function reader.wordAfterSelector(bytes) external returns (uint256) envfree;

    // The Safe's call to the Delay (Executor.sol, Safe v1.4.1).
    unresolved external in SafeV141Harness._ => DISPATCH [
        DelayTarget.setTxNonce(uint256)
    ] default HAVOC_ALL;
}

/// Head of the Safe's module list.
definition SENTINEL() returns address = 0x1;

/*
 * An enabled module's execTransactionFromModule(Delay, 0, setTxNonce(n),
 * Call) on the Safe returns true and sets the Delay's txNonce to n, for any n
 * the Delay accepts (txNonce < n <= queueNonce), when the Safe owns the
 * Delay.
 */
rule delayOwnerSafeLandsTheVeto(uint256 n, bytes data) {
    env e;
    require e.msg.value == 0;

    // The caller is an enabled module; on chain, the Roles Modifier.
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;

    // The Safe owns the Delay.
    require delay.owner() == currentContract;

    require data.length == 36;
    require selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector;
    require reader.wordAfterSelector(data) == n;

    require delay.txNonce() < n;
    require n <= delay.queueNonce();

    bool success = execTransactionFromModule@withrevert(e, delay, 0, data, Enum.Operation.Call);

    assert !lastReverted && success,
        "the DelayOwnerSafe's module call of setTxNonce(n) did not succeed";
    assert delay.txNonce() == n,
        "the DelayOwnerSafe's module call did not set the Delay's txNonce";
}
