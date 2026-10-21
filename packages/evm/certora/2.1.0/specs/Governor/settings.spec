/*
 * Governor entry points and settings: the Governor's write functions are
 * exactly fourteen known functions, and none of them changes the voting
 * token, proposal threshold, voting threshold or quorum.
 *
 * The Governor is the deployed TermFinanceGovernor
 * (certora/vendor/TermFinanceGovernor) under
 * TermFinanceGovernorSettingsHarness, which adds only view getters, with its
 * token linked to TermToken.
 */

using TermToken as termToken;

methods {
    function nameHash() external returns (bytes32) envfree;
    function versionHash() external returns (bytes32) envfree;
    function countingModeHash() external returns (bytes32) envfree;
    function executor() external returns (address) envfree;
    function votingDelay() external returns (uint256) envfree;
    function votingPeriod() external returns (uint256) envfree;
    function proposalThreshold() external returns (uint256) envfree;
    function quorumNumerator() external returns (uint256) envfree;
    function quorumDenominator() external returns (uint256) envfree;
    function proposalNeedsQueuing(uint256) external returns (bool) envfree;
    function token() external returns (address) envfree;
    function hashProposal(address[], uint256[], bytes[], bytes32) external returns (uint256) envfree;
    function proposalProposer(uint256) external returns (address) envfree;
    function proposalEta(uint256) external returns (uint256) envfree;
    function proposalVotes(uint256) external returns (uint256, uint256, uint256) envfree;
    function voteSucceeded(uint256) external returns (bool) envfree;

    // The Governor's reads of TERM through `_token`, and the arbitrary calls
    // of execute and relay.
    unresolved external in TermFinanceGovernorSettingsHarness._ => DISPATCH [
        TermToken.clock(),
        TermToken.getPastVotes(address, uint256),
        TermToken.getPastTotalSupply(uint256)
    ] default HAVOC_ECF;
}

/* ------------------------------------------------------------------------
 * 1. Every write function is accounted for, and none is a setter
 * --------------------------------------------------------------------- */

definition isProposalLifecycle(method f) returns bool =
    f.selector == sig:propose(address[], uint256[], bytes[], string).selector ||
    f.selector == sig:queue(address[], uint256[], bytes[], bytes32).selector ||
    f.selector == sig:execute(address[], uint256[], bytes[], bytes32).selector ||
    f.selector == sig:cancel(address[], uint256[], bytes[], bytes32).selector;

definition isVoting(method f) returns bool =
    f.selector == sig:castVote(uint256, uint8).selector ||
    f.selector == sig:castVoteWithReason(uint256, uint8, string).selector ||
    f.selector == sig:castVoteWithReasonAndParams(uint256, uint8, string, bytes).selector ||
    f.selector == sig:castVoteBySig(uint256, uint8, address, bytes).selector ||
    f.selector == sig:castVoteWithReasonAndParamsBySig(uint256, uint8, address, string, bytes, bytes).selector;

definition isQueue(method f) returns bool =
    f.selector == sig:queue(address[], uint256[], bytes[], bytes32).selector;

/// relay: onlyGovernance, so callable only by the Governor itself.
definition isRelay(method f) returns bool =
    f.selector == sig:relay(address, uint256, bytes).selector;

/// Token-receipt hooks: each returns its own selector and writes nothing.
definition isTokenReceiver(method f) returns bool =
    f.selector == sig:onERC721Received(address, address, uint256, bytes).selector ||
    f.selector == sig:onERC1155Received(address, address, uint256, uint256, bytes).selector ||
    f.selector == sig:onERC1155BatchReceived(address, address, uint256[], uint256[], bytes).selector;

/*
 * The Governor has no write functions besides these fourteen. The Prover
 * checks `receive` as the fallback entry; the Governor declares no
 * `fallback`.
 *   proposal lifecycle   propose, queue, execute, cancel
 *   voting               castVote, castVoteWithReason,
 *                        castVoteWithReasonAndParams, castVoteBySig,
 *                        castVoteWithReasonAndParamsBySig
 *   governance only      relay
 *   token receipt        onERC721Received, onERC1155Received,
 *                        onERC1155BatchReceived
 *   ETH receipt          receive
 */
rule governorWriteFunctionsAreTheKnownFourteen(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure }
{
    env e;

    f@withrevert(e, args);

    assert f.isFallback || isProposalLifecycle(f) || isVoting(f) || isRelay(f) || isTokenReceiver(f),
        "the Governor has a write function that is not one of the known fourteen";
}

/*
 * Every call to queue reverts, so it never sets a proposal's eta.
 */
rule queueAlwaysReverts(address[] targets, uint256[] values, bytes[] calldatas, bytes32 descriptionHash) {
    env e;

    queue@withrevert(e, targets, values, calldatas, descriptionHash);

    assert lastReverted, "queue succeeded on a Governor with no queuing";
}

/* ------------------------------------------------------------------------
 * 2. No write function changes a setting
 * --------------------------------------------------------------------- */

/*
 * No write function changes a setting, whoever calls it and with whatever
 * arguments, including relay called by the Governor as an action of a passed
 * proposal. queue is left out: it never succeeds (queueAlwaysReverts).
 */
rule governorSettingsNeverChange(method f, calldataarg args, uint256 proposalId)
    filtered { f -> !f.isView && !f.isPure && !isQueue(f) }
{
    env e;

    bytes32 nameBefore = nameHash();
    bytes32 versionBefore = versionHash();
    bytes32 countingModeBefore = countingModeHash();
    address executorBefore = executor();
    address tokenBefore = token();
    uint256 votingDelayBefore = votingDelay();
    uint256 votingPeriodBefore = votingPeriod();
    uint256 proposalThresholdBefore = proposalThreshold();
    uint256 quorumNumeratorBefore = quorumNumerator();
    uint256 quorumDenominatorBefore = quorumDenominator();
    bool needsQueuingBefore = proposalNeedsQueuing(proposalId);

    f(e, args);

    assert nameHash() == nameBefore, "a Governor function changed name";
    assert versionHash() == versionBefore, "a Governor function changed version";
    assert countingModeHash() == countingModeBefore, "a Governor function changed COUNTING_MODE";
    assert executor() == executorBefore, "a Governor function changed the executor";
    assert token() == tokenBefore, "a Governor function changed the voting token";
    assert votingDelay() == votingDelayBefore, "a Governor function changed votingDelay";
    assert votingPeriod() == votingPeriodBefore, "a Governor function changed votingPeriod";
    assert proposalThreshold() == proposalThresholdBefore, "a Governor function changed proposalThreshold";
    assert quorumNumerator() == quorumNumeratorBefore, "a Governor function changed quorumNumerator";
    assert quorumDenominator() == quorumDenominatorBefore, "a Governor function changed quorumDenominator";
    assert proposalNeedsQueuing(proposalId) == needsQueuingBefore, "a Governor function changed proposalNeedsQueuing";
}

/* ------------------------------------------------------------------------
 * 3. The settings are compiled in
 * --------------------------------------------------------------------- */

/*
 * In every state of the Governor's storage, the settings in code return the
 * deployed values, and quorum at any past timepoint is 1% of TERM's total
 * supply at that timepoint. None of them reads Governor storage, so nothing
 * the Governor ever stores can change them.
 */
rule governorSettingsAreTheDeployedValues(uint256 proposalId, uint256 timepoint) {
    env e;
    // getPastTotalSupply only answers for timepoints before TERM's clock, the
    // block timestamp.
    require timepoint < e.block.timestamp;

    assert votingDelay() == 0, "votingDelay is not 0";
    assert votingPeriod() == 22 * 3600, "votingPeriod is not 22 hours";
    assert proposalThreshold() == 1000 * 10^18, "proposalThreshold is not 1,000 TERM";
    assert quorumNumerator() == 1, "quorumNumerator is not 1";
    assert quorumDenominator() == 100, "quorumDenominator is not 100";
    assert executor() == currentContract, "the executor is not the Governor itself";
    assert !proposalNeedsQueuing(proposalId), "a proposal needs queuing";
    assert to_mathint(quorum(e, timepoint)) == termToken.getPastTotalSupply(e, timepoint) / 100,
        "quorum is not 1% of TERM's past total supply";
}

/*
 * In every state, a proposal's vote succeeds exactly when its For votes are
 * strictly more than its Against votes (GovernorCountingSimple.sol:67). The
 * only stored data it reads is the tallies.
 */
rule votingThresholdIsTheDeployedRule(uint256 proposalId) {
    uint256 againstVotes;
    uint256 forVotes;
    uint256 abstainVotes;
    againstVotes, forVotes, abstainVotes = proposalVotes(proposalId);

    assert voteSucceeded(proposalId) <=> forVotes > againstVotes,
        "the vote does not succeed exactly when For votes are strictly over Against votes";
}

/* ------------------------------------------------------------------------
 * 4. cancel
 * --------------------------------------------------------------------- */

/*
 * A successful cancel came from the address recorded as the proposal's
 * proposer.
 */
rule onlyTheProposerCanCancel(
    address[] targets, uint256[] values, bytes[] calldatas, bytes32 descriptionHash
) {
    env e;
    uint256 proposalId = hashProposal(targets, values, calldatas, descriptionHash);
    address proposer = proposalProposer(proposalId);

    cancel@withrevert(e, targets, values, calldatas, descriptionHash);

    assert !lastReverted => e.msg.sender == proposer,
        "someone other than the proposer cancelled a proposal";
}

/*
 * The proposer can cancel, so the rule above is not vacuous.
 */
rule proposerCanCancel(
    address[] targets, uint256[] values, bytes[] calldatas, bytes32 descriptionHash
) {
    env e;
    uint256 proposalId = hashProposal(targets, values, calldatas, descriptionHash);
    require e.msg.sender == proposalProposer(proposalId);

    cancel@withrevert(e, targets, values, calldatas, descriptionHash);

    satisfy !lastReverted, "the proposer cannot cancel";
}

/* ------------------------------------------------------------------------
 * 5. receive
 * --------------------------------------------------------------------- */

persistent ghost bool wroteStorage;
persistent ghost bool madeAnyCall;
persistent ghost bool createdOrDestroyed;
persistent ghost bool callsItself;

hook ALL_SSTORE(uint loc, uint v) {
    wroteStorage = true;
}
hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength,
          uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
    if (addr == currentContract) {
        callsItself = true;
    }
}
hook CALLCODE(uint g, address addr, uint value, uint argsOffset, uint argsLength,
              uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
}
hook DELEGATECALL(uint g, address addr, uint argsOffset, uint argsLength,
                  uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
}
hook STATICCALL(uint g, address addr, uint argsOffset, uint argsLength,
                uint retOffset, uint retLength) uint rc {
    madeAnyCall = true;
}
hook CREATE1(uint value, uint offset, uint length) address v {
    createdOrDestroyed = true;
}
hook CREATE2(uint value, uint offset, uint length, bytes32 salt) address v {
    createdOrDestroyed = true;
}
hook SELFDESTRUCT(address a) {
    createdOrDestroyed = true;
}

/*
 * A successful receive writes no storage, makes no call of any kind and
 * creates or destroys no contract.
 */
rule receiveChangesNoState(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;
    require !wroteStorage;
    require !madeAnyCall;
    require !createdOrDestroyed;

    f@withrevert(e, args);

    assert !lastReverted => (!wroteStorage && !madeAnyCall && !createdOrDestroyed),
        "receive changed state";
}

/*
 * Some call to receive succeeds, so the rule above is not vacuous.
 */
rule receiveRuns(method f, calldataarg args)
    filtered { f -> f.isFallback }
{
    env e;

    f@withrevert(e, args);

    satisfy !lastReverted, "no call reaches receive";
}

/* ------------------------------------------------------------------------
 * 6. execute, relay and the token-receipt hooks
 * --------------------------------------------------------------------- */

/*
 * No proposal is ever Queued: the only write to a proposal's eta is in queue,
 * which never succeeds (queueAlwaysReverts).
 */
invariant noProposalIsQueued(uint256 proposalId)
    proposalEta(proposalId) == 0
    filtered { f -> !isQueue(f) }

/*
 * A successful execute ran a proposal whose state was Succeeded. execute also
 * accepts Queued, which noProposalIsQueued rules out.
 */
rule executeOnlyRunsSucceededProposals(
    address[] targets, uint256[] values, bytes[] calldatas, bytes32 descriptionHash
) {
    env e;
    uint256 proposalId = hashProposal(targets, values, calldatas, descriptionHash);
    requireInvariant noProposalIsQueued(proposalId);
    IGovernor.ProposalState stateBefore = state(e, proposalId);

    execute@withrevert(e, targets, values, calldatas, descriptionHash);

    assert !lastReverted => stateBefore == IGovernor.ProposalState.Succeeded,
        "execute ran a proposal that had not succeeded";
}

definition isExecute(method f) returns bool =
    f.selector == sig:execute(address[], uint256[], bytes[], bytes32).selector;

/*
 * No write function except execute and relay makes a call to the Governor.
 * With relayOnlyCallableByTheGovernor, relay runs only as an action of an
 * executed proposal.
 */
rule governorOnlyCallsItselfFromExecuteAndRelay(method f, calldataarg args)
    filtered { f -> !f.isView && !f.isPure && !isExecute(f) && !isRelay(f) }
{
    env e;
    require !callsItself;

    f@withrevert(e, args);

    assert !callsItself, "a function other than execute and relay called the Governor";
}

/*
 * A successful relay came from the Governor itself.
 */
rule relayOnlyCallableByTheGovernor(address target, uint256 value, bytes data) {
    env e;

    relay@withrevert(e, target, value, data);

    assert !lastReverted => e.msg.sender == currentContract,
        "relay succeeded for a caller other than the Governor";
}

/*
 * The Governor can relay, so the rule above is not vacuous.
 */
rule relayCanRun(address target, uint256 value, bytes data) {
    env e;
    require e.msg.sender == currentContract;

    relay@withrevert(e, target, value, data);

    satisfy !lastReverted, "the Governor cannot relay";
}

/*
 * A successful onERC721Received, onERC1155Received or onERC1155BatchReceived
 * writes no storage, makes no call of any kind and creates or destroys no
 * contract.
 */
rule tokenReceiptChangesNoState(method f, calldataarg args)
    filtered { f -> isTokenReceiver(f) }
{
    env e;
    require !wroteStorage;
    require !madeAnyCall;
    require !createdOrDestroyed;

    f@withrevert(e, args);

    assert !lastReverted => (!wroteStorage && !madeAnyCall && !createdOrDestroyed),
        "a token-receipt hook changed state";
}

/*
 * Each of the three can succeed, so the rule above is not vacuous.
 */
rule tokenReceiptRuns(method f, calldataarg args)
    filtered { f -> isTokenReceiver(f) }
{
    env e;

    f@withrevert(e, args);

    satisfy !lastReverted, "no call reaches the token-receipt hook";
}
