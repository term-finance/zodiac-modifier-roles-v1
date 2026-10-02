/*
 * GnosisSafe v1.3.0 (solc 0.7.6): fallback() writes none of the Safe's
 * storage. Outside its call to the handler (SE-14), it does nothing, and with
 * no handler set it makes no call at all (SE-13).
 *
 * fallback() (FallbackManager.sol:32) reads the handler slot and either
 * returns or makes one plain CALL to the handler; it has no SSTORE. The scene
 * holds only the Safe, so every SSTORE the hook sees is the Safe's own code
 * writing the Safe's storage. The handler's code is not in the scene: the
 * Prover cannot resolve the call to it, so whatever the handler does happens
 * inside that call and is not counted. That is the property: outside the
 * handler call, fallback() writes nothing.
 *
 * Assumes the handler is not the Safe itself. Then fallback() calls back into
 * the Safe, and SE-16 shows the Safe's storage ends exactly as it was.
 *
 * The Prover's fallback entry also covers receive(), which writes no storage
 * either (SE-17).
 */

methods {
    function fallbackHandlerAddress() external returns (address) envfree;
}

/// Persistent so the unresolved call to the handler cannot havoc it.
persistent ghost bool wroteStorage;

hook ALL_SSTORE(uint loc, uint v) {
    wroteStorage = true;
}

rule fallbackWritesNoStorage(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require fallbackHandlerAddress() != currentContract;
    require !wroteStorage;

    f@withrevert(e, args);

    assert !wroteStorage,
        "fallback wrote the Safe's storage outside its call to the handler";
}

/*
 * The rule above is not vacuous: the hook does see the Safe write storage.
 * approveHash records the caller's approval in storage, and a call to it
 * that succeeds sets the flag. Without this, the rule above would also pass
 * if the hook never fired.
 */
rule storageWriteHookFires(method f, calldataarg args)
    filtered { f -> f.selector == sig:approveHash(bytes32).selector }
{
    env e;
    require !wroteStorage;

    f@withrevert(e, args);
    bool reverted = lastReverted;

    satisfy !reverted && wroteStorage,
        "no successful approveHash wrote storage the hook could see";
}
