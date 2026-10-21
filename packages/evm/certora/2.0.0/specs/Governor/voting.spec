/*
 * Governor vote counting: through each of the five voting functions, a
 * proposal's tally grows by exactly the voter's votes at its snapshot, so an
 * account with no votes at the snapshot moves nothing.
 *
 * The Governor is the deployed TermFinanceGovernor under
 * TermFinanceGovernorSettingsHarness, which adds only view getters, with its
 * token linked to TermToken. The Governor's vote count is summarized as an
 * arbitrary value per account and timepoint; governorVotesAreTermPastVotes
 * (GV-4) shows it is TERM's getPastVotes.
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

/// The three voting functions whose voter is the caller.
definition isDirectVote(method f) returns bool =
    f.selector == sig:castVote(uint256, uint8).selector ||
    f.selector == sig:castVoteWithReason(uint256, uint8, string).selector ||
    f.selector == sig:castVoteWithReasonAndParams(uint256, uint8, string, bytes).selector;

/// The two whose voter is named in the call.
definition isVoteBySig(method f) returns bool =
    f.selector == sig:castVoteBySig(uint256, uint8, address, bytes).selector ||
    f.selector == sig:castVoteWithReasonAndParamsBySig(uint256, uint8, address, string, bytes, bytes).selector;

/*
 * For any proposal: if the caller voted on it in this call, its tally grew by
 * exactly the caller's votes at its snapshot; otherwise its tally did not
 * move. An account with no votes at the snapshot adds nothing.
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
 * A caller with votes at the snapshot can vote, and its vote moves the tally,
 * so the rules above are not vacuous.
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
