/*
 * Veto end to end: a TERM holder proposes the veto, a TERM holder votes it
 * through, anyone executes it once the vote has ended, and the Delay's
 * txNonce becomes n. The proposal starts with no votes, so the Governor's own
 * counting of TERM votes is what passes it.
 *
 * The veto is one action: the Roles Modifier's execTransactionWithRole(Delay,
 * 0, setTxNonce(n), Call, 1, true). The scene is veto.spec's, except that the
 * DelayOwnerSafe is ForwardingAvatar, a stand-in that forwards the Roles
 * Modifier's call into the Delay (DelayTarget). delayOwnerSafeLandsTheVeto
 * (GV-3) shows the real Safe v1.4.1 lands the veto.
 */

using TermToken as termToken;
using RolesHarness as roles;
using SetTxNonceGuard as setTxNonceGuard;
using ForwardingAvatar as avatar;
using DelayTarget as delay;

methods {
    function proposalSnapshot(uint256) external returns (uint256) envfree;
    function votingPeriod() external returns (uint256) envfree;
    function proposalVotes(uint256) external returns (uint256, uint256, uint256) envfree;
    function hasVoted(uint256, address) external returns (bool) envfree;
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

    function avatar.modules(address) external returns (address) envfree;
    function avatar.delay() external returns (address) envfree;

    function delay.owner() external returns (address) envfree;
    function delay.txNonce() external returns (uint256) envfree;
    function delay.queueNonce() external returns (uint256) envfree;

    // The Governor's call to its proposal's target, and its reads of TERM
    // through `_token`.
    unresolved external in TermFinanceGovernorHarness._ => DISPATCH [
        RolesHarness.execTransactionWithRole(address, uint256, bytes, Enum.Operation, uint16, bool),
        TermToken.clock(),
        TermToken.getPastVotes(address, uint256),
        TermToken.getPastTotalSupply(uint256)
    ] default HAVOC_ALL;
}

/// Head of the Roles Modifier's and the Safe's module lists.
definition SENTINEL() returns address = 0x1;

/// The role the veto runs under.
definition ROLE() returns uint16 = 1;

/// A proposal's three tallies, summed.
function tally(uint256 proposalId) returns mathint {
    uint256 againstVotes;
    uint256 forVotes;
    uint256 abstainVotes;
    againstVotes, forVotes, abstainVotes = proposalVotes(proposalId);
    return againstVotes + forVotes + abstainVotes;
}

/*
 * The deployed wiring of the veto path:
 *   - SetTxNonceGuard is the Roles Modifier's guard, pointed at this Delay;
 *   - role 1 is scoped to the Delay, with setTxNonce allowed and no value or
 *     delegatecall;
 *   - the Governor is an enabled module and a member of role 1;
 *   - the Roles Modifier's target is ForwardingAvatar, the DelayOwnerSafe,
 *     which has the Roles Modifier as a module and owns the Delay.
 */
function vetoPathWired() {
    require roles.guard() == setTxNonceGuard;
    require setTxNonceGuard.delay() == delay;

    require roles.target() == avatar;
    require avatar.delay() == delay;
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

    // The DelayOwnerSafe has Roles enabled as a module, and owns the Delay.
    require roles != SENTINEL();
    require avatar.modules(roles) != 0;
    require delay.owner() == avatar;
}

/*
 * A holder proposes the veto for a nonce n the Delay accepts, a holder votes
 * for it, and once the vote has ended anyone executes it: the proposal is
 * Succeeded, execute succeeds, and the Delay's txNonce is n.
 */
rule termHoldersVetoThroughTheGovernor(uint256 n, string proposalText) {
    env ePropose;
    env eVote;
    env eExecute;
    require ePropose.msg.value == 0 && eVote.msg.value == 0 && eExecute.msg.value == 0;

    // Proposal, then vote, then execution, as the Governor's clock runs.
    require ePropose.block.timestamp > 0;
    require eVote.block.timestamp > ePropose.block.timestamp;
    require to_mathint(eVote.block.timestamp) <= ePropose.block.timestamp + votingPeriod();
    require to_mathint(eExecute.block.timestamp) > ePropose.block.timestamp + votingPeriod();
    require to_mathint(eExecute.block.timestamp) < 2^48;

    vetoPathWired();

    // A nonce the Delay accepts from its owner.
    require delay.txNonce() < n && n <= delay.queueNonce();

    // The proposal does not exist yet and has no votes.
    bytes32 descriptionHash = descriptionHashOf(proposalText);
    uint256 id = vetoProposalId(roles, delay, n, descriptionHash);
    require proposalSnapshot(id) == 0;
    require tally(id) == 0;
    require !hasVoted(id, eVote.msg.sender);

    // A holder proposes the veto.
    require descriptionAllowedFor(ePropose.msg.sender, proposalText);
    proposeVeto(ePropose, roles, delay, n, proposalText);

    // A holder votes for it. 1 is VoteType.For (GovernorCountingSimple.sol).
    castVote(eVote, id, 1);

    // The vote has ended and the veto passed, through the votes cast above.
    IGovernor.ProposalState passed = state(eExecute, id);

    // Anyone executes it.
    executeVeto(eExecute, roles, delay, n, descriptionHash);

    satisfy passed == IGovernor.ProposalState.Succeeded && delay.txNonce() == n,
        "a TERM holder's veto could not be proposed, voted through and executed to move the Delay's txNonce";
}
