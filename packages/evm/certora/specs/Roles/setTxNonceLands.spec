/*
 * The Governor's setTxNonce lands on the Delay exactly when the Delay would
 * accept it. In range, with the Roles Modifier's target owning the Delay, the
 * call completes and txNonce becomes n; out of range, or with a target that
 * does not own the Delay, txNonce does not move.
 *
 * `target` is ForwardingAvatar, a stand-in for the DelayOwnerSafe's module
 * path that forwards to the Delay (DelayTarget). SetTxNonceGuard and role 1's
 * configuration are both installed, as in setTxNonceGuardAndRoleConfig.spec.
 */

using SetTxNonceGuard as setTxNonceGuardContract;
using ForwardingAvatar as avatarContract;
using DelayTarget as delayMod;

methods {
    function memberOf(uint16, address) external returns (bool) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForSelector(uint16, address, uint32) external returns (uint256) envfree;
    function unpackFunctionOptions(uint256) external returns (RolesHarness.ExecutionOptions, bool, uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;
    function pluckStaticUintAt(bytes, uint256) external returns (uint256) envfree;
    function multisend() external returns (address) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;
    function owner() external returns (address) envfree;
    function defaultRoles(address) external returns (uint16) envfree;

    function setTxNonceGuardContract.delay() external returns (address) envfree;
    function avatarContract.modules(address) external returns (address) envfree;
    function avatarContract.delay() external returns (address) envfree;
    function delayMod.owner() external returns (address) envfree;
    function delayMod.txNonce() external returns (uint256) envfree;
    function delayMod.queueNonce() external returns (uint256) envfree;

    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);

    unresolved external in ForwardingAvatar.execTransactionFromModule(
        address, uint256, bytes, Enum.Operation
    ) => DISPATCH [
        DelayTarget.setTxNonce(uint256)
    ] default HAVOC_ALL;
}

definition ROLE() returns uint16 = 1;
definition SENTINEL_MODULES() returns address = 0x1;

/*
 * Both gates, role 1's configuration and a setTxNonce(n) calldata. Each rule
 * pins the Delay's owner.
 */
function governorWiredToDelay(env e, address governor, bytes data) {
    // SetTxNonceGuard installed and pinned to this Delay.
    require guard() == setTxNonceGuardContract;
    require setTxNonceGuardContract.delay() == delayMod;

    // Three distinct contracts on the path, and the module already set up.
    require target() == avatarContract;
    require delayMod != currentContract;
    require delayMod != multisend();
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();

    // ForwardingAvatar's typed setTxNonce path is keyed on its linked Delay.
    require avatarContract.delay() == delayMod;

    // The DelayOwnerSafe has the Roles Modifier enabled as a module.
    require currentContract != SENTINEL_MODULES();
    require avatarContract.modules(currentContract) != 0;

    // scopeTarget(1, delay) and scopeAllowFunction(1, delay, setTxNonce, None).
    require clearanceOf(ROLE(), delayMod) == RolesHarness.Clearance.Function;
    require selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector;
    require data.length == 36;
    require functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data)) != 0;
    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length =
        unpackFunctionOptions(
            functionScopeConfigForSelector(ROLE(), delayMod, selectorOf(data))
        );
    require options == RolesHarness.ExecutionOptions.None;
    require isWildcarded;

    // assignRoles(governor, [1], [true]).
    require moduleEntry(governor) != 0;
    require memberOf(ROLE(), governor);
    require defaultRoles(governor) == ROLE();
    require governor != owner();

    require e.msg.sender == governor;
    require e.msg.value == 0;
}

/*
 * For every nonce the Delay accepts from its owner, the Governor's call
 * completes, with shouldRevert set, and the Delay then holds that nonce. The
 * queue does not move.
 */
rule governorSetTxNonceLandsWhenDelayAccepts(bytes data) {
    env e;
    address governor;
    governorWiredToDelay(e, governor, data);
    require delayMod.owner() == target();

    uint256 n = pluckStaticUintAt(data, 0);
    uint256 txNonceBefore = delayMod.txNonce();
    uint256 queueNonceBefore = delayMod.queueNonce();
    require txNonceBefore < n && n <= queueNonceBefore;

    execTransactionWithRole@withrevert(
        e, delayMod, 0, data, Enum.Operation.Call, ROLE(), true
    );

    assert !lastReverted,
        "the Governor's in-range setTxNonce did not complete";
    assert delayMod.txNonce() == n,
        "the Governor's setTxNonce completed but the Delay does not hold the new nonce";
    assert delayMod.queueNonce() == queueNonceBefore,
        "the Governor's setTxNonce moved the Delay's queue";
}

/*
 * A nonce the Delay refuses does not land, and the refusal reaches the
 * caller: a revert when shouldRevert is set, `false` otherwise.
 */
rule governorSetTxNonceOutsideDelayBoundsDoesNotLand(bytes data, bool shouldRevert) {
    env e;
    address governor;
    governorWiredToDelay(e, governor, data);
    require delayMod.owner() == target();

    uint256 n = pluckStaticUintAt(data, 0);
    uint256 txNonceBefore = delayMod.txNonce();
    require n <= txNonceBefore || n > delayMod.queueNonce();

    bool ok = execTransactionWithRole@withrevert(
        e, delayMod, 0, data, Enum.Operation.Call, ROLE(), shouldRevert
    );
    bool reverted = lastReverted;

    assert delayMod.txNonce() == txNonceBefore,
        "a setTxNonce the Delay should refuse moved txNonce";
    assert shouldRevert => reverted,
        "a refused setTxNonce did not revert although the Governor asked it to";
    assert !reverted => !ok,
        "a refused setTxNonce was reported to the Governor as successful";
}

/*
 * If the Roles Modifier's target does not own the Delay, nothing the Governor
 * sends moves txNonce.
 */
rule setTxNonceDoesNotLandUnlessTargetOwnsDelay(bytes data, bool shouldRevert) {
    env e;
    address governor;
    governorWiredToDelay(e, governor, data);
    require delayMod.owner() != target();

    uint256 txNonceBefore = delayMod.txNonce();

    execTransactionWithRole@withrevert(
        e, delayMod, 0, data, Enum.Operation.Call, ROLE(), shouldRevert
    );

    assert delayMod.txNonce() == txNonceBefore,
        "setTxNonce landed although Roles' target does not own the Delay";
}
