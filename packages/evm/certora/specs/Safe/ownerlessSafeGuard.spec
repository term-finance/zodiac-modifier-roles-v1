/*
 * Property: ConfigLockGuard on the Ownerless Safe (GnosisSafe v1.3.0) leaves
 * the governance path open, and has no function that can change it.
 *
 * The Ownerless Safe owns no modifier once it renounces the Roles Modifier,
 * so its ConfigLockGuard is built with lockedModifier = address(0). That is
 * the Proposer Safe's configuration on the same Safe code, so what the guard
 * blocks for the signers is proved by specs/Safe/proposerSafeGuard.spec (PG)
 * and is not repeated here. This file adds what is specific to the Ownerless
 * Safe:
 *
 *   - its one module, the Delay, is how governance proposals run. Safe v1.3.0
 *     never consults the guard on the module path, so with the guard
 *     installed the Delay can still make the Safe change any of its settings
 *     and call out to any contract;
 *   - the guard itself has no state-changing function, so nothing can change
 *     what it checks once deployed.
 *
 * "The guard" in this file always means ConfigLockGuard, installed as the
 * Safe's transaction guard. The scene is the real v1.3.0 code through
 * GnosisSafeHarness (solc 0.7.6) and the real ConfigLockGuard (solc 0.8.6).
 *
 * Rules, by property:
 *
 *   every entry point of the guard is accounted for
 *     configLockGuardFunctionsAreTheKnownFour    the guard has no fallback,
 *                                                its functions are exactly
 *                                                checkTransaction,
 *                                                checkAfterExecution,
 *                                                supportsInterface and
 *                                                lockedModifier, and none of
 *                                                them writes state
 *
 *   once installed, governance through the module still works
 *     moduleCanStillChangeEachSetting            for each of the Safe's eight
 *                                                settings functions, an
 *                                                enabled module's call to it
 *                                                succeeds and a setting
 *                                                changes
 *     moduleCanStillCallOut                      an enabled module's plain
 *                                                call to another contract
 *                                                succeeds
 *
 * Modelling notes.
 *   - checkTransaction and checkAfterExecution are DISPATCHER(true), so
 *     wherever the Safe calls its guard the real ConfigLockGuard code runs: it
 *     is the only contract in the scene that implements them. On the module
 *     path v1.3.0 calls neither.
 *   - The Safe's low-level call to `to` has a symbolic target. As in
 *     proposerSafeGuard.spec, it is DISPATCHed to the Safe's eight settings
 *     functions. DISPATCH runs the function on the Safe whatever `to` is, so
 *     moduleCanStillChangeEachSetting pins `to` to the Safe itself. A call
 *     whose selector is none of the eight is HAVOC_ECF.
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

    // Guard hooks. ConfigLockGuard is the only implementation in the scene.
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
 * The guard has no fallback, its external functions are exactly the four
 * below, and none of them writes state. So what it checks is fixed at
 * deployment: lockedModifier is immutable and there is no admin. If a
 * function is ever added, this rule fails.
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
 *
 * The module is the Delay on chain, so these calls are governance proposals
 * that have waited out the cooldown.
 * --------------------------------------------------------------------- */

/*
 * For each of the Safe's eight settings functions, including the four the
 * guard blocks for the signers, an enabled module's execTransactionFromModule
 * addressed to the Safe with a call to it succeeds and a setting changes. `f`
 * only picks which selector the call carries.
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
 * An enabled module's plain call to another contract, the shape of a
 * governance proposal acting on the protocol, still succeeds with the guard
 * installed.
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
