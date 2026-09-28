/*
 * TermFinanceGovernor: TERM holders can propose the veto, and once it has
 * passed, anyone can execute it and the veto lands on the Delay.
 *
 * The veto is the runbook's proposal: one action, calling the Roles Modifier
 * with execTransactionWithRole(Delay, 0, setTxNonce(n), Call, 1, true).
 *
 * Every contract on the path is the deployed code:
 *   Governor        TermFinanceGovernor 0x2B715634134220ffeEE9458b4e34E41A41418607,
 *                   verified source in certora/vendor/TermFinanceGovernor
 *                   (OpenZeppelin v5.2.0, solc 0.8.20)
 *   TERM            TermToken, the implementation 0xeC222d8AfB8b4E78C418ebc1ab2cA181f19FbadC
 *                   behind the TERM proxy 0xC3d21f79C3120A4fFda7A535f8005a7c297799bF,
 *                   verified source in certora/vendor/TermToken (solc 0.8.20)
 *   Roles Modifier  contracts/Roles.sol, which verify_fv_source.sh ties to
 *                   the deployed mastercopy
 *   guard           contracts/helpers/SetTxNonceGuard.sol
 *   DelayOwnerSafe  Safe v1.4.1 (SafeV141Harness)
 *   Delay           DelayTarget, the vendored Delay v1.0.1 (see its header
 *                   for why the upstream file cannot share a scene with Roles)
 *
 * Modelling notes.
 *   - On chain TERM is an ERC1967 proxy that delegatecalls TermToken. Here
 *     the Governor's token is linked straight to TermToken; the proxy adds
 *     nothing but the delegatecall.
 *   - The Governor's call to its proposal's target and the DelayOwnerSafe's
 *     module call to the Delay are low-level calls to addresses taken from
 *     calldata, which the Prover cannot resolve on its own. The DISPATCH
 *     entries route them to the function they reach on chain. Any other
 *     unresolved call is havoced (HAVOC_ALL), which can only make these
 *     rules harder to pass, never easier.
 *   - The Governor reads TERM through its immutable `_token`, which the conf
 *     links to TermToken. The Prover resolves some of those calls from the
 *     link but not all: the first run left propose's getPastVotes call
 *     unresolved, havoced it to return no data, and the Governor's ABI decoder
 *     reverted. The Governor's DISPATCH list therefore also sends clock,
 *     getPastVotes and getPastTotalSupply to TermToken, where every call
 *     through `_token` lands on chain.
 */

using TermToken as termToken;
using RolesHarness as roles;
using SetTxNonceGuard as setTxNonceGuard;
using SafeV141Harness as delayOwnerSafe;
using DelayTarget as delay;

methods {
    function proposalSnapshot(uint256) external returns (uint256) envfree;
    function proposalDeadline(uint256) external returns (uint256) envfree;
    function proposalProposer(uint256) external returns (address) envfree;
    function proposalThreshold() external returns (uint256) envfree;
    function votingPeriod() external returns (uint256) envfree;
    function vetoProposalId(address, address, uint256, bytes32) external returns (uint256) envfree;
    function descriptionHashOf(string) external returns (bytes32) envfree;
    function descriptionAllowedFor(address, string) external returns (bool) envfree;

    function roles.memberOf(uint16, address) external returns (bool) envfree;
    function roles.moduleEntry(address) external returns (address) envfree;
    function roles.clearanceOf(uint16, address) external returns (RolesHarness.Clearance) envfree;
    function roles.functionScopeConfigForSelector(uint16, address, uint32) external returns (uint256) envfree;
    function roles.unpackFunctionOptions(uint256) external returns (RolesHarness.ExecutionOptions, bool, uint256) envfree;
    function roles.multisend() external returns (address) envfree;
    function roles.guard() external returns (address) envfree;
    function roles.target() external returns (address) envfree;

    function setTxNonceGuard.delay() external returns (address) envfree;
    function delayOwnerSafe.moduleEntry(address) external returns (address) envfree;
    function delay.owner() external returns (address) envfree;
    function delay.txNonce() external returns (uint256) envfree;
    function delay.queueNonce() external returns (uint256) envfree;

    // Roles' exec calls its guard; SetTxNonceGuard is the implementation.
    function _.checkTransaction(
        address, uint256, bytes, Enum.Operation,
        uint256, uint256, uint256, address, address, bytes, address
    ) external => DISPATCHER(true);
    function _.checkAfterExecution(bytes32, bool) external => DISPATCHER(true);

    // The Governor's call to its proposal's target (Governor.sol:447-458),
    // and its reads of TERM through `_token` that the link leaves unresolved
    // (GovernorVotes.sol:35 and :62, TermFinanceGovernor.sol:44).
    unresolved external in TermFinanceGovernorHarness._ => DISPATCH [
        RolesHarness.execTransactionWithRole(address, uint256, bytes, Enum.Operation, uint16, bool),
        TermToken.clock(),
        TermToken.getPastVotes(address, uint256),
        TermToken.getPastTotalSupply(uint256)
    ] default HAVOC_ALL;

    // The DelayOwnerSafe's call to the Delay (Executor.sol, Safe v1.4.1).
    unresolved external in SafeV141Harness._ => DISPATCH [
        DelayTarget.setTxNonce(uint256)
    ] default HAVOC_ALL;
}

/// Head of the module lists on Roles and on the Safe.
definition SENTINEL() returns address = 0x1;

/// The role the veto runs under.
definition ROLE() returns uint16 = 1;

/*
 * The deployed wiring of the veto path, as the runbook sets it up and the
 * verification plan checks it on chain:
 *   - SetTxNonceGuard is Roles' guard and is pointed at this Delay;
 *   - role 1 is scoped to the Delay (scopeTarget) with setTxNonce allowed
 *     and no value or delegatecall (scopeAllowFunction, options None);
 *   - the Governor is an enabled module on Roles and a member of role 1;
 *   - Roles' target is the DelayOwnerSafe, which has Roles as a module and
 *     owns the Delay.
 */
function vetoPathWired() {
    require roles.guard() == setTxNonceGuard;
    require setTxNonceGuard.delay() == delay;

    require roles.target() == delayOwnerSafe;
    require delay != roles;
    require delay != roles.multisend();
    require roles.moduleEntry(SENTINEL()) == SENTINEL();

    require roles.clearanceOf(ROLE(), delay) == RolesHarness.Clearance.Function;
    uint256 scope = roles.functionScopeConfigForSelector(
        ROLE(), delay, sig:DelayTarget.setTxNonce(uint256).selector
    );
    RolesHarness.ExecutionOptions options; bool isWildcarded; uint256 length;
    options, isWildcarded, length = roles.unpackFunctionOptions(scope);
    require options == RolesHarness.ExecutionOptions.None;
    require isWildcarded;

    // The module lists' head 0x1 cannot send transactions; the Prover must
    // not place a scene contract there.
    require currentContract != SENTINEL();
    require roles != SENTINEL();
    require roles.moduleEntry(currentContract) != 0;
    require roles.memberOf(ROLE(), currentContract);

    require delayOwnerSafe.moduleEntry(roles) != 0;
    require delay.owner() == delayOwnerSafe;
}

/*
 * Any address with at least the proposal threshold of TERM votes (1,000 TERM)
 * at clock() - 1 can propose the veto, for any nonce n and any description
 * propose accepts from it, unless that exact proposal already exists. The new
 * proposal records the caller as proposer, and its vote opens at once
 * (votingDelay is 0) and runs for the voting period (22 hours).
 */
rule holderAboveThresholdCanProposeVeto(uint256 n, string proposalText) {
    env e;
    require e.msg.value == 0;
    // TERM's clock is the block timestamp (TermToken.sol:81-83).
    require e.block.timestamp > 0;
    require to_mathint(e.block.timestamp) < 2^48;

    require termToken.getPastVotes(e, e.msg.sender, assert_uint256(e.block.timestamp - 1))
        >= proposalThreshold();
    require descriptionAllowedFor(e.msg.sender, proposalText);

    uint256 id = vetoProposalId(roles, delay, n, descriptionHashOf(proposalText));
    require proposalSnapshot(id) == 0;

    proposeVeto@withrevert(e, roles, delay, n, proposalText);

    assert !lastReverted,
        "a holder with at least the proposal threshold could not propose the veto";
    assert proposalProposer(id) == e.msg.sender,
        "the veto proposal does not record its proposer";
    assert to_mathint(proposalSnapshot(id)) == to_mathint(e.block.timestamp),
        "the veto's vote does not open when it is proposed";
    assert to_mathint(proposalDeadline(id)) == e.block.timestamp + votingPeriod(),
        "the veto's vote does not run for the voting period";
}

/*
 * Once the veto has passed (its state is Succeeded), anyone's execute
 * succeeds and the Delay's txNonce becomes n, for any n the Delay accepts
 * (txNonce < n <= queueNonce). Holds under the deployed wiring above.
 */
rule passedVetoExecutes(uint256 n, bytes32 descriptionHash) {
    env e;
    require e.msg.value == 0;
    vetoPathWired();
    require delay.txNonce() < n;
    require n <= delay.queueNonce();

    uint256 id = vetoProposalId(roles, delay, n, descriptionHash);
    require state(e, id) == IGovernor.ProposalState.Succeeded;

    executeVeto@withrevert(e, roles, delay, n, descriptionHash);

    assert !lastReverted,
        "a veto that passed could not be executed";
    assert delay.txNonce() == n,
        "executing the veto did not set the Delay's txNonce";
}
