/*
 * GnosisSafe v1.3.0 (solc 0.7.6): receive() only emits SafeReceived.
 *
 * receive() (EtherPaymentFallback.sol:10) is `emit SafeReceived(msg.sender,
 * msg.value);` and nothing else. The Prover has no CALLDATASIZE hook, so it
 * cannot see which calls land in receive() rather than fallback(); both sit
 * behind its fallback entry. The rules below therefore key on the event:
 * whenever SafeReceived is emitted, that is all the call did.
 *
 * The ghosts are persistent so an unresolved call on the fallback() path
 * cannot havoc them. Every assertion is on non-reverting runs only.
 */

/// keccak256("SafeReceived(address,uint256)")
definition SAFE_RECEIVED() returns bytes32 =
    to_bytes32(0x3d0ce9bfc3ed7d6862dbb28b2dea94561fe714a1b4d019aa8af39730d1ad7c3d);

persistent ghost bool emittedSafeReceived;
persistent ghost bytes32 safeReceivedSender;
persistent ghost mathint logCount;
persistent ghost bool madeAnyCall;
persistent ghost bool wroteStorage;

hook LOG0(uint offset, uint length) {
    logCount = logCount + 1;
}
hook LOG1(uint offset, uint length, bytes32 t1) {
    logCount = logCount + 1;
}
hook LOG2(uint offset, uint length, bytes32 t1, bytes32 t2) {
    logCount = logCount + 1;
    if (t1 == SAFE_RECEIVED()) {
        emittedSafeReceived = true;
        safeReceivedSender = t2;
    }
}
hook LOG3(uint offset, uint length, bytes32 t1, bytes32 t2, bytes32 t3) {
    logCount = logCount + 1;
}
hook LOG4(uint offset, uint length, bytes32 t1, bytes32 t2, bytes32 t3, bytes32 t4) {
    logCount = logCount + 1;
}

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
}
hook DELEGATECALL(uint g, address addr, uint argsOffset, uint argsLength,
                  uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
}
hook STATICCALL(uint g, address addr, uint argsOffset, uint argsLength,
                uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
}
hook CALLCODE(uint g, address addr, uint value, uint argsOffset, uint argsLength,
              uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
}

hook ALL_SSTORE(uint loc, uint v) {
    wroteStorage = true;
}

/*
 * Whenever receive() runs, it does nothing beyond the event: exactly one log,
 * SafeReceived with the caller as its sender, no call of any kind and no
 * storage write.
 */
rule receiveOnlyEmitsSafeReceived(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require !emittedSafeReceived;
    require logCount == 0;
    require !madeAnyCall;
    require !wroteStorage;

    f@withrevert(e, args);
    bool reverted = lastReverted;

    assert (!reverted && emittedSafeReceived) => logCount == 1,
        "receive emitted more than SafeReceived";
    assert (!reverted && emittedSafeReceived) =>
        safeReceivedSender == to_bytes32(assert_uint256(to_mathint(e.msg.sender))),
        "SafeReceived did not name the caller";
    assert (!reverted && emittedSafeReceived) => !madeAnyCall,
        "receive made a call";
    assert (!reverted && emittedSafeReceived) => !wroteStorage,
        "receive wrote storage";
}

/*
 * receive() is reachable, so the rule above is not vacuous: some call to the
 * Safe succeeds and emits SafeReceived.
 */
rule receiveCanRun(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require !emittedSafeReceived;

    f@withrevert(e, args);
    bool reverted = lastReverted;

    satisfy !reverted && emittedSafeReceived,
        "no call to the Safe reached receive";
}
