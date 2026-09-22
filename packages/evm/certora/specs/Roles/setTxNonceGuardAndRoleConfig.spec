/*
 * Property 1 — SetTxNonceGuard AND the setTxNonce role configuration: in the
 * full governance setup, setTxNonce on the Delay is the only call the
 * Governor can get through the Roles module.
 *
 * "The guard" in this file always means SetTxNonceGuard, installed on the
 * Roles module. PauseGuard, installed on the Delay, is not in this
 * scene and nothing here says anything about it.
 *
 * The setup being modelled, branch 2 of the governance design:
 *
 *     Governor --module of--> Roles (+ SetTxNonceGuard)
 *                                |  target
 *                                v
 *                        Delay-owner Safe (9/9) --owner of--> Delay
 *
 * The Governor is an enabled module on Roles and a member of role 1. Role 1
 * is scoped (Clearance.Function) on the Delay with only setTxNonce allowed.
 * SetTxNonceGuard is installed via setGuard and pinned to that same Delay.
 * Both gates are active here; the two companion files take them apart:
 * setTxNonceGuardSufficient.spec keeps only the guard,
 * setTxNonceRoleConfigSufficient.spec keeps only the role configuration.
 *
 * "Only successful call" is stated at the Roles boundary, on the arguments
 * the module would hand to IAvatar.execTransactionFromModule. That is where
 * both gates act, and it is the strongest place to state it: whatever the
 * Safe and the Delay then do, they are handed nothing but
 * setTxNonce(uint256), value 0, Enum.Operation.Call, addressed to the Delay.
 *
 * Deliberately NOT claimed here:
 *   - Anything about Delay.sol as deployed. DelayTarget is in the scene only
 *     so `sig:DelayTarget.setTxNonce(uint256).selector` names the selector by
 *     signature instead of by the magic number 0x46ba2307; no rule calls into
 *     it. See the provenance notes at the top of certora/helpers/DelayTarget.sol.
 *   - That the setTxNonce which arrives is ACCEPTED. Delay.setTxNonce is
 *     onlyOwner and carries its own require()s on the nonce value; a rejected
 *     call comes back as success == false through the Safe rather than as a
 *     revert. governorExecTransactionWithRoleLimitedToDelaySetTxNonce bounds what is
 *     attempted, not what lands.
 *   - Anything about the 9/9 Safe's own signed transactions. The Safe owners
 *     retain every power they had; this is about the module path only.
 *
 * Modelling note. `target` is linked to DummyAvatar (always succeeds, never
 * reverts) so the avatar contributes no revert behaviour of its own and the
 * guard plus Permissions.check are the only things that can reject a call.
 * The IGuard hooks are resolved by DISPATCHER rather than by linking
 * RolesHarness:guard, so that `guard() == 0` stays expressible — the
 * companion spec setTxNonceRoleConfigSufficient.spec needs exactly that, and keeping
 * the two scenes identical makes the three results comparable.
 */

using SetTxNonceGuard as setTxNonceGuardContract;
using DelayTarget as delayMod;

methods {
    function memberOf(uint16, address) external returns (bool) envfree;
    function moduleEntry(address) external returns (address) envfree;
    function clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function functionScopeConfigForData(uint16, address, bytes) external returns (uint256) envfree;
    function unpackFunctionOptions(uint256) external returns (RolesHarness.ExecutionOptions, bool, uint256) envfree;
    function selectorOf(bytes) external returns (uint32) envfree;
    function multisend() external returns (address) envfree;
    function guard() external returns (address) envfree;
    function target() external returns (address) envfree;
    function avatar() external returns (address) envfree;
    function owner() external returns (address) envfree;
    function defaultRoles(address) external returns (uint16) envfree;

    function setTxNonceGuardContract.delay() external returns (address) envfree;

    // Module.exec / execAndReturnData call these on `guard` when it is set.
    // Resolved against the scene; SetTxNonceGuard is the only implementor.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);
}

definition ROLE() returns uint16 = 1;
definition SENTINEL_MODULES() returns address = 0x1;

/*
 * The wiring half of the deployment: who the Governor is, and that the guard
 * is installed and pinned to the Delay. Nothing here mentions roles[] scoping.
 */
function governorWiredWithSetTxNonceGuard(env e, address governor) {
    require guard() == setTxNonceGuardContract;              // Roles.setGuard
    require setTxNonceGuardContract.delay() == delayMod;     // guard pinned to this Delay
    require delayMod != currentContract;
    require target() != currentContract;

    // The three parties on the veto path are three distinct contracts: the
    // Roles module, the Delay-owner Safe it routes through, and the Delay.
    //
    // target() != delayMod is already true in this scene — the Prover assumes
    // distinct contracts have distinct addresses — but it holds by accident
    // of the scene rather than because anything states it, so it is written
    // out here to survive a future scene where the Delay is not its own
    // contract.
    require target() != delayMod;

    // Roles' admin and Roles' execution route are two different Safes in this
    // deployment:
    //
    //   owner == avatar == the Safe that administers the Roles module
    //   target          == the Delay-owner Safe (9/9), which owns the Delay
    //
    // so avatar() != target() follows. target is the one that matters for the
    // veto: Module.exec calls IAvatar(target).execTransactionFromModule, so
    // target is the contract that ends up calling Delay.setTxNonce, and
    // Delay.owner has to be target for that call to land.
    //
    // avatar is written by setUp/setAvatar and read nowhere on the execution
    // path (Module.sol reads only `target` in exec/execAndReturnData), so
    // avatar() == owner() documents the deployment rather than constraining
    // anything below.
    //
    // NOTE: neither line says anything about branch 1. The Term DAO is the
    // DELAY's avatar, not this module's, and is not in this scene; proving
    // Delay-owner Safe != Term DAO needs branch 1 modelled.
    //
    // Both narrow the states explored, so both weaken every rule below. Drop
    // them if the rules verify without them.
    require avatar() == owner();
    require target() != owner();

    // The module has already been set up. The Prover does not run
    // constructors, so without this the starting state is a module that was
    // never initialized and setUp is callable by anyone — which is a real
    // property of an undeployed proxy, but not of the instance under audit.
    //
    // Stated through setupModules' self-link (Roles.sol:56-59) rather than
    // through OZ's `_initialized`, which is private and unreadable from the
    // harness. It is also the sounder of the two: setUp carries NO
    // initializer modifier of its own, so its re-entry protection is
    // secondhand — __Ownable_init()'s `initializer` (OZ 4.3.1) and this
    // assert. The assert fires whatever `_initialized` happens to be.
    require moduleEntry(SENTINEL_MODULES()) == SENTINEL_MODULES();

    require moduleEntry(governor) != 0;            // assignRoles enabled it
    require memberOf(ROLE(), governor);
    require defaultRoles(governor) == ROLE();

    // The Governor does not own the Roles module. If it did it could call
    // setGuard(0) and scopeTarget itself, and none of this would hold.
    require governor != owner();

    require e.msg.sender == governor;
    require e.msg.value == 0;
}

/*
 * The configuration half (runbook steps 2, 3 and 4).
 *
 * `to`, `role` and `data` must be the very arguments the rule then executes
 * with. The Prover chooses them when it hunts for a counterexample, so
 * binding storage to that same choice is what makes these pointwise requires
 * equivalent to the global statements they stand for: "no target other than
 * the Delay has clearance", "nothing but setTxNonce is allowed on the Delay",
 * "the Governor belongs to no role but role 1". Passing variables the rule
 * does not go on to use would leave the Prover free to satisfy the
 * implications vacuously, constraining nothing.
 */
function setTxNonceRoleConfigPinned(address governor, address to, uint16 role, bytes data) {
    require clearanceOf(ROLE(), delayMod) == RolesHarness.Clearance.Function;
    require to != delayMod => clearanceOf(role, to) == RolesHarness.Clearance.None;
    // The function-scope pin (runbook step 3, "nothing but setTxNonce is
    // allowed on the Delay") is deliberately ABSENT here.
    //
    // Stating it as
    //     require selectorOf(data) != sig:DelayTarget.setTxNonce(uint256).selector
    //         => functionScopeConfigForData(role, delayMod, data) == 0;
    // made all four governorExec rules below report counterexamples in which
    // to, value, operation AND the selector were simultaneously unconstrained
    // -- i.e. the OTHER pins in this predicate stopped binding too. That is not
    // possible for a sound require: adding one can only remove states, and the
    // same four conclusions verify with FEWER assumptions in
    // setTxNonceGuardSufficient.spec, whose preconditions this predicate is a
    // superset of. Calling functionScopeConfigForData inside a require is the
    // trigger; bisected against -bisectA (require removed) and -bisectB (same
    // pin expressed without that getter), both of which verify.
    //
    // Dropping it is sound here because it strengthens the result: these rules
    // now bound execution using only the clearance and membership pins. The
    // pin IS load-bearing in setTxNonceRoleConfigSufficient.spec, where no
    // guard is installed -- see the bisect alongside it.
    require role != ROLE() => !memberOf(role, governor);
}

/*
 * The Governor cannot reach any entry point other than the four execution
 * ones. Everything else on Roles is onlyOwner, and setUp is spent once the
 * module has been set up — see the note in governorWiredWithSetTxNonceGuard, which is what
 * closes it.
 *
 * Filtered to non-view methods: the harness getters are external views that
 * of course succeed, and they perform no transaction.
 */
rule governorSucceedsOnlyThroughRolesExecEntryPoints(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);

    f@withrevert(e, args);

    assert !lastReverted => (
        f.selector == sig:execTransactionFromModule(address,uint256,bytes,Enum.Operation).selector ||
        f.selector == sig:execTransactionFromModuleReturnData(address,uint256,bytes,Enum.Operation).selector ||
        f.selector == sig:execTransactionWithRole(address,uint256,bytes,Enum.Operation,uint16,bool).selector ||
        f.selector == sig:execTransactionWithRoleReturnData(address,uint256,bytes,Enum.Operation,uint16,bool).selector
    ), "the Governor got through a Roles entry point other than the four execution ones";
}

/*
 * THE property, on the entry point that names its role explicitly.
 */
rule governorExecTransactionWithRoleLimitedToDelaySetTxNonce(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, to, role, data);

    execTransactionWithRole@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the Governor completed a call that was not setTxNonce on the Delay";
}

/*
 * Same, via the default-role entry point. Roles reads
 * roles[defaultRoles[msg.sender]] rather than a caller-supplied role, so this
 * covers the case where the Governor never names a role at all.
 */
rule governorExecTransactionFromModuleLimitedToDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, to, ROLE(), data);

    execTransactionFromModule@withrevert(e, to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the Governor completed a non-setTxNonce call through its default role";
}

/*
 * The ReturnData variants route through execAndReturnData rather than exec.
 * Same guard hooks, same Permissions.check, asserted separately so a future
 * divergence between the two Module paths cannot hide.
 */
rule governorExecTransactionWithRoleReturnDataLimitedToDelaySetTxNonce(
    address to, uint256 value, bytes data,
    Enum.Operation operation, uint16 role, bool shouldRevert
) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, to, role, data);

    execTransactionWithRoleReturnData@withrevert(e, to, value, data, operation, role, shouldRevert);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the Governor completed a non-setTxNonce call through the ReturnData path";
}

/*
 * The fourth and last execution entry point: the default role AND
 * execAndReturnData. The four entry points are the 2x2 of {caller-named role,
 * defaultRoles[msg.sender]} x {exec, execAndReturnData}; the three rules above
 * cover the other three corners. This one is not implied by any of them —
 * it reads defaultRoles like execTransactionFromModule and routes through
 * execAndReturnData like the rule above — and governorSucceedsOnlyThroughRolesExecEntryPoints
 * names its selector as reachable by the Governor, so leaving it unbounded
 * would leave a reachable path unproved.
 */
rule governorExecTransactionFromModuleReturnDataLimitedToDelaySetTxNonce(
    address to, uint256 value, bytes data, Enum.Operation operation
) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, to, ROLE(), data);

    execTransactionFromModuleReturnData@withrevert(e, to, value, data, operation);

    assert !lastReverted => (
        to == delayMod &&
        value == 0 &&
        operation == Enum.Operation.Call &&
        selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector
    ), "the Governor completed a non-setTxNonce call through the default-role ReturnData path";
}

/*
 * Non-vacuity. Every rule above is an implication with `!lastReverted` on the
 * left, so all of them would hold trivially in a configuration where the
 * Governor can do nothing at all. This witness shows the intended call really
 * does go through, which is what makes the others meaningful.
 */
rule governorCanStillCallDelaySetTxNonce(bytes data, uint256 scopeConfig) {
    env e;
    address governor;
    governorWiredWithSetTxNonceGuard(e, governor);
    setTxNonceRoleConfigPinned(governor, delayMod, ROLE(), data);

    require selectorOf(data) == sig:DelayTarget.setTxNonce(uint256).selector;
    require data.length == 36;

    // The function really is allowed: wildcarded, no Send, no DelegateCall.
    require functionScopeConfigForData(ROLE(), delayMod, data) == scopeConfig;
    require scopeConfig != 0;
    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length = unpackFunctionOptions(scopeConfig);
    require isWildcarded;
    require options == RolesHarness.ExecutionOptions.None;
    require delayMod != multisend();

    execTransactionWithRole(e, delayMod, 0, data, Enum.Operation.Call, ROLE(), true);

    satisfy true, "the configured setTxNonce call is not reachable at all, so the bounding rules are vacuous";
}
