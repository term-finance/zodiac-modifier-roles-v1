/*
 * Delay Modifier access control and module list.
 *
 * The scene is the real Delay (certora/helpers/Delay.sol) under DelayHarness.
 * `target` is linked to ReenteringAvatar, which calls enableModule back on
 * the Delay whenever the Delay forwards a call to it.
 */

using ReenteringAvatar as hostileAvatar;
using PauseGuard as pauseGuard;

methods {
    function owner() external returns (address) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;
    function avatar() external returns (address) envfree;
    function txNonce() external returns (uint256) envfree;
    function queueNonce() external returns (uint256) envfree;
    function txHash(uint256) external returns (bytes32) envfree;
    function moduleEntry(address) external returns (address) envfree;

    function hostileAvatar.delay() external returns (address) envfree;
    function hostileAvatar.attacker() external returns (address) envfree;
    function hostileAvatar.attempts() external returns (uint256) envfree;
    function hostileAvatar.succeeded() external returns (bool) envfree;

    // Guard calls resolve to PauseGuard, the only guard in the scene.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
    function _.supportsInterface(bytes4) external => DISPATCHER(true);
}

// SENTINEL_MODULES, an internal constant in Modifier.sol.
definition SENTINEL_MODULES() returns address = 0x1;

/* ------------------------------------------------------------------------
 * 1. setUp is spent
 * --------------------------------------------------------------------- */

/*
 * Once the module list is set up, setUp always reverts, so nobody can re-run
 * it to reset the module list or the owner. The parametric rules below
 * exclude setUp; this rule covers it.
 */
rule setUpAlwaysRevertsAfterDeployment(bytes initParams) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();

    setUp@withrevert(e, initParams);

    assert lastReverted,
        "setUp ran a second time, which would reset the module ring and the owner";
}

/* ------------------------------------------------------------------------
 * 2. The module list
 * --------------------------------------------------------------------- */

/*
 * Over every write function except setUp, the module list changes only
 * through enableModule or disableModule, and only when the caller is the
 * owner.
 */
rule modulesOnlyChangeThroughOwnerEnableOrDisable(method f, calldataarg args, address m)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:DelayHarness.setUp(bytes).selector
    }
{
    env e;
    require target() != owner();

    address ownerBefore = owner();
    address entryBefore = moduleEntry(m);

    f(e, args);

    assert moduleEntry(m) != entryBefore =>
        (f.selector == sig:DelayHarness.enableModule(address).selector ||
         f.selector == sig:DelayHarness.disableModule(address,address).selector),
        "an entry point other than enableModule or disableModule changed the module ring";
    assert moduleEntry(m) != entryBefore => e.msg.sender == ownerBefore,
        "a caller other than the owner changed the module ring";
}

/*
 * The owner's enableModule succeeds, so the rule above is not vacuous.
 */
rule ownerCanEnableModule(address m) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require e.msg.sender == owner();
    require m != 0 && m != SENTINEL_MODULES();
    require moduleEntry(m) == 0;

    enableModule@withrevert(e, m);

    assert !lastReverted,
        "the Delay's owner could not enable a module";
}

/* ------------------------------------------------------------------------
 * 3. Who may queue
 * --------------------------------------------------------------------- */

/*
 * Over every write function except setUp, only an enabled module can move the
 * queue nonce or write a queue entry.
 */
rule queueOnlyGrowsThroughEnabledModules(method f, calldataarg args, uint256 n)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:DelayHarness.setUp(bytes).selector
    }
{
    env e;
    uint256 queueNonceBefore = queueNonce();
    bytes32 txHashBefore = txHash(n);

    f(e, args);

    assert queueNonce() != queueNonceBefore => moduleEntry(e.msg.sender) != 0,
        "a caller that is not an enabled module moved the queue nonce";
    assert txHash(n) != txHashBefore => moduleEntry(e.msg.sender) != 0,
        "a caller that is not an enabled module wrote a queue entry";
}

/*
 * An enabled module's execTransactionFromModule succeeds and moves the queue
 * nonce forward by one, so the rule above is not vacuous.
 */
rule enabledModuleCanQueue(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require moduleEntry(e.msg.sender) != 0;

    uint256 queueNonceBefore = queueNonce();
    require queueNonceBefore < max_uint256;

    execTransactionFromModule@withrevert(e, to, value, data, operation);

    assert !lastReverted,
        "an enabled module could not queue a transaction";
    assert to_mathint(queueNonce()) == queueNonceBefore + 1,
        "queueing returned without advancing the queue nonce";
}

/* ------------------------------------------------------------------------
 * 4. The owner and the guard
 * --------------------------------------------------------------------- */

/*
 * Over every write function except setUp, the owner changes only through
 * transferOwnership or renounceOwnership, and only when the caller is the
 * current owner.
 */
rule ownerOnlyChangesThroughOwnableTransfer(method f, calldataarg args)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:DelayHarness.setUp(bytes).selector
    }
{
    env e;
    address ownerBefore = owner();

    f(e, args);

    assert owner() != ownerBefore =>
        (f.selector == sig:DelayHarness.transferOwnership(address).selector ||
         f.selector == sig:DelayHarness.renounceOwnership().selector),
        "an entry point other than transferOwnership or renounceOwnership changed the owner";
    assert owner() != ownerBefore => e.msg.sender == ownerBefore,
        "a caller other than the owner changed the owner";
}

/*
 * Over every write function except setUp, the guard changes only through
 * setGuard, and only when the caller is the owner.
 */
rule guardOnlyChangesThroughOwnerSetGuard(method f, calldataarg args)
    filtered {
        f -> !f.isView && !f.isPure &&
             f.selector != sig:DelayHarness.setUp(bytes).selector
    }
{
    env e;
    address ownerBefore = owner();
    address guardBefore = guard();

    f(e, args);

    assert guard() != guardBefore =>
        f.selector == sig:DelayHarness.setGuard(address).selector,
        "an entry point other than setGuard changed the guard";
    assert guard() != guardBefore => e.msg.sender == ownerBefore,
        "a caller other than the owner changed the guard";
}

// The ten onlyOwner functions.
definition isOnlyOwner(method f) returns bool =
    f.selector == sig:DelayHarness.setTxCooldown(uint256).selector ||
    f.selector == sig:DelayHarness.setTxExpiration(uint256).selector ||
    f.selector == sig:DelayHarness.setTxNonce(uint256).selector ||
    f.selector == sig:DelayHarness.setAvatar(address).selector ||
    f.selector == sig:DelayHarness.setTarget(address).selector ||
    f.selector == sig:DelayHarness.enableModule(address).selector ||
    f.selector == sig:DelayHarness.disableModule(address,address).selector ||
    f.selector == sig:DelayHarness.setGuard(address).selector ||
    f.selector == sig:DelayHarness.transferOwnership(address).selector ||
    f.selector == sig:DelayHarness.renounceOwnership().selector;

/*
 * Each onlyOwner function succeeds only when the caller is the owner, and
 * from the same state no two different callers can both succeed.
 */
rule atMostOneCallerPassesOnlyOwner(method f, calldataarg args)
    filtered { f -> isOnlyOwner(f) }
{
    env ea;
    env eb;
    require ea.msg.sender != eb.msg.sender;

    address ownerBefore = owner();
    storage init = lastStorage;

    f@withrevert(ea, args);
    bool aPassed = !lastReverted;

    f@withrevert(eb, args) at init;
    bool bPassed = !lastReverted;

    assert aPassed => ea.msg.sender == ownerBefore,
        "an onlyOwner entry point admitted a caller other than owner()";
    assert !(aPassed && bPassed),
        "two distinct callers both passed the same onlyOwner entry point from the same state";
}

/*
 * For each onlyOwner function, some call from the owner succeeds, so
 * atMostOneCallerPassesOnlyOwner is not vacuous.
 */
rule ownerCanCallEachDelaySetting(method f, calldataarg args)
    filtered { f -> isOnlyOwner(f) }
{
    env e;
    require e.msg.sender == owner();

    f@withrevert(e, args);

    satisfy !lastReverted,
        "the owner cannot successfully call this onlyOwner function";
}

/* ------------------------------------------------------------------------
 * 5. An execution is not a module grant
 * --------------------------------------------------------------------- */

/*
 * Executing a queue entry cannot enable a module, even when the avatar calls
 * enableModule back on the Delay: that call reverts and the module list is
 * unchanged.
 */
rule executeNextTxCannotEnableModuleThroughTheAvatar(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require target() == hostileAvatar;
    require hostileAvatar.delay() == currentContract;
    require guard() == 0;

    require target() != owner();

    address attacker = hostileAvatar.attacker();
    require attacker != 0 && attacker != SENTINEL_MODULES();
    require moduleEntry(attacker) == 0;
    require !hostileAvatar.succeeded();

    executeNextTx@withrevert(e, to, value, data, operation);

    assert moduleEntry(attacker) == 0,
        "executing a queue entry put an address in the module ring";
    assert !hostileAvatar.succeeded(),
        "the avatar's enableModule call on the Delay returned instead of reverting";
}

/*
 * executeNextTx can succeed with the avatar reached and attempting
 * enableModule, so the rule above is not vacuous.
 */
rule avatarEnableModuleAttemptIsReachable(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require target() == hostileAvatar;
    require hostileAvatar.delay() == currentContract;
    require guard() == 0;

    uint256 attemptsBefore = hostileAvatar.attempts();
    require attemptsBefore < max_uint256;

    executeNextTx(e, to, value, data, operation);

    satisfy hostileAvatar.attempts() > attemptsBefore,
        "no queue entry reaches the avatar at all, so the claim-4 rule is vacuous";
}

/* ------------------------------------------------------------------------
 * 6. Execution and skipping are open to anyone
 * --------------------------------------------------------------------- */

/*
 * Whether executeNextTx or skipExpired succeeds, and what it changes, does
 * not depend on who the caller is: from the same state, block and msg.value,
 * two different callers get the same outcome.
 */
rule anyoneCanExecuteNextTx(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e1;
    env e2;
    require e2.block.timestamp == e1.block.timestamp;
    require e2.block.number == e1.block.number;
    require e2.msg.value == e1.msg.value;
    require target() == hostileAvatar;
    require hostileAvatar.delay() == currentContract;
    require guard() == 0 || guard() == pauseGuard;

    storage init = lastStorage;

    executeNextTx@withrevert(e1, to, value, data, operation);
    bool reverted1 = lastReverted;
    storage after1 = lastStorage;

    executeNextTx@withrevert(e2, to, value, data, operation) at init;
    bool reverted2 = lastReverted;
    storage after2 = lastStorage;

    assert reverted1 == reverted2,
        "executeNextTx succeeded for one caller and reverted for another";
    assert !reverted1 => after1[currentContract] == after2[currentContract],
        "executeNextTx left the Delay in a different state for a different caller";
    assert !reverted1 => after1[hostileAvatar] == after2[hostileAvatar],
        "executeNextTx left the avatar in a different state for a different caller";
}

rule anyoneCanSkipExpired() {
    env e1;
    env e2;
    require e2.block.timestamp == e1.block.timestamp;
    require e2.block.number == e1.block.number;
    require e2.msg.value == e1.msg.value;

    storage init = lastStorage;

    skipExpired@withrevert(e1);
    bool reverted1 = lastReverted;
    storage after1 = lastStorage;

    skipExpired@withrevert(e2) at init;
    bool reverted2 = lastReverted;
    storage after2 = lastStorage;

    assert reverted1 == reverted2,
        "skipExpired succeeded for one caller and reverted for another";
    assert !reverted1 => after1[currentContract] == after2[currentContract],
        "skipExpired left the Delay in a different state for a different caller";
}

/*
 * A caller that is neither the owner nor an enabled module can execute or
 * skip a queue entry, so the two rules above are not vacuous.
 */
rule outsiderCanExecuteNextTx(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require e.msg.sender != owner();
    require moduleEntry(e.msg.sender) == 0;
    require target() == hostileAvatar;
    require hostileAvatar.delay() == currentContract;
    require guard() == 0;

    uint256 nonceBefore = txNonce();

    executeNextTx@withrevert(e, to, value, data, operation);

    satisfy !lastReverted && to_mathint(txNonce()) == nonceBefore + 1,
        "a caller that is neither the owner nor a module cannot execute a queue entry";
}

rule outsiderCanSkipExpired() {
    env e;
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();
    require e.msg.value == 0;
    require e.msg.sender != owner();
    require moduleEntry(e.msg.sender) == 0;

    uint256 nonceBefore = txNonce();

    skipExpired@withrevert(e);

    satisfy !lastReverted && txNonce() > nonceBefore,
        "a caller that is neither the owner nor a module cannot skip an expired entry";
}

/* ------------------------------------------------------------------------
 * 7. Every entry point is accounted for
 * --------------------------------------------------------------------- */

// Together with isOnlyOwner, these make up the Delay's fifteen write
// functions.
definition isQueueing(method f) returns bool =
    f.selector == sig:DelayHarness.execTransactionFromModule(address,uint256,bytes,Enum.Operation).selector ||
    f.selector == sig:DelayHarness.execTransactionFromModuleReturnData(address,uint256,bytes,Enum.Operation).selector;

definition isOpenToAnyone(method f) returns bool =
    f.selector == sig:DelayHarness.executeNextTx(address,uint256,bytes,Enum.Operation).selector ||
    f.selector == sig:DelayHarness.skipExpired().selector;

definition isSetUp(method f) returns bool =
    f.selector == sig:DelayHarness.setUp(bytes).selector;

/*
 * The Delay has no fallback, and its write functions are exactly the fifteen
 * in isOnlyOwner, isQueueing, isOpenToAnyone and isSetUp.
 */
rule delayWriteFunctionsAreTheKnownFifteen(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;

    f(e, args);

    assert !f.isFallback,
        "the Delay has a fallback, which no access rule covers";
    assert isOnlyOwner(f) || isQueueing(f) || isOpenToAnyone(f) || isSetUp(f),
        "the Delay has a write function that no access rule covers";
}

/*
 * Apart from executeNextTx, skipExpired and setUp, a call to any write
 * function succeeds only if the caller is the owner or an enabled module.
 */
rule onlyModulesOrOwnerCanCallDelay(method f, calldataarg args)
    filtered {
        f -> !f.isView && !f.isPure && !isOpenToAnyone(f) && !isSetUp(f)
    }
{
    env e;
    address ownerBefore = owner();
    bool wasModule = moduleEntry(e.msg.sender) != 0;

    f@withrevert(e, args);

    assert !lastReverted => (e.msg.sender == ownerBefore || wasModule),
        "a caller that is neither the owner nor an enabled module successfully called the Delay";
}

/*
 * execTransactionFromModule and execTransactionFromModuleReturnData only
 * succeed for an address in the module ring: moduleOnly (Modifier.sol:59-62)
 * checks modules[msg.sender] before anything else. Mirrors the Roles'
 * onlyEnabledModulesCanExec.
 */
rule onlyEnabledModulesCanCallExecFromModule(method f, calldataarg args)
    filtered { f -> isQueueing(f) }
{
    env e;
    bool senderWasModule = moduleEntry(e.msg.sender) != 0;

    f@withrevert(e, args);

    assert !lastReverted => senderWasModule,
        "a caller that is not an enabled module successfully called execTransactionFromModule";
}

/*
 * An enabled module that is not the owner cannot call setTxNonce: the call
 * always reverts, whatever the nonce.
 */
rule enabledModuleThatIsNotOwnerCannotSetTxNonce(uint256 nonce) {
    env e;
    require e.msg.sender != SENTINEL_MODULES();
    require moduleEntry(e.msg.sender) != 0;
    require e.msg.sender != owner();

    setTxNonce@withrevert(e, nonce);

    assert lastReverted,
        "an enabled module that is not the owner set txNonce";
}

/*
 * The owner's setTxNonce succeeds and sets txNonce, so the rule above does
 * not hold just because setTxNonce always reverts.
 */
rule ownerCanSetTxNonce(uint256 nonce) {
    env e;
    require e.msg.sender == owner();

    setTxNonce@withrevert(e, nonce);

    satisfy !lastReverted && txNonce() == nonce,
        "the owner could not set txNonce";
}
