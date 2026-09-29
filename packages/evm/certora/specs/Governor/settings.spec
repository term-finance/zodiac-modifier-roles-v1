/*
 * TermFinanceGovernor: the Governor has no settings functions, so nobody can
 * change its settings.
 *
 * The Governor is the deployed code: TermFinanceGovernor
 * 0x2B715634134220ffeEE9458b4e34E41A41418607, verified source in
 * certora/vendor/TermFinanceGovernor (OpenZeppelin v5.2.0, solc 0.8.20),
 * inherited unmodified by TermFinanceGovernorSettingsHarness, which adds only
 * view getters.
 *
 * TermFinanceGovernor builds on Governor, GovernorVotes and
 * GovernorCountingSimple only. It does not use GovernorSettings (the
 * extension with setVotingDelay, setVotingPeriod and setProposalThreshold),
 * GovernorVotesQuorumFraction (updateQuorumNumerator) or
 * GovernorTimelockControl (updateTimelock). Its settings are:
 *
 *   setting               value             where it lives
 *   votingDelay           0                 code (TermFinanceGovernor.sol:16)
 *   votingPeriod          22 hours          code (TermFinanceGovernor.sol:20)
 *   proposalThreshold     1,000 TERM        code (TermFinanceGovernor.sol:36)
 *   quorumNumerator       1                 code (TermFinanceGovernor.sol:24)
 *   quorumDenominator     100               code (TermFinanceGovernor.sol:28)
 *   quorum(t)             1% of TERM's      code (TermFinanceGovernor.sol:43)
 *                         supply at t
 *   token                 TERM              immutable (GovernorVotes.sol:17)
 *   executor              the Governor      code (Governor.sol:679): no timelock
 *   proposalNeedsQueuing  false             code (Governor.sol:215)
 *   COUNTING_MODE         "support=bravo&quorum=for,abstain"
 *                                           code (GovernorCountingSimple.sol:34)
 *   version               "1"               code (Governor.sol:109)
 *   name                  "TermFinanceGovernor"
 *                                           storage (Governor.sol:48), written
 *                                           only by the constructor
 *
 * Four rules make the claim:
 *
 *   governorWriteFunctionsAreTheKnownFourteen
 *     the Governor's write functions are exactly the fourteen listed, none
 *     of them a setter. If one is ever added, this rule fails.
 *   queueAlwaysReverts
 *     queue, one of the fourteen, never succeeds: there is no timelock, so
 *     the Governor has no queuing to do.
 *   governorSettingsNeverChange
 *     over every other write function, for any caller and any arguments,
 *     every setting above reads the same afterwards. This holds for a
 *     function added later too.
 *   governorSettingsAreTheDeployedValues
 *     in every state, the settings in code return the values in the table.
 *     They are compiled in, not stored, so no storage write could move them.
 *
 * Modelling notes.
 *   - The Governor reads TERM through its immutable `_token`, which the conf
 *     links to TermToken. As in veto.spec, the DISPATCH list sends clock,
 *     getPastVotes and getPastTotalSupply to TermToken, where every call
 *     through `_token` lands on chain.
 *   - execute and relay call arbitrary addresses taken from calldata. Those
 *     calls are havoced with HAVOC_ECF: they may do anything to every
 *     contract but the Governor. What they cannot do directly is write the
 *     Governor's storage, and a call back into the Governor is itself one of
 *     the write functions governorSettingsNeverChange covers, so a reentrant
 *     call changes no setting either. HAVOC_ALL would also havoc `_name`,
 *     which no Governor code writes after construction, and fail the rule
 *     for a reason the code does not have. Every setting but `name` is in
 *     code or an immutable, so for those the havoc mode makes no difference.
 *   - loop_iter 1 with optimistic_loop: execute and propose are checked for
 *     one-action proposals, and the vote-by-signature path for short
 *     signatures. No loop body in the Governor writes a setting, and all but
 *     `name` are not in storage at all (governorSettingsAreTheDeployedValues
 *     holds in every state), so more iterations cannot move them.
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

    // The Governor's reads of TERM through `_token` that the link leaves
    // unresolved (GovernorVotes.sol:35 and :62, TermFinanceGovernor.sol:44),
    // and the arbitrary calls of execute and relay (Governor.sol:447-458,
    // :670-673). See the modelling notes for HAVOC_ECF.
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

/// onlyGovernance: callable only by the Governor itself, so only as an
/// action of an executed proposal. It makes one call out and writes nothing.
definition isRelay(method f) returns bool =
    f.selector == sig:relay(address, uint256, bytes).selector;

/// Token-receipt hooks: each returns its own selector and writes nothing.
definition isTokenReceiver(method f) returns bool =
    f.selector == sig:onERC721Received(address, address, uint256, bytes).selector ||
    f.selector == sig:onERC1155Received(address, address, uint256, uint256, bytes).selector ||
    f.selector == sig:onERC1155BatchReceived(address, address, uint256[], uint256[], bytes).selector;

/*
 * The Governor's write functions are exactly these fourteen. The Prover
 * checks `receive` (Governor.sol:83, which accepts ETH and writes nothing) as
 * the fallback entry; the Governor declares no `fallback`, so any other
 * calldata reverts.
 *
 *   proposal lifecycle   propose, queue, execute, cancel
 *   voting               castVote, castVoteWithReason,
 *                        castVoteWithReasonAndParams, castVoteBySig,
 *                        castVoteWithReasonAndParamsBySig
 *   governance only      relay
 *   token receipt        onERC721Received, onERC1155Received,
 *                        onERC1155BatchReceived
 *   ETH receipt          receive
 *
 * None of them is a setter. If a function is ever added, this rule fails.
 *
 * The call is made with @withrevert, so queue, which always reverts, is
 * still enumerated.
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
 * queue always reverts, for any caller, any arguments and any state.
 * TermFinanceGovernor does not override _queueOperations, which returns 0
 * (Governor.sol:390-398), and queue reverts with GovernorQueueNotImplemented
 * whenever it does (Governor.sol:367-371). A proposal goes straight from
 * Succeeded to execute.
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
 * For every write function of the Governor, including relay called by the
 * Governor itself as a proposal action, any caller, any arguments and any
 * starting state: every setting reads the same after a successful call as
 * before it.
 *
 * queue is left out: it never succeeds (queueAlwaysReverts), so there is no
 * successful call to check, and the sanity check would flag it as vacuous.
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
    // TERM's clock is the block timestamp (TermToken.sol:81-83), and
    // getPastTotalSupply only answers for timepoints before it.
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
