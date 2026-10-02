/*
 * Safe v1.4.1 (solc 0.7.6): with no fallbackHandler set, fallback()
 * changes no state at all, and receive() changes no state beyond the ETH it
 * is sent, whatever the handler.
 *
 * EVM code can change state only through these opcodes: SSTORE (storage),
 * CALL, CALLCODE and DELEGATECALL (other code runs, ETH can move), CREATE and
 * CREATE2 (a new account), and SELFDESTRUCT. TSTORE does not exist before
 * Cancun, and solc 0.7.6 cannot emit it. STATICCALL cannot change state but
 * is flagged too, so "no call of any kind" holds. The hooks below flag each
 * one. The scene holds only the Safe, so every flag is the Safe's own code.
 *
 * ETH sent with a call is not the code's doing: the EVM credits msg.value
 * before any code runs. fallback() is not payable, so a fallback() call that
 * succeeds carries no ETH (checked below). receive() is payable, so a call
 * to it credits the Safe with the ETH sent.
 *
 * The Prover's fallback entry covers both fallback() and receive(); it has
 * no CALLDATASIZE hook to tell them apart. receive() always emits
 * SafeReceived (SE141-17) and fallback() emits nothing, so the rules tell them
 * apart by that event.
 *
 * The ghosts are persistent so an unresolved call cannot havoc them.
 */

methods {
    function fallbackHandlerSlotWord() external returns (uint256) envfree;
    function fallbackHandlerAddress() external returns (address) envfree;
}

/// keccak256("SafeReceived(address,uint256)")
definition SAFE_RECEIVED() returns bytes32 =
    to_bytes32(0x3d0ce9bfc3ed7d6862dbb28b2dea94561fe714a1b4d019aa8af39730d1ad7c3d);

persistent ghost bool wroteStorage;
persistent ghost bool madeAnyCall;
persistent ghost bool createdOrDestroyed;
persistent ghost bool emittedSafeReceived;

hook ALL_SSTORE(uint loc, uint v) {
    wroteStorage = true;
}

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
}

hook CALLCODE(uint g, address addr, uint value, uint argsOffset, uint argsLength,
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

hook CREATE1(uint value, uint offset, uint length) address v {
    createdOrDestroyed = true;
}

hook CREATE2(uint value, uint offset, uint length, bytes32 salt) address v {
    createdOrDestroyed = true;
}

hook SELFDESTRUCT(address a) {
    createdOrDestroyed = true;
}

hook LOG2(uint offset, uint length, bytes32 t1, bytes32 t2) {
    if (t1 == SAFE_RECEIVED()) {
        emittedSafeReceived = true;
    }
}

/*
 * With no handler set, the fallback entry changes no state: no storage
 * write, no call of any kind, no contract created or destroyed. This covers
 * receive() too, which runs on the same entry. And a fallback() call that
 * succeeds (no SafeReceived) carries no ETH, so not even the Safe's balance
 * moves.
 */
rule noHandlerFallbackChangesNoState(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require fallbackHandlerSlotWord() == 0;
    require !wroteStorage;
    require !madeAnyCall;
    require !createdOrDestroyed;
    require !emittedSafeReceived;

    f@withrevert(e, args);
    bool reverted = lastReverted;

    assert !wroteStorage,
        "fallback with no handler wrote storage";
    assert !madeAnyCall,
        "fallback with no handler made a call";
    assert !createdOrDestroyed,
        "fallback with no handler created or destroyed a contract";
    assert (!reverted && !emittedSafeReceived) => e.msg.value == 0,
        "fallback with no handler accepted ETH";
}

/*
 * Whatever the handler, a call that runs receive() and succeeds changes no
 * state beyond the ETH it was sent: no storage write, no call of any kind,
 * no contract created or destroyed.
 */
rule receiveChangesNoState(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require !wroteStorage;
    require !madeAnyCall;
    require !createdOrDestroyed;
    require !emittedSafeReceived;

    f@withrevert(e, args);
    bool ranReceive = !lastReverted && emittedSafeReceived;

    assert ranReceive => !wroteStorage,
        "receive wrote storage";
    assert ranReceive => !madeAnyCall,
        "receive made a call";
    assert ranReceive => !createdOrDestroyed,
        "receive created or destroyed a contract";
}

/*
 * The rules above are not vacuous. Both paths run: with no handler set, a
 * fallback() call succeeds without emitting SafeReceived, and a call reaches
 * receive() and succeeds.
 */
rule noHandlerFallbackSucceeds(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require fallbackHandlerSlotWord() == 0;
    require !emittedSafeReceived;

    f@withrevert(e, args);
    bool reverted = lastReverted;

    satisfy !reverted && !emittedSafeReceived,
        "no fallback call with no handler succeeded";
}

rule receiveRuns(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require !emittedSafeReceived;

    f@withrevert(e, args);
    bool reverted = lastReverted;

    satisfy !reverted && emittedSafeReceived,
        "no call reached receive";
}

/*
 * The hooks do fire. A successful approveHash writes storage, and fallback()
 * with a handler set makes its CALL to the handler. The Safe's code has no
 * CREATE, CREATE2 or SELFDESTRUCT anywhere, so no call can show those hooks
 * firing; they rest on the Prover's opcode instrumentation.
 */
rule storageHookFires(method f, calldataarg args)
    filtered { f -> f.selector == sig:approveHash(bytes32).selector }
{
    env e;
    require !wroteStorage;

    f@withrevert(e, args);
    bool reverted = lastReverted;

    satisfy !reverted && wroteStorage,
        "no successful approveHash wrote storage the hook could see";
}

rule callHookFires(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require fallbackHandlerSlotWord() != 0;
    require fallbackHandlerAddress() != currentContract;
    require !madeAnyCall;

    f@withrevert(e, args);

    satisfy madeAnyCall,
        "fallback with a handler set made no call the hook could see";
}
