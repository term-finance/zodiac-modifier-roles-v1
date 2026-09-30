/*
 * TermFinanceGovernor: only TERM holders can vote. A vote adds exactly the
 * voter's votes at the proposal's snapshot to that proposal's tally, so an
 * account with no TERM votes at the snapshot adds nothing, and nothing but a
 * vote moves a tally.
 *
 * The Governor counts votes with GovernorCountingSimple
 * (GovernorCountingSimple.sol:76-99): an account votes at most once per
 * proposal, and its vote adds `totalWeight` to one of againstVotes, forVotes
 * or abstainVotes. `totalWeight` is _getVotes(voter, proposalSnapshot(id))
 * (Governor.sol:648), which GovernorVotes reads from TERM's getPastVotes
 * (GovernorVotes.sol:57-63).
 *
 * Rules:
 *
 *   directVoteCountsOnlyTheVotersVotes
 *     castVote, castVoteWithReason and castVoteWithReasonAndParams, where the
 *     voter is the caller: every proposal's tally moves by exactly the
 *     caller's votes at that proposal's snapshot if the caller voted on it,
 *     and not at all otherwise
 *   voteBySigCountsOnlyTheVotersVotes
 *   voteWithReasonAndParamsBySigCountsOnlyTheVotersVotes
 *     the same for the two by-signature functions, where the voter is the
 *     account named in the call, whoever submits it
 *   termHolderVoteCounts
 *     a caller with votes at the snapshot can vote, and its vote moves the
 *     tally (witness)
 *
 * nothingButAVoteMovesATally, the rule that nothing but a vote moves a tally,
 * is in tallies.spec, without this file's ghost and internal summaries.
 * Together they cover every write function of the Governor: the five voting
 * functions are this file's first three rules', queue never succeeds (GS-4
 * queueAlwaysReverts, settings.spec), and tallies.spec takes the rest.
 *
 * The contracts are the deployed code, as in settings.spec: TermFinanceGovernor
 * 0x2B715634134220ffeEE9458b4e34E41A41418607 through
 * TermFinanceGovernorSettingsHarness, which adds only view getters, so the
 * write functions quantified over are exactly the deployed Governor's. Its
 * token is linked to TermToken.
 *
 * Modelling notes.
 *   - _getVotes (GovernorVotes.sol:57-63) is summarised as an arbitrary value
 *     per account and timepoint, as in proposalThreshold.spec, and the rules
 *     state a vote's weight against that value. GV-4
 *     `governorVotesAreTermPastVotes` (veto.spec) shows the Governor's vote
 *     count is TERM's getPastVotes.
 *   - SignatureChecker.isValidSignatureNow is summarised as an arbitrary
 *     boolean. If it returns false the by-signature functions revert, and if
 *     true they count the named voter's votes. Whether a signature is valid
 *     is not what these rules are about; that a vote counts only the named
 *     voter's votes, whoever submits it, is.
 *   - As in settings.spec, the arbitrary calls of execute and relay are
 *     havoced with HAVOC_ECF: they may do anything to every contract but the
 *     Governor. A call back into the Governor is itself one of the write
 *     functions these rules cover.
 */

using TermToken as termToken;

methods {
    function proposalVotes(uint256) external returns (uint256, uint256, uint256) envfree;
    function hasVoted(uint256, address) external returns (bool) envfree;
    function proposalSnapshot(uint256) external returns (uint256) envfree;

    function GovernorVotes._getVotes(address account, uint256 timepoint, bytes memory) internal returns (uint256)
        => votesAt[account][timepoint];

    function SignatureChecker.isValidSignatureNow(address, bytes32, bytes memory) internal returns (bool) => NONDET;

    unresolved external in TermFinanceGovernorSettingsHarness._ => DISPATCH [
        TermToken.clock(),
        TermToken.getPastVotes(address, uint256),
        TermToken.getPastTotalSupply(uint256)
    ] default HAVOC_ECF;
}

/// The Governor's vote count for an account at a timepoint.
ghost mapping(address => mapping(uint256 => uint256)) votesAt;

/// A proposal's three tallies, summed.
function tally(uint256 proposalId) returns mathint {
    uint256 againstVotes;
    uint256 forVotes;
    uint256 abstainVotes;
    againstVotes, forVotes, abstainVotes = proposalVotes(proposalId);
    return againstVotes + forVotes + abstainVotes;
}

/// The three voting functions whose voter is the caller (Governor.sol:532-561).
definition isDirectVote(method f) returns bool =
    f.selector == sig:castVote(uint256, uint8).selector ||
    f.selector == sig:castVoteWithReason(uint256, uint8, string).selector ||
    f.selector == sig:castVoteWithReasonAndParams(uint256, uint8, string, bytes).selector;

/// The two whose voter is named in the call (Governor.sol:565-620).
definition isVoteBySig(method f) returns bool =
    f.selector == sig:castVoteBySig(uint256, uint8, address, bytes).selector ||
    f.selector == sig:castVoteWithReasonAndParamsBySig(uint256, uint8, address, string, bytes, bytes).selector;

/*
 * For any proposal: if the caller voted on it in this call, its tally grew by
 * exactly the caller's votes at its snapshot; otherwise its tally did not
 * move. An account with no votes at the snapshot adds nothing. Checked once
 * per function.
 */
rule directVoteCountsOnlyTheVotersVotes(method f, calldataarg args, uint256 proposalId)
    filtered { f -> isDirectVote(f) }
{
    env e;
    mathint tallyBefore = tally(proposalId);
    bool votedBefore = hasVoted(proposalId, e.msg.sender);
    uint256 snapshot = proposalSnapshot(proposalId);

    f(e, args);

    bool votedNow = !votedBefore && hasVoted(proposalId, e.msg.sender);
    assert tally(proposalId) == tallyBefore + (votedNow ? to_mathint(votesAt[e.msg.sender][snapshot]) : 0),
        "a vote moved a tally by something other than the voter's votes at the snapshot";
}

/*
 * The same for castVoteBySig, where the voter is the account named in the
 * call. Whoever submits the signature, the vote counts the named voter's
 * votes and nobody else's.
 */
rule voteBySigCountsOnlyTheVotersVotes(
    uint256 proposalId, uint256 votedOn, uint8 support, address voter, bytes signature
) {
    env e;
    mathint tallyBefore = tally(proposalId);
    bool votedBefore = hasVoted(proposalId, voter);
    uint256 snapshot = proposalSnapshot(proposalId);

    castVoteBySig(e, votedOn, support, voter, signature);

    bool votedNow = !votedBefore && hasVoted(proposalId, voter);
    assert tally(proposalId) == tallyBefore + (votedNow ? to_mathint(votesAt[voter][snapshot]) : 0),
        "a vote by signature moved a tally by something other than the named voter's votes";
}

/* And for castVoteWithReasonAndParamsBySig. */
rule voteWithReasonAndParamsBySigCountsOnlyTheVotersVotes(
    uint256 proposalId, uint256 votedOn, uint8 support, address voter,
    string reason, bytes params, bytes signature
) {
    env e;
    mathint tallyBefore = tally(proposalId);
    bool votedBefore = hasVoted(proposalId, voter);
    uint256 snapshot = proposalSnapshot(proposalId);

    castVoteWithReasonAndParamsBySig(e, votedOn, support, voter, reason, params, signature);

    bool votedNow = !votedBefore && hasVoted(proposalId, voter);
    assert tally(proposalId) == tallyBefore + (votedNow ? to_mathint(votesAt[voter][snapshot]) : 0),
        "a vote by signature moved a tally by something other than the named voter's votes";
}

/*
 * The rules above are not achieved by nothing working: a caller with votes
 * at the snapshot can vote, and its vote moves the tally. Witness.
 */
rule termHolderVoteCounts(uint256 proposalId, uint8 support) {
    env e;
    uint256 snapshot = proposalSnapshot(proposalId);
    require votesAt[e.msg.sender][snapshot] > 0;
    mathint tallyBefore = tally(proposalId);

    castVote@withrevert(e, proposalId, support);

    satisfy !lastReverted && tally(proposalId) > tallyBefore,
        "a caller with votes at the snapshot cannot vote";
}
