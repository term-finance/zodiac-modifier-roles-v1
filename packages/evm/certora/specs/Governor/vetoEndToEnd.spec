/*
 * TermFinanceGovernor: a TERM holder can veto a Delay Modifier transaction,
 * from the proposal to the Delay's txNonce, in one rule.
 *
 * A holder proposes the veto, a holder votes it through, anyone executes it
 * once the vote has ended, and the Delay's txNonce becomes n. veto.spec
 * follows the same path in pieces: GV-1 proposes, GV-2 starts from a veto
 * whose state is already Succeeded, and GV-3 and RL-1 take it from the
 * DelayOwnerSafe and from Roles into the Delay. No rule there derives the
 * pass from votes. This rule chains them, with the pass coming from the
 * Governor's own vote counting over TERM's checkpoints.
 *
 * The veto is the runbook's proposal: one action, calling the Roles Modifier
 * with execTransactionWithRole(Delay, 0, setTxNonce(n), Call, 1, true).
 *
 *     Governor --execTransactionWithRole--> Roles (+ SetTxNonceGuard)
 *        --exec--> DelayOwnerSafe --call--> Delay.setTxNonce
 *
 * The scene is veto.spec's, with one change. The Governor, TERM, the Roles
 * Modifier and SetTxNonceGuard are the deployed code, wired as in veto.spec.
 * The DelayOwnerSafe is ForwardingAvatar, not RecordingAvatar, and the Delay
 * (DelayTarget, the vendored Delay v1.0.1) is linked into it, so the veto's
 * module call goes on into the Delay and the rule can read the Delay's own
 * state afterwards. ForwardingAvatar forwards the way the Safe's module path
 * does (see its header). GV-3 (specs/SafeV141/vetoLandsOnDelay.spec) shows
 * the real Safe v1.4.1 returns true for that module call and sets the Delay's
 * txNonce, which is what the stand-in does here.
 *
 * Modelling notes.
 *   - The real Safe v1.4.1 cannot be in this scene. With it inlined behind
 *     the Governor's dispatched call to Roles, the Prover (certora-cli
 *     7.31.0) stops with an internal error at the Safe's call to the Delay
 *     (certora/helpers/RecordingAvatar.sol). ForwardingAvatar makes that call
 *     as a typed call that the `ForwardingAvatar:delay` link resolves, with
 *     no DISPATCH entry. Roles' setTxNonceLands.spec declares a DISPATCH
 *     entry for its other forwards; it is left out here, since a second
 *     DISPATCH entry behind the Governor's is what stopped the Prover with
 *     the real Safe. The veto never takes those forwards.
 *   - Everything else is as in veto.spec: the Governor's DISPATCH list sends
 *     its reads of TERM and its call to Roles where they land on chain, and
 *     the conf unrolls copy loops 32 times for propose.
 *   - The proposal, the vote and the execution are three calls with three
 *     envs. TERM's clock is the block timestamp (TermToken.sol:81-83), so
 *     the envs' timestamps order them: the vote opens at once after the
 *     proposal (votingDelay is 0) and runs for the voting period (22 hours),
 *     and execution comes after it ends.
 *   - The Governor's storage starts arbitrary. The rule starts from a
 *     proposal that does not exist and has no votes, as it would on chain,
 *     so a vote cannot pass on tallies that were already there.
 *   - A satisfy, like DV-1 (specs/Delay/vetoSignedPath.spec). It shows the
 *     whole path can run on the real code, a holder's vote carrying the veto
 *     through to the Delay. It does not say every holder can: which holders
 *     have the votes is TERM's state, and the Governor's vote thresholds
 *     (the proposal threshold, GP-1, and the 1% quorum) decide it.
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

    // The Governor's call to its proposal's target (Governor.sol:447-458),
    // and its reads of TERM through `_token` that the link leaves unresolved
    // (GovernorVotes.sol:35 and :62, TermFinanceGovernor.sol:44), as in
    // veto.spec.
    unresolved external in TermFinanceGovernorHarness._ => DISPATCH [
        RolesHarness.execTransactionWithRole(address, uint256, bytes, Enum.Operation, uint16, bool),
        TermToken.clock(),
        TermToken.getPastVotes(address, uint256),
        TermToken.getPastTotalSupply(uint256)
    ] default HAVOC_ALL;
}

/// Head of the Roles Modifier's module list, and of the Safe's: neither can
/// send transactions, so the Prover must not place a caller there.
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
 * The deployed wiring of the veto path, as the runbook sets it up and the
 * verification plan checks it on chain (veto.spec's vetoPathWired), plus the
 * DelayOwnerSafe's side, which veto.spec leaves to GV-3:
 *   - SetTxNonceGuard is Roles' guard and is pointed at this Delay;
 *   - role 1 is scoped to the Delay (scopeTarget) with setTxNonce allowed
 *     and no value or delegatecall (scopeAllowFunction, options None);
 *   - the Governor is an enabled module on Roles and a member of role 1;
 *   - Roles' target is the DelayOwnerSafe, here ForwardingAvatar, with Roles
 *     enabled as a module on it, and it owns the Delay.
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
