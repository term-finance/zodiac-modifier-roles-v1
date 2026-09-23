/*
 * Property 1, continued — the setTxNonce that gets out of Roles LANDS on the
 * Delay exactly when the Delay would accept it.
 *
 * 1.1 bounds what the Governor can attempt, at the Roles boundary: the
 * arguments handed to IAvatar(target).execTransactionFromModule. Every other
 * Roles scene links `target` to DummyAvatar, which returns true and forwards
 * nothing, so none of them can say whether the call then does anything. This
 * scene closes that gap. `target` is ForwardingAvatar, which forwards the way
 * the DelayOwnerSafe's module path does (ModuleManager.sol:61-73 over
 * Executor.execute), and the Delay is in scene as DelayTarget, so the rules
 * below observe the Delay's own state after a Governor call.
 *
 * The chain being followed:
 *
 *     Governor --execTransactionWithRole--> Roles (+ SetTxNonceGuard)
 *        --exec--> ForwardingAvatar (DelayOwnerSafe) --call--> Delay.setTxNonce
 *
 * Delay.setTxNonce (DelayTarget.sol, vendored from Delay.sol:114-122) accepts
 * only from its owner, and only a nonce with txNonce < n <= queueNonce. The
 * three rules pin down both sides of that:
 *
 *   1.4  in range, owner wired     -> the call completes and txNonce == n
 *   1.5  out of range              -> txNonce unchanged, and the rejection
 *                                     surfaces: a revert under shouldRevert,
 *                                     `false` otherwise
 *   1.6  target does not own Delay -> txNonce unchanged
 *
 * Wiring and configuration are the runbook's, as in
 * setTxNonceGuardAndRoleConfig.spec, with both gates installed.
 *
 * Modelling note. ForwardingAvatar forwards a plain Call of setTxNonce to
 * its linked Delay as a typed call, resolved statically through the
 * `ForwardingAvatar:delay` link; see the deviation note in
 * helpers/ForwardingAvatar.sol for why the low-level path could not be used.
 * Every other forward is Executor's low-level `call`, resolved with
 * `unresolved external ... => DISPATCH` defaulting to HAVOC_ALL, so an
 * unresolved call can only widen what the Prover explores, never narrow it.
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
 * Both gates, the runbook configuration, and a setTxNonce(n) calldata. The
 * Delay's owner is deliberately NOT pinned here: 1.4 and 1.5 pin it to the
 * target, 1.6 pins it away.
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

    // The DelayOwnerSafe has Roles enabled as a module (setup step 4). The
    // Safe's module check also rejects the sentinel itself as a caller
    // (ModuleManager.sol:68), and the Prover is free to place a scene
    // contract at address(0x1) -- the second run of 1.4 did exactly that and
    // failed on GS104 before reaching the Delay. No deployed Roles sits at
    // the sentinel, so ruling it out narrows nothing real.
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
 * 1.4 — THE LIVENESS HALF. For every nonce the Delay would accept from its
 * owner, the Governor's call completes and that nonce is what the Delay now
 * holds. Stated with shouldRevert == true, so "completes" means the inner
 * call really succeeded rather than being swallowed as `false`. Nothing else
 * on the Delay's queue moves.
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
 * 1.5 — THE EXACTNESS HALF. A nonce the Delay would refuse does not land,
 * whatever the Governor asks for, and the refusal is visible to the caller:
 * a revert when it asked for one, `false` otherwise. Nothing is silently
 * reported as done.
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
 * 1.6 — WHY THE OWNER WIRING MATTERS. If the contract at Roles' `target` is
 * not the Delay's owner, nothing the Governor sends moves txNonce, in range
 * or not. The cancel power is the DelayOwnerSafe's ownership of the Delay;
 * Roles only lets the Governor borrow it.
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
