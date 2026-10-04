/*
 * MultiSendCallOnly: no entry point ever writes storage. It runs under
 * delegatecall in the avatar's storage context, so a write would land on the
 * Safe's own slots.
 */

methods {
    function multiSend(bytes) external;
}

/*
 * The threshold, kept in step with shortBatchExecutesNothing.spec.
 */
definition ABI_HEADER() returns mathint = 4 + 32 + 32;      // 68
definition ROLES_LOOP_START() returns mathint = 100;        // Permissions.sol:219
definition MULTISEND_HOLE_MAX() returns mathint =
    ROLES_LOOP_START() - ABI_HEADER();                      // 32

/*
 * Set by the ALL_SSTORE hook.
 */
ghost bool sawStore;

hook ALL_SSTORE(uint loc, uint v) {
    sawStore = true;
}

/*
 * No entry point of MultiSendCallOnly writes storage, for any input length.
 */
rule noEntryPointWritesStorage(method f, calldataarg args) {
    env e;

    require !sawStore;

    f@withrevert(e, args);

    assert !sawStore,
        "an entry point of MultiSendCallOnly wrote storage, which under delegatecall is the avatar's";
}
