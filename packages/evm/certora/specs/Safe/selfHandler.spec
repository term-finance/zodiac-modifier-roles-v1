/*
 * GnosisSafe v1.3.0 (solc 0.7.6): a Safe set as its own fallback handler.
 * v1.3.0 allows this (v1.4.0 forbids it, GS400); only the Safe can set its
 * handler (SE-7).
 *
 * fallback() then calls the Safe itself, as the Safe, with the caller's
 * calldata plus the caller's 20-byte address appended:
 *  - 4+ bytes of calldata: the selector matched nothing (that is why fallback
 *    ran), the inner call has the same selector, so it lands in fallback
 *    again, forever, until gas or call depth runs out and every level reverts.
 *  - 1-3 bytes: the inner selector is those bytes plus the first bytes of the
 *    caller's address, so it can pick another function, but with only 21-23
 *    bytes of calldata. Any function with an argument fails ABI decoding
 *    (one argument needs 36 bytes); every function with none is a view
 *    (getThreshold, getOwners, getChainId, domainSeparator, nonce, VERSION).
 * So fallback either reverts or returns a view's answer.
 *
 * The self-call resolves to the Safe in this scene. The conf's recursion
 * limit cuts off the endless fallback->fallback case, which reverts on chain.
 */

methods {
    function fallbackHandlerAddress() external returns (address) envfree;
    function fallbackHandlerIs(address) external returns (bool) envfree;
}

persistent ghost bool calledSomeoneElse;
persistent ghost bool calledWithValue;
persistent ghost bool madeDelegateCall;

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    // The hook sees CALL's raw 256-bit address word; the EVM calls only its
    // low 160 bits, so compare the address actually called.
    if (to_mathint(addr) % 2^160 != to_mathint(currentContract)) {
        calledSomeoneElse = true;
    }
    if (value != 0) {
        calledWithValue = true;
    }
}

hook DELEGATECALL(uint g, address addr, uint argsOffset, uint argsLength,
                  uint retOffset, uint retLength) uint rc {
    madeDelegateCall = true;
}

/*
 * With the Safe as its own handler, a call to fallback() leaves every byte of
 * the Safe's storage as it was, and if it succeeds, the Safe called nothing
 * but itself, sent no ETH, and made no delegatecall.
 */
rule selfHandlerFallbackChangesNothing(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    // The slot word is exactly the Safe's address, upper 96 bits clear, so the
    // Prover resolves fallback()'s call as a call to the Safe itself. A word
    // with upper bits set behaves the same on chain (CALL uses only the low
    // 160 bits), but the Prover would treat it as an unknown address.
    require fallbackHandlerIs(currentContract);
    require !calledSomeoneElse;
    require !calledWithValue;
    require !madeDelegateCall;
    storage before = lastStorage;

    f@withrevert(e, args);
    bool succeeded = !lastReverted;

    assert lastStorage[currentContract] == before[currentContract],
        "with the Safe as its own handler, fallback changed the Safe's storage";
    assert succeeded => !calledSomeoneElse,
        "with the Safe as its own handler, fallback made the Safe call another address";
    assert succeeded => !calledWithValue,
        "with the Safe as its own handler, fallback sent ETH";
    assert succeeded => !madeDelegateCall,
        "with the Safe as its own handler, fallback delegatecalled";
}
