/*
 * Safe v1.4.1 as the DelayOwnerSafe: the module call the Roles Modifier
 * makes for a passed veto lands on the Delay.
 *
 * GV-2 (specs/Governor/veto.spec) follows a passed veto from the Governor
 * through the Roles Modifier to its module call on the DelayOwnerSafe,
 * execTransactionFromModule(Delay, 0, setTxNonce(n), Call), with a recording
 * avatar in the Safe's place. This rule, GV-3, is that call's other side, on
 * the real Safe v1.4.1: made by an enabled module, it returns true and the
 * Delay's txNonce becomes n. The Delay is DelayTarget, the vendored Delay
 * v1.0.1 the Roles scenes use.
 *
 * Modelling note. The Safe calls the Delay with Executor's low-level `call`
 * (Executor.sol, Safe v1.4.1) to an address taken from calldata, which the
 * Prover cannot resolve on its own. The DISPATCH entry routes it to
 * DelayTarget.setTxNonce, where it lands on chain. Any other unresolved call
 * is havoced (HAVOC_ALL), which can only make the rule harder to pass. The
 * Safe is called directly here, where the Prover handles this dispatch;
 * behind the Governor and the Roles Modifier it does not (see
 * certora/helpers/RecordingAvatar.sol).
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

/// Head of the Safe's module list. It cannot send transactions, so the
/// Prover must not place the caller there.
definition SENTINEL() returns address = 0x1;

/*
 * An enabled module's execTransactionFromModule(Delay, 0, setTxNonce(n), Call)
 * on the Safe returns true and sets the Delay's txNonce to n, for any n the
 * Delay accepts (txNonce < n <= queueNonce), when the Safe owns the Delay.
 * `data` is setTxNonce(n) as GV-2 records it: 36 bytes, setTxNonce's selector,
 * then n.
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
