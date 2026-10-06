/*
 * Safe v1.4.1: outside its call to the handler, fallback writes none of the
 * Safe's storage.
 *
 * The scene holds only the Safe, so every SSTORE the hook sees is the Safe
 * writing its own storage. The handler's code is not in the scene, so what
 * the handler does inside that call is not counted. Assumes the handler is
 * not the Safe itself.
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
 * A successful approveHash is seen writing storage, so the rule above is not
 * vacuous.
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
