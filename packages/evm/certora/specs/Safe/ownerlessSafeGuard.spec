/*
 * ConfigLockGuard on the OwnerlessSafe (GnosisSafe v1.3.0), built with
 * lockedModifier = address(0): it leaves the governance path through the
 * module open, and has no function that can change what it checks. What the
 * guard blocks for the signers is proposerSafeGuard.spec's.
 *
 * The scene is the real GnosisSafe v1.3.0 (GnosisSafeHarness) with the real
 * ConfigLockGuard in its guard slot. The module's call to `to` is routed to
 * the Safe's eight settings functions, so moduleCanStillChangeEachSetting
 * pins `to` to the Safe.
 */

using ConfigLockGuard as configLockGuard;

methods {
    function guardAddress() external returns (address) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function fallbackHandlerSlotWord() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    function configLockGuard.lockedModifier() external returns (address) envfree;

    // Guard calls resolve to ConfigLockGuard, the only guard in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);

    // The Safe's call to `to`, run as a call to its own settings functions.
    unresolved external in GnosisSafeHarness.execTransactionFromModule(address, uint256, bytes, Enum.Operation) => DISPATCH [
        GnosisSafeHarness.enableModule(address),
        GnosisSafeHarness.disableModule(address, address),
        GnosisSafeHarness.addOwnerWithThreshold(address, uint256),
        GnosisSafeHarness.removeOwner(address, address, uint256),
        GnosisSafeHarness.swapOwner(address, address, address),
        GnosisSafeHarness.changeThreshold(uint256),
        GnosisSafeHarness.setGuard(address),
        GnosisSafeHarness.setFallbackHandler(address)
    ] default HAVOC_ECF;
}

/// Head of the Safe's owner and module lists.
definition SENTINEL() returns address = 0x1;

/// ConfigLockGuard's external functions, by selector.
definition CHECK_TRANSACTION() returns uint32 = 0x75f0bb52;
definition CHECK_AFTER_EXECUTION() returns uint32 = 0x93271368;
definition SUPPORTS_INTERFACE() returns uint32 = 0x01ffc9a7;
definition LOCKED_MODIFIER() returns uint32 = 0x97e50690;

/// The Safe's eight settings functions.
definition isSettingsFunction(method f) returns bool =
    f.selector == sig:enableModule(address).selector ||
    f.selector == sig:disableModule(address, address).selector ||
    f.selector == sig:addOwnerWithThreshold(address, uint256).selector ||
    f.selector == sig:removeOwner(address, address, uint256).selector ||
    f.selector == sig:swapOwner(address, address, address).selector ||
    f.selector == sig:changeThreshold(uint256).selector ||
    f.selector == sig:setGuard(address).selector ||
    f.selector == sig:setFallbackHandler(address).selector;

/* ------------------------------------------------------------------------
 * 1. Every entry point of the guard is accounted for
 * --------------------------------------------------------------------- */

/*
 * ConfigLockGuard has no fallback, its functions are exactly
 * checkTransaction, checkAfterExecution, supportsInterface and
 * lockedModifier, and none of them writes state. lockedModifier is immutable
 * and the guard has no admin, so what it checks is fixed at deployment.
 */
rule configLockGuardFunctionsAreTheKnownFour(method f, calldataarg args)
    filtered { f -> f.contract == configLockGuard }
{
    env e;

    f(e, args);

    assert !f.isFallback,
        "ConfigLockGuard has a fallback";
    assert f.selector == CHECK_TRANSACTION() ||
           f.selector == CHECK_AFTER_EXECUTION() ||
           f.selector == SUPPORTS_INTERFACE() ||
           f.selector == LOCKED_MODIFIER(),
        "ConfigLockGuard has a function this file does not account for";
    assert f.isView || f.isPure,
        "ConfigLockGuard has a function that can write state";
}

/* ------------------------------------------------------------------------
 * 2. Once installed, governance through the module still works
 * --------------------------------------------------------------------- */

/*
 * For each of the Safe's eight settings functions, including the four the
 * guard blocks for the signers, an enabled module's execTransactionFromModule
 * addressed to the Safe with a call to it succeeds and a setting changes. `f`
 * picks the selector the call carries.
 */
rule moduleCanStillChangeEachSetting(method f, bytes data, address a)
    filtered { f -> f.contract == currentContract && isSettingsFunction(f) }
{
    env e;
    require guardAddress() == configLockGuard;
    require configLockGuard.lockedModifier() == 0;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;
    require selectorOf(data) == f.selector;

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    address guardBefore = guardAddress();
    uint256 handlerBefore = fallbackHandlerSlotWord();

    bool success = execTransactionFromModule@withrevert(
        e, currentContract, 0, data, Enum.Operation.Call);

    satisfy !lastReverted && success && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != guardBefore ||
        fallbackHandlerSlotWord() != handlerBefore),
        "with ConfigLockGuard installed, an enabled module could not use this settings function";
}

/*
 * With the guard installed, an enabled module's plain
 * execTransactionFromModule to another contract succeeds.
 */
rule moduleCanStillCallOut(address to, uint256 value, bytes data) {
    env e;
    require guardAddress() == configLockGuard;
    require configLockGuard.lockedModifier() == 0;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;
    require to != currentContract;

    bool success = execTransactionFromModule@withrevert(
        e, to, value, data, Enum.Operation.Call);

    satisfy !lastReverted && success,
        "with ConfigLockGuard installed, an enabled module could not make a plain call to another contract";
}
