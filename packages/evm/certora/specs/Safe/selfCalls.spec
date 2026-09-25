/*
 * GnosisSafe v1.3.0 (solc 0.7.6): modules and owners can change the Safe's
 * settings, by having the Safe call its own settings functions.
 *
 * Those calls are low-level `call`s with a symbolic target, which the Prover
 * cannot resolve, and by default it assumes an unresolved call leaves the
 * calling contract's own storage alone. So the DISPATCH declarations below
 * route that call to the matching settings function on the Safe, which is
 * what happens on chain when `to` is the Safe itself. Kept in its own conf so
 * the rules in executionPaths.spec keep the default call handling.
 */

methods {
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function guardAddress() external returns (address) envfree;
    function fallbackHandlerSlotWord() external returns (uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;

    // The signature check passes, as in executionPaths.spec.
    function checkSignatures(bytes32, bytes memory, bytes memory) internal => NONDET;

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

    unresolved external in GnosisSafeHarness.execTransactionFromModuleReturnData(address, uint256, bytes, Enum.Operation) => DISPATCH [
        GnosisSafeHarness.enableModule(address),
        GnosisSafeHarness.disableModule(address, address),
        GnosisSafeHarness.addOwnerWithThreshold(address, uint256),
        GnosisSafeHarness.removeOwner(address, address, uint256),
        GnosisSafeHarness.swapOwner(address, address, address),
        GnosisSafeHarness.changeThreshold(uint256),
        GnosisSafeHarness.setGuard(address),
        GnosisSafeHarness.setFallbackHandler(address)
    ] default HAVOC_ECF;

    unresolved external in GnosisSafeHarness.execTransaction(
        address, uint256, bytes, Enum.Operation, uint256, uint256, uint256, address, address, bytes
    ) => DISPATCH [
        GnosisSafeHarness.enableModule(address),
        GnosisSafeHarness.disableModule(address, address),
        GnosisSafeHarness.addOwnerWithThreshold(address, uint256),
        GnosisSafeHarness.removeOwner(address, address, uint256),
        GnosisSafeHarness.swapOwner(address, address, address),
        GnosisSafeHarness.changeThreshold(uint256),
        GnosisSafeHarness.setGuard(address),
        GnosisSafeHarness.setFallbackHandler(address)
    ] default HAVOC_ECF;

    // Every other call the Safe makes, fallback()'s call to its handler
    // included, is routed the same way whatever its target: as if the target
    // were the Safe. That can only add ways for a setting to change.
    unresolved external in GnosisSafeHarness._ => DISPATCH [
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

definition isExecTransaction(method f) returns bool =
    f.selector == sig:execTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes
    ).selector;

definition isModuleExec(method f) returns bool =
    f.selector == sig:execTransactionFromModule(address, uint256, bytes, Enum.Operation).selector ||
    f.selector == sig:execTransactionFromModuleReturnData(address, uint256, bytes, Enum.Operation).selector;

definition isSelfOnlySetting(method f) returns bool =
    f.selector == sig:enableModule(address).selector ||
    f.selector == sig:disableModule(address, address).selector ||
    f.selector == sig:addOwnerWithThreshold(address, uint256).selector ||
    f.selector == sig:removeOwner(address, address, uint256).selector ||
    f.selector == sig:swapOwner(address, address, address).selector ||
    f.selector == sig:changeThreshold(uint256).selector ||
    f.selector == sig:setGuard(address).selector ||
    f.selector == sig:setFallbackHandler(address).selector;

/*
 * A module can change each setting: for each of the eight settings functions,
 * a module's execTransactionFromModule addressed to the Safe, with a call to
 * that function, succeeds and a setting changes. `f` only picks which
 * function's selector the call carries; the call itself goes through the
 * module transaction.
 */
rule moduleCanChangeSettings(method f, bytes data, address a)
    filtered { f -> isSelfOnlySetting(f) }
{
    env e;
    require thresholdValue() > 0;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;
    require selectorOf(data) == f.selector;

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    address guardBefore = guardAddress();
    uint256 handlerBefore = fallbackHandlerSlotWord();

    execTransactionFromModule@withrevert(e, currentContract, 0, data, Enum.Operation.Call);

    satisfy !lastReverted && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != guardBefore ||
        fallbackHandlerSlotWord() != handlerBefore),
        "a module transaction cannot use this settings function to change the Safe's settings";
}

/* The same through the module's other entry point, execTransactionFromModuleReturnData. */
rule moduleCanChangeSettingsWithReturnData(method f, bytes data, address a)
    filtered { f -> isSelfOnlySetting(f) }
{
    env e;
    require thresholdValue() > 0;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;
    require selectorOf(data) == f.selector;

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    address guardBefore = guardAddress();
    uint256 handlerBefore = fallbackHandlerSlotWord();

    execTransactionFromModuleReturnData@withrevert(e, currentContract, 0, data, Enum.Operation.Call);

    satisfy !lastReverted && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != guardBefore ||
        fallbackHandlerSlotWord() != handlerBefore),
        "a module transaction through execTransactionFromModuleReturnData cannot use this settings function to change the Safe's settings";
}

/*
 * Owners can change each setting: the same through execTransaction, once the
 * threshold is passed. No guard and gasPrice 0, as in ownersCanMakeTheSafeAct.
 */
rule ownersCanChangeSettings(
    method f, bytes data, address a, uint256 safeTxGas, uint256 baseGas,
    address gasToken, address refundReceiver, bytes signatures
)
    filtered { f -> isSelfOnlySetting(f) }
{
    env e;
    require thresholdValue() > 0;
    require guardAddress() == 0;
    require selectorOf(data) == f.selector;

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    uint256 handlerBefore = fallbackHandlerSlotWord();

    execTransaction@withrevert(e,
        currentContract, 0, data, Enum.Operation.Call, safeTxGas, baseGas, 0, gasToken, refundReceiver, signatures);

    satisfy !lastReverted && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != 0 ||
        fallbackHandlerSlotWord() != handlerBefore),
        "an owner transaction cannot use this settings function to change the Safe's settings";
}


/*
 * The Safe's settings only change through a module transaction from an
 * enabled module or through execTransaction (which needs the owners'
 * signatures, SE-5 and SE-12). Over every write function, fallback included.
 * The Safe's calls to itself run the real settings functions (DISPATCH above);
 * any other call it makes is routed the same way, as if it went to the Safe,
 * so a fallback handler is treated as the Safe itself. The caller is never the
 * Safe itself: a call the Safe makes to itself starts inside one of these
 * functions and is covered there.
 */
rule settingsOnlyChangeThroughAModuleOrOwners(method f, calldataarg args, address a)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    require thresholdValue() > 0;
    require e.msg.sender != currentContract;
    bool senderWasModule = e.msg.sender != SENTINEL() && moduleEntry(e.msg.sender) != 0;

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    address guardBefore = guardAddress();
    uint256 handlerBefore = fallbackHandlerSlotWord();

    f@withrevert(e, args);

    bool changed = !lastReverted && (
        thresholdValue() != thresholdBefore ||
        ownerEntry(a) != ownerBefore ||
        moduleEntry(a) != moduleBefore ||
        guardAddress() != guardBefore ||
        fallbackHandlerSlotWord() != handlerBefore);

    assert changed => ((isModuleExec(f) && senderWasModule) || isExecTransaction(f)),
        "a setting changed through something other than an enabled module's transaction or execTransaction";
}
