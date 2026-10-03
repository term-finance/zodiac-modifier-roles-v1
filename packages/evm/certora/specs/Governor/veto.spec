/*
 * Governor veto: TERM holders can propose the veto, and once it has passed
 * anyone can execute it and the Roles Modifier forwards it to the
 * DelayOwnerSafe.
 *
 * The veto is one action: the Roles Modifier's execTransactionWithRole(Delay,
 * 0, setTxNonce(n), Call, 1, true). The scene is the deployed
 * TermFinanceGovernor (TermFinanceGovernorHarness) with its token linked to
 * TermToken, the Roles Modifier (RolesHarness) with SetTxNonceGuard, and
 * DelayTarget as the Delay. The DelayOwnerSafe is RecordingAvatar, a stand-in
 * that records the module call and returns true; delayOwnerSafeLandsTheVeto
 * (GV-3) shows the real Safe v1.4.1 lands the veto.
 */

using TermToken as termToken;
using RolesHarness as roles;
using SetTxNonceGuard as setTxNonceGuard;
using RecordingAvatar as avatar;
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

    function avatar.callCount() external returns (uint256) envfree;
    function avatar.lastCaller() external returns (address) envfree;
    function avatar.lastTo() external returns (address) envfree;
    function avatar.lastValue() external returns (uint256) envfree;
    function avatar.lastDataLength() external returns (uint256) envfree;
    function avatar.lastDataSelector() external returns (uint32) envfree;
    function avatar.lastDataWord() external returns (uint256) envfree;
    function avatar.lastOperation() external returns (uint8) envfree;

    // The Governor's call to its proposal's target, and its reads of TERM
    // through `_token`.
    unresolved external in TermFinanceGovernorHarness._ => DISPATCH [
        RolesHarness.execTransactionWithRole(address, uint256, bytes, Enum.Operation, uint16, bool),
        TermToken.clock(),
        TermToken.getPastVotes(address, uint256),
        TermToken.getPastTotalSupply(uint256)
    ] default HAVOC_ALL;
}

/// Head of the Roles Modifier's module list.
definition SENTINEL() returns address = 0x1;

/// The role the veto runs under.
definition ROLE() returns uint16 = 1;

/*
 * The deployed wiring of the veto path through the Roles Modifier:
 *   - SetTxNonceGuard is the Roles Modifier's guard, pointed at this Delay;
 *   - role 1 is scoped to the Delay, with setTxNonce allowed and no value or
 *     delegatecall;
 *   - the Governor is an enabled module and a member of role 1;
 *   - the Roles Modifier's target is RecordingAvatar, the DelayOwnerSafe.
 */
function vetoPathWired() {
    require roles.guard() == setTxNonceGuard;
    require setTxNonceGuard.delay() == delay;

    require roles.target() == avatar;
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

    require currentContract != SENTINEL();
    require roles.moduleEntry(currentContract) != 0;
    require roles.memberOf(ROLE(), currentContract);
}

/*
 * A caller with at least the proposal threshold of TERM votes (1,000 TERM) at
 * clock() - 1 can propose the veto, for any nonce n and any description
 * propose accepts from it, unless that exact proposal already exists. The
 * proposal records the caller as proposer, and its vote opens at once and
 * runs for the voting period. So callerBelowProposalThresholdCannotPropose is
 * not vacuous.
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
 * succeeds, and the Roles Modifier forwards the veto to the DelayOwnerSafe as
 * exactly one module call, execTransactionFromModule(Delay, 0, setTxNonce(n),
 * Call), for any n. So executeOnlyRunsSucceededProposals is not vacuous.
 */
rule passedVetoReachesTheDelayOwnerSafe(uint256 n, bytes32 descriptionHash) {
    env e;
    require e.msg.value == 0;
    vetoPathWired();
    require avatar.callCount() == 0;

    uint256 id = vetoProposalId(roles, delay, n, descriptionHash);
    require state(e, id) == IGovernor.ProposalState.Succeeded;

    executeVeto@withrevert(e, roles, delay, n, descriptionHash);

    assert !lastReverted,
        "a veto that passed could not be executed";
    assert avatar.callCount() == 1,
        "executing the veto did not make exactly one module call on the DelayOwnerSafe";
    assert avatar.lastCaller() == roles,
        "the module call did not come from the Roles Modifier";
    // Operation 0 is Enum.Operation.Call.
    assert avatar.lastTo() == delay && avatar.lastValue() == 0 && avatar.lastOperation() == 0,
        "the module call is not a zero-value Call to the Delay";
    assert avatar.lastDataLength() == 36
        && avatar.lastDataSelector() == sig:DelayTarget.setTxNonce(uint256).selector
        && avatar.lastDataWord() == n,
        "the module call's data is not setTxNonce(n)";
}

/*
 * For any account and any timepoint before the current clock, the Governor's
 * getVotes returns TERM's getPastVotes. So the votes the Governor rules count
 * are TERM votes.
 */
rule governorVotesAreTermPastVotes(address account, uint256 timepoint) {
    env e;
    require e.msg.value == 0;
    // TERM's clock is the block timestamp (TermToken.sol:81-83).
    require to_mathint(e.block.timestamp) < 2^48;
    require timepoint < e.block.timestamp;

    uint256 governorVotes = getVotes(e, account, timepoint);
    uint256 termVotes = termToken.getPastVotes(e, account, timepoint);

    assert governorVotes == termVotes,
        "the Governor's vote count differs from TERM's past votes";
}
