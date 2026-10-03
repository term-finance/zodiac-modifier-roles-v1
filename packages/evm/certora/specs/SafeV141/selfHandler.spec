/*
 * Safe v1.4.1: a Safe set as its own fallback handler. fallback then calls
 * the Safe itself, as the Safe, with the caller's calldata plus the caller's
 * 20-byte address appended.
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
    // CALL's address word may carry upper bits; the EVM calls its low 160
    // bits.
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
    // The slot word is exactly the Safe's address, so the Prover resolves
    // fallback's call as a call to the Safe itself.
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
