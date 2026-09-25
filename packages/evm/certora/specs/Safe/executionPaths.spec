/*
 * Property: with no modules and no fallback handler, execTransaction is the
 * only way to make a Safe act.
 *
 * The scene is GnosisSafe v1.3.0 itself, inherited unmodified by
 * certora/harness/GnosisSafeHarness.sol, which adds view getters and no logic.
 * v1.3.0 is the version of the Proposer Safe and the Ownerless Safe.
 *
 * A Safe "acts" when it makes an outgoing CALL or DELEGATECALL: that is how
 * it moves funds, calls a protocol contract, or runs a delegatecall payload.
 * STATICCALL is left out on purpose: it cannot change state, and it is what
 * checkSignatures uses to ask a contract owner about its signature.
 *
 * A Safe has three ways to act:
 *   execTransaction                     needs owner signatures up to the threshold
 *   execTransactionFromModule(ReturnData) needs the caller to be an enabled module
 *   fallback()                          forwards to the fallback handler, if one is set
 * These rules close the last two and show nothing else exists.
 *
 * Rules:
 *
 *   onlyExecTransactionMakesTheSafeAct  over every function except
 *                                       execTransaction: a call that succeeds,
 *                                       from anyone who is not an enabled
 *                                       module, with no fallback handler set,
 *                                       makes the Safe perform no CALL or
 *                                       DELEGATECALL
 *   onlyExecTransactionChangesSettings  under the same conditions, no other
 *                                       function changes the Safe's owners,
 *                                       threshold, modules, guard or
 *                                       fallback handler
 *   enabledModuleCanMakeTheSafeAct      witness: an enabled module can, so
 *                                       the call hook is live and the
 *                                       "no modules" condition is doing work
 *
 * Why settings follow from calls. Every settings function is `authorized`
 * (SelfAuthorized.sol): it requires msg.sender to be the Safe itself. The
 * only way for the Safe to call itself is an outgoing CALL, which the first
 * rule shows only execTransaction makes.
 *
 * Deliberately NOT claimed here:
 *   - That execTransaction checks signatures correctly. That is checkNSignatures
 *     (GnosisSafe.sol:240), audited and formally verified by the Safe team;
 *     this file shows only that there is no way around it.
 *   - Anything about the deployed Safes' settings. "No modules" and "no
 *     fallback handler" are checked on chain (G1.5, G1.6, and the Proposer
 *     Safe's cleared handler), not proved here.
 *   - The guard. A guard can only add reverts to execTransaction; it opens no
 *     new way to act.
 *
 * Modelling notes.
 *   - "Not an enabled module" is the exact check execTransactionFromModule
 *     makes (ModuleManager.sol:68): msg.sender != SENTINEL_MODULES and
 *     modules[msg.sender] == 0.
 *   - threshold > 0 stands for "the Safe has been set up". setup() requires
 *     threshold == 0 (OwnerManager.sol:31), so this is what closes it.
 *   - The caller is not the Safe itself. The Safe calling itself is exactly
 *     what execTransaction does to change settings.
 *   - Storage splitting is disabled in the conf. The Safe reads its fallback
 *     handler and guard with inline-assembly sloads of fixed slots
 *     (FallbackManager.sol:33, GuardManager.sol:44). With splitting on, the
 *     Prover modelled the harness getter's read and fallback()'s read of the
 *     same slot as different values, so `fallbackHandlerAddress() == 0` did
 *     not reach fallback() and the rule failed on a handler that could not
 *     exist. With one storage map, both reads see the same value.
 *   - requiredTxGas and simulateAndRevert do execute a call or delegatecall,
 *     but always revert afterwards, so nothing they do survives. The rules
 *     assert only about calls that succeed.
 */

methods {
    function moduleEntry(address) external returns (address) envfree;
    function ownerEntry(address) external returns (address) envfree;
    function thresholdValue() external returns (uint256) envfree;
    function guardAddress() external returns (address) envfree;
    function fallbackHandlerAddress() external returns (address) envfree;
}

/// ModuleManager.sol:16 / OwnerManager.sol:13 — `address internal constant`.
definition SENTINEL() returns address = 0x1;

definition isExecTransaction(method f) returns bool =
    f.selector == sig:execTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes
    ).selector;

/*
 * Set when the Safe makes an outgoing CALL or DELEGATECALL.
 */
ghost bool safeActed;

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    safeActed = true;
}

hook DELEGATECALL(uint g, address addr, uint argsOffset, uint argsLength,
                  uint retOffset, uint retLength) uint rc {
    safeActed = true;
}

/// The conditions the deployed Safes are in, for a caller who is not an owner
/// signing through execTransaction.
function noModuleNoFallback(env e) {
    require thresholdValue() > 0;
    require e.msg.sender != currentContract;
    require e.msg.sender == SENTINEL() || moduleEntry(e.msg.sender) == 0;
    require fallbackHandlerAddress() == 0;
}

/* ------------------------------------------------------------------------
 * 1. Only execTransaction makes the Safe act
 * --------------------------------------------------------------------- */

rule onlyExecTransactionMakesTheSafeAct(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isExecTransaction(f) }
{
    env e;
    noModuleNoFallback(e);
    require !safeActed;

    f@withrevert(e, args);

    assert !lastReverted => !safeActed,
        "a function other than execTransaction made the Safe perform a call or delegatecall";
}

/* ------------------------------------------------------------------------
 * 2. Only execTransaction changes the Safe's settings
 * --------------------------------------------------------------------- */

rule onlyExecTransactionChangesSettings(method f, calldataarg args, address a)
    filtered { f -> !f.isView && !f.isPure && !isExecTransaction(f) }
{
    env e;
    noModuleNoFallback(e);

    uint256 thresholdBefore = thresholdValue();
    address ownerBefore = ownerEntry(a);
    address moduleBefore = moduleEntry(a);
    address guardBefore = guardAddress();

    f@withrevert(e, args);
    bool succeeded = !lastReverted;

    assert succeeded => thresholdValue() == thresholdBefore,
        "a function other than execTransaction changed the threshold";
    assert succeeded => ownerEntry(a) == ownerBefore,
        "a function other than execTransaction changed the owners";
    assert succeeded => moduleEntry(a) == moduleBefore,
        "a function other than execTransaction changed the modules";
    assert succeeded => guardAddress() == guardBefore,
        "a function other than execTransaction changed the guard";
    assert succeeded => fallbackHandlerAddress() == 0,
        "a function other than execTransaction set a fallback handler";
}

/* ------------------------------------------------------------------------
 * 3. Witness: the module path is real
 * --------------------------------------------------------------------- */

/*
 * An enabled module can make the Safe act. This shows the call hook fires, so
 * rule 1 is not green because the hook is dead, and it shows the "no modules"
 * condition is what closes this path.
 */
rule enabledModuleCanMakeTheSafeAct(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require e.msg.sender != SENTINEL();
    require moduleEntry(e.msg.sender) != 0;
    require !safeActed;

    execTransactionFromModule@withrevert(e, to, value, data, operation);

    satisfy !lastReverted && safeActed,
        "an enabled module cannot make the Safe act, so the call hook is not live";
}
